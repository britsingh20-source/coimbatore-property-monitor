from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import unicodedata

import requests

from interior_social_autopilot import handle_update as handle_interior_update, interior_id
from telegram_r2_ingest import ingest as handle_property_updates

STATE_PATH = Path(os.environ.get("TELEGRAM_INGEST_STATE", "data/telegram_ingest_state.json"))
QUEUE_PATH = Path(os.environ.get("TELEGRAM_PROMPT_QUEUE", "data/telegram_prompt_queue.json"))

# User-confirmed recovery from the 2026-09-12 Telegram screenshot. The uploaded
# MP4 belongs to the prompt shown immediately above it, VIDEO_ID Fs9ObmoAxhY.
# The separately typed BN27nDLnj fs is an older already-published VIDEO_ID and
# must never be allowed to reassign this new upload.
CONFIRMED_PAIRINGS = {
    "AgADkSEAAuovKVU": "Fs9ObmoAxhY",
}


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def telegram(method: str, token: str, data: dict | None = None) -> dict:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data or {},
        timeout=60,
    )
    body = response.json()
    if not response.ok or not body.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {body.get('description') or body}")
    return body


def _load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_cursor() -> int:
    state = _load_json(STATE_PATH, {})
    return int(state.get("last_update_id") or 0)


def advance_cursor(update_id: int) -> None:
    state = _load_json(STATE_PATH, {"files": {}})
    state["last_update_id"] = max(int(state.get("last_update_id") or 0), int(update_id or 0))
    _save_json(STATE_PATH, state)


def _video_attachment(message: dict) -> dict | None:
    video = message.get("video")
    if video:
        return video
    document = message.get("document")
    mime = str((document or {}).get("mime_type") or "").lower()
    filename = str((document or {}).get("file_name") or "").lower()
    if document and (mime.startswith("video/") or filename.endswith(".mp4")):
        return document
    return None


def _normalized_video_id(message: dict) -> str:
    """Extract a mobile-safe 11-character VIDEO_ID.

    Accepts forms such as:
      VIDEO_ID: Fs9ObmoAxhY
      Video ID: Fs9 ObmoAxhY
      Fs9ObmoAxhY

    Internal whitespace and invisible Unicode format characters are ignored only
    inside the candidate ID, never across arbitrary prose.
    """
    text = str(message.get("caption") or message.get("text") or "").strip()
    if not text:
        return ""

    labelled = re.search(r"(?:video[\s_-]*id|id)\s*[:=\-]\s*(.+)$", text, flags=re.I)
    candidate = labelled.group(1).strip() if labelled else text
    compact = "".join(
        char
        for char in candidate
        if not char.isspace() and unicodedata.category(char) != "Cf"
    )
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", compact):
        return compact
    return ""


def _pending_prompt(video_id: str) -> dict | None:
    queue = _load_json(QUEUE_PATH, {"prompts": []})
    return next(
        (
            item
            for item in queue.get("prompts", [])
            if item.get("video_id") == video_id
            and item.get("status") == "pending_mobile_upload"
        ),
        None,
    )


def _remember_preceding_video_id(update: dict, video_id: str) -> None:
    state = _load_json(STATE_PATH, {"files": {}})
    state["pending_preceding_video_id"] = {
        "video_id": video_id,
        "update_id": int(update.get("update_id") or 0),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    state["last_update_id"] = max(
        int(state.get("last_update_id") or 0),
        int(update.get("update_id") or 0),
    )
    _save_json(STATE_PATH, state)


def _take_preceding_video_id(update_id: int) -> str:
    state = _load_json(STATE_PATH, {"files": {}})
    pending = state.get("pending_preceding_video_id") or {}
    video_id = str(pending.get("video_id") or "").strip()
    saved_update_id = int(pending.get("update_id") or 0)
    # Only carry an ID to the immediately following few Telegram updates. This
    # avoids a stale ID being attached to a later unrelated video.
    if video_id and 0 < int(update_id or 0) - saved_update_id <= 3 and _pending_prompt(video_id):
        return video_id
    if pending:
        state.pop("pending_preceding_video_id", None)
        _save_json(STATE_PATH, state)
    return ""


def _clear_preceding_video_id() -> None:
    state = _load_json(STATE_PATH, {"files": {}})
    if state.pop("pending_preceding_video_id", None) is not None:
        _save_json(STATE_PATH, state)


def recover_confirmed_pairings() -> None:
    """Idempotently pair user-confirmed unmatched R2 uploads before publishing."""
    state = _load_json(STATE_PATH, {"files": {}})
    queue = _load_json(QUEUE_PATH, {"prompts": []})
    changed = False

    for unique_id, video_id in CONFIRMED_PAIRINGS.items():
        item = state.setdefault("files", {}).get(unique_id)
        if not item or not item.get("r2_key"):
            continue
        if item.get("status") not in {
            "uploaded_awaiting_content_match",
            "uploaded_awaiting_video_id",
            "uploaded_exact_video_id",
        }:
            continue

        prompt = next(
            (entry for entry in queue.get("prompts", []) if entry.get("video_id") == video_id),
            None,
        )
        if prompt is None:
            continue

        already_paired = (
            item.get("status") == "uploaded_exact_video_id"
            and item.get("video_id") == video_id
            and prompt.get("r2_key") == item.get("r2_key")
        )
        if already_paired:
            continue

        now = datetime.now(timezone.utc).isoformat()
        item.update(
            {
                "status": "uploaded_exact_video_id",
                "video_id": video_id,
                "paired_at": now,
                "paired_by": "user_confirmed_screenshot_2026-09-12",
            }
        )
        item.pop("candidate_video_ids", None)
        prompt.update(
            {
                "status": "assigned_to_r2_upload",
                "r2_key": item["r2_key"],
                "telegram_file_unique_id": unique_id,
                "uploaded_at": item.get("uploaded_at") or now,
            }
        )
        changed = True
        print(f"Recovered {unique_id} -> VIDEO_ID {video_id} -> {item['r2_key']}")

    if changed:
        _save_json(STATE_PATH, state)
        _save_json(QUEUE_PATH, queue)


def route_one(update: dict) -> None:
    message = update.get("message") or update.get("edited_message") or {}
    if interior_id(message):
        print(f"Routing Telegram update {update.get('update_id')} to Interior publisher")
        handle_interior_update(update)
        advance_cursor(int(update.get("update_id") or 0))
        return

    attachment = _video_attachment(message)
    supplied_id = _normalized_video_id(message)

    # Support the user's normal mobile flow: send/copy the VIDEO_ID first, then
    # upload the MP4 as the next Telegram message. Only a currently pending
    # prompt may be remembered; an old published VIDEO_ID is rejected safely.
    if attachment is None and supplied_id:
        if _pending_prompt(supplied_id):
            _remember_preceding_video_id(update, supplied_id)
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
            chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
            if token and chat_id:
                telegram(
                    "sendMessage",
                    token,
                    {
                        "chat_id": chat_id,
                        "text": f"✅ VIDEO_ID {supplied_id} saved. Send the matching MP4 as your next message.",
                    },
                )
            print(f"Saved preceding VIDEO_ID {supplied_id} for next property MP4")
            return

    routed_update = update
    carried_id = ""
    if attachment is not None and not supplied_id:
        carried_id = _take_preceding_video_id(int(update.get("update_id") or 0))
        if carried_id:
            routed_update = json.loads(json.dumps(update))
            routed_message = routed_update.get("message") or routed_update.get("edited_message") or {}
            routed_message["caption"] = f"VIDEO_ID: {carried_id}"
            print(f"Applying preceding VIDEO_ID {carried_id} to Telegram video update {update.get('update_id')}")

    print(f"Routing Telegram update {update.get('update_id')} to Property publisher")
    old = os.environ.get("TELEGRAM_WEBHOOK_UPDATE_JSON")
    os.environ["TELEGRAM_WEBHOOK_UPDATE_JSON"] = json.dumps(routed_update, ensure_ascii=False)
    try:
        handle_property_updates()
        if carried_id:
            _clear_preceding_video_id()
    finally:
        if old is None:
            os.environ.pop("TELEGRAM_WEBHOOK_UPDATE_JSON", None)
        else:
            os.environ["TELEGRAM_WEBHOOK_UPDATE_JSON"] = old


def main() -> None:
    recover_confirmed_pairings()

    supplied = os.environ.get("TELEGRAM_WEBHOOK_UPDATE_JSON", "").strip()
    if supplied:
        route_one(json.loads(supplied))
        return

    token = required("TELEGRAM_BOT_TOKEN")
    offset = load_cursor() + 1
    body = telegram(
        "getUpdates",
        token,
        {
            "offset": str(offset),
            "limit": "100",
            "timeout": "0",
            "allowed_updates": json.dumps(["message", "edited_message"]),
        },
    )
    updates = body.get("result") or []
    if not updates:
        print("No new Telegram messages for router.")
        return

    for update in updates:
        route_one(update)


if __name__ == "__main__":
    main()
