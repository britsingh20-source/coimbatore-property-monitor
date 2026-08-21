from __future__ import annotations

import argparse
import html
import io
import json
import os
from pathlib import Path

import requests

from veo_prompt import build_veo_prompt, telegram_filename


JOBS = Path("data/video_jobs")


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


def send_prompt(job: dict, bot_token: str, chat_id: str) -> None:
    prompt = build_veo_prompt(job)
    prop = job.get("property") or {}
    location = str(job.get("property_location") or "Coimbatore")
    title = " ".join(
        part for part in (
            str(prop.get("bhk") or "").strip(),
            str(prop.get("property_type") or "Property").strip(),
        )
        if part and part.upper() != "NOT SPECIFIED"
    )
    caption = (
        "<b>New 10-second Gemini/Veo property prompt</b>\n"
        f"<b>Property:</b> {html.escape(title)}\n"
        f"<b>Location:</b> {html.escape(location)}\n"
        f"<b>Video ID:</b> <code>{html.escape(str(job.get('video_id', '')))}</code>\n"
        f"<b>Site visit:</b> 9003787621\n\n"
        "Upload the original source video to Gemini, then paste the attached prompt."
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
            f"Telegram sendDocument failed for {job.get('video_id')} "
            f"(HTTP {response.status_code}): {_telegram_error(response)}"
        )
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram rejected prompt for {job.get('video_id')}: {_telegram_error(response)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
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
        print(f"Sent Gemini/Veo prompt to Telegram: {video_id}")


if __name__ == "__main__":
    main()
