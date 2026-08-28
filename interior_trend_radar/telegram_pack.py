from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import parse, request


def _send(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]; chat_id = os.environ["TELEGRAM_CHAT_ID"]
    for start in range(0, len(text), 3800):
        body = parse.urlencode({"chat_id": chat_id, "text": text[start:start + 3800], "disable_web_page_preview": "true"}).encode()
        with request.urlopen(request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body), timeout=60) as response:
            result = json.loads(response.read())
        if not result.get("ok"): raise RuntimeError(result)


def format_pack(job: dict) -> str:
    prompts = "\n\n".join(f"CLIP {i}\n{p}" for i, p in enumerate(job["google_video_prompts"], 1))
    sources = "\n".join(job.get("source_urls", []))
    return f"""INTERIOR TREND RADAR
Trend: {job['trend_name']}
Why it works: {job['why_it_works']}
Visual confidence: {job.get('confidence', 'unknown')}
Limitation: {job.get('limitations', 'none')}

ORIGINAL TAMIL-ENGLISH CONTENT
{job['original_tamil_english_script']}

GOOGLE FLOW / VEO — GENERATE 4 SEPARATE CLIPS
{prompts}

COVER: {job['cover_text']}
CAPTION: {job['caption']}
{' '.join(job['hashtags'])}

REFERENCE IDEAS (do not repost their footage)
{sources}
"""


def deliver(path: str) -> None:
    _send(format_pack(json.loads(Path(path).read_text(encoding="utf-8"))))


if __name__ == "__main__":
    import sys
    deliver(sys.argv[1])
