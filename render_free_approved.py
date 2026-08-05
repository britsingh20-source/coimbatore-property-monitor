import os
from pathlib import Path

from free_video_renderer import render_job
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


def main() -> None:
    queue = queued_ids()
    if not queue:
        print("No queued IDs. Nothing rendered.")
        return
    failures = []
    for video_id in queue:
        job = JOBS / f"{video_id}.json"
        try:
            print(f"Rendered: {render_job(job)}")
        except Exception as error:
            failures.append(f"{video_id}: {error}")
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
