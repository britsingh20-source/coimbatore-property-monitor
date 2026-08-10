import json
import os
from pathlib import Path

from meta_publisher import publish
from social_caption import build_caption


QUEUE = Path(os.environ.get("VIDEO_IDS_FILE", "data/render_queue.txt"))
OUTPUT_DIR = Path("outputs/social_publish")
PLATFORMS = {
    item.strip().lower()
    for item in os.environ.get("META_PLATFORMS", "instagram,facebook").split(",")
    if item.strip()
}


def _video_path(video_id: str) -> Path:
    root = Path("outputs") / video_id
    preferred = root / f"{video_id}-professional-vertical.mp4"
    fallback = root / "final-free-vertical.mp4"
    if preferred.exists():
        return preferred
    if fallback.exists():
        return fallback
    mp4s = sorted(root.glob("*.mp4"), key=lambda path: path.stat().st_size, reverse=True)
    if mp4s:
        return mp4s[0]
    raise FileNotFoundError(f"No completed MP4 found for {video_id}")


def _ids() -> list[str]:
    if not QUEUE.exists():
        return []
    return [
        line.strip()
        for line in QUEUE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for video_id in _ids():
        try:
            job_path = Path("data/video_jobs") / f"{video_id}.json"
            job = json.loads(job_path.read_text(encoding="utf-8"))
            caption = build_caption(job)
            result = publish(_video_path(video_id), video_id, caption, PLATFORMS)
            (OUTPUT_DIR / f"{video_id}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Meta publish completed for {video_id}: {list(result['platforms'])}")
        except Exception as error:
            failures.append(f"{video_id}: {error}")
            print(f"META PUBLISH ERROR {video_id}: {error}")
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
