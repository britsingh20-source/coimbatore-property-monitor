import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


STATE_PATH = Path("data/state.json")
RETRYABLE = {"discovered", "retry_pending"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"videos": {}}
    with STATE_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(STATE_PATH)


def register_videos(state: dict, videos: list[dict]) -> None:
    now = utc_now().isoformat()
    for video in videos:
        video_id = video["video_id"]
        state["videos"].setdefault(video_id, {
            "status": "discovered",
            "attempts": 0,
            "first_seen_at": now,
            "next_retry_at": now,
        })


def eligible(state: dict, video: dict) -> bool:
    record = state["videos"].get(video["video_id"], {})
    if record.get("status") not in RETRYABLE:
        return False
    next_retry = record.get("next_retry_at")
    return not next_retry or datetime.fromisoformat(next_retry) <= utc_now()


def mark_success(state: dict, video_id: str, target: bool) -> None:
    record = state["videos"][video_id]
    record.update({
        "status": "video_queued" if target else "archived_non_target",
        "completed_at": utc_now().isoformat(),
        "last_error": "",
    })


def mark_failure(state: dict, video_id: str, error: Exception) -> None:
    record = state["videos"][video_id]
    attempts = int(record.get("attempts", 0)) + 1
    delay_hours = min(24, 2 ** min(attempts, 4))
    record.update({
        "status": "retry_pending" if attempts < 6 else "manual_review",
        "attempts": attempts,
        "last_error": str(error)[:1000],
        "last_attempt_at": utc_now().isoformat(),
        "next_retry_at": (utc_now() + timedelta(hours=delay_hours)).isoformat(),
    })
