from video_pipeline import JOBS, approved_ids
from free_video_renderer import render_job


def main() -> None:
    approvals = approved_ids()
    if not approvals:
        print("No approved IDs. Nothing rendered.")
        return
    failures = []
    for video_id in approvals:
        job = JOBS / f"{video_id}.json"
        try:
            print(f"Rendered: {render_job(job)}")
        except Exception as error:
            failures.append(f"{video_id}: {error}")
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
