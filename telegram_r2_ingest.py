from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import unicodedata
from pathlib import Path
import tempfile

import boto3
import requests

from reference_frames import extract_frames_from_local_video, send_reference_frames


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


def _reference_video_id(message: dict) -> str:
    text = str(message.get("caption") or message.get("text") or "").strip()
    match = re.search(
        r"reference[\\s_-]*id\\s*[:=\\-]\\s*([A-Za-z0-9_-]{6,32})",
        text,
        flags=re.I,
    )
    return match.group(1) if match else ""


def _explicit_video_id(message: dict) -> str:
    text = str(message.get("caption") or message.get("text") or "").strip()
    match = re.search(r"(?:video[\\s_-]*id|id)\\s*[:=\\-]\\s*([A-Za-z0-9_-]{6,32})", text, flags=re.I)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text

    # iOS/Telegram may insert spaces, non-breaking spaces or invisible Unicode
    # format characters into a copied YouTube ID. The old regex accidentally
    # looked for the literal characters "\\s", so spaced IDs were discarded.
    compact_text = "".join(
        char
        for char in text
        if not char.isspace() and unicodedata.category(char) != "Cf"
    )
    separators_only = all(
        char.isalnum()
        or char in "_-"
        or char.isspace()
        or unicodedata.category(char) == "Cf"
        for char in text
    )
    if (
        separators_only
        and re.fullmatch(r"[A-Za-z0-9_-]{11}", compact_text)
    ):
        return compact_text

    replied = message.get("reply_to_message") or {}
    replied_document = replied.get("document") or {}
    filename = str(replied_document.get("file_name") or "")
    match = re.match(r"([A-Za-z0-9_-]{11})-gemini-veo-prompt\\.txt$", filename, flags=re.I)
    return match.group(1) if match else ""


def _unique_pending_video_id(supplied_id: str, queue: dict) -> str:
    """Resolve only a unique pending ID with harmless mobile glyph confusion."""
    pending_ids = [
        str(item.get("video_id") or "").strip()
        for item in queue.get("prompts", [])
        if item.get("status") == "pending_mobile_upload" and item.get("video_id")
    ]
    if supplied_id in pending_ids:
        return supplied_id

    ambiguous_groups = (set("0O"), set("1Il"))
    matches = []
    for candidate in pending_ids:
        if len(candidate) != len(supplied_id):
            continue
        compatible = True
        for supplied_char, candidate_char in zip(supplied_id, candidate):
            if supplied_char == candidate_char:
                continue
            if not any(
                supplied_char in group and candidate_char in group
                for group in ambiguous_groups
            ):
                compatible = False
                break
        if compatible:
            matches.append(candidate)
    return matches[0] if len(matches) == 1 else ""


def _resolve_supplied_video_id(supplied_id: str, queue: dict) -> str:
    """Accept an exact known ID even when an earlier upload was published.

    A user may regenerate a property video and send the same VIDEO_ID again.
    Glyph correction remains limited to pending prompts so an ambiguous typo can
    never select an old property silently.
    """
    known_ids = {
        str(item.get("video_id") or "").strip()
        for item in queue.get("prompts", [])
        if item.get("video_id")
    }
    if supplied_id in known_ids:
        return supplied_id
    return _unique_pending_video_id(supplied_id, queue)


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
        if incoming_chat_id != chat_id:
            continue

        attachment = _video_attachment(message)
        if attachment is None:
            standalone_video_id = _explicit_video_id(message)
            if not standalone_video_id:
                continue
            resolved_video_id = _resolve_supplied_video_id(standalone_video_id, queue)
            if resolved_video_id:
                standalone_video_id = resolved_video_id
            prompt = next(
                (
                    item
                    for item in queue.get("prompts", [])
                    if item.get("video_id") == standalone_video_id
                ),
                None,
            )
            candidates = [
                (unique_id, item)
                for unique_id, item in state.setdefault("files", {}).items()
                if item.get("status") in {
                    "uploaded_awaiting_content_match",
                    "uploaded_awaiting_video_id",
                }
                and standalone_video_id in (item.get("candidate_video_ids") or [])
                and item.get("r2_key")
            ]
            candidates.sort(
                key=lambda pair: int(pair[1].get("update_id") or 0),
                reverse=True,
            )
            if not candidates:
                # When the ID belongs to an already-published prompt it was not
                # part of the video's pending candidate snapshot. Safely pair
                # only the most recent unmatched upload sent immediately before
                # this standalone ID message.
                recent_unmatched = [
                    (unique_id, item)
                    for unique_id, item in state.setdefault("files", {}).items()
                    if item.get("status") in {
                        "uploaded_awaiting_content_match",
                        "uploaded_awaiting_video_id",
                    }
                    and item.get("r2_key")
                    and 0 < update_id - int(item.get("update_id") or 0) <= 5
                ]
                recent_unmatched.sort(
                    key=lambda pair: int(pair[1].get("update_id") or 0),
                    reverse=True,
                )
                candidates = recent_unmatched[:1]
            if prompt is None or not candidates:
                _send(
                    token,
                    chat_id,
                    f"Could not pair VIDEO_ID {standalone_video_id}. "
                    "Reply to the prompt with the ID or include VIDEO_ID in the video caption.",
                )
                continue

            paired_unique_id, paired = candidates[0]
            now = datetime.now(timezone.utc).isoformat()
            paired.update(
                {
                    "status": "uploaded_exact_video_id",
                    "video_id": standalone_video_id,
                    "paired_at": now,
                    "paired_by": "next_telegram_message",
                }
            )
            paired.pop("candidate_video_ids", None)
            prompt.update(
                {
                    "status": "assigned_to_r2_upload",
                    "r2_key": paired["r2_key"],
                    "telegram_file_unique_id": paired_unique_id,
                    "uploaded_at": paired.get("uploaded_at") or now,
                }
            )
            _send(
                token,
                chat_id,
                f"✅ Previous video paired exactly\nVIDEO_ID: {standalone_video_id}\n"
                f"R2: {paired['r2_key']}\nSocial publishing can now continue.",
            )
            print(
                f"Standalone VIDEO_ID {standalone_video_id} paired to "
                f"Telegram file {paired_unique_id}"
            )
            continue

        unique_id = str(attachment.get("file_unique_id") or attachment.get("file_id") or "")
        if unique_id in state.setdefault("files", {}):
            print(f"Duplicate Telegram video ignored: {unique_id}")
            continue

        reference_video_id = _reference_video_id(message)
        reference_job = Path("data/video_jobs") / f"{reference_video_id}.json"
        if reference_video_id and not reference_job.exists():
            state["files"][unique_id] = {
                "status": "rejected_invalid_reference_id",
                "provided_reference_id": reference_video_id,
                "update_id": update_id,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
            _send(
                token,
                chat_id,
                f"REFERENCE_ID {reference_video_id} has no property job. Nothing was uploaded or published.",
            )
            continue

        pending_ids = [
            str(item.get("video_id") or "").strip()
            for item in queue.get("prompts", [])
            if item.get("status") == "pending_mobile_upload" and item.get("video_id")
        ]
        explicit_video_id = "" if reference_video_id else _explicit_video_id(message)
        if explicit_video_id:
            resolved_video_id = _resolve_supplied_video_id(explicit_video_id, queue)
            if resolved_video_id:
                explicit_video_id = resolved_video_id
        known_ids = {
            str(item.get("video_id") or "").strip()
            for item in queue.get("prompts", [])
            if item.get("video_id")
        }
        if explicit_video_id and explicit_video_id not in known_ids:
            state["files"][unique_id] = {
                "status": "rejected_invalid_video_id",
                "provided_video_id": explicit_video_id,
                "update_id": update_id,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
            _send(
                token,
                chat_id,
                f"Video ID {explicit_video_id} is not a known property prompt. Nothing was uploaded or published. Please resend with the exact VIDEO_ID from the prompt.",
            )
            continue

        if not reference_video_id and not pending_ids:
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

        file_info = _telegram("getFile", token, data={"file_id": str(attachment["file_id"])})
        file_path = str((file_info.get("result") or {}).get("file_path") or "")
        if not file_path:
            raise RuntimeError("Telegram getFile returned no file_path")

        response = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=180)
        response.raise_for_status()
        if len(response.content) > MAX_BYTES:
            raise RuntimeError(f"Downloaded Telegram video exceeds {MAX_BYTES} bytes")

        if reference_video_id:
            with tempfile.TemporaryDirectory(
                prefix=f"telegram-reference-{reference_video_id}-"
            ) as temp_dir:
                source_path = Path(temp_dir) / "source.mp4"
                source_path.write_bytes(response.content)
                frame_paths = extract_frames_from_local_video(
                    source_path,
                    Path(temp_dir),
                    target_count=5,
                )
                send_reference_frames(
                    frame_paths,
                    token,
                    chat_id,
                    reference_video_id,
                )

            now = datetime.now(timezone.utc).isoformat()
            state["files"][unique_id] = {
                "status": "reference_frames_sent",
                "video_id": reference_video_id,
                "size": len(response.content),
                "update_id": update_id,
                "processed_at": now,
            }
            prompt = next(
                (
                    item
                    for item in queue.get("prompts", [])
                    if item.get("video_id") == reference_video_id
                ),
                None,
            )
            if prompt is not None:
                prompt.update(
                    {
                        "reference_frame_count": 5,
                        "reference_status": "sent_from_telegram_source",
                        "reference_sent_at": now,
                    }
                )
                prompt.pop("reference_error", None)
            _send(
                token,
                chat_id,
                f"✅ Five reference frames extracted for {reference_video_id}. "
                "The source tour was not uploaded to R2 and will not be published. "
                "Attach all five images in Gemini → Videos, then paste the matching prompt file.",
            )
            print(
                f"Telegram source video {unique_id} -> five reference frames; "
                f"REFERENCE_ID {reference_video_id}"
            )
            continue

        safe_unique_id = re.sub(r"[^A-Za-z0-9_-]+", "-", unique_id).strip("-")
        key_name = explicit_video_id if explicit_video_id else f"telegram-{safe_unique_id}"
        key = f"{PREFIX.rstrip('/')}/{key_name}.mp4"
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
        if explicit_video_id:
            state["files"][unique_id] = {
                "status": "uploaded_exact_video_id",
                "video_id": explicit_video_id,
                "r2_key": key,
                "size": len(response.content),
                "update_id": update_id,
                "uploaded_at": now,
            }
            prompt = next(item for item in queue.get("prompts", []) if item.get("video_id") == explicit_video_id)
            prompt.update({
                "status": "assigned_to_r2_upload",
                "r2_key": key,
                "telegram_file_unique_id": unique_id,
                "uploaded_at": now,
            })
            confirmation = (
                f"✅ Property video received and exactly matched\n"
                f"VIDEO_ID: {explicit_video_id}\nUploaded to R2: {key}\n"
                "Social publishing will run automatically without Gemini matching."
            )
            print(f"Telegram video {unique_id} -> {key}; exact VIDEO_ID {explicit_video_id}")
        else:
            state["files"][unique_id] = {
                "status": "uploaded_awaiting_video_id",
                "candidate_video_ids": pending_ids,
                "r2_key": key,
                "size": len(response.content),
                "update_id": update_id,
                "uploaded_at": now,
            }
            confirmation = (
                f"✅ Property video received\nUploaded to R2: {key}\n"
                "No VIDEO_ID was supplied, so this video is safely paused and will not be published.\n"
                "Send the exact 11-character VIDEO_ID as your next message before sending another video."
            )
            print(f"Telegram video {unique_id} -> {key}; awaiting exact VIDEO_ID")
        uploaded += 1
        _send(token, chat_id, confirmation)

    _save(STATE_PATH, state)
    _save(QUEUE_PATH, queue)
    print(f"Telegram ingest complete: {len(updates)} update(s), {uploaded} video(s) uploaded")
    return uploaded


if __name__ == "__main__":
    ingest()
