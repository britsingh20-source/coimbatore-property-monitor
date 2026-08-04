import csv
from pathlib import Path


OUTPUT = Path("data/properties.csv")
FIELDS = [
    "source_name", "video_id", "video_title", "video_url", "published_at",
    "transcript_status", "gemini_status", "gemini_error",
    "is_property_listing", "location", "normalized_locality",
    "is_target_location", "location_score", "property_type", "bhk",
    "land_area", "built_up_area", "price", "facing", "road_width",
    "floors", "bedrooms", "bathrooms", "parking", "approval",
    "amenities", "nearby_landmarks", "contact_details", "missing_fields",
    "source_facts", "visual_style", "exterior_description",
    "neighbourhood_description", "video_status",
]


def _value(value):
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    return value


def upsert_record(video: dict, result: dict, location: dict) -> None:
    rows = {}
    if OUTPUT.exists():
        with OUTPUT.open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                if row.get("video_id"):
                    rows[row["video_id"]] = row

    row = {field: "" for field in FIELDS}
    row.update({
        "source_name": video.get("source_name", ""),
        "video_id": video["video_id"],
        "video_title": video.get("title", ""),
        "video_url": video.get("url", ""),
        "published_at": video.get("published_at", ""),
        "normalized_locality": " | ".join(location["matched_localities"]),
        "is_target_location": location["is_target_location"],
        "location_score": location["location_score"],
        "video_status": "approval_pending" if location["is_target_location"] else "not_target",
    })
    for field in FIELDS:
        if field in result:
            row[field] = _value(result[field])
    rows[video["video_id"]] = row

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows.values())
    temporary.replace(OUTPUT)


def legacy_retry_videos() -> list[dict]:
    """Recover previously failed CSV rows so they are not permanently lost."""
    if not OUTPUT.exists():
        return []
    videos = []
    with OUTPUT.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("video_id") and row.get("gemini_status") != "success":
                videos.append({
                    "video_id": row["video_id"],
                    "title": row.get("video_title", ""),
                    "description": "",
                    "published_at": row.get("published_at", ""),
                    "channel_title": row.get("source_name", ""),
                    "source_name": row.get("source_name", ""),
                    "url": row.get("video_url") or f"https://www.youtube.com/watch?v={row['video_id']}",
                })
    return videos
