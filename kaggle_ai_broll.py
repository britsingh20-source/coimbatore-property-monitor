import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import boto3


STATUS_POLL_SECONDS = int(os.environ.get("KAGGLE_BROLL_POLL_SECONDS", "20"))
STATUS_MAX_POLLS = int(os.environ.get("KAGGLE_BROLL_MAX_POLLS", "180"))
R2_TTL_SECONDS = int(os.environ.get("KAGGLE_BROLL_SOURCE_TTL", "7200"))


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
    attribution = Path("data/media_attribution") / f"{video_id}.json"
    if attribution.exists():
        try:
            data = json.loads(attribution.read_text(encoding="utf-8"))
            stack = data if isinstance(data, list) else list(data.values()) if isinstance(data, dict) else []
            for item in stack:
                if isinstance(item, dict):
                    local = item.get("local_file")
                    if local and Path(local).exists() and Path(local).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                        return Path(local)
        except Exception:
            pass

    candidates = []
    for root in (Path("assets"), Path("data")):
        if not root.exists():
            continue
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            candidates.extend(path for path in root.rglob(ext) if video_id.lower() in str(path).lower())
    if not candidates:
        raise RuntimeError(f"No local source image found for {video_id}; run media preparation first")
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def build_prompt(job: dict) -> str:
    prop = job.get("property", {})
    location = job.get("property_location") or job.get("location") or "Coimbatore residential area"
    property_type = prop.get("property_type") or "modern house"
    bhk = prop.get("bhk") or ""
    base = f"Photorealistic real-estate footage of this exact {bhk} {property_type} in {location}."
    motion = (
        " Preserve the building, room geometry, materials and visible details from the reference image. "
        "Create only subtle realistic camera motion: slow stabilized gimbal push-in with gentle parallax, "
        "natural daylight, realistic Indian residential context, no people, no text, no logos, no religious buildings. "
        "Do not invent extra floors, doors, windows, furniture or surrounding landmarks. Professional property walkthrough B-roll."
    )
    return re.sub(r"\s+", " ", base + motion).strip()


def upload_source_image(path: Path, video_id: str) -> tuple[str, str]:
    client = r2_client()
    bucket = required("R2_BUCKET_NAME")
    key = f"ai-broll-input/{video_id}/{path.name}"
    content_type = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(path.suffix.lower(), "application/octet-stream")
    client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=R2_TTL_SECONDS,
    )
    return key, url


def kernel_script(source_url: str, prompt: str, video_id: str) -> str:
    return f'''import os
import shutil
import subprocess
from pathlib import Path
import requests

SOURCE_URL = {source_url!r}
PROMPT = {prompt!r}
VIDEO_ID = {video_id!r}

work = Path("/kaggle/working")
image_path = work / "source.jpg"
response = requests.get(SOURCE_URL, timeout=120)
response.raise_for_status()
image_path.write_bytes(response.content)

subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Lightricks/LTX-Video.git", "/kaggle/working/LTX-Video"], check=True)
repo = Path("/kaggle/working/LTX-Video")
subprocess.run(["python", "-m", "pip", "install", "-q", "-e", ".[inference]"], cwd=repo, check=True)

before = set(repo.rglob("*.mp4"))
cmd = [
    "python", "inference.py",
    "--prompt", PROMPT,
    "--conditioning_media_paths", str(image_path),
    "--conditioning_start_frames", "0",
    "--height", "736",
    "--width", "480",
    "--num_frames", "81",
    "--seed", "42",
    "--pipeline_config", "configs/ltxv-2b-0.9.8-distilled.yaml",
]
subprocess.run(cmd, cwd=repo, check=True)
after = [p for p in repo.rglob("*.mp4") if p not in before]
if not after:
    after = list(repo.rglob("*.mp4"))
if not after:
    raise RuntimeError("LTX-Video completed but no MP4 output was found")
latest = max(after, key=lambda p: p.stat().st_mtime)
out = work / f"{{VIDEO_ID}}-ai-broll.mp4"
shutil.copy2(latest, out)
print(f"OUTPUT={{out}} size={{out.stat().st_size}}")
'''


def write_kernel(folder: Path, username: str, video_id: str, source_url: str, prompt: str) -> str:
    slug = "coimbatore-property-ai-broll"
    kernel_id = f"{username}/{slug}"
    (folder / "ai_broll_kernel.py").write_text(kernel_script(source_url, prompt, video_id), encoding="utf-8")
    metadata = {
        "id": kernel_id,
        "title": "Coimbatore Property AI B-roll",
        "code_file": "ai_broll_kernel.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "keywords": ["ltx-video", "image-to-video", "real-estate"],
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": [],
        "model_sources": [],
    }
    (folder / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return kernel_id


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(args))
    return subprocess.run(args, text=True, capture_output=True, check=check)


def wait_for_kernel(kernel_id: str) -> None:
    last = ""
    for _ in range(STATUS_MAX_POLLS):
        proc = run_command(["kaggle", "kernels", "status", kernel_id], check=False)
        text = (proc.stdout + "\n" + proc.stderr).strip()
        if text != last:
            print(text)
            last = text
        low = text.lower()
        if any(term in low for term in ("complete", "completed", "success")) and not any(term in low for term in ("error", "failed", "cancel")):
            return
        if any(term in low for term in ("error", "failed", "cancel")):
            raise RuntimeError(f"Kaggle kernel failed: {text}")
        time.sleep(STATUS_POLL_SECONDS)
    raise TimeoutError(f"Timed out waiting for Kaggle kernel {kernel_id}")


def download_output(kernel_id: str, output_dir: Path, video_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = run_command(["kaggle", "kernels", "output", kernel_id, "-p", str(output_dir), "-o"], check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stdout + "\n" + proc.stderr).strip())
    matches = list(output_dir.rglob(f"{video_id}-ai-broll.mp4")) or list(output_dir.rglob("*.mp4"))
    if not matches:
        raise RuntimeError("Kaggle run completed but no MP4 was downloaded")
    return max(matches, key=lambda p: p.stat().st_size)


def persist_to_r2(path: Path, video_id: str) -> str:
    client = r2_client()
    bucket = required("R2_BUCKET_NAME")
    key = f"ai-broll/{video_id}/{path.name}"
    client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": "video/mp4"})
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--job", default="")
    parser.add_argument("--output-dir", default="outputs/kaggle-ai-broll")
    args = parser.parse_args()

    username = required("KAGGLE_USERNAME")
    required("KAGGLE_API_TOKEN")
    video_id = args.video_id.strip()
    job_path = Path(args.job) if args.job else Path("data/video_jobs") / f"{video_id}.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    source_image = find_source_image(video_id)
    prompt = build_prompt(job)
    source_key, source_url = upload_source_image(source_image, video_id)
    print(f"Source image: {source_image}; temporary R2 key: {source_key}")
    print(f"Prompt: {prompt}")

    with tempfile.TemporaryDirectory(prefix="kaggle-ai-broll-") as tmp:
        kernel_dir = Path(tmp)
        kernel_id = write_kernel(kernel_dir, username, video_id, source_url, prompt)
        proc = run_command(["kaggle", "kernels", "push", "-p", str(kernel_dir), "--accelerator", "NvidiaTeslaP100", "--timeout", "3600"], check=False)
        print(proc.stdout)
        print(proc.stderr)
        if proc.returncode != 0:
            raise RuntimeError("Kaggle kernel push failed")
        wait_for_kernel(kernel_id)
        result = download_output(kernel_id, Path(args.output_dir) / video_id, video_id)
        if result.stat().st_size < 100_000:
            raise RuntimeError(f"Generated B-roll is suspiciously small: {result.stat().st_size} bytes")
        r2_key = persist_to_r2(result, video_id)
        summary = {
            "video_id": video_id,
            "source_image": str(source_image),
            "prompt": prompt,
            "kernel_id": kernel_id,
            "output": str(result),
            "r2_key": r2_key,
            "bytes": result.stat().st_size,
        }
        summary_path = Path(args.output_dir) / video_id / "manifest.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
