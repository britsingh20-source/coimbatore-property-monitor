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
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    preferred_roots = [Path("assets/properties") / video_id, Path("assets/media") / video_id, Path("assets") / video_id]
    for root in preferred_roots:
        if not root.exists():
            continue
        candidates = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in allowed and "map" not in str(p).lower() and "thumbnail" not in str(p).lower()]
        if candidates:
            return max(candidates, key=lambda p: p.stat().st_size)
    candidates = [p for root in (Path("assets"), Path("data")) if root.exists() for p in root.rglob("*") if p.is_file() and p.suffix.lower() in allowed and video_id.lower() in str(p).lower() and "map" not in str(p).lower() and "thumbnail" not in str(p).lower()]
    if not candidates:
        raise RuntimeError(f"No property-specific source image found for {video_id}; run media preparation first")
    return max(candidates, key=lambda p: p.stat().st_size)


def build_prompt(job: dict) -> str:
    prop = job.get("property", {})
    location = job.get("property_location") or job.get("location") or "Coimbatore, Tamil Nadu, India"
    ptype = prop.get("property_type") or "residential property"
    bhk = prop.get("bhk") or ""
    return re.sub(r"\s+", " ", f"Photorealistic real-estate footage of this exact {bhk} {ptype} in {location}. Preserve the visible building or room geometry, materials and details from the reference image. Create only subtle realistic camera motion: slow stabilized gimbal push-in with gentle parallax, natural daylight, realistic Indian residential context, no people, no text, no logos, no religious buildings. Do not invent extra floors, doors, windows, furniture or surrounding landmarks. Professional property walkthrough B-roll.").strip()


def kernel_script(image_b64: str, image_suffix: str, ltx_b64: str, prompt: str, video_id: str) -> str:
    return f'''import base64
import os
import shutil
import subprocess
import tarfile
import traceback
from pathlib import Path

import yaml

PROMPT = {prompt!r}
VIDEO_ID = {video_id!r}
IMAGE_SUFFIX = {image_suffix!r}
IMAGE_B64 = {image_b64!r}
LTX_B64 = {ltx_b64!r}
work = Path("/kaggle/working")
inputs = Path("/kaggle/input")
progress = work / "progress.txt"
failure = work / "failure.txt"

def mark(message):
    print(message, flush=True)
    with progress.open("a", encoding="utf-8") as fh:
        fh.write(message + "\\n")

def choose_file(patterns):
    hits = []
    for pattern in patterns:
        hits.extend(inputs.rglob(pattern))
    hits = [p for p in hits if p.is_file()]
    if not hits:
        return None
    return max(hits, key=lambda p: p.stat().st_size)

def choose_text_encoder_dir():
    candidates = []
    for tok in inputs.rglob("tokenizer_config.json"):
        parent = tok.parent
        low = str(parent).lower()
        if any(key in low for key in ("pixart", "t5", "text_encoder", "text-encoder")):
            candidates.append(parent)
    return candidates[0] if candidates else None

try:
    mark("stage=decode_embedded_source")
    image_path = work / ("source" + IMAGE_SUFFIX)
    image_path.write_bytes(base64.b64decode(IMAGE_B64))
    mark(f"source_bytes={{image_path.stat().st_size}}")

    mark("stage=unpack_embedded_ltx")
    archive = work / "ltx-video-src.tar.gz"
    archive.write_bytes(base64.b64decode(LTX_B64))
    mark(f"ltx_archive_bytes={{archive.stat().st_size}}")
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(work)
    repo = work / "LTX-Video"
    if not (repo / "inference.py").exists():
        raise RuntimeError("Embedded LTX source unpacked but inference.py is missing")

    mark("stage=patch_optional_pyav")
    crf_file = repo / "ltx_video" / "pipelines" / "crf_compressor.py"
    crf_file.write_text("import torch\\n\\ndef compress(image: torch.Tensor, crf=29):\\n    return image\\n", encoding="utf-8")
    mark("pyav_bypass=identity_crf")

    mark("stage=discover_kaggle_model_inputs")
    checkpoint = choose_file(["ltxv-2b-0.9.8-distilled.safetensors", "*2b*0.9.8*distilled*.safetensors"])
    upscaler = choose_file(["ltxv-spatial-upscaler-0.9.8.safetensors", "*spatial*upscaler*0.9.8*.safetensors"])
    encoder_dir = choose_text_encoder_dir()
    if checkpoint is None:
        inventory = [str(p) for p in inputs.rglob("*.safetensors")][:80]
        raise RuntimeError("No LTX 2B checkpoint found in attached Kaggle inputs. safetensors=" + repr(inventory))
    mark(f"checkpoint={{checkpoint}} bytes={{checkpoint.stat().st_size}}")
    if upscaler:
        mark(f"upscaler={{upscaler}} bytes={{upscaler.stat().st_size}}")
    else:
        mark("upscaler=not_found")
    mark(f"text_encoder_dir={{encoder_dir if encoder_dir else 'not_found'}}")

    config_path = repo / "configs" / "ltxv-2b-0.9.8-distilled.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg["checkpoint_path"] = str(checkpoint)
    if upscaler:
        cfg["spatial_upscaler_model_path"] = str(upscaler)
    if encoder_dir:
        cfg["text_encoder_model_name_or_path"] = str(encoder_dir)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    mark("local_model_paths_patched=true")

    mark("stage=dependency_probe")
    probe_code = "import torch, transformers, diffusers, PIL, safetensors, yaml; print('deps-ok')"
    probe = subprocess.run(["python", "-c", probe_code], cwd=repo, text=True, capture_output=True)
    mark(f"dependency_probe_rc={{probe.returncode}}")
    if probe.returncode != 0:
        raise RuntimeError("Kaggle image is missing LTX runtime dependencies: " + probe.stderr[-3000:])

    mark("stage=source_import_probe")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    src_probe = subprocess.run(["python", "-c", "import ltx_video; import ltx_video.inference; print('ltx-source-ok')"], cwd=repo, env=env, text=True, capture_output=True)
    mark(f"source_import_probe_rc={{src_probe.returncode}}")
    if src_probe.returncode != 0:
        raise RuntimeError("LTX source import failed without pip install: " + src_probe.stderr[-3000:])

    mark("stage=run_inference_offline")
    before = set(repo.rglob("*.mp4"))
    cmd = ["python", "inference.py", "--prompt", PROMPT, "--conditioning_media_paths", str(image_path), "--conditioning_start_frames", "0", "--height", "512", "--width", "320", "--num_frames", "49", "--seed", "42", "--pipeline_config", str(config_path)]
    mark("command=" + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=repo, env=env, text=True, capture_output=True)
    (work / "inference-stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (work / "inference-stderr.txt").write_text(proc.stderr or "", encoding="utf-8")
    mark(f"inference_rc={{proc.returncode}}")
    if proc.returncode != 0:
        raise RuntimeError("Offline LTX inference failed: " + (proc.stderr or proc.stdout)[-7000:])

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


def reusable_sources(source_metadata: dict) -> dict:
    return {
        "dataset_sources": source_metadata.get("dataset_sources", []) or [],
        "kernel_sources": source_metadata.get("kernel_sources", []) or [],
        "competition_sources": source_metadata.get("competition_sources", []) or [],
        "model_sources": source_metadata.get("model_sources", []) or [],
    }


def write_kernel(folder: Path, username: str, source_image: Path, ltx_bundle: Path, prompt: str, video_id: str, source_metadata: dict) -> str:
    kernel_id = f"{username}/coimbatore-property-ai-b-roll"
    image_b64 = base64.b64encode(source_image.read_bytes()).decode("ascii")
    ltx_b64 = base64.b64encode(ltx_bundle.read_bytes()).decode("ascii")
    (folder / "ai_broll_kernel.py").write_text(kernel_script(image_b64, source_image.suffix.lower() or ".jpg", ltx_b64, prompt, video_id), encoding="utf-8")
    sources = reusable_sources(source_metadata)
    metadata = {
        "id": kernel_id,
        "title": "Coimbatore Property AI B-roll",
        "code_file": "ai_broll_kernel.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": False,
        "keywords": ["real-estate"],
        **sources,
    }
    (folder / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("Reusing Kaggle input sources: " + json.dumps(sources, ensure_ascii=False), flush=True)
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
    for name in ("progress.txt", "failure.txt", "inference-stderr.txt", "inference-stdout.txt"):
        matches = list(dest.rglob(name))
        if matches:
            print(f"===== KAGGLE {name} =====", flush=True)
            print(matches[0].read_text(encoding="utf-8", errors="replace")[-16000:], flush=True)


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
    r2_client().upload_file(str(path), required("R2_BUCKET_NAME"), key, ExtraArgs={"ContentType": "video/mp4"})
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--job", default="")
    parser.add_argument("--ltx-bundle", default=".cache/ltx-video-src.tar.gz")
    parser.add_argument("--source-metadata", required=True)
    parser.add_argument("--output-dir", default="outputs/kaggle-ai-broll")
    args = parser.parse_args()

    username = required("KAGGLE_USERNAME")
    required("KAGGLE_API_TOKEN")
    video_id = args.video_id.strip()
    job_path = Path(args.job) if args.job else Path("data/video_jobs") / f"{video_id}.json"
    ltx_bundle = Path(args.ltx_bundle)
    source_metadata_path = Path(args.source_metadata)
    if not ltx_bundle.exists():
        raise RuntimeError(f"Offline LTX bundle missing: {ltx_bundle}")
    if not source_metadata_path.exists():
        raise RuntimeError(f"Kaggle source metadata missing: {source_metadata_path}")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    source_metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
    source_image = find_source_image(video_id)
    prompt = build_prompt(job)
    print(f"Source image embedded: {source_image} ({source_image.stat().st_size} bytes)", flush=True)
    print(f"Offline LTX bundle embedded: {ltx_bundle} ({ltx_bundle.stat().st_size} bytes)", flush=True)

    out_dir = Path(args.output_dir) / video_id
    diag_dir = out_dir / "kaggle-output"
    with tempfile.TemporaryDirectory(prefix="kaggle-ai-broll-") as tmp:
        kernel_id = write_kernel(Path(tmp), username, source_image, ltx_bundle, prompt, video_id, source_metadata)
        proc = run(["kaggle", "kernels", "push", "-p", tmp, "--accelerator", "NvidiaTeslaP100", "--timeout", "3600"])
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
        summary = {"video_id": video_id, "source_image": str(source_image), "kernel_id": kernel_id, "output": str(result), "r2_key": r2_key, "bytes": result.stat().st_size, "input_delivery": "embedded_base64", "ltx_delivery": "embedded_tarball", "kaggle_internet": False, "ltx_execution": "source_via_pythonpath", "pyav_mode": "bypassed_identity_crf", "model_delivery": "reused_public_kaggle_inputs"}
        (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
