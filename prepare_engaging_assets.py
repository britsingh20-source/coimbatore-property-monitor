import json
import os
from pathlib import Path

from cloudflare_ai_visual_pipeline import generate_for_job
from engaging_broll_pool import source_engaging_broll
from map_assets import render_map_sequence
from tamil_voiceover import create_voiceover
from video_pipeline import JOBS


def queued_ids() -> set[str]:
    path = Path(os.environ.get("VIDEO_IDS_FILE", "data/render_queue.txt"))
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def has_complete_ai(video_id: str) -> bool:
    root = Path("assets/ai_broll") / video_id
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    scenes = manifest.get("scenes") or []
    if not scenes:
        return False
    for row in scenes:
        video = Path(str(row.get("video") or ""))
        still = Path(str(row.get("still") or ""))
        if not video.exists() or video.stat().st_size < 100_000:
            return False
        if not still.exists() or still.stat().st_size < 50_000:
            return False
    return True


def env_true(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    queue = queued_ids()
    if not queue:
        print("No queued IDs. Nothing prepared.")
        return

    force_regenerate = env_true("FORCE_REGENERATE_AI")
    failure_path = Path(os.environ.get("ASSET_FAILURES_FILE", "outputs/asset-failure-ids.txt"))
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text("", encoding="utf-8")
    failures = []

    for video_id in queue:
        try:
            job = json.loads((JOBS / f"{video_id}.json").read_text(encoding="utf-8"))

            if has_complete_ai(video_id) and not force_regenerate:
                print(f"Reusing complete cached AI scene pack for {video_id}; no image-generation credits consumed.")
            else:
                has_cloudflare = bool(
                    (os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip() or os.environ.get("R2_ACCOUNT_ID", "").strip())
                    and os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
                )
                has_pollinations = bool(os.environ.get("POLLINATIONS_API_KEY", "").strip())
                has_hf = bool(os.environ.get("HF_TOKEN", "").strip())
                if not has_cloudflare and not has_pollinations and not has_hf:
                    raise RuntimeError(
                        "A fresh AI scene pack is required. Configure Cloudflare Workers AI credentials "
                        "(preferred), POLLINATIONS_API_KEY, or HF_TOKEN."
                    )
                if has_cloudflare:
                    backend = "Cloudflare Workers AI FLUX.1-schnell"
                elif has_pollinations:
                    backend = "Pollinations Flux fallback"
                else:
                    backend = "Hugging Face fallback"
                reason = "forced fresh test" if force_regenerate else "cache miss"
                print(f"Generating fresh AI scene pack for {video_id} with {backend} ({reason}).")
                generate_for_job(job)

            if not has_complete_ai(video_id):
                raise RuntimeError(f"AI scene pack is incomplete for {video_id}; refusing stock fallback")

            clips = source_engaging_broll(job)
            maps = render_map_sequence(job)
            voice = create_voiceover(job)
            print(f"Prepared {video_id}: AI-only clips={len(clips)}, maps={len(maps)}, voice={voice}")
        except Exception as error:
            failures.append(f"{video_id}: {error}")
            with failure_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{video_id}\n")
            print(f"AI-ONLY ASSET FAILURE {video_id}: {error}")

    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
