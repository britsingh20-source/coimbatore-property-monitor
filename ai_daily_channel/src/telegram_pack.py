from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from urllib import parse, request

from .job_validation import validate_job

API = "https://api.telegram.org/bot{token}/{method}"


def _post(token: str, method: str, fields: dict[str, str]) -> dict:
    data = parse.urlencode(fields).encode()
    with request.urlopen(request.Request(API.format(token=token, method=method), data=data), timeout=60) as response:
        return json.loads(response.read())


def send_text(token: str, chat_id: str, text: str) -> None:
    result = _post(token, "sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"})
    if not result.get("ok"):
        raise RuntimeError(result)


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
        f"CINEMATIC HOOK PROMPT\n{job['prompts']['cinematic_hook']}\n\n"
        f"AI B-ROLL PROMPT\n{job['prompts']['ai_broll']}\n\n"
        "Generate both Gemini clips, record this exact script, complete the edit, "
        f"and upload the final MP4 as a Telegram document with caption: FINAL {job['job_id']}"
    )


def deliver(job_path: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    errors = validate_job(job)
    if errors:
        raise ValueError("; ".join(errors))
    send_text(token, chat_id, summary(job))


if __name__ == "__main__":
    import sys
    deliver(sys.argv[1])
