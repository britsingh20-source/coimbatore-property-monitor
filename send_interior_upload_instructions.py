from __future__ import annotations

import json
import os
from pathlib import Path

import requests


def main() -> None:
    path = Path("interior_trend_radar/output/production_pack.json")
    if not path.exists():
        print("No interior production pack found")
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    jobs = payload.get("jobs") or []
    if not jobs:
        print("No interior jobs in production pack")
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    for job in jobs:
        candidate = job.get("candidate") or {}
        video_id = str(candidate.get("video_id") or "").strip()
        if not video_id:
            continue
        caption = f"INTERIOR_ID: {video_id}"
        text = (
            "After Gemini generates this interior video, send the MP4 to this bot with this exact caption:\n\n"
            f"{caption}\n\n"
            "This routes the video only to the Interior Instagram and Interior YouTube channel."
        )
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {
                    "inline_keyboard": [[{
                        "text": "Copy INTERIOR_ID",
                        "copy_text": {"text": caption},
                    }]]
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError(body)
        print(f"Sent copy-ready interior upload instruction for {video_id}")


if __name__ == "__main__":
    main()
