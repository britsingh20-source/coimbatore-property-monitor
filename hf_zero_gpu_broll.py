import argparse
import base64
import json
import os
import re
from pathlib import Path

import boto3
from gradio_client import Client

DEFAULT_SPACE_ID = os.environ.get("HF_SPACE_ID", "ShaundeOoO/ltx-2.3-fast")


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def r2_client():
    account_id = required("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def find_source_image(video_id: str) -> Path:
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    preferred_roots = [
        Path("assets/properties") / video_id,
        Path("assets/media") / video_id,
        Path("assets") / video_id,
    ]
    for root in preferred_roots:
        if not root.exists():
            continue
        candidates = [
            p for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in allowed
            and "map" not in str(p).lower()
            and "thumbnail" not in str(p).lower()
        ]
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_size)

    candidates = [
        p
        for root in (Path("assets"), Path("data"))
        if root.exists()
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in allowed
        and video_id.lower() in str(p).lower()
        and "map" not in str(p).lower()
        and "thumbnail" not in str(p).lower()
    ]
    if not candidates:
        raise RuntimeError(f"No property-specific source image found for {video_id}; run media preparation first")
    return max(candidates, key=lambda p: p.stat().st_size)


def build_prompt(job: dict) -> str:
    prop = job.get("property", {})
    location = job.get("property_location") or job.get("location") or "Coimbatore, Tamil Nadu, India"
    ptype = prop.get("property_type") or "residential property"
    bhk = prop.get("bhk") or ""
    text = (
        f"Photorealistic professional real-estate walkthrough footage of this exact {bhk} {ptype} in {location}. "
        "Preserve the visible architecture, room geometry, materials, openings and proportions from the reference image. "
        "Create subtle stabilized gimbal movement with a gentle slow push-in and realistic parallax. "
        "Natural daylight, realistic Indian residential context, no people, no text, no logos, no religious buildings. "
        "Do not invent extra floors, doors, windows, furniture, roads or landmarks. Keep motion smooth and believable."
    )
    return re.sub(r"\s+", " ", text).strip()


def image_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def extract_video_bytes(result) -> tuple[bytes, dict]:
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected Hugging Face response type: {type(result).__name__}")
    video = result.get("video") or {}
    url = video.get("url") or ""
    if not isinstance(url, str) or not url.startswith("data:") or "," not in url:
        raise RuntimeError("Hugging Face response did not contain an inline video data URI")
    _, payload = url.split(",", 1)
    return base64.b64decode(payload), result


def persist_to_r2(path: Path, video_id: str) -> str:
    key = f"ai-broll/{video_id}/{path.name}"
    r2_client().upload_file(
        str(path),
        required("R2_BUCKET_NAME"),
        key,
        ExtraArgs={"ContentType": "video/mp4"},
    )
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--job", default="")
    parser.add_argument("--space-id", default=DEFAULT_SPACE_ID)
    parser.add_argument("--output-dir", default="outputs/hf-zero-gpu-ai-broll")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--resolution", choices=["720p", "1080p"], default="720p")
    args = parser.parse_args()

    hf_token = required("HF_TOKEN")
    video_id = args.video_id.strip()
    job_path = Path(args.job) if args.job else Path("data/video_jobs") / f"{video_id}.json"
    if not job_path.exists():
        raise RuntimeError(f"Video job not found: {job_path}")

    source_image = find_source_image(video_id)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    prompt = build_prompt(job)
    out_dir = Path(args.output_dir) / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"HF Space: {args.space_id}", flush=True)
    print(f"Source image: {source_image} ({source_image.stat().st_size} bytes)", flush=True)
    print(f"Prompt: {prompt}", flush=True)
    print(f"Profile: {args.resolution}, {args.duration}s, audio=false", flush=True)

    # gradio_client 1.x (Gradio 5 generation) uses hf_token. Gradio 6 renamed it to token.
    client = Client(args.space_id, hf_token=hf_token)
    result = client.predict(
        image_url=image_data_uri(source_image),
        prompt=prompt,
        negative_prompt="people, text, watermark, logo, distortion, warped architecture, extra doors, extra windows, fantasy, religious building",
        resolution=args.resolution,
        duration=max(5, min(10, int(args.duration))),
        seed=42,
        output_format="video/h264-mp4",
        generate_audio=False,
        sync_mode=True,
        api_name="/generate",
    )

    video_bytes, response = extract_video_bytes(result)
    output_path = out_dir / f"{video_id}-hf-ai-broll.mp4"
    output_path.write_bytes(video_bytes)
    if output_path.stat().st_size < 100_000:
        raise RuntimeError(f"Generated video is suspiciously small: {output_path.stat().st_size} bytes")

    r2_key = persist_to_r2(output_path, video_id)
    light_response = dict(response)
    if isinstance(light_response.get("video"), dict):
        light_response["video"] = {k: v for k, v in light_response["video"].items() if k != "url"}

    manifest = {
        "video_id": video_id,
        "backend": "huggingface_zerogpu",
        "space_id": args.space_id,
        "source_image": str(source_image),
        "prompt": prompt,
        "resolution": args.resolution,
        "duration_requested": max(5, min(10, int(args.duration))),
        "output": str(output_path),
        "bytes": output_path.stat().st_size,
        "r2_key": r2_key,
        "response": light_response,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
