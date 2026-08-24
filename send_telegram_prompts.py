from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import io
import json
import os
from pathlib import Path

import requests

from veo_prompt import build_veo_prompt, telegram_filename


JOBS = Path("data/video_jobs")
DEFAULT_QUEUE = Path("data/telegram_prompt_queue.json")


def _ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _telegram_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:500] or "No response body"
    return str(body.get("description") or body)[:500]


def _queue_prompt(queue_path: Path, job: dict) -> None:
    queue = {"prompts": []}
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    prompts = queue.setdefault("prompts", [])
    video_id = str(job.get("video_id") or "").strip()
    existing = next((item for item in prompts if item.get("video_id") == video_id), None)
    update = {
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_mobile_upload",
    }
    if existing is None:
        prompts.append({"video_id": video_id, **update})
    elif existing.get("status") != "published":
        existing.update(update)
        existing.pop("r2_key", None)
        existing.pop("reference_frame_count", None)
        existing.pop("reference_status", None)
        existing.pop("reference_error", None)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def send_prompt(job: dict, bot_token: str, chat_id: str) -> None:
    prompt = build_veo_prompt(job)
    prop = job.get("property") or {}
    location = str(job.get("property_location") or "Coimbatore")
    video_id = str(job.get("video_id") or "").strip()
    title = " ".join(
        part
        for part in (
            str(prop.get("bhk") or "").strip(),
            str(prop.get("property_type") or "Property").strip(),
        )
        if part and part.upper() != "NOT SPECIFIED"
    )
    caption = (
        "<b>New 10-second Gemini/Veo property prompt</b>\n"
        f"<b>Property:</b> {html.escape(title)}\n"
        f"<b>Location:</b> {html.escape(location)}\n"
        f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>\n"
        "<b>Site visit:</b> 9003787621\n\n"
        "Open Gemini mobile, paste the attached prompt, and allow Gemini to open "
        "the included YouTube reference. After generation, send the downloaded MP4 "
        "to this bot as a file. "
        f"Add this exact caption: <code>VIDEO_ID: {html.escape(video_id)}</code>. "
        "The mobile filename can remain unchanged."
    )
    payload = io.BytesIO(prompt.encode("utf-8"))
    payload.name = telegram_filename(job)
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
        files={"document": (payload.name, payload, "text/plain; charset=utf-8")},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(
            f"Telegram sendDocument failed for {video_id} "
            f"(HTTP {response.status_code}): {_telegram_error(response)}"
        )
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(
            f"Telegram rejected prompt for {video_id}: {_telegram_error(response)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
    parser.add_argument("--queue-file", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    if not chat_id.lstrip("-").isdigit():
        raise SystemExit("TELEGRAM_CHAT_ID must be the numeric chat id returned by getUpdates")

    video_ids = _ids(args.ids_file)
    if not video_ids:
        print("No new property prompts to send.")
        return

    for video_id in video_ids:
        path = JOBS / f"{video_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing video job: {path}")
        job = json.loads(path.read_text(encoding="utf-8"))
        send_prompt(job, bot_token, chat_id)
        _queue_prompt(args.queue_file, job)
        print(f"Sent Gemini/Veo YouTube-reference prompt to Telegram: {video_id}")


if __name__ == "__main__":
    main()
