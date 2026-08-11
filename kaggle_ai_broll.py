import argparse
import base64
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
    # Prefer actual property/media images and explicitly avoid maps/thumbnails.
    preferred_roots = [
        Path("assets/properties") / video_id,
        Path("assets/media") / video_id,
        Path("assets") / video_id,
    ]
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    for root in preferred_roots:
        if not root.exists():
            continue
        candidates = [
            p for p in root.rglob("*")
            if p.is_file()
            and p.suffix.lower() in allowed
            and "map" not in p.name.lower()
            and "thumbnail" not in p.name.lower()
        ]
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_size)

    candidates = []
    for root in (Path("assets"), Path("data")):
        if not root.exists():
            continue
        for p in root.rglob("*"):
            text = str(p).lower()
            if (
                p.is_file()
                and p.suffix.lower() in allowed
                and video_id.lower() in text
                and "map" not in text
                and "thumbnail" not in text
            ):
                candidates.append(p)
    if not candidates:
        raise RuntimeError(f"No property-specific source image found for {video_id}; run media preparation first")
    return max(candidates, key=lambda p: p.stat().st_size)


def build_prompt(job: dict) -> str:
    prop = job.get("property", {})
    location = job.get("property_location") or job.get("location") or "Coimbatore, Tamil Nadu, India"
    property_type = prop.get("property_type") or "residential property"
    bhk = prop.get("bhk") or ""
    return re.sub(
        r"\s+",
        " ",
        f"Photorealistic real-estate footage of this exact {bhk} {property_type} in {location}. "
        "Preserve the visible building or room geometry, materials and details from the reference image. "
        "Create only subtle realistic camera motion: slow stabilized gimbal push-in with gentle parallax, "
        "natural daylight, realistic Indian residential context, no people, no text, no logos, no religious buildings. "
        "Do not invent extra floors, doors, windows, furniture or surrounding landmarks. Professional property walkthrough B-roll.",
    ).strip()


def kernel_script(image_b64: str, image_suffix: str, prompt: str, video_id: str) -> str:
    # Input image is embedded directly so Kaggle does not need to reach Cloudflare R2.
    return f'''import base64
import shutil
import subprocess
import traceback
from pathlib import Path

PROMPT = {prompt!r}
VIDEO_ID = {video_id!r}
IMAGE_SUFFIX = {image_suffix!r}
IMAGE_B64 = {image_b64!r}
work = Path("/kaggle/working")
progress = work / "progress.txt"
failure = work / "failure.txt"


def mark(message):
    print(message, flush=True)
    with progress.open("a", encoding="utf-8") as fh:
        fh.write(message + "\\n")


try:
    mark("stage=decode_embedded_source")
    image_path = work / ("source" + IMAGE_SUFFIX)
    image_path.write_bytes(base64.b64decode(IMAGE_B64))
    mark(f"source_path={{image_path}} source_bytes={{image_path.stat().st_size}}")
    if image_path.stat().st_size < 10_000:
        raise RuntimeError("Embedded source image is unexpectedly small")

    mark("stage=network_probe_github")
    probe = subprocess.run(["git", "ls-remote", "https://github.com/Lightricks/LTX-Video.git", "HEAD"], text=True, capture_output=True, timeout=45)
    mark(f"github_probe_rc={{probe.returncode}}")
    if probe.returncode != 0:
        raise RuntimeError("Kaggle internet cannot reach GitHub: " + probe.stderr[-1000:])

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


def write_kernel(folder: Path, username: str, source_image: Path, prompt: str, video_id: str) -> str:
    slug = "coimbatore-property-ai-b-roll"
    kernel_id = f"{username}/{slug}"
    image_b64 = base64.b64encode(source_image.read_bytes()).decode("ascii")
    script = kernel_script(image_b64, source_image.suffix.lower() or ".jpg", prompt, video_id)
    (folder / "ai_broll_kernel.py").write_text(script, encoding="utf-8")
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
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": [],
        "model_sources": [],
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


def wait_for_kernel(kernel_id: str, diag_dir: Path) -> None:
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
    parser.add_argument("--output-dir", default="outputs/kaggle-ai-broll")
    args = parser.parse_args()

    username = required("KAGGLE_USERNAME")
    required("KAGGLE_API_TOKEN")
    video_id = args.video_id.strip()
    job_path = Path(args.job) if args.job else Path("data/video_jobs") / f"{video_id}.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    source_image = find_source_image(video_id)
    prompt = build_prompt(job)
    print(f"Source image embedded directly into Kaggle kernel: {source_image} ({source_image.stat().st_size} bytes)", flush=True)
    print(f"Prompt: {prompt}", flush=True)

    out_dir = Path(args.output_dir) / video_id
    diag_dir = out_dir / "kaggle-output"
    with tempfile.TemporaryDirectory(prefix="kaggle-ai-broll-") as tmp:
        kernel_dir = Path(tmp)
        kernel_id = write_kernel(kernel_dir, username, source_image, prompt, video_id)
        proc = run(["kaggle", "kernels", "push", "-p", str(kernel_dir), "--accelerator", "NvidiaTeslaP100", "--timeout", "3600"])
        print(proc.stdout, flush=True)
        print(proc.stderr, flush=True)
        if proc.returncode != 0:
            raise RuntimeError("Kaggle kernel push failed")

        wait_for_kernel(kernel_id, diag_dir)
        download_kernel_output(kernel_id, diag_dir)
        print_diagnostics(diag_dir)
        videos = list(diag_dir.rglob(f"{video_id}-ai-broll.mp4")) or list(diag_dir.rglob("*.mp4"))
        if not videos:
            raise RuntimeError("Kaggle completed but no MP4 was downloaded")
        result = max(videos, key=lambda p: p.stat().st_size)
        if result.stat().st_size < 100_000:
            raise RuntimeError(f"Generated B-roll is suspiciously small: {result.stat().st_size} bytes")

        r2_key = persist_to_r2(result, video_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "video_id": video_id,
            "source_image": str(source_image),
            "prompt": prompt,
            "kernel_id": kernel_id,
            "output": str(result),
            "r2_key": r2_key,
            "bytes": result.stat().st_size,
            "input_delivery": "embedded_base64",
        }
        (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
