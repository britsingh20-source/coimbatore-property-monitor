from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

import boto3
import requests
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from meta_publisher import publish_facebook_reel

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


FORBIDDEN_PUBLIC_WORDING = re.compile(
    r"\b(?:reference(?:d)?|inspir(?:ed|ation)|source\s+(?:video|channel|creator)|"
    r"reconstruct(?:ed|ion)?|ai[-\s]?(?:generated|created|enhanced|visual)|"
    r"artificial intelligence|copied footage)\b",
    flags=re.I,
)


def _json_object(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Interior video analysis did not return JSON")
    return json.loads(cleaned[start:end + 1])


def _clean_hashtags(values: object, subject: str) -> list[str]:
    subject_tags: list[str] = []
    if isinstance(values, list):
        for value in values:
            tag = "#" + re.sub(r"[^A-Za-z0-9]", "", str(value).lstrip("#"))
            normalized = tag.lower()
            if re.search(r"(?:reference|inspir|source|reconstruct|ai(?:generated|created|enhanced))", normalized):
                continue
            if normalized in {"#olivetreeinteriors", "#coimbatoreinteriors"}:
                continue
            if len(tag) > 1 and normalized not in {x.lower() for x in subject_tags}:
                subject_tags.append(tag)
    fallback_subject = "#" + re.sub(r"[^A-Za-z0-9]", "", subject.title())[:40]
    topic_tag = subject_tags[0] if subject_tags else fallback_subject
    if len(topic_tag) <= 1 or FORBIDDEN_PUBLIC_WORDING.search(topic_tag):
        topic_tag = "#InteriorDesign"
    return [topic_tag, "#OliveTreeInteriors", "#CoimbatoreInteriors"]


def analyze_publish_content(video_path: Path) -> dict:
    prompt = """Watch the uploaded interior video completely, including its visuals and audio.
Create original, customer-focused social content for Olive Tree Interiors in Coimbatore.

Return one JSON object with these exact keys:
subject, hook, interior_features, customer_benefits, instagram_caption,
youtube_title, youtube_description, hashtags, youtube_tags.

Rules:
- Describe only interior elements clearly visible or audible in this uploaded video.
- Identify the room, materials, finishes, colour palette, storage, lighting, hardware,
  space-saving mechanism, craftsmanship and practical benefits when actually supported.
- Lead with a strong specific hook, not a generic phrase.
- Instagram caption: 70-140 words, easy English, short readable paragraphs, premium but natural,
  with a save/share/DM call to action. Do not put hashtags inside this field.
- YouTube title: specific, searchable and compelling; maximum 85 characters; no hashtags.
- YouTube description: 90-180 words, searchable natural language, key design features first,
  Olive Tree Interiors and Coimbatore included, and a contact/DM call to action.
  Do not put hashtags inside this field.
- hashtags: exactly 3 highly relevant hashtags, including OliveTreeInteriors and CoimbatoreInteriors.
- youtube_tags: 5-10 concise search phrases.
- Never mention a reference, source, inspiration creator/channel, reconstruction, AI generation,
  competitor, copied footage, or how the video was produced.
- Never invent dimensions, brands, materials, mechanisms, prices or project claims.
"""
    client = genai.Client(api_key=required("GEMINI_API_KEY"))
    uploaded = client.files.upload(file=str(video_path))
    try:
        for _ in range(30):
            state = str(getattr(getattr(uploaded, "state", None), "name", "") or "").upper()
            if state in {"", "ACTIVE"}:
                break
            if state == "FAILED":
                raise RuntimeError("Gemini could not process the interior video")
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)
        response = client.models.generate_content(
            model=os.environ.get("INTERIOR_GEMINI_MODEL", "gemini-2.5-flash"),
            contents=[uploaded, prompt],
            config={"response_mime_type": "application/json", "temperature": 0.35},
        )
        result = _json_object(response.text)
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

    subject = str(result.get("subject") or "Modern Home Interior").strip()
    hashtags = _clean_hashtags(result.get("hashtags"), subject)
    caption = str(result.get("instagram_caption") or "").strip()
    description = str(result.get("youtube_description") or "").strip()
    title = str(result.get("youtube_title") or subject).strip()[:85]
    searchable = " ".join((caption, description, title, " ".join(hashtags)))
    if FORBIDDEN_PUBLIC_WORDING.search(searchable):
        raise ValueError("Generated social copy contained prohibited reference/source wording")
    if not caption or not description or len(hashtags) != 3:
        raise ValueError("Generated interior social copy was incomplete")
    result["subject"] = subject
    result["instagram_caption"] = f"{caption}\n\n{' '.join(hashtags)}"
    result["youtube_title"] = title
    result["youtube_description"] = f"{description}\n\n{' '.join(hashtags)}"
    result["hashtags"] = hashtags
    tags = result.get("youtube_tags")
    result["youtube_tags"] = [str(x).strip() for x in tags if str(x).strip()][:10] if isinstance(tags, list) else []
    return result


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


def publish_instagram_story(video_url: str) -> dict:
    token = required("INTERIOR_META_ACCESS_TOKEN")
    ig_user_id = required("INTERIOR_IG_USER_ID")
    response = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "STORIES",
            "video_url": video_url,
            "access_token": token,
        },
        timeout=60,
    )
    body = response.json()
    if not response.ok or body.get("error") or not body.get("id"):
        raise RuntimeError(f"Instagram Story container creation failed: {body}")
    creation_id = str(body["id"])
    wait_instagram_container(creation_id, token)
    response = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    published = response.json()
    if not response.ok or published.get("error") or not published.get("id"):
        raise RuntimeError(f"Instagram Story publish failed: {published}")
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


def publish_youtube_short(video_path: Path, content: dict) -> dict:
    youtube = build("youtube", "v3", credentials=youtube_credentials(), cache_discovery=False)
    body = {
        "snippet": {
            "title": content["youtube_title"],
            "description": content["youtube_description"],
            "tags": content.get("youtube_tags") or [
                "Interior Design", "Home Interiors", "Olive Tree Interiors", "Coimbatore Interiors"
            ],
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
            "facebook": {},
            "instagram_story": {},
            "youtube": {},
        }
        state["telegram_files"][unique_id] = record
        state.setdefault("objects", {})[key] = record
        save_state(state)

        try:
            content = analyze_publish_content(Path(handle.name))
            record["content"] = content
            save_state(state)
        except Exception as error:
            record["content"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)
            send_message(
                token,
                chat_id,
                "⚠️ Interior video publishing stopped: content analysis failed. No social post was created.",
            )
            raise

        caption = content["instagram_caption"]
        try:
            record["instagram"] = {"status": "published", **publish_instagram_reel(video_url, caption)}
            save_state(state)
        except Exception as error:
            record["instagram"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)

        try:
            record["facebook"] = {
                "status": "published",
                **publish_facebook_reel(Path(handle.name), caption, channel="interior"),
            }
            save_state(state)
        except Exception as error:
            record["facebook"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)

        try:
            record["instagram_story"] = {"status": "published", **publish_instagram_story(video_url)}
            save_state(state)
        except Exception as error:
            record["instagram_story"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)

        try:
            record["youtube"] = {"status": "published", **publish_youtube_short(Path(handle.name), content)}
            save_state(state)
        except Exception as error:
            record["youtube"] = {"status": "failed", "error": str(error)[:3000]}
            save_state(state)

    failures = [
        name
        for name in ("instagram", "facebook", "instagram_story", "youtube")
        if record[name].get("status") != "published"
    ]
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
        "Destinations: Instagram Reel + Facebook Reel + Instagram Story + YouTube Short",
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
