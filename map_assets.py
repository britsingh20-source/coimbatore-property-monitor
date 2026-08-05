import json
import os
import re
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = os.environ.get(
    "MAP_USER_AGENT",
    "CoimbatorePropertyMonitor/2.0 (GitHub Actions property-video renderer)",
)


def location_label(job: dict) -> str:
    """Return the specific locality that should appear in maps and VFX labels."""
    raw = str(job.get("property_location") or "Coimbatore").strip()
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    priority = ("colony", "nagar", "layout", "pattanam", "saravanampatti", "thudiyalur")
    chosen = next((part for marker in priority for part in parts if marker in part.lower()), parts[0])
    from_match = re.search(r"\bfrom\s+(.+)$", chosen, flags=re.IGNORECASE)
    if from_match:
        chosen = from_match.group(1)
    chosen = re.sub(r"^(?:near|close to)\s+", "", chosen, flags=re.IGNORECASE)
    chosen = re.sub(r"^\d+(?:\.\d+)?\s*(?:km|kms|kilometres?)\s+", "", chosen, flags=re.IGNORECASE)
    return chosen.strip(" ,-") or "Coimbatore"


def geocode_candidates(job: dict) -> list[str]:
    """Try the most specific locality first instead of one brittle long query."""
    raw = str(job.get("property_location") or "Coimbatore").strip()
    label = location_label(job)
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    candidates = [
        f"{label}, Coimbatore, Tamil Nadu, India",
        f"{', '.join(parts[:2])}, Coimbatore, Tamil Nadu, India",
        f"{raw}, Tamil Nadu, India" if "coimbatore" in raw.lower() else f"{raw}, Coimbatore, Tamil Nadu, India",
        "Coimbatore, Tamil Nadu, India",
    ]
    unique = []
    for query in candidates:
        query = re.sub(r"(?:,\s*Coimbatore){2,}", ", Coimbatore", query, flags=re.IGNORECASE)
        if query.lower() not in {item.lower() for item in unique}:
            unique.append(query)
    return unique


def geocode_query(job: dict) -> str:
    return geocode_candidates(job)[0]


def geocode(job: dict) -> dict:
    video_id = job["video_id"]
    raw_location = str(job.get("property_location") or "Coimbatore").strip()
    cache = Path("data/geocoding") / f"{video_id}.json"
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("source_location") == raw_location:
            return cached

    result = None
    for query in geocode_candidates(job):
        response = requests.get(
            NOMINATIM,
            params={"q": query, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            result = {
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
                "display_name": results[0].get("display_name", query),
                "query": query,
                "source_location": raw_location,
                "location_label": location_label(job),
                "provider": "OpenStreetMap contributors / Nominatim",
            }
            break
    if result is None:
        raise RuntimeError(f"Location was not found: {geocode_candidates(job)}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _placeholder(path: Path, title: str, subtitle: str) -> None:
    image = Image.new("RGB", (1080, 1350), "#071A2E")
    draw = ImageDraw.Draw(image)
    for radius, color in [(390, "#12395B"), (230, "#19517A"), (70, "#D8A63D")]:
        box = (540 - radius, 675 - radius, 540 + radius, 675 + radius)
        draw.ellipse(box, outline=color, width=10)
    font = ImageFont.load_default(size=42)
    small = ImageFont.load_default(size=26)
    draw.rounded_rectangle((90, 950, 990, 1190), radius=40, fill="#F5F0E6")
    draw.text((140, 1000), title[:42], fill="#071A2E", font=font)
    draw.text((140, 1080), subtitle[:65], fill="#526477", font=small)
    draw.text((140, 1150), "Map unavailable - verify location", fill="#9C6C16", font=small)
    image.save(path, quality=92)


def render_map_sequence(job: dict) -> list[Path]:
    """Create a three-step OSM zoom centered on this job's specific locality."""
    output = Path("assets/maps") / job["video_id"]
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("map-*.jpg"):
        stale.unlink()
    try:
        point = geocode(job)
        from staticmap import CircleMarker, StaticMap

        paths = []
        for index, zoom in enumerate((7, 12, 15), start=1):
            canvas = StaticMap(
                1080,
                1350,
                url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                tile_request_timeout=20,
                headers={"User-Agent": USER_AGENT},
            )
            canvas.add_marker(CircleMarker((point["lon"], point["lat"]), "#C88B25", 28))
            image = canvas.render(zoom=zoom, center=[point["lon"], point["lat"]])
            path = output / f"map-{index}.jpg"
            image.convert("RGB").save(path, quality=92)
            paths.append(path)
        (output / "attribution.json").write_text(json.dumps(point, ensure_ascii=False, indent=2), encoding="utf-8")
        return paths
    except Exception as error:
        print(f"Map rendering fallback: {error}")
        paths = []
        labels = ("Tamil Nadu", "Coimbatore", location_label(job))
        for index, label in enumerate(labels, start=1):
            path = output / f"map-{index}.jpg"
            _placeholder(path, str(label), "OpenStreetMap location sequence")
            paths.append(path)
        return paths
