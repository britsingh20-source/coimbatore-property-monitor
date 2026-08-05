import html
import json
import os
import re
import textwrap
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


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


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def generate_fact_graphics(job: dict, destination: Path, count: int, start: int = 1) -> list[dict]:
    """Create honest branded VFX plates when free location media is insufficient."""
    destination.mkdir(parents=True, exist_ok=True)
    prop = job.get("property") or {}
    location = job.get("property_location", "Coimbatore")
    location_short = ", ".join(part.strip() for part in location.split(",")[:2])
    cards = [
        ("LOCATION FOCUS", location_short, "COIMBATORE"),
        ("LAND HIGHLIGHT", prop.get("land_area", "PROPERTY DETAILS"), prop.get("property_type", "PROPERTY")),
        ("ROAD CONNECTIVITY", prop.get("road_width", "LOCAL ACCESS"), prop.get("facing", "VERIFY ON SITE")),
        ("PROJECT FACTS", prop.get("approval", "DETAILS FROM SOURCE"), "SITE VISIT RECOMMENDED"),
    ]
    colors = [(6, 18, 35), (8, 30, 28), (30, 20, 8), (25, 10, 35)]
    output = []
    for offset in range(count):
        title, value, footer = cards[offset % len(cards)]
        image = Image.new("RGB", (1080, 1920), colors[offset % len(colors)])
        draw = ImageDraw.Draw(image)
        accent = (35, 231, 190)
        draw.rounded_rectangle((70, 120, 1010, 1800), radius=48, outline=accent, width=5)
        for radius in (130, 230, 330):
            draw.ellipse((540-radius, 510-radius, 540+radius, 510+radius), outline=(*accent, 110), width=4)
        draw.line((175, 1130, 410, 900, 665, 1050, 900, 780), fill=accent, width=18)
        for x, y in ((175, 1130), (410, 900), (665, 1050), (900, 780)):
            draw.ellipse((x-24, y-24, x+24, y+24), fill=(255, 190, 45), outline="white", width=5)
        draw.text((100, 150), "COIMBATOREVEEDU BUILDERS", font=_font(42, True), fill="white")
        draw.text((100, 1270), title, font=_font(46, True), fill=accent)
        wrapped = textwrap.fill(str(value), width=20)
        draw.multiline_text((100, 1360), wrapped, font=_font(72, True), fill="white", spacing=16)
        draw.text((100, 1690), str(footer), font=_font(38, True), fill=(255, 190, 45))
        draw.text((100, 1760), "Representative graphic • Verify property on site", font=_font(28), fill=(205, 215, 225))
        path = destination / f"{start + offset:02d}-autopilot-vfx.jpg"
        image.save(path, quality=92)
        output.append({
            "local_file": str(path), "provider": "CoimbatoreVeedu Builders Autopilot",
            "license": "Original generated graphic", "media_kind": "image",
            "actual_property": False, "exact_location_candidate": False,
            "source_url": job.get("source_url", ""),
        })
    return output


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
    prop = job.get("property") or {}
    property_type = prop.get("property_type", "property")
    queries = [
        f"{location} Coimbatore Tamil Nadu",
        f"{location} roads buildings",
        f"{property_type} layout Coimbatore Tamil Nadu",
        "Coimbatore Tamil Nadu streets architecture",
        "Coimbatore aerial city Tamil Nadu",
    ]
    candidates = []
    seen_urls = set()
    for query in queries:
        try:
            results = search_commons(query, limit=8)
        except requests.RequestException as error:
            print(f"Commons search skipped for {query!r}: {error}")
            continue
        for item in results:
            if item["download_url"] not in seen_urls:
                candidates.append(item)
                seen_urls.add(item["download_url"])
    candidates.extend(search_pexels(f"modern Indian {property_type} interior exterior", limit=8))

    saved = download_media(candidates, destination, limit=6)
    for item in saved:
        item["actual_property"] = False
    if len(saved) < minimum:
        fallback_count = minimum - len(saved)
        saved.extend(generate_fact_graphics(job, destination, fallback_count, start=len(saved) + 1))
        print(f"Used {fallback_count} autopilot VFX fallback plate(s) for {video_id}")

    attribution = Path("data/media_attribution")
    attribution.mkdir(parents=True, exist_ok=True)
    (attribution / f"{video_id}.json").write_text(
        json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8"
    )
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
    property_type = str((job.get("property") or {}).get("property_type", "property")).lower()
    if any(kind in property_type for kind in ("plot", "land", "site")):
        queries = [
            f"residential land plots aerial roads {location}",
            "plotted development layout roads aerial India",
            "residential land site road drone India",
        ]
    else:
        queries = [
            f"modern Indian {property_type} exterior walkthrough {location}",
            "modern Indian house interior walkthrough",
            "residential street house exterior India",
        ]
    candidates = []
    seen_sources = set()
    for query in queries:
        for item in search_pexels_videos(query, limit=limit):
            identity = item.get("source_url") or item.get("download_url")
            if identity not in seen_sources:
                candidates.append(item)
                seen_sources.add(identity)
        if len(candidates) >= limit:
            break
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
