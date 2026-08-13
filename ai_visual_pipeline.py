import argparse
import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests
from gradio_client import Client
from huggingface_hub import InferenceClient


HF_IMAGE_MODEL = os.environ.get("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
POLLINATIONS_IMAGE_MODEL = os.environ.get("POLLINATIONS_IMAGE_MODEL", "flux").strip() or "flux"
POLLINATIONS_BASE_URL = os.environ.get("POLLINATIONS_BASE_URL", "https://gen.pollinations.ai").rstrip("/")
VIDEO_SPACE = os.environ.get("HF_VIDEO_SPACE_ID", "ShaundeOoO/ltx-2.3-fast").strip()
ROOT = Path("assets/ai_broll")
DEFAULT_ANIMATED = int(os.environ.get("AI_BROLL_MAX_ANIMATED", "0"))


def present(value) -> bool:
    return str(value or "").strip().upper() not in {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def scene_names(job: dict) -> list[str]:
    prop = job.get("property") or {}
    ptype = str(prop.get("property_type") or "property").lower()
    if any(word in ptype for word in ("plot", "land", "site")):
        return ["location", "road", "land", "exterior"]
    return ["exterior", "location", "living", "kitchen", "bedroom", "road"]


def locality(job: dict) -> str:
    value = str(job.get("property_location") or "Coimbatore").strip()
    return value.split(",")[0].strip() or "Coimbatore"


def property_kind(job: dict) -> str:
    ptype = str((job.get("property") or {}).get("property_type") or "property").lower()
    if any(word in ptype for word in ("flat", "apartment")):
        return "flat"
    if any(word in ptype for word in ("villa", "house", "independent")):
        return "house"
    if any(word in ptype for word in ("plot", "land", "site")):
        return "land"
    return "home"


def compact_size(job: dict) -> str:
    prop = job.get("property") or {}
    area = str(prop.get("built_up_area") or "").strip()
    return area if present(area) else "compact realistic size"


def floor_hint(job: dict) -> str:
    facts = str(job.get("verified_facts") or "")
    match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+floor\b", facts, flags=re.I)
    if not match:
        return ""
    return (
        f"The listed unit is on the {match.group(1)} floor, but do not highlight one exact window "
        "or imply the generated building is the actual property. "
    )


def common_prompt(job: dict) -> str:
    prop = job.get("property") or {}
    ptype = str(prop.get("property_type") or "residential property")
    bhk = str(prop.get("bhk") or "") if present(prop.get("bhk")) else ""
    loc = locality(job)
    title = " ".join(x for x in (bhk, ptype) if x).strip()
    area = compact_size(job)
    return (
        f"Photorealistic representative real-estate advertising visual for a {title} in {loc}, Coimbatore, Tamil Nadu, India. "
        f"The listed built-up size is {area}; keep all spaces and architecture proportionate to that market segment. "
        "Use authentic contemporary Tamil Nadu residential design, realistic Indian construction details, tropical daylight and believable local proportions. "
        "Create an engaging premium property-marketing composition with foreground depth, leading lines, natural shadows and a clean focal point, while remaining physically plausible. "
        "Vertical 9:16 composition. No people, no text, no logos, no watermarks, no religious buildings, no flags, no mountains, no tea estates and no foreign suburban architecture. "
        "Do not create impossible cantilevers, floating rooms, buildings spanning over a public road, roads passing through a building, duplicate doors/windows, warped railings, fantasy geometry or luxury scale inconsistent with the property. "
        "Representative visual only; do not recreate or copy any real listing image. "
    )


def build_prompt(job: dict, scene: str) -> str:
    base = common_prompt(job)
    kind = property_kind(job)
    area = compact_size(job)
    hint = floor_hint(job)

    if kind == "flat":
        details = {
            "exterior": (
                "Show one coherent mid-rise Coimbatore apartment building, approximately ground/stilt plus 3 to 5 residential floors, set completely behind the road edge. "
                "Use a practical entrance, compound/gate, realistic stilt or ground-level parking, vertically aligned balconies, normal structural columns and a believable neutral South Indian facade. "
                "The building must NOT bridge across the road, straddle the street, float above another house or narrow unrealistically into a tower. "
                + hint
                + "Use a low three-quarter property-photography camera angle with clean depth."
            ),
            "location": (
                f"Show a realistic {locality(job)} residential neighbourhood with a normal-width local tar road continuing unobstructed through the frame. "
                "Place apartment buildings and independent houses only on the sides of the road, with utility poles, compound walls and tropical greenery. "
                "No building may sit in, bridge over or block the road."
            ),
            "road": (
                "Show a believable Coimbatore residential access road as the main subject, with modest apartment buildings and houses safely set back on both sides. "
                "Keep the road continuous, physically usable and correctly scaled; include realistic utility poles and greenery. No highway, flyover or impossible structures."
            ),
            "living": (
                f"Show a compact furnished Indian apartment living room consistent with about {area}, not a villa-sized hall. "
                "Use a practical two/three-seat sofa, TV wall, vitrified flooring, warm laminate accents and realistic circulation with natural daylight."
            ),
            "kitchen": (
                f"Show a compact practical Indian modular kitchen appropriate to a {area} flat. "
                "Use a straight or small L-shaped layout, realistic counter depth, upper/base cabinets, chimney, tiled backsplash and sensible appliance clearance. "
                "No oversized island, luxury villa kitchen or impossible cabinet geometry."
            ),
            "bedroom": (
                f"Show a compact furnished Indian bedroom appropriate to a {area} flat. "
                "Use one realistic cot, a practical wardrobe, one small side table and simple curtains with believable walking clearance. "
                "No oversized hotel suite or impossible room proportions."
            ),
            "land": "Show only a normal urban residential site context if required; never imply the flat owns vacant land.",
        }
    elif kind == "house":
        details = {
            "exterior": "Show one coherent contemporary Tamil Nadu independent house or villa entirely within its plot, flat-roof South Indian architecture, compound wall, gate and practical car parking. No impossible cantilevers or foreign suburban styling.",
            "location": "Show a realistic Coimbatore residential neighbourhood with independent houses on both sides of an unobstructed local road, tropical greenery and utility poles.",
            "road": "Show a believable Tamil Nadu residential access road with houses set back on both sides, realistic utility poles and greenery, no highway, flyover or blocked carriageway.",
            "living": "Show a realistic modern Indian living room proportionate to the property, practical sofa and TV wall, warm wood accents, believable circulation and premium natural daylight.",
            "kitchen": "Show a practical premium Indian modular kitchen with realistic counters, cabinets, chimney and backsplash, no oversized foreign-style island unless the property scale supports it.",
            "bedroom": "Show a comfortable modern Tamil Nadu bedroom with realistic cot, wardrobe, side table and curtains, believable proportions and warm natural light.",
            "land": "Show a believable residential house-site context in Tamil Nadu without fake measurements or survey markings.",
        }
    else:
        details = {
            "exterior": "Show one coherent, physically plausible Tamil Nadu residential building appropriate to the stated property type and scale, with clean frontage and realistic local construction.",
            "location": "Show a realistic Coimbatore residential neighbourhood with an unobstructed local road and buildings only on the roadside plots.",
            "road": "Show a believable Tamil Nadu residential access road, correctly scaled and unobstructed, with local houses and greenery.",
            "living": "Show a realistic modern Indian living area proportionate to the stated property size.",
            "kitchen": "Show a practical Indian modular kitchen proportionate to the stated property size.",
            "bedroom": "Show a realistic Indian bedroom proportionate to the stated property size.",
            "land": "Show believable residential plotted land in Tamil Nadu with local road access and modest surrounding houses, no plantation, mountain or fake measurements.",
        }
    return base + details[scene]


def _validate_image_bytes(data: bytes, destination: Path) -> None:
    if len(data) < 50_000:
        raise RuntimeError(f"Generated still is suspiciously small: {len(data)} bytes")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def generate_still_pollinations(prompt: str, destination: Path, seed: int) -> None:
    token = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    if not token:
        raise RuntimeError("POLLINATIONS_API_KEY is not configured")
    encoded = quote(prompt, safe="")
    url = f"{POLLINATIONS_BASE_URL}/image/{encoded}"
    response = requests.get(
        url,
        params={
            "model": POLLINATIONS_IMAGE_MODEL,
            "width": 768,
            "height": 1344,
            "seed": seed,
            "nologo": "true",
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=180,
    )
    if response.status_code >= 400:
        detail = response.text[:500].replace("\n", " ")
        raise RuntimeError(f"Pollinations image request failed ({response.status_code}): {detail}")
    content_type = response.headers.get("content-type", "").lower()
    if "image" not in content_type and not response.content.startswith((b"\xff\xd8", b"\x89PNG")):
        raise RuntimeError(f"Pollinations returned non-image content: {content_type or 'unknown'}")
    _validate_image_bytes(response.content, destination)


def generate_still_hf(prompt: str, destination: Path, seed: int) -> None:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is not configured")
    client = InferenceClient(provider="auto", api_key=token)
    image = client.text_to_image(
        prompt,
        model=HF_IMAGE_MODEL,
        width=768,
        height=1344,
        num_inference_steps=4,
        seed=seed,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(destination, format="JPEG", quality=94, optimize=True)
    if destination.stat().st_size < 50_000:
        raise RuntimeError(f"Generated still is suspiciously small: {destination}")


def generate_still(prompt: str, destination: Path, seed: int) -> str:
    pollinations_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    errors = []

    if pollinations_key:
        try:
            generate_still_pollinations(prompt, destination, seed)
            return f"pollinations:{POLLINATIONS_IMAGE_MODEL}"
        except Exception as error:
            errors.append(f"Pollinations: {error}")

    if hf_token:
        try:
            generate_still_hf(prompt, destination, seed)
            return f"huggingface:{HF_IMAGE_MODEL}"
        except Exception as error:
            errors.append(f"Hugging Face: {error}")

    if not pollinations_key and not hf_token:
        raise RuntimeError("No AI image backend configured. Add POLLINATIONS_API_KEY (preferred) or HF_TOKEN.")
    raise RuntimeError("; ".join(errors))


def image_data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _extract_video(result, destination: Path) -> None:
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected video response type: {type(result).__name__}")
    video = result.get("video") or {}
    url = video.get("url") or ""
    if isinstance(url, str) and url.startswith("data:") and "," in url:
        destination.write_bytes(base64.b64decode(url.split(",", 1)[1]))
    else:
        raise RuntimeError("Video Space response did not contain inline MP4 data")
    if destination.stat().st_size < 100_000:
        raise RuntimeError(f"Generated video is suspiciously small: {destination.stat().st_size} bytes")


def animate_still(client: Client, still: Path, prompt: str, destination: Path, seed: int) -> None:
    result = client.predict(
        image_url=image_data_uri(still),
        prompt=prompt + " Add subtle professional stabilized camera movement, preserve architecture and geometry, no morphing.",
        negative_prompt="people, text, watermark, logo, warped architecture, extra doors, extra windows, fantasy, religious building, foreign suburban house, building over road, blocked road, impossible cantilever",
        resolution="720p",
        duration=5,
        seed=seed,
        output_format="video/h264-mp4",
        generate_audio=False,
        sync_mode=True,
        api_name="/generate",
    )
    _extract_video(result, destination)


def still_motion_fallback(still: Path, destination: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(still),
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,zoompan=z='min(zoom+0.00065,1.045)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=121:s=720x1280:fps=24,format=yuv420p",
            "-t", "5.05", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(destination),
        ],
        check=True,
        timeout=180,
    )
    if not destination.exists() or destination.stat().st_size < 100_000:
        raise RuntimeError(f"Could not create AI-still motion clip: {destination}")


def generate_for_job(job: dict, max_animated: int = DEFAULT_ANIMATED) -> dict:
    video_id = str(job["video_id"])
    root = ROOT / video_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    video_client = Client(VIDEO_SPACE, hf_token=hf_token) if max_animated > 0 and hf_token else None
    scenes = scene_names(job)
    manifest = {
        "video_id": video_id,
        "representative_visuals": True,
        "image_backend_preference": "pollinations-first",
        "pollinations_model": POLLINATIONS_IMAGE_MODEL,
        "hf_image_model": HF_IMAGE_MODEL,
        "video_space": VIDEO_SPACE,
        "scenes": [],
    }

    for index, scene in enumerate(scenes):
        scene_dir = root / scene
        scene_dir.mkdir(parents=True, exist_ok=True)
        prompt = build_prompt(job, scene)
        still = scene_dir / f"{scene}-representative.jpg"
        clip = scene_dir / f"{scene}-representative.mp4"
        entry = {
            "scene": scene,
            "prompt": prompt,
            "still": str(still),
            "video": str(clip),
            "animated_backend": "ai-still-motion",
        }
        try:
            entry["image_backend"] = generate_still(prompt, still, 1000 + index)
        except Exception as error:
            entry["error"] = str(error)[:700]
            manifest["scenes"].append(entry)
            (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            raise RuntimeError(f"AI still generation failed for {video_id}/{scene}: {error}") from error

        if video_client is not None and index < max(0, max_animated):
            try:
                animate_still(video_client, still, prompt, clip, 2000 + index)
                entry["animated_backend"] = "ltx-2.3-zerogpu"
            except Exception as error:
                entry["video_error"] = str(error)[:700]
                still_motion_fallback(still, clip)
        else:
            still_motion_fallback(still, clip)

        entry["bytes"] = clip.stat().st_size
        print(
            f"AI visual {video_id}/{scene}: image={entry['image_backend']} "
            f"motion={entry['animated_backend']} {entry['bytes']} bytes"
        )
        manifest["scenes"].append(entry)

    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    successful = [
        row for row in manifest["scenes"]
        if Path(row["video"]).exists() and Path(row["video"]).stat().st_size >= 100_000
        and Path(row["still"]).exists() and Path(row["still"]).stat().st_size >= 50_000
    ]
    if len(successful) != len(scenes):
        raise RuntimeError(f"Incomplete AI scene pack for {video_id}: {len(successful)}/{len(scenes)} scenes")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default=os.environ.get("VIDEO_IDS_FILE", "data/render_queue.txt"))
    parser.add_argument("--max-animated", type=int, default=DEFAULT_ANIMATED)
    args = parser.parse_args()
    queue = Path(args.queue)
    if not queue.exists():
        raise SystemExit(f"Queue not found: {queue}")
    failures = []
    for video_id in [
        line.strip() for line in queue.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]:
        try:
            job_path = Path("data/video_jobs") / f"{video_id}.json"
            job = json.loads(job_path.read_text(encoding="utf-8"))
            generate_for_job(job, args.max_animated)
        except Exception as error:
            failures.append(f"{video_id}: {error}")
            print(f"AI VISUAL PIPELINE ERROR {video_id}: {error}")
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
