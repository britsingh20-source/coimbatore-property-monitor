from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from urllib import parse, request

import boto3

from .job_validation import validate_job

API = "https://api.telegram.org/bot{token}/{method}"
PRESENTER_KEY = os.getenv("AIBROS_PRESENTER_KEY", "aibros/private/presenter_reference.jpg")


def _post(token: str, method: str, fields: dict[str, str]) -> dict:
    data = parse.urlencode(fields).encode()
    with request.urlopen(request.Request(API.format(token=token, method=method), data=data), timeout=60) as response:
        return json.loads(response.read())


def send_text(token: str, chat_id: str, text: str) -> None:
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= 3900:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, 3900)
        if cut < 1000:
            cut = 3900
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()
    for chunk in chunks:
        result = _post(token, "sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": "true",
        })
        if not result.get("ok"):
            raise RuntimeError(result)


def send_photo(token: str, chat_id: str, photo_path: str, caption: str) -> None:
    boundary = "----Aibros" + uuid.uuid4().hex
    image = Path(photo_path).read_bytes()
    parts = []
    for name, value in (("chat_id", chat_id), ("caption", caption)):
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"aibros-presenter-reference.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode()
        + image + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    req = request.Request(
        API.format(token=token, method="sendPhoto"),
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with request.urlopen(req, timeout=90) as response:
        result = json.loads(response.read())
    if not result.get("ok"):
        raise RuntimeError(result)


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def download_presenter_reference() -> str:
    bucket = os.environ["R2_BUCKET_NAME"]
    target = Path(tempfile.gettempdir()) / "aibros-presenter-reference.jpg"
    try:
        r2_client().download_file(bucket, PRESENTER_KEY, str(target))
    except Exception as exc:
        raise RuntimeError(
            "Aibros presenter reference is not registered in R2. "
            "Send the portrait to Telegram with caption AIBROS PRESENTER and run the registration workflow."
        ) from exc
    return str(target)


def summary(job: dict) -> str:
    tool = job["tool"]
    script = job["script"]
    return (
        f"PRODUCTION JOB: {job['job_id']}\n"
        f"Language: {job['language']}\n"
        f"Tool: {tool['name']}\n"
        f"Free status: {tool['free_claim']}\n"
        f"Verified: {tool['verified_at']}\n"
        f"Official: {tool['official_url']}\n\n"
        f"EXACT SCRIPT\n{script['exact_text']}\n\n"
        "STEP 2 — CINEMATIC HOOK\n"
        "Upload the presenter photograph sent immediately before this message to Gemini, then paste this prompt:\n\n"
        f"{job['prompts']['cinematic_hook']}\n\n"
        "STEP 3 — AI B-ROLL\n"
        "Generate separately; the presenter reference is normally not required:\n\n"
        f"{job['prompts']['ai_broll']}\n\n"
        "Complete the manual voice recording and edit, then upload the final MP4 as a Telegram document with caption: "
        f"FINAL {job['job_id']}"
    )


def deliver(job_path: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    errors = validate_job(job)
    if errors:
        raise ValueError("; ".join(errors))
    reference = download_presenter_reference()
    send_photo(
        token,
        chat_id,
        reference,
        "STEP 1 — AIBROS PRESENTER REFERENCE\nDownload this image and attach it to Gemini before pasting the cinematic-hook prompt.",
    )
    send_text(token, chat_id, summary(job))


if __name__ == "__main__":
    import sys
    deliver(sys.argv[1])
