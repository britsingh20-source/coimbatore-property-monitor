from __future__ import annotations

import json
import os
from urllib import parse, request

from .telegram_pack import API, PRESENTER_KEY, r2_client, send_text


def get_json(url: str) -> dict:
    with request.urlopen(url, timeout=60) as response:
        return json.loads(response.read())


def latest_presenter_message(token: str, chat_id: str) -> tuple[str, str]:
    data = get_json(API.format(token=token, method="getUpdates") + "?limit=100&timeout=0")
    if not data.get("ok"):
        raise RuntimeError(data)
    wanted = str(chat_id)
    for update in reversed(data.get("result", [])):
        message = update.get("message") or update.get("channel_post") or {}
        if str((message.get("chat") or {}).get("id")) != wanted:
            continue
        if "AIBROS PRESENTER" not in (message.get("caption") or "").upper():
            continue
        document = message.get("document") or {}
        if document.get("file_id") and str(document.get("mime_type", "")).startswith("image/"):
            return document["file_id"], document.get("mime_type", "image/jpeg")
        photos = message.get("photo") or []
        if photos:
            return photos[-1]["file_id"], "image/jpeg"
    raise RuntimeError(
        "No presenter image found. Send the portrait to this bot as a photo or image document "
        "with the exact caption: AIBROS PRESENTER"
    )


def register() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    file_id, content_type = latest_presenter_message(token, chat_id)
    info = get_json(API.format(token=token, method="getFile") + "?" + parse.urlencode({"file_id": file_id}))
    if not info.get("ok"):
        raise RuntimeError(info)
    telegram_path = info["result"]["file_path"]
    with request.urlopen(f"https://api.telegram.org/file/bot{token}/{telegram_path}", timeout=90) as response:
        image = response.read()
    if len(image) < 20_000:
        raise RuntimeError("Presenter image is unexpectedly small; send the original high-quality portrait.")
    r2_client().put_object(
        Bucket=os.environ["R2_BUCKET_NAME"],
        Key=PRESENTER_KEY,
        Body=image,
        ContentType=content_type,
        CacheControl="private, no-store",
        Metadata={"purpose": "aibros-presenter-identity-reference"},
    )
    send_text(
        token,
        chat_id,
        "AIBROS PRESENTER REGISTERED\nYour private presenter reference is stored in R2 and will be attached to every future cinematic-hook package.",
    )
    print(f"Registered presenter reference at {PRESENTER_KEY} ({len(image)} bytes)")


if __name__ == "__main__":
    register()
