import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client


IMAGE_SPACE = os.environ.get("HF_IMAGE_SPACE_ID", "black-forest-labs/FLUX.1-schnell").strip()
VIDEO_SPACE = os.environ.get("HF_VIDEO_SPACE_ID", "ShaundeOoO/ltx-2.3-fast").strip()
ROOT = Path("assets/ai_broll")
DEFAULT_ANIMATED = int(os.environ.get("AI_BROLL_MAX_ANIMATED", "3"))


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
        "Authentic contemporary South Indian residential design, believable middle-class to premium local materials, tropical climate, realistic Indian proportions and detailing. "
        "Vertical 9:16 composition, professional property photography, natural daylight, visually engaging but believable. "
        "No people, no text, no logos, no watermarks, no religious buildings, no flags, no mountains, no tea estates, no foreign suburban architecture. "
        "This is a representative visual, not the exact listed property. "
    )


def build_prompt(job: dict, scene: str) -> str:
    base = common_prompt(job)
    details = {
        "exterior": "Show a strong cinematic hero exterior of a newly constructed Tamil Nadu independent home or locally plausible residential building, clean frontage, compound wall, practical covered parking, flat-roof South Indian architecture, ordinary Coimbatore residential context.",
        "location": "Show a calm Coimbatore residential neighbourhood with locally plausible independent houses and small apartment buildings, trees and utility poles, clean realistic local road, no famous landmark and do not imply this is the exact street.",
        "road": "Show a believable Tamil Nadu residential access road with houses on both sides, local tar road, modest setbacks, realistic utility poles and greenery, no highway, no flyover, no heavy traffic.",
        "living": "Show an engaging modern Indian living room suitable for a Coimbatore home, practical TV wall, sofa, vitrified tile or stone floor, warm wood accents, realistic room size, uncluttered and lived-in quality without people.",
        "kitchen": "Show a practical premium Indian modular kitchen suitable for a Coimbatore home, realistic countertop, overhead and base cabinets, chimney, tiled backsplash and efficient compact layout, no food preparation and no people.",
        "bedroom": "Show a comfortable modern Indian bedroom suitable for a Coimbatore residence, realistic wardrobe, cot, side table, curtains and warm neutral materials, believable room proportions, no people.",
        "land": "Show a believable residential house-site layout in Tamil Nadu, vacant plotted land with local road access and modest surrounding houses, no farmland, no plantation, no mountains, no fake boundary measurements.",
    }[scene]
    return base + details


def _named_endpoints(client: Client) -> list[str]:
    try:
        info = client.view_api(return_format="dict") or {}
    except Exception:
        return []
    named = info.get("named_endpoints") if isinstance(info, dict) else None
    if isinstance(named, dict):
        return list(named.keys())
    return []


def _image_endpoint(client: Client) -> str | None:
    endpoints = _named_endpoints(client)
    for preferred in ("/infer", "/generate", "/predict"):
        if preferred in endpoints:
            return preferred
    return endpoints[0] if endpoints else None


def _path_from_result(result) -> Path:
    candidates = result if isinstance(result, (list, tuple)) else [result]
    for item in candidates:
        if isinstance(item, str) and Path(item).exists():
            return Path(item)
        if isinstance(item, dict):
            for key in ("path", "name"):
                value = item.get(key)
                if isinstance(value, str) and Path(value).exists():
                    return Path(value)
    raise RuntimeError(f"Could not find generated image file in result type {type(result).__name__}")


def generate_still(client: Client, prompt: str, destination: Path, seed: int) -> None:
    endpoint = _image_endpoint(client)
    kwargs = dict(prompt=prompt, seed=seed, randomize_seed=False, width=768, height=1344, num_inference_steps=4)
    try:
        result = client.predict(api_name=endpoint, **kwargs) if endpoint else client.predict(**kwargs)
    except TypeError:
        # Older/public Gradio Spaces can expose only positional parameters.
        args = [prompt, seed, False, 768, 1344, 4]
        result = client.predict(*args, api_name=endpoint) if endpoint else client.predict(*args)
    source = _path_from_result(result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if destination.stat().st_size < 50_000:
        raise RuntimeError(f"Generated still is suspiciously small: {destination}")


def image_data_uri(path: Path) -> str:
    import base64
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _extract_video(result, destination: Path) -> None:
    import base64
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
    # Produce a genuine moving vertical MP4 from the generated still so every scene
    # stays usable even when ZeroGPU video quota/queue is unavailable.
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
        raise RuntimeError(f"Could not create fallback motion clip: {destination}")


def generate_for_job(job: dict, max_animated: int = DEFAULT_ANIMATED) -> dict:
    token = required("HF_TOKEN")
    video_id = str(job["video_id"])
    root = ROOT / video_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    image_client = Client(IMAGE_SPACE, hf_token=token)
    video_client = Client(VIDEO_SPACE, hf_token=token)
    scenes = scene_names(job)
    manifest = {"video_id": video_id, "representative_visuals": True, "image_space": IMAGE_SPACE, "video_space": VIDEO_SPACE, "scenes": []}

    for index, scene in enumerate(scenes):
        scene_dir = root / scene
        scene_dir.mkdir(parents=True, exist_ok=True)
        prompt = build_prompt(job, scene)
        still = scene_dir / f"{scene}-representative.jpg"
        clip = scene_dir / f"{scene}-representative.mp4"
        entry = {"scene": scene, "prompt": prompt, "still": str(still), "video": str(clip), "animated_backend": "still-motion"}
        try:
            generate_still(image_client, prompt, still, 1000 + index)
            if index < max(0, max_animated):
                try:
                    animate_still(video_client, still, prompt, clip, 2000 + index)
                    entry["animated_backend"] = "ltx-2.3-zerogpu"
                except Exception as error:
                    entry["video_error"] = str(error)[:500]
                    still_motion_fallback(still, clip)
            else:
                still_motion_fallback(still, clip)
            entry["bytes"] = clip.stat().st_size
            print(f"AI visual {video_id}/{scene}: {entry['animated_backend']} {entry['bytes']} bytes")
        except Exception as error:
            entry["error"] = str(error)[:500]
            print(f"AI visual failed {video_id}/{scene}: {error}")
        manifest["scenes"].append(entry)

    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    successful = [row for row in manifest["scenes"] if Path(row["video"]).exists() and Path(row["video"]).stat().st_size >= 100_000]
    if not successful:
        raise RuntimeError(f"No AI representative scene clips were generated for {video_id}")
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
