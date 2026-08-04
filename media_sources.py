import html
import json
import os
import re
from pathlib import Path
import requests


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PEXELS_API = "https://api.pexels.com/v1/search"
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
    response = requests.get(PEXELS_API, params={
        "query": query, "orientation": "portrait", "per_page": min(limit, 80),
    }, headers={"Authorization": api_key}, timeout=30)
    response.raise_for_status()
    return [{
        "download_url": photo["src"].get("large2x") or photo["src"]["large"],
        "source_url": photo["url"],
        "creator": photo.get("photographer", "Pexels contributor"),
        "license": "Pexels License",
        "provider": "Pexels",
        "exact_location_candidate": False,
    } for photo in response.json().get("photos", [])]


def download_media(items: list[dict], destination: Path, limit: int = 6) -> list[dict]:
    destination.mkdir(parents=True, exist_ok=True)
    saved = []
    for index, item in enumerate(items[:limit], start=1):
        try:
            response = requests.get(item["download_url"], headers={"User-Agent": USER_AGENT}, timeout=45)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
            extension = {"image/png": ".png", "image/webp": ".webp"}.get(content_type, ".jpg")
            path = destination / f"{index:02d}-{item['provider'].lower().replace(' ', '-')}{extension}"
            path.write_bytes(response.content)
            saved.append({**item, "local_file": str(path)})
        except requests.RequestException as error:
            print(f"Media download skipped: {error}")
    return saved


def source_property_media(job: dict, minimum: int = 3) -> list[dict]:
    video_id = job["video_id"]
    destination = Path("assets/properties") / video_id
    existing = list(destination.glob("*.*")) if destination.exists() else []
    if len(existing) >= minimum:
        return [{"local_file": str(path), "provider": "Advertiser supplied", "license": "Owner supplied"} for path in existing]

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
    attribution = Path("data/media_attribution")
    attribution.mkdir(parents=True, exist_ok=True)
    (attribution / f"{video_id}.json").write_text(
        json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if len(saved) < minimum:
        raise RuntimeError(f"Only {len(saved)} reusable images found for {location}; need {minimum}")
    return saved
