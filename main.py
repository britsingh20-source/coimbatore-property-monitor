import os

from location_matcher import match_location
from property_analyzer import RetryableAnalysisError, analyze_property
from records import legacy_retry_videos, upsert_record
from state_store import (
    eligible,
    load_state,
    mark_failure,
    mark_success,
    register_videos,
    save_state,
)
from video_pipeline import build_video_job
from youtube_monitor import main as monitor_channels


MAX_PER_RUN = int(os.environ.get("MAX_VIDEOS_PER_RUN", "3"))


def run() -> None:
    state = load_state()
    recent = monitor_channels()
    recent_ids = {video["video_id"] for video in recent}
    videos = recent + [
        video for video in legacy_retry_videos()
        if video["video_id"] not in recent_ids
    ]
    register_videos(state, videos)

    queue = [video for video in videos if eligible(state, video)][:MAX_PER_RUN]
    print(
        f"Recent: {len(recent)} | Including legacy retries: {len(videos)} "
        f"| Eligible now: {len(queue)}"
    )

    hard_failures = 0
    retryable_failures = 0
    for video in queue:
        video_id = video["video_id"]
        try:
            result = analyze_property(video)
            location = match_location(
                video.get("title", ""),
                video.get("description", ""),
                result.get("location", ""),
                result.get("nearby_landmarks", []).__str__(),
            )
            upsert_record(video, result, location)
            if result.get("is_property_listing") and location["is_target_location"]:
                build_video_job(video, result, location)
            mark_success(state, video_id, bool(location["is_target_location"]))
            print(f"Processed {video_id}: target={location['is_target_location']}")
        except RetryableAnalysisError as error:
            retryable_failures += 1
            mark_failure(state, video_id, error)
            print(f"RETRY {video_id}: {error}")
        except Exception as error:
            hard_failures += 1
            mark_failure(state, video_id, error)
            print(f"ERROR {video_id}: {error}")
        finally:
            save_state(state)

    if retryable_failures:
        print(f"Deferred {retryable_failures} video(s) because of transient API/quota conditions; state backoff will retry them automatically.")
    if hard_failures:
        raise RuntimeError(f"{hard_failures} video(s) failed with non-retryable errors")


if __name__ == "__main__":
    run()
