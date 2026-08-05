import html
import json
import os
import re
from pathlib import Path
import requests


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PEXELS_PHOTO_API = "https://api.pexels.com/v1/search"
PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"
USER_AGENT = "CoimbatorePropertyMonitor/1.0 (property media attribution bot)"


def _plain(value: str) -> str:
    value = html.unescape(value or "")
    return re.sub(r"<[^>]+>", "", value).strip()


def search_commons(query: str, limit: int = 8) -> list[dict]:
    response = requests.get(COMMONS_API, params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|mime|extmetadata", "iiurlwidth": 1600,
    }, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    items = []
    for page in response.json().get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        metadata = info.get("extmetadata", {})
        items.append({
            "download_url": info.get("thumburl") or info.get("url"),
            "source_url": info.get("descriptionurl") or info.get("url"),
            "creator": _plain(metadata.get("Artist", {}).get("value", "Wikimedia contributor")),
            "license": _plain(metadata.get("LicenseShortName", {}).get("value", "See source page")),
            "provider": "Wikimedia Commons",
            "exact_location_candidate": True,
        })
    return [item for item in items if item["download_url"]]


def search_pexels(query: str, limit: int = 8) -> list[dict]:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return []
    response = requests.get(PEXELS_PHOTO_API, params={
        "query": query, "orientation": "portrait", "per_page": min(limit, 80),
    }, headers={"Authorization": api_key}, timeout=30)
    response.raise_for_status()
    return [{
        "download_url": photo["src"].get("large2x") or photo["src"]["large"],
        "source_url": photo["url"],
        "creator": photo.get("photographer", "Pexels contributor"),
        "license": "Pexels License",
        "provider": "Pexels",
        "media_kind": "image",
        "exact_location_candidate": False,
    } for photo in response.json().get("photos", [])]


def search_pexels_videos(query: str, limit: int = 6) -> list[dict]:
    """Return reusable portrait property clips from the free Pexels video API."""
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return []
    response = requests.get(PEXELS_VIDEO_API, params={
        "query": query, "orientation": "portrait", "per_page": min(limit, 80),
    }, headers={"Authorization": api_key}, timeout=30)
    response.raise_for_status()
    clips = []
    for video in response.json().get("videos", []):
        files = [item for item in video.get("video_files", []) if item.get("file_type") == "video/mp4"]
        if not files:
            continue
        portrait = [item for item in files if (item.get("height") or 0) >= (item.get("width") or 0)]
        candidates = portrait or files
        candidates.sort(key=lambda item: abs((item.get("height") or 0) - 1920) + abs((item.get("width") or 0) - 1080))
        chosen = candidates[0]
        user = video.get("user") or {}
        clips.append({
            "download_url": chosen["link"],
            "source_url": video.get("url", "https://www.pexels.com/videos/"),
            "creator": user.get("name", "Pexels contributor"),
            "license": "Pexels License",
            "provider": "Pexels",
            "media_kind": "video",
            "exact_location_candidate": False,
        })
    return clips


def download_media(items: list[dict], destination: Path, limit: int = 6) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    saved = []
    for index, item in enumerate(items[:limit], start=1):
        try:
            response = requests.get(item["download_url"], headers={"User-Agent": USER_AGENT}, timeout=45)
            response.raise_for_status()
            default_type = "video/mp4" if item.get("media_kind") == "video" else "image/jpeg"
            content_type = response.headers.get("content-type", default_type).split(";")[0]
            extension = {
                "image/png": ".png", "image/webp": ".webp", "video/mp4": ".mp4",
            }.get(content_type, ".jpg")
            path = destination / f"{index:02d}-{item['provider'].lower().replace(' ', '-')}{extension}"
            path.write_bytes(response.content)
            saved.append({**item, "local_file": str(path)})
        except requests.RequestException as error:
            print(f"Media download skipped: {error}")
    return saved


def source_property_media(job: dict, minimum: int = 3) -> list[dict]:
    video_id = job["video_id"]
    destination = Path("assets/properties") / video_id
    existing = []
    if destination.exists():
        for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            existing.extend(destination.glob(pattern))
    if len(existing) >= minimum:
        return [{
            "local_file": str(path), "provider": "Advertiser supplied",
            "license": "Owner supplied", "media_kind": "image", "actual_property": True,
        } for path in sorted(existing)]

    location = job.get("property_location", "Coimbatore")
    queries = [
        f"{location} Coimbatore Tamil Nadu",
        f"{location} architecture",
        "Coimbatore Tamil Nadu streets architecture",
    ]
    candidates = []
    for query in queries:
        candidates.extend(search_commons(query, limit=6))
        if len(candidates) >= 6:
            break
    if len(candidates) < minimum:
        candidates.extend(search_pexels("modern Indian house interior exterior", limit=8))

    saved = download_media(candidates, destination, limit=6)
    for item in saved:
        item["actual_property"] = False
    attribution = Path("data/media_attribution")
    attribution.mkdir(parents=True, exist_ok=True)
    (attribution / f"{video_id}.json").write_text(
        json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if len(saved) < minimum:
        raise RuntimeError(f"Only {len(saved)} reusable images found for {location}; need {minimum}")
    return saved


def source_property_videos(job: dict, limit: int = 4) -> list[dict]:
    """Prefer advertiser-owned clips, then fetch clearly labelled stock footage."""
    video_id = job["video_id"]
    owned_folder = Path("assets/properties") / video_id
    owned = []
    for pattern in ("*.mp4", "*.mov", "*.webm", "*.m4v"):
        owned.extend(owned_folder.glob(pattern))
    if owned:
        return [{
            "local_file": str(path), "provider": "Advertiser supplied",
            "license": "Owner supplied", "media_kind": "video", "actual_property": True,
        } for path in sorted(owned)]

    location = job.get("property_location", "Coimbatore")
    candidates = search_pexels_videos(f"modern Indian house walkthrough {location}", limit=limit)
    if len(candidates) < 2:
        candidates.extend(search_pexels_videos("modern house interior walkthrough", limit=limit))
    saved = download_media(candidates, Path("assets/videos") / video_id, limit=limit)
    for item in saved:
        item["actual_property"] = False

    attribution_path = Path("data/media_attribution") / f"{video_id}.json"
    attribution_path.parent.mkdir(parents=True, exist_ok=True)
    prior = []
    if attribution_path.exists():
        prior = json.loads(attribution_path.read_text(encoding="utf-8"))
    attribution_path.write_text(json.dumps(prior + saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return saved
