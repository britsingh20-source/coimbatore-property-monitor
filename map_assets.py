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
    """Return the most specific usable locality/street label available in the job."""
    raw = str(job.get("property_location") or "Coimbatore").strip()
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    priority = (
        "colony", "hudco", "nagar", "layout", "pattanam", "street", "road",
        "saravanampatti", "thudiyalur",
    )
    chosen = next((part for marker in priority for part in parts if marker in part.lower()), parts[0])
    from_match = re.search(r"\bfrom\s+(.+)$", chosen, flags=re.IGNORECASE)
    if from_match:
        chosen = from_match.group(1)
    chosen = re.sub(r"^(?:near|close to)\s+", "", chosen, flags=re.IGNORECASE)
    chosen = re.sub(r"^\d+(?:\.\d+)?\s*(?:km|kms|kilometres?)\s+", "", chosen, flags=re.IGNORECASE)
    return chosen.strip(" ,-") or "Coimbatore"


def geocode_candidates(job: dict) -> list[str]:
    """Try only specific property/locality queries; never silently fall back to all-Coimbatore."""
    raw = str(job.get("property_location") or "Coimbatore").strip()
    label = location_label(job)
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    candidates = [
        f"{label}, Coimbatore, Tamil Nadu, India",
        f"{raw}, Tamil Nadu, India" if "coimbatore" in raw.lower() else f"{raw}, Coimbatore, Tamil Nadu, India",
        f"{', '.join(parts[:2])}, Coimbatore, Tamil Nadu, India" if len(parts) >= 2 else "",
    ]
    unique = []
    for query in candidates:
        query = re.sub(r"(?:,\s*Coimbatore){2,}", ", Coimbatore", query, flags=re.IGNORECASE).strip(" ,")
        if query and query.lower() not in {item.lower() for item in unique}:
            unique.append(query)
    return unique


def geocode_query(job: dict) -> str:
    return geocode_candidates(job)[0]


def _specific_enough(display_name: str, label: str) -> bool:
    text = display_name.lower()
    wanted = [token for token in re.split(r"[^a-z0-9]+", label.lower()) if len(token) >= 4]
    return not wanted or any(token in text for token in wanted)


def geocode(job: dict) -> dict:
    video_id = job["video_id"]
    raw_location = str(job.get("property_location") or "Coimbatore").strip()
    label = location_label(job)
    cache = Path("data/geocoding") / f"{video_id}.json"
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if (
            cached.get("source_location") == raw_location
            and _specific_enough(str(cached.get("display_name") or ""), label)
        ):
            return cached

    result = None
    for query in geocode_candidates(job):
        response = requests.get(
            NOMINATIM,
            params={"q": query, "format": "jsonv2", "limit": 5, "countrycodes": "in"},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        results = response.json()
        chosen = next(
            (item for item in results if _specific_enough(str(item.get("display_name") or ""), label)),
            None,
        )
        if chosen:
            result = {
                "lat": float(chosen["lat"]),
                "lon": float(chosen["lon"]),
                "display_name": chosen.get("display_name", query),
                "query": query,
                "source_location": raw_location,
                "location_label": label,
                "provider": "OpenStreetMap contributors / Nominatim",
            }
            break
    if result is None:
        raise RuntimeError(f"Specific location was not found: {geocode_candidates(job)}")
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
    draw.text((140, 1150), "Exact street not available - verify location", fill="#9C6C16", font=small)
    image.save(path, quality=92)


def render_map_sequence(job: dict) -> list[Path]:
    """Create locality/street-level OSM views; never render state/country-wide maps."""
    output = Path("assets/maps") / job["video_id"]
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("map-*.jpg"):
        stale.unlink()
    try:
        point = geocode(job)
        from staticmap import CircleMarker, StaticMap

        paths = []
        # Reel maps should start close and get closer: neighbourhood -> streets -> immediate block.
        for index, zoom in enumerate((14, 16, 18), start=1):
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
        label = location_label(job)
        for index, detail in enumerate(("Neighbourhood", "Street area", "Immediate area"), start=1):
            path = output / f"map-{index}.jpg"
            _placeholder(path, label, detail)
            paths.append(path)
        return paths
