from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import parse, request
from xml.etree import ElementTree

UA = "Interior-Trend-Radar/1.0"


def _json(url: str) -> dict:
    with request.urlopen(request.Request(url, headers={"User-Agent": UA}), timeout=45) as response:
        return json.loads(response.read())


def _id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _youtube_search(query: str, api_key: str, published_after: str) -> list[dict]:
    params = {
        "part": "snippet", "type": "video", "videoDuration": "short", "order": "date",
        "maxResults": 10, "q": query, "publishedAfter": published_after, "key": api_key,
    }
    data = _json("https://www.googleapis.com/youtube/v3/search?" + parse.urlencode(params))
    items = []
    for row in data.get("items", []):
        video_id = row.get("id", {}).get("videoId")
        snippet = row.get("snippet", {})
        if not video_id:
            continue
        items.append({
            "platform": "youtube", "video_id": video_id,
            "url": f"https://www.youtube.com/shorts/{video_id}",
            "title": snippet.get("title", ""), "description": snippet.get("description", ""),
            "creator": snippet.get("channelTitle", ""), "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "query": query,
        })
    return items


def _resolve_handle(handle: str, api_key: str) -> str:
    params = {"part": "id", "forHandle": handle.lstrip("@"), "key": api_key}
    data = _json("https://www.googleapis.com/youtube/v3/channels?" + parse.urlencode(params))
    items = data.get("items", [])
    return items[0]["id"] if items else ""


def _youtube_channel_search(channel: dict, api_key: str, published_after: str) -> list[dict]:
    channel_id = channel.get("channel_id", "") or _resolve_handle(channel.get("handle", ""), api_key)
    if not channel_id:
        raise ValueError(f"could not resolve @{channel.get('handle', '')}")
    params = {
        "part": "snippet", "type": "video", "order": "date", "maxResults": 10,
        "channelId": channel_id, "publishedAfter": published_after, "key": api_key,
    }
    data = _json("https://www.googleapis.com/youtube/v3/search?" + parse.urlencode(params))
    items = []
    for row in data.get("items", []):
        video_id = row.get("id", {}).get("videoId"); snippet = row.get("snippet", {})
        if not video_id: continue
        items.append({
            "platform": "youtube", "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": snippet.get("title", ""), "description": snippet.get("description", ""),
            "creator": channel.get("name") or snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "query": "priority-channel", "channel_id": channel_id,
            "channel_priority": int(channel.get("priority", 2)),
        })
    return items


def _youtube_feed(channel_id: str) -> list[dict]:
    url = "https://www.youtube.com/feeds/videos.xml?" + parse.urlencode({"channel_id": channel_id})
    with request.urlopen(request.Request(url, headers={"User-Agent": UA}), timeout=45) as response:
        root = ElementTree.fromstring(response.read())
    atom = "http://www.w3.org/2005/Atom"; yt = "http://www.youtube.com/xml/schemas/2015"
    items = []
    for entry in root.findall(f"{{{atom}}}entry"):
        video_id = entry.findtext(f"{{{yt}}}videoId", "")
        items.append({
            "platform": "youtube", "video_id": video_id,
            "url": f"https://www.youtube.com/shorts/{video_id}",
            "title": entry.findtext(f"{{{atom}}}title", ""), "description": "",
            "creator": entry.findtext(f"{{{atom}}}author/{{{atom}}}name", ""),
            "published_at": entry.findtext(f"{{{atom}}}published", ""), "thumbnail": "", "query": "channel-feed",
        })
    return items


def discover(config_path: str, output_path: str) -> dict:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(config.get("lookback_days", 10)))
    after = cutoff.isoformat().replace("+00:00", "Z")
    candidates, errors = [], []
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if api_key:
        for channel in config.get("monitored_youtube_channels", []):
            try: candidates.extend(_youtube_channel_search(channel, api_key, after))
            except Exception as exc: errors.append(f"youtube channel {channel.get('name', '')}: {type(exc).__name__}: {exc}")
        for query in config.get("youtube_queries", []):
            try: candidates.extend(_youtube_search(query, api_key, after))
            except Exception as exc: errors.append(f"youtube search {query}: {type(exc).__name__}: {exc}")
    else:
        errors.append("YOUTUBE_API_KEY missing; query discovery skipped")
    for channel_id in config.get("youtube_channel_ids", []):
        try: candidates.extend(_youtube_feed(channel_id))
        except Exception as exc: errors.append(f"youtube feed {channel_id}: {type(exc).__name__}: {exc}")
    for url in config.get("manual_competitor_urls", []):
        candidates.append({"platform": "manual", "video_id": _id(url), "url": url, "title": "Manual competitor reference", "description": "", "creator": "", "published_at": datetime.now(timezone.utc).isoformat(), "thumbnail": "", "query": "manual"})
    unique = {item["url"]: item for item in candidates}
    ranked = sorted(
        unique.values(),
        key=lambda x: (-(int(x.get("channel_priority", 99))), x.get("published_at", "")),
        reverse=True,
    )
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "errors": errors, "candidates": ranked[:int(config.get("max_candidates", 12))]}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(result['candidates'])} interior candidates")
    return result


if __name__ == "__main__":
    import sys
    discover(sys.argv[1] if len(sys.argv) > 1 else "interior_trend_radar/config.json", sys.argv[2] if len(sys.argv) > 2 else "interior_trend_radar/output/candidates.json")
