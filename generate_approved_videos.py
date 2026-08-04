from pathlib import Path

from video_pipeline import JOBS, approved_ids, generate_job


def main() -> None:
    approvals = approved_ids()
    if not approvals:
        print("No approved video IDs. Nothing will be generated or charged.")
        return
    for video_id in approvals:
        job = JOBS / f"{video_id}.json"
        if not job.exists():
            print(f"Missing job for approved ID: {video_id}")
            continue
        print(f"Generated: {generate_job(job)}")


if __name__ == "__main__":
    main()
