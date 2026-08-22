from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

import boto3
import requests


STATE_PATH = Path(os.environ.get("TELEGRAM_INGEST_STATE", "data/telegram_ingest_state.json"))
QUEUE_PATH = Path(os.environ.get("TELEGRAM_PROMPT_QUEUE", "data/telegram_prompt_queue.json"))
PREFIX = os.environ.get("R2_SOCIAL_PREFIX", "social-ready/").strip().lstrip("/")
MAX_BYTES = int(os.environ.get("TELEGRAM_MAX_VIDEO_BYTES", str(20 * 1024 * 1024)))


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _load(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _r2():
    account_id = _required("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=_required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def _telegram(method: str, token: str, *, data: dict | None = None, timeout: int = 60) -> dict:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data or {},
        timeout=timeout,
    )
    try:
        body = response.json()
    except ValueError as error:
        raise RuntimeError(f"Telegram {method} returned HTTP {response.status_code}") from error
    if not response.ok or not body.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {body.get('description') or body}")
    return body


def _send(token: str, chat_id: str, text: str) -> None:
    _telegram("sendMessage", token, data={"chat_id": chat_id, "text": text})


def _video_attachment(message: dict) -> dict | None:
    video = message.get("video")
    if video:
        return video
    document = message.get("document")
    mime = str((document or {}).get("mime_type") or "").lower()
    if document and (mime.startswith("video/") or str(document.get("file_name") or "").lower().endswith(".mp4")):
        return document
    return None


def _oldest_pending(queue: dict) -> dict | None:
    pending = [
        item for item in queue.get("prompts", [])
        if item.get("status") == "pending_mobile_upload" and item.get("video_id")
    ]
    pending.sort(key=lambda item: str(item.get("sent_at") or ""))
    return pending[0] if pending else None


def ingest() -> int:
    token = _required("TELEGRAM_BOT_TOKEN")
    chat_id = _required("TELEGRAM_CHAT_ID")
    bucket = _required("R2_BUCKET_NAME")
    state = _load(STATE_PATH, {"last_update_id": 0, "files": {}})
    queue = _load(QUEUE_PATH, {"prompts": []})
    offset = int(state.get("last_update_id") or 0) + 1

    body = _telegram(
        "getUpdates",
        token,
        data={"offset": str(offset), "limit": "100", "timeout": "0", "allowed_updates": json.dumps(["message"])},
    )
    updates = body.get("result") or []
    if not updates:
        print("No new Telegram messages.")
        return 0

    client = _r2()
    uploaded = 0
    for update in updates:
        update_id = int(update.get("update_id") or 0)
        state["last_update_id"] = max(int(state.get("last_update_id") or 0), update_id)
        message = update.get("message") or {}
        incoming_chat_id = str((message.get("chat") or {}).get("id") or "")
        attachment = _video_attachment(message)
        if incoming_chat_id != chat_id or attachment is None:
            continue

        unique_id = str(attachment.get("file_unique_id") or attachment.get("file_id") or "")
        if unique_id in state.setdefault("files", {}):
            print(f"Duplicate Telegram video ignored: {unique_id}")
            continue

        pending = _oldest_pending(queue)
        if pending is None:
            state["files"][unique_id] = {
                "status": "ignored_no_pending_prompt",
                "update_id": update_id,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
            _send(token, chat_id, "Video received, but there is no pending property prompt. It was not uploaded or published.")
            continue

        size = int(attachment.get("file_size") or 0)
        if size and size > MAX_BYTES:
            state["files"][unique_id] = {
                "status": "rejected_too_large",
                "size": size,
                "update_id": update_id,
            }
            _send(
                token,
                chat_id,
                f"Video is too large for the Telegram Bot download limit ({size / 1024 / 1024:.1f} MB). "
                "Please export it below 20 MB and resend as a file.",
            )
            continue

        video_id = str(pending["video_id"]).strip()
        file_info = _telegram("getFile", token, data={"file_id": str(attachment["file_id"])})
        file_path = str((file_info.get("result") or {}).get("file_path") or "")
        if not file_path:
            raise RuntimeError("Telegram getFile returned no file_path")

        response = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=180)
        response.raise_for_status()
        if len(response.content) > MAX_BYTES:
            raise RuntimeError(f"Downloaded Telegram video exceeds {MAX_BYTES} bytes")

        key = f"{PREFIX.rstrip('/')}/{video_id}.mp4"
        with tempfile.NamedTemporaryFile(prefix="telegram-property-", suffix=".mp4") as handle:
            handle.write(response.content)
            handle.flush()
            client.upload_file(
                handle.name,
                bucket,
                key,
                ExtraArgs={"ContentType": "video/mp4"},
            )

        now = datetime.now(timezone.utc).isoformat()
        pending.update({
            "status": "assigned_to_r2_upload",
            "r2_key": key,
            "telegram_file_unique_id": unique_id,
            "uploaded_at": now,
        })
        state["files"][unique_id] = {
            "status": "uploaded",
            "video_id": video_id,
            "r2_key": key,
            "size": len(response.content),
            "update_id": update_id,
            "uploaded_at": now,
        }
        uploaded += 1
        _send(
            token,
            chat_id,
            f"✅ Property video received\nMatched prompt: {video_id}\nUploaded to R2: {key}\nSocial publishing will run automatically.",
        )
        print(f"Telegram video {unique_id} -> {key}")

    _save(STATE_PATH, state)
    _save(QUEUE_PATH, queue)
    print(f"Telegram ingest complete: {len(updates)} update(s), {uploaded} video(s) uploaded")
    return uploaded


if __name__ == "__main__":
    ingest()
