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


def build_social_content(job: dict) -> dict[str, str | list[str]]:
    prop = job.get("property") or {}
    location = _clean(job.get("property_location")) or "Coimbatore"
    kind = _clean(prop.get("property_type")) or "Property"
    bhk = _clean(prop.get("bhk"))
    price = _clean(prop.get("price"))
    land = _clean(prop.get("land_area"))
    built_up = _clean(prop.get("built_up_area"))
    facing = _clean(prop.get("facing"))
    parking = _clean(prop.get("parking"))
    approval = _clean(prop.get("approval"))

    bhk_label = bhk if re.search(r"\\bBHK\\b", bhk, flags=re.IGNORECASE) else (f"{bhk} BHK" if bhk else "")
    subject = " ".join(part for part in (bhk_label, kind) if part)
    hook = f"{price} {subject} in {location}" if price else f"{subject} in {location}"
    title = f"{hook} | Site Visit {CONTACT_NUMBER}"[:100]

    facts = [
        f"📍 Location: {location}",
        f"🏡 Property: {subject}",
    ]
    for icon, label, value in (
        ("💰", "Price", price),
        ("📐", "Land", land),
        ("🏗️", "Built-up", built_up),
        ("🧭", "Facing", facing),
        ("🚗", "Parking", parking),
        ("✅", "Approval", approval),
    ):
        if value:
            facts.append(f"{icon} {label}: {value}")

    hashtags = [
        "#CoimbatoreProperty",
        _hashtag(f"{location}Property"),
        "#CoimbatoreRealEstate",
    ]
    caption = "\n".join([
        f"🏠 {hook} — would you visit this property?",
        "",
        *facts,
        "",
        f"📞 Site visit and complete details: {CONTACT_NUMBER}",
        "Availability, measurements, documents and final price must be verified during the site visit.",
        "",
        " ".join(hashtags),
    ])
    youtube_description = "\n".join([
        f"{hook}. Watch the complete 10-second walkthrough.",
        "",
        *facts,
        "",
        f"For complete details and a site visit, call {CONTACT_NUMBER}.",
        "Property information is based on the source listing. Verify availability, documents, dimensions and price before purchase.",
        "",
        " ".join(hashtags),
    ])
    return {
        "title": title,
        "caption": caption,
        "youtube_description": youtube_description,
        "hashtags": hashtags,
    }
