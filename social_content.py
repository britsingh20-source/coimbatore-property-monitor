from __future__ import annotations

import re
from typing import Any


CONTACT_NUMBER = "9003787621"
MISSING = {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.upper() in MISSING else text


def _hashtag(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value)
    return f"#{cleaned}" if cleaned else "#CoimbatoreProperty"


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = _clean(item)
        if text and text not in output:
            output.append(text)
    return output


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


def build_social_content(job: dict) -> dict[str, str | list[str]]:
    prop = job.get("property") or {}
    manual_audio = job.get("source_type") == "manual_audio"
    location = _clean(job.get("property_location")) or "Coimbatore"
    kind = _clean(prop.get("property_type")) or "Property"
    bhk = _clean(prop.get("bhk"))
    price = _clean(prop.get("price"))
    land = _clean(prop.get("land_area"))
    built_up = _clean(prop.get("built_up_area"))
    facing = _clean(prop.get("facing"))
    road_width = _clean(prop.get("road_width"))
    parking = _clean(prop.get("parking"))
    approval = _clean(prop.get("approval"))
    contact = _clean(job.get("contact_number")) or CONTACT_NUMBER

    bhk_label = bhk if re.search(r"\bBHK\b", bhk, flags=re.IGNORECASE) else (f"{bhk} BHK" if bhk else "")
    subject = " ".join(part for part in (bhk_label, kind) if part)
    factual_hook = f"{price} {subject} in {location}" if price else f"{subject} in {location}"
    marketing_hook = _clean(job.get("marketing_hook")) if manual_audio else ""
    hook = marketing_hook or factual_hook
    title_hook = factual_hook
    title = f"{title_hook} | Site Visit {contact}"[:100]

    facts = [
        f"📍 Location: {location}",
        f"🏡 Property: {subject}",
    ]
    for icon, label, value in (
        ("💰", "Price", price),
        ("📐", "Land", land),
        ("🏗️", "Built-up", built_up),
        ("🧭", "Facing", facing),
        ("🛣️", "Road", road_width),
        ("🚗", "Parking", parking),
        ("✅", "Approval", approval),
    ):
        if value:
            facts.append(f"{icon} {label}: {value}")

    amenities = _clean_list(prop.get("amenities"))
    landmarks = _clean_list(prop.get("nearby_landmarks"))
    selling_points = _clean_list(job.get("selling_points"))
    highlights = _unique([*selling_points, *amenities])[:5]

    hashtags = [
        "#CoimbatoreProperty",
        _hashtag(f"{location}Property"),
        "#CoimbatoreRealEstate",
    ]
    if manual_audio:
        area = location.split(",")[0].strip()
        hashtags = _unique([
            *hashtags,
            _hashtag(kind),
            _hashtag(f"{area}RealEstate"),
            "#PropertyForSale",
            "#TamilNaduRealEstate",
            "#HouseHunting",
        ])[:8]

    caption_parts = [
        f"🏠 {hook}",
        "",
        *facts,
    ]
    if highlights:
        caption_parts.extend(["", "✨ Highlights:", *[f"• {item}" for item in highlights]])
    if landmarks:
        caption_parts.extend(["", "📌 Nearby:", *[f"• {item}" for item in landmarks[:4]]])
    caption_parts.extend([
        "",
        f"📞 Site visit and complete details: {contact}",
        "Availability, measurements, documents and final price must be verified during the site visit.",
        "",
        " ".join(hashtags),
    ])
    caption = "\n".join(caption_parts)

    youtube_parts = [
        f"{hook}. Watch the complete property walkthrough.",
        "",
        *facts,
    ]
    if highlights:
        youtube_parts.extend(["", "Highlights:", *[f"- {item}" for item in highlights]])
    if landmarks:
        youtube_parts.extend(["", "Nearby landmarks:", *[f"- {item}" for item in landmarks[:4]]])
    youtube_parts.extend([
        "",
        f"For complete details and a site visit, call {contact}.",
        "Property information is based on the spoken video narration. Verify availability, documents, dimensions and price before purchase."
        if manual_audio else
        "Property information is based on the source listing. Verify availability, documents, dimensions and price before purchase.",
        "",
        " ".join(["#Shorts", *hashtags]),
    ])
    youtube_description = "\n".join(youtube_parts)
    return {
        "title": title,
        "caption": caption,
        "youtube_description": youtube_description,
        "hashtags": hashtags,
    }
