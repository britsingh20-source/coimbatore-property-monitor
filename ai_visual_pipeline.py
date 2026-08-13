import argparse
import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client
from huggingface_hub import InferenceClient


IMAGE_MODEL = os.environ.get("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
VIDEO_SPACE = os.environ.get("HF_VIDEO_SPACE_ID", "ShaundeOoO/ltx-2.3-fast").strip()
ROOT = Path("assets/ai_broll")
DEFAULT_ANIMATED = int(os.environ.get("AI_BROLL_MAX_ANIMATED", "1"))


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


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


def common_prompt(job: dict) -> str:
    prop = job.get("property") or {}
    ptype = str(prop.get("property_type") or "residential property")
    bhk = str(prop.get("bhk") or "") if present(prop.get("bhk")) else ""
    loc = locality(job)
    title = " ".join(x for x in (bhk, ptype) if x).strip()
    return (
        f"Photorealistic representative real-estate advertising visual for {title} in the style of {loc}, Coimbatore, Tamil Nadu, India. "
        "Authentic contemporary South Indian residential design, believable Tamil Nadu materials and proportions, tropical climate, realistic Indian detailing. "
        "Vertical 9:16 composition, premium property photography, natural daylight, visually engaging but believable. "
        "No people, no text, no logos, no watermarks, no religious buildings, no flags, no mountains, no tea estates, no foreign suburban architecture. "
        "Representative visual only; do not recreate or copy any real listing image. "
    )


def build_prompt(job: dict, scene: str) -> str:
    base = common_prompt(job)
    details = {
        "exterior": "Strong cinematic hero exterior of a newly constructed Tamil Nadu independent home or locally plausible residential building, clean frontage, compound wall, practical covered parking, flat-roof South Indian architecture, ordinary Coimbatore residential context.",
        "location": "Calm Coimbatore residential neighbourhood with locally plausible independent houses and small apartment buildings, trees, utility poles and a realistic local road; no famous landmark and do not imply this is the exact street.",
        "road": "Believable Tamil Nadu residential access road with houses on both sides, local tar road, modest setbacks, realistic utility poles and greenery, no highway, no flyover, no heavy traffic.",
        "living": "Engaging modern Indian living room suitable for a Coimbatore home, practical TV wall, sofa, vitrified tile or stone floor, warm wood accents, realistic room size, uncluttered, no people.",
        "kitchen": "Practical premium Indian modular kitchen suitable for a Coimbatore home, realistic countertop, overhead and base cabinets, chimney, tiled backsplash and efficient compact layout, no food preparation, no people.",
        "bedroom": "Comfortable modern Indian bedroom suitable for a Coimbatore residence, realistic wardrobe, cot, side table, curtains and warm neutral materials, believable room proportions, no people.",
        "land": "Believable residential house-site layout in Tamil Nadu, vacant plotted land with local road access and modest surrounding houses, no farmland, no plantation, no mountains, no fake boundary measurements.",
    }[scene]
    return base + details


def generate_still(client: InferenceClient, prompt: str, destination: Path, seed: int) -> None:
    image = client.text_to_image(
        prompt,
        model=IMAGE_MODEL,
        width=768,
        height=1344,
        num_inference_steps=4,
        seed=seed,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = image.convert("RGB")
    image.save(destination, format="JPEG", quality=94, optimize=True)
    if destination.stat().st_size < 50_000:
        raise RuntimeError(f"Generated still is suspiciously small: {destination}")


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
        prompt=prompt + " Add subtle professional stabilized camera movement, gentle push-in or lateral parallax, preserve architecture and geometry, no morphing.",
        negative_prompt="people, text, watermark, logo, warped architecture, extra doors, extra windows, fantasy, religious building, foreign suburban house",
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
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,zoompan=z='min(zoom+0.0008,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=121:s=720x1280:fps=24,format=yuv420p",
            "-t", "5.05", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(destination),
        ],
        check=True,
        timeout=180,
    )
    if not destination.exists() or destination.stat().st_size < 100_000:
        raise RuntimeError(f"Could not create AI-still motion clip: {destination}")


def generate_for_job(job: dict, max_animated: int = DEFAULT_ANIMATED) -> dict:
    token = required("HF_TOKEN")
    video_id = str(job["video_id"])
    root = ROOT / video_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    # IMPORTANT: still images use HF Inference Providers, not a ZeroGPU Space.
    # This prevents six image generations from consuming the user's 5-minute daily ZeroGPU quota.
    image_client = InferenceClient(provider="auto", api_key=token)
    video_client = Client(VIDEO_SPACE, hf_token=token) if max_animated > 0 else None
    scenes = scene_names(job)
    manifest = {
        "video_id": video_id,
        "representative_visuals": True,
        "image_backend": "hf-inference-providers",
        "image_model": IMAGE_MODEL,
        "video_space": VIDEO_SPACE,
        "scenes": [],
    }

    for index, scene in enumerate(scenes):
        scene_dir = root / scene
        scene_dir.mkdir(parents=True, exist_ok=True)
        prompt = build_prompt(job, scene)
        still = scene_dir / f"{scene}-representative.jpg"
        clip = scene_dir / f"{scene}-representative.mp4"
        entry = {"scene": scene, "prompt": prompt, "still": str(still), "video": str(clip), "animated_backend": "ai-still-motion"}
        try:
            generate_still(image_client, prompt, still, 1000 + index)
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
                # A video-quota failure must never send us back to Pexels. We keep the new AI still and animate it locally.
                entry["video_error"] = str(error)[:700]
                still_motion_fallback(still, clip)
        else:
            still_motion_fallback(still, clip)

        entry["bytes"] = clip.stat().st_size
        print(f"AI visual {video_id}/{scene}: {entry['animated_backend']} {entry['bytes']} bytes")
        manifest["scenes"].append(entry)

    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    successful = [row for row in manifest["scenes"] if Path(row["video"]).exists() and Path(row["video"]).stat().st_size >= 100_000]
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
    for video_id in [line.strip() for line in queue.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]:
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
