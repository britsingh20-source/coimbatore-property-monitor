from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

import boto3
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GRAPH = "https://graph.facebook.com/v23.0"
STATE_PATH = Path("data/interior_social_publish_state.json")
R2_PREFIX = "interior-social-ready/"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"telegram_files": {}, "objects": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def telegram(method: str, token: str, data: dict | None = None, timeout: int = 60) -> dict:
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


def send_message(token: str, chat_id: str, text: str) -> None:
    telegram("sendMessage", token, {"chat_id": chat_id, "text": text})


def r2_client():
    account_id = required("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def video_attachment(message: dict) -> dict | None:
    if message.get("video"):
        return message["video"]
    document = message.get("document") or {}
    mime = str(document.get("mime_type") or "").lower()
    name = str(document.get("file_name") or "").lower()
    if document and (mime.startswith("video/") or name.endswith(".mp4")):
        return document
    return None


def interior_id(message: dict) -> str:
    text = str(message.get("caption") or message.get("text") or "")
    match = re.search(r"INTERIOR[\s_-]*ID\s*[:=\-]\s*([A-Za-z0-9_-]{6,32})", text, flags=re.I)
    return match.group(1) if match else ""


def history_record(source_id: str) -> dict:
    path = Path("data/interior_trend_state.json")
    if not path.exists():
        return {}
    state = json.loads(path.read_text(encoding="utf-8"))
    for item in reversed(state.get("history", [])):
        if str(item.get("video_id") or "") == source_id:
            return item
    return {}


def instagram_caption(source_id: str) -> str:
    item = history_record(source_id)
    creator = str(item.get("creator") or "Interior design reference").strip()
    return (
        "Smart interior ideas for modern homes.\n\n"
        "AI visual reconstruction inspired by a verified interior reference. "
        "Design details should be adapted to actual site dimensions and requirements.\n\n"
        f"Reference inspiration: {creator}\n"
        "#OlivetreeInteriors #InteriorDesign #HomeInteriors #InteriorIdeas #ModernInteriors #CoimbatoreInteriors"
    )


def wait_instagram_container(creation_id: str, token: str) -> None:
    for _ in range(30):
        response = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        body = response.json()
        if not response.ok or body.get("error"):
            raise RuntimeError(f"Instagram status failed: {body}")
        status = str(body.get("status_code") or "").upper()
        if status == "FINISHED":
            return
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container failed: {body}")
        time.sleep(10)
    raise RuntimeError("Instagram container timed out")


def publish_instagram_reel(video_url: str, caption: str) -> dict:
    token = required("INTERIOR_META_ACCESS_TOKEN")
    ig_user_id = required("INTERIOR_IG_USER_ID")
    response = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=60,
    )
    body = response.json()
    if not response.ok or body.get("error") or not body.get("id"):
        raise RuntimeError(f"Instagram Reel container creation failed: {body}")
    creation_id = str(body["id"])
    wait_instagram_container(creation_id, token)
    response = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    published = response.json()
    if not response.ok or published.get("error") or not published.get("id"):
        raise RuntimeError(f"Instagram Reel publish failed: {published}")
    return {"creation_id": creation_id, "media_id": published["id"]}


def youtube_credentials() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=required("INTERIOR_YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=required("INTERIOR_YOUTUBE_CLIENT_ID"),
        client_secret=required("INTERIOR_YOUTUBE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )


def publish_youtube_short(video_path: Path, source_id: str) -> dict:
    youtube = build("youtube", "v3", credentials=youtube_credentials(), cache_discovery=False)
    body = {
        "snippet": {
            "title": "Smart Interior Idea | Olivetree Interiors #Shorts",
            "description": instagram_caption(source_id),
            "tags": ["Shorts", "Interior Design", "Home Interiors", "Olivetree Interiors", "Coimbatore Interiors"],
            "categoryId": "26",
        },
        "status": {
            "privacyStatus": os.environ.get("INTERIOR_YOUTUBE_PRIVACY_STATUS", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return {"video_id": response.get("id")}


def handle_update(update: dict) -> int:
    token = required("TELEGRAM_BOT_TOKEN")
    chat_id = required("TELEGRAM_CHAT_ID")
    message = update.get("message") or update.get("edited_message") or {}
    incoming_chat = str((message.get("chat") or {}).get("id") or "")
    if incoming_chat != chat_id:
        print("Ignoring Telegram update from another chat")
        return 0

    source_id = interior_id(message)
    if not source_id:
        print("Not an INTERIOR_ID upload; interior publisher skipped")
        return 0

    attachment = video_attachment(message)
    if attachment is None:
        print("INTERIOR_ID message has no video attachment")
        return 0

    unique_id = str(attachment.get("file_unique_id") or attachment.get("file_id") or "")
    state = load_state()
    if unique_id in state.setdefault("telegram_files", {}):
        print(f"Duplicate interior Telegram file ignored: {unique_id}")
        return 0

    info = telegram("getFile", token, {"file_id": str(attachment["file_id"])})
    file_path = str((info.get("result") or {}).get("file_path") or "")
    if not file_path:
        raise RuntimeError("Telegram getFile returned no file_path")
    response = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=180)
    response.raise_for_status()

    client = r2_client()
    bucket = required("R2_BUCKET_NAME")
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "-", source_id).strip("-")
    key = f"{R2_PREFIX}{safe_id}-{unique_id}.mp4"
    with tempfile.NamedTemporaryFile(prefix="interior-social-", suffix=".mp4") as handle:
        handle.write(response.content)
        handle.flush()
        client.upload_file(handle.name, bucket, key, ExtraArgs={"ContentType": "video/mp4"})

        video_url = client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=21600
        )
        record = {
            "source_id": source_id,
            "r2_key": key,
            "instagram": {},
            "youtube": {},
        }
        state["telegram_files"][unique_id] = record
        state.setdefault("objects", {})[key] = record
        save_state(state)

        caption = instagram_caption(source_id)
        try:
            record["instagram"] = {"status": "published", **publish_instagram_reel(video_url, caption)}
            save_state(state)
        except Exception as error:
            record["instagram"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)

        try:
            record["youtube"] = {"status": "published", **publish_youtube_short(Path(handle.name), source_id)}
            save_state(state)
        except Exception as error:
            record["youtube"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)

    failures = [name for name in ("instagram", "youtube") if record[name].get("status") != "published"]
    if failures:
        send_message(
            token,
            chat_id,
            "⚠️ Interior video processed, but publishing failed for: " + ", ".join(failures) + ". Check GitHub Actions logs.",
        )
        raise RuntimeError("Interior publishing failed for: " + ", ".join(failures))

    send_message(
        token,
        chat_id,
        "✅ Interior video published successfully\n"
        f"INTERIOR_ID: {source_id}\n"
        "Destinations: Instagram Reel + YouTube Short",
    )
    return 1


def main() -> None:
    raw = os.environ.get("TELEGRAM_WEBHOOK_UPDATE_JSON", "").strip()
    if not raw:
        print("No webhook update supplied; nothing to do")
        return
    handle_update(json.loads(raw))


if __name__ == "__main__":
    main()
