from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Any

from google import genai


MODEL = os.environ.get("GEMINI_MANUAL_AUDIO_MODEL", "gemini-3.5-flash-lite")
MISSING = {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE", "NULL"}
MANUAL_PATTERN = re.compile(
    r"(?:^|\s)(?:MANUAL_PUBLISH|MANUAL[\s_-]*PUBLISH|MODE\s*[:=]\s*MANUAL)(?:\s|$)",
    flags=re.I,
)


def manual_publish_requested(message: dict) -> bool:
    """Require an explicit publishing instruction in the video's own caption."""
    raw = str(message.get("caption") or message.get("text") or "")
    text = "".join(
        char for char in raw
        if unicodedata.category(char) != "Cf"
    ).strip()
    return bool(MANUAL_PATTERN.search(text))


def manual_video_id(file_unique_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", str(file_unique_id)).strip("-")
    if not safe:
        raise ValueError("Telegram video has no stable file_unique_id")
    return f"manual-{safe}"


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.upper() in MISSING else text


def _list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        cleaned = _clean(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Manual-video analysis did not return JSON")
    value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Manual-video analysis must return one JSON object")
    return value


def analyze_manual_video(video_url: str) -> dict:
    """Transcribe the video's spoken audio and extract only explicitly stated facts."""
    prompt = """
Listen carefully to the spoken narration in this manually recorded property video.
The speaker may use Tamil, English, or a mixture of both.

Use the AUDIO as the source of truth. Do not infer property facts from the visuals.
Do not guess, calculate, correct, or add facts that were not spoken.
Preserve prices, measurements, place names and phone numbers exactly as spoken.
If a field was not stated, return an empty string.

Return one JSON object only with exactly these keys:
{
  "transcript": "faithful transcript in the language spoken",
  "property_location": "",
  "property_type": "",
  "bhk": "",
  "price": "",
  "land_area": "",
  "built_up_area": "",
  "facing": "",
  "road_width": "",
  "parking": "",
  "approval": "",
  "amenities": [],
  "nearby_landmarks": [],
  "selling_points": [],
  "contact_number": "",
  "marketing_hook": "",
  "spoken_facts": []
}

Rules for marketing_hook:
- Write one attractive, truthful English sentence for a social-media caption.
- Use only facts explicitly present in the narration.
- Do not use superlatives such as "best", "cheapest", "guaranteed" or "luxury"
  unless the speaker explicitly said them.
- Do not invent availability, loan eligibility, approval, distance or pricing.
- Keep it below 140 characters.

Rules for selling_points and spoken_facts:
- Include only information explicitly heard in the audio.
- Keep each entry concise.
"""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    interaction = client.interactions.create(
        model=MODEL,
        input=[
            {"type": "video", "uri": video_url},
            {"type": "text", "text": prompt},
        ],
    )
    result = _parse_json(interaction.output_text)
    normalized = {
        "transcript": _clean(result.get("transcript")),
        "property_location": _clean(result.get("property_location")),
        "property_type": _clean(result.get("property_type")),
        "bhk": _clean(result.get("bhk")),
        "price": _clean(result.get("price")),
        "land_area": _clean(result.get("land_area")),
        "built_up_area": _clean(result.get("built_up_area")),
        "facing": _clean(result.get("facing")),
        "road_width": _clean(result.get("road_width")),
        "parking": _clean(result.get("parking")),
        "approval": _clean(result.get("approval")),
        "amenities": _list(result.get("amenities")),
        "nearby_landmarks": _list(result.get("nearby_landmarks")),
        "selling_points": _list(result.get("selling_points")),
        "contact_number": _clean(result.get("contact_number")),
        "marketing_hook": _clean(result.get("marketing_hook")),
        "spoken_facts": _list(result.get("spoken_facts")),
    }
    return normalized


def build_manual_job(video_id: str, analysis: dict) -> dict:
    """Convert verified spoken details into the existing publisher job contract."""
    location = _clean(analysis.get("property_location"))
    property_type = _clean(analysis.get("property_type"))
    commercial_facts = [
        _clean(analysis.get("bhk")),
        _clean(analysis.get("price")),
        _clean(analysis.get("land_area")),
        _clean(analysis.get("built_up_area")),
    ]
    if not location or not property_type or not any(commercial_facts):
        raise ValueError(
            "Audio must clearly state the location, property type, and at least one "
            "of BHK, price, land area or built-up area"
        )

    prop = {
        "property_type": property_type,
        "bhk": _clean(analysis.get("bhk")),
        "price": _clean(analysis.get("price")),
        "land_area": _clean(analysis.get("land_area")),
        "built_up_area": _clean(analysis.get("built_up_area")),
        "facing": _clean(analysis.get("facing")),
        "road_width": _clean(analysis.get("road_width")),
        "parking": _clean(analysis.get("parking")),
        "approval": _clean(analysis.get("approval")),
        "amenities": _list(analysis.get("amenities")),
        "nearby_landmarks": _list(analysis.get("nearby_landmarks")),
    }
    return {
        "video_id": video_id,
        "source_type": "manual_audio",
        "property_location": location,
        "property": prop,
        "verified_facts": _list(analysis.get("spoken_facts")),
        "selling_points": _list(analysis.get("selling_points")),
        "marketing_hook": _clean(analysis.get("marketing_hook")),
        "contact_number": _clean(analysis.get("contact_number")),
        "manual_audio": {
            "transcript": _clean(analysis.get("transcript")),
            "analysis_model": MODEL,
            "fact_policy": "spoken_audio_only_no_inference",
        },
        "status": "auto_approved",
        "approval_mode": "explicit_manual_publish_caption",
        "aspect_ratio": "9:16",
    }
