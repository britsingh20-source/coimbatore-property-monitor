import argparse
import json
import os
import subprocess
from pathlib import Path


RENDERABLE_STATUSES = {"auto_approved", "approved"}


def read_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def changed_job_ids(before: str, after: str) -> set[str]:
    if not before or set(before) == {"0"}:
        return set()
    result = subprocess.run(
        ["git", "diff", "--name-only", before, after, "--", "data/video_jobs/*.json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {Path(line).stem for line in result.stdout.splitlines() if line.strip()}


def renderable_ids(jobs_dir: Path) -> set[str]:
    selected = set()
    for path in jobs_dir.glob("*.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if job.get("status") in RENDERABLE_STATUSES:
            selected.add(str(job.get("video_id") or path.stem))
    return selected


def select_ids(event_name: str, jobs_dir: Path, approved_file: Path, before: str, after: str) -> list[str]:
    renderable = renderable_ids(jobs_dir)
    explicitly_approved = read_ids(approved_file)
    if event_name == "push":
        selected = changed_job_ids(before, after) & renderable
    elif event_name == "pull_request":
        selected = explicitly_approved
    else:
        selected = renderable | explicitly_approved
    return sorted(video_id for video_id in selected if (jobs_dir / f"{video_id}.json").exists())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", type=Path, default=Path("data/video_jobs"))
    parser.add_argument("--approved-file", type=Path, default=Path("data/approved_video_ids.txt"))
    parser.add_argument("--output", type=Path, default=Path("data/render_queue.txt"))
    parser.add_argument("--event-name", default=os.environ.get("EVENT_NAME", "workflow_dispatch"))
    parser.add_argument("--before", default=os.environ.get("BEFORE_SHA", ""))
    parser.add_argument("--after", default=os.environ.get("AFTER_SHA", "HEAD"))
    args = parser.parse_args()

    selected = select_ids(args.event_name, args.jobs_dir, args.approved_file, args.before, args.after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(f"{video_id}\n" for video_id in selected), encoding="utf-8")
    print(f"Selected {len(selected)} render job(s): {', '.join(selected) if selected else 'none'}")


if __name__ == "__main__":
    main()
