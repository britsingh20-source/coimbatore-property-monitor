"""Oldest-first Shorts backlog, independent of the existing recent-video radar."""
from __future__ import annotations

import argparse
import json
import os
import signal
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .discovery import _json, _resolve_handle
from .reference_first import _send_prompt, build_reference_prompt


class _StageExpired(BaseException):
    """Bypass dependency retry loops when the overall stage deadline expires."""


@contextmanager
def stage_deadline(name: str, seconds: int):
    def expired(signum, frame):
        raise _StageExpired()

    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)
    print(f"SHORTS_STAGE_START stage={name} deadline_seconds={seconds}", flush=True)
    try:
        yield
    except _StageExpired:
        raise TimeoutError(f"Shorts stage '{name}' exceeded {seconds} seconds; retry required") from None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def discover_shorts(handle: str, api_key: str) -> list[dict]:
    from yt_dlp import YoutubeDL

    channel_id = _resolve_handle(handle, api_key)
    if not channel_id:
        raise ValueError(f"Cannot resolve channel @{handle}")
    print(f"SHORTS_CHANNEL_RESOLVED channel_id={channel_id}", flush=True)
    # Membership of /shorts is the filter: short duration alone also matches
    # ordinary horizontal videos. Never fall back to /videos or keyword search.
    with YoutubeDL({"extract_flat": True, "skip_download": True, "quiet": True,
                    "socket_timeout": 15, "retries": 2, "extractor_retries": 2,
                    "ignoreerrors": False}) as youtube:
        listing = youtube.extract_info(f"https://www.youtube.com/@{handle}/shorts", download=False)
        entries = list((listing or {}).get("entries") or [])
    if not entries or any(not entry or not entry.get("id") for entry in entries):
        raise ValueError("Shorts listing unavailable or incomplete; refusing a partial backlog")
    ids = list(dict.fromkeys(entry["id"] for entry in entries))
    print(f"SHORTS_LISTING_COMPLETE count={len(ids)}", flush=True)
    candidates = []
    for offset in range(0, len(ids), 50):
        batch = ids[offset:offset + 50]
        params = {"part": "snippet", "id": ",".join(batch), "key": api_key}
        data = _json("https://www.googleapis.com/youtube/v3/videos?" + urlencode(params))
        for row in data.get("items", []):
            snippet = row.get("snippet", {})
            if snippet.get("channelId") != channel_id or not snippet.get("publishedAt"):
                raise ValueError("Shorts metadata did not match the configured channel")
            candidates.append({
                "platform": "youtube", "video_id": row["id"],
                "url": f"https://www.youtube.com/shorts/{row['id']}",
                "title": snippet.get("title", ""), "description": snippet.get("description", ""),
                "creator": snippet.get("channelTitle", handle), "channel_id": channel_id,
                "published_at": snippet["publishedAt"], "query": "shorts-backlog",
            })
        if set(batch) != {row.get("id") for row in data.get("items", [])}:
            raise ValueError("Incomplete Shorts metadata; retry instead of skipping older entries")
    return sorted(candidates, key=lambda item: (item["published_at"], item["video_id"]))


def process(config_path: str, state_path: str, output_path: str, deliver: bool,
            *, discover=None, analyze=None, send=None, now=None) -> dict:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    source = config["shorts_backlog"]
    if not source.get("enabled"):
        return {"status": "disabled", "jobs": []}
    state_file = Path(state_path)
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    if state.get("pending_delivery"):
        raise RuntimeError("Previous Telegram delivery is unconfirmed; check Telegram and resolve pending_delivery before retrying")
    today = (now or datetime.now(ZoneInfo("Asia/Kolkata"))).astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    history = state.setdefault("history", [])
    completed = {item["video_id"] for item in history}
    delivered_today = sum(item["date_ist"] == today for item in history)
    remaining = max(0, min(2, int(source["daily_limit"])) - delivered_today)
    result = {"date_ist": today, "source": source["handle"], "jobs": [], "remaining_today": remaining}
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if remaining:
        with stage_deadline("discover-shorts", 180):
            candidates = (discover or discover_shorts)(source["handle"], os.environ["YOUTUBE_API_KEY"])
        # Save the full queue for inspection, including all dates rather than a lookback window.
        state["queue"] = [item for item in candidates if item["video_id"] not in completed]
        if deliver:
            save_state(state_file, state)
        for candidate in state["queue"][:remaining]:
            if analyze is None:
                from .video_analyzer import analyze_interior_video
                analyze = analyze_interior_video
            # A failed analysis leaves this item at the head of tomorrow's queue.
            print(f"SHORTS_ANALYSIS video_id={candidate['video_id']}", flush=True)
            with stage_deadline("analyze-" + candidate["video_id"], 180):
                analysis = analyze(candidate)
            prompt = build_reference_prompt(candidate, analysis, config)
            job = {"candidate": candidate, "video_analysis": analysis, "gemini_prompt": prompt}
            if deliver:
                state["pending_delivery"] = {"video_id": candidate["video_id"], "date_ist": today}
                save_state(state_file, state)
                (send or _send_prompt)(prompt, candidate, os.environ["TELEGRAM_BOT_TOKEN"],
                                       os.environ["TELEGRAM_CHAT_ID"], delivered_today + 1, 2)
                history.append({"video_id": candidate["video_id"], "date_ist": today, "url": candidate["url"]})
                state.pop("pending_delivery")
                state["queue"] = [item for item in state["queue"] if item["video_id"] != candidate["video_id"]]
                save_state(state_file, state)
                delivered_today += 1
            result["jobs"].append(job)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["remaining_today"] = max(0, min(2, int(source["daily_limit"])) - delivered_today)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SHORTS_BACKLOG source={source['handle']} prepared={len(result['jobs'])} delivered_today={delivered_today}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="interior_trend_radar/config.json")
    parser.add_argument("--state", default="data/havenhaus_shorts_state.json")
    parser.add_argument("--output", default="interior_trend_radar/output/havenhaus_shorts_pack.json")
    parser.add_argument("--deliver", action="store_true")
    args = parser.parse_args()
    process(args.config, args.state, args.output, args.deliver)
