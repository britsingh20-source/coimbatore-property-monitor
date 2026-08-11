import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import boto3

POLL_SECONDS = int(os.environ.get("KAGGLE_BROLL_POLL_SECONDS", "20"))
MAX_POLLS = int(os.environ.get("KAGGLE_BROLL_MAX_POLLS", "180"))
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
    candidates = []
    for root in (Path("assets/properties") / video_id, Path("assets"), Path("data")):
        if not root.exists():
            continue
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            candidates.extend(root.rglob(ext))
    if not candidates:
        raise RuntimeError(f"No local source image found for {video_id}")
    candidates = [p for p in candidates if video_id.lower() in str(p).lower() or (Path("assets/properties") / video_id) in p.parents]
    if not candidates:
        raise RuntimeError(f"No property-specific source image found for {video_id}")
    return max(candidates, key=lambda p: p.stat().st_size)


def build_prompt(job: dict) -> str:
    prop = job.get("property", {})
    location = job.get("property_location") or "Coimbatore, Tamil Nadu, India"
    bhk = prop.get("bhk") or ""
    ptype = prop.get("property_type") or "residential property"
    return re.sub(r"\s+", " ", (
        f"Photorealistic real-estate footage of this exact {bhk} {ptype} in {location}. "
        "Preserve the visible building or room geometry, materials and details from the reference image. "
        "Create subtle realistic camera motion only: slow stabilized gimbal push-in with gentle parallax, natural daylight, "
        "realistic Indian residential context, no people, no text, no logos, no religious buildings. "
        "Do not invent extra floors, doors, windows, furniture or landmarks. Professional property walkthrough B-roll."
    )).strip()


def upload_source(path: Path, video_id: str) -> tuple[str, str]:
    client = r2_client()
    bucket = required("R2_BUCKET_NAME")
    key = f"ai-broll-input/{video_id}/{path.name}"
    client.upload_file(str(path), bucket, key)
    url = client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=R2_TTL_SECONDS)
    return key, url


def kernel_code(source_url: str, prompt: str, video_id: str) -> str:
    return f'''import subprocess
import shutil
import traceback
from pathlib import Path
import requests

work = Path("/kaggle/working")
failure = work / "failure.txt"
progress = work / "progress.txt"
VIDEO_ID = {video_id!r}
SOURCE_URL = {source_url!r}
PROMPT = {prompt!r}

def mark(message):
    print(message, flush=True)
    with progress.open("a", encoding="utf-8") as f:
        f.write(message + "\\n")

try:
    mark("stage=download_source")
    image_path = work / "source.jpg"
    r = requests.get(SOURCE_URL, timeout=120)
    r.raise_for_status()
    image_path.write_bytes(r.content)
    mark(f"source_bytes={{image_path.stat().st_size}}")

    mark("stage=clone_ltx")
    repo = work / "LTX-Video"
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/Lightricks/LTX-Video.git", str(repo)], check=True)

    mark("stage=install_ltx")
    subprocess.run(["python", "-m", "pip", "install", "-e", ".[inference]"], cwd=repo, check=True)

    mark("stage=run_inference")
    before = set(repo.rglob("*.mp4"))
    cmd = [
        "python", "inference.py",
        "--prompt", PROMPT,
        "--conditioning_media_paths", str(image_path),
        "--conditioning_start_frames", "0",
        "--height", "512",
        "--width", "320",
        "--num_frames", "49",
        "--seed", "42",
        "--pipeline_config", "configs/ltxv-2b-0.9.8-distilled.yaml",
    ]
    mark("command=" + " ".join(cmd))
    subprocess.run(cmd, cwd=repo, check=True)

    mark("stage=find_output")
    after = [p for p in repo.rglob("*.mp4") if p not in before] or list(repo.rglob("*.mp4"))
    if not after:
        raise RuntimeError("LTX inference finished but no MP4 was produced")
    latest = max(after, key=lambda p: p.stat().st_mtime)
    out = work / f"{{VIDEO_ID}}-ai-broll.mp4"
    shutil.copy2(latest, out)
    mark(f"success output={{out}} bytes={{out.stat().st_size}}")
except Exception:
    failure.write_text(traceback.format_exc(), encoding="utf-8")
    mark("stage=error traceback_saved=failure.txt")
    raise
'''


def write_kernel(folder: Path, username: str, source_url: str, prompt: str, video_id: str) -> str:
    slug = "coimbatore-property-ai-b-roll"
    kernel_id = f"{username}/{slug}"
    (folder / "ai_broll_kernel.py").write_text(kernel_code(source_url, prompt, video_id), encoding="utf-8")
    metadata = {
        "id": kernel_id,
        "title": "Coimbatore Property AI B-roll",
        "code_file": "ai_broll_kernel.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "keywords": ["real-estate"],
        "dataset_sources": [], "kernel_sources": [], "competition_sources": [], "model_sources": []
    }
    (folder / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return kernel_id


def run(args: list[str]) -> subprocess.CompletedProcess:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, text=True, capture_output=True)


def download_kernel_output(kernel_id: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    proc = run(["kaggle", "kernels", "output", kernel_id, "-p", str(dest), "-o"])
    print(proc.stdout, flush=True)
    print(proc.stderr, flush=True)


def print_diagnostics(dest: Path) -> None:
    for name in ("progress.txt", "failure.txt"):
        matches = list(dest.rglob(name))
        if matches:
            print(f"===== KAGGLE {name} =====", flush=True)
            print(matches[0].read_text(encoding="utf-8", errors="replace"), flush=True)


def wait(kernel_id: str, diag_dir: Path) -> None:
    last = ""
    for _ in range(MAX_POLLS):
        proc = run(["kaggle", "kernels", "status", kernel_id])
        text = (proc.stdout + "\n" + proc.stderr).strip()
        if text != last:
            print(text, flush=True)
            last = text
        low = text.lower()
        if "error" in low or "failed" in low or "cancel" in low:
            download_kernel_output(kernel_id, diag_dir)
            print_diagnostics(diag_dir)
            raise RuntimeError(f"Kaggle kernel failed: {text}")
        if "complete" in low or "success" in low:
            return
        time.sleep(POLL_SECONDS)
    download_kernel_output(kernel_id, diag_dir)
    print_diagnostics(diag_dir)
    raise TimeoutError(f"Timed out waiting for Kaggle kernel {kernel_id}")


def persist(path: Path, video_id: str) -> str:
    key = f"ai-broll/{video_id}/{path.name}"
    r2_client().upload_file(str(path), required("R2_BUCKET_NAME"), key, ExtraArgs={"ContentType": "video/mp4"})
    return key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--output-dir", default="outputs/kaggle-ai-broll")
    args = ap.parse_args()
    username = required("KAGGLE_USERNAME")
    required("KAGGLE_API_TOKEN")
    video_id = args.video_id.strip()
    job = json.loads((Path("data/video_jobs") / f"{video_id}.json").read_text(encoding="utf-8"))
    source = find_source_image(video_id)
    prompt = build_prompt(job)
    key, url = upload_source(source, video_id)
    print(f"Source image: {source}; temporary R2 key: {key}", flush=True)
    print(f"Prompt: {prompt}", flush=True)

    out_dir = Path(args.output_dir) / video_id
    diag_dir = out_dir / "kaggle-output"
    with tempfile.TemporaryDirectory(prefix="kaggle-ai-broll-") as tmp:
        kernel_id = write_kernel(Path(tmp), username, url, prompt, video_id)
        proc = run(["kaggle", "kernels", "push", "-p", tmp, "--accelerator", "NvidiaTeslaP100", "--timeout", "3600"])
        print(proc.stdout, flush=True)
        print(proc.stderr, flush=True)
        if proc.returncode != 0:
            raise RuntimeError("Kaggle kernel push failed")
        wait(kernel_id, diag_dir)
        download_kernel_output(kernel_id, diag_dir)
        print_diagnostics(diag_dir)
        videos = list(diag_dir.rglob(f"{video_id}-ai-broll.mp4")) or list(diag_dir.rglob("*.mp4"))
        if not videos:
            raise RuntimeError("Kaggle completed but no MP4 was downloaded")
        result = max(videos, key=lambda p: p.stat().st_size)
        if result.stat().st_size < 100_000:
            raise RuntimeError(f"Generated MP4 too small: {result.stat().st_size} bytes")
        r2_key = persist(result, video_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"video_id": video_id, "kernel_id": kernel_id, "source_image": str(source), "output": str(result), "r2_key": r2_key, "bytes": result.stat().st_size}
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
