from __future__ import annotations

import json
import os
import re
from pathlib import Path

from google import genai


MODEL = os.environ.get("GEMINI_SOCIAL_MATCH_MODEL", "gemini-2.5-flash-lite")
MIN_CONFIDENCE = float(os.environ.get("SOCIAL_MATCH_MIN_CONFIDENCE", "0.85"))


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini matching response did not contain JSON")
    return json.loads(cleaned[start:end + 1])


def _candidate(video_id: str) -> dict:
    job = json.loads((Path("data/video_jobs") / f"{video_id}.json").read_text(encoding="utf-8"))
    prop = job.get("property") or {}
    return {
        "video_id": video_id,
        "location": job.get("property_location"),
        "property_type": prop.get("property_type"),
        "bhk": prop.get("bhk"),
        "land_area": prop.get("land_area"),
        "built_up_area": prop.get("built_up_area"),
        "price": prop.get("price"),
        "facing": prop.get("facing"),
        "parking": prop.get("parking"),
        "approval": prop.get("approval"),
        "verified_facts": job.get("verified_facts"),
    }


def match_uploaded_video(video_url: str, pending_video_ids: list[str]) -> dict:
    candidates = [_candidate(video_id) for video_id in pending_video_ids]
    if not candidates:
        return {"video_id": None, "confidence": 0.0, "evidence": ["no pending prompts"]}

    prompt = f"""
Analyse this uploaded 10-second property advertisement frame-by-frame and listen to any audio.
Match it to exactly one pending property candidate only when the evidence is strong.

Prioritise visible footer text: location, price, land area, built-up area and phone number.
Also compare BHK, property type, approval, facing, parking, exterior and interior features.
Do not match merely because every candidate is in Coimbatore.
Never choose by list order, upload time or filename.

Return one JSON object only:
{{
  "video_id": "candidate id or null",
  "confidence": 0.0,
  "evidence": ["specific matching facts"],
  "conflicts": ["specific contradictions"],
  "observed_footer": {{
    "location": "",
    "price": "",
    "land_area": "",
    "contact": ""
  }}
}}

Rules:
- confidence must be at least 0.85 only when at least two independent property facts match;
- any contradictory price, land area or location must prevent a match;
- use null when text is unreadable, evidence is generic, multiple candidates are plausible, or the video does not match.

PENDING PROPERTY CANDIDATES
{json.dumps(candidates, ensure_ascii=False, indent=2)}
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
    matched = str(result.get("video_id") or "").strip()
    confidence = float(result.get("confidence") or 0)
    valid_ids = set(pending_video_ids)
    if matched not in valid_ids or confidence < MIN_CONFIDENCE:
        result["video_id"] = None
    result["confidence"] = confidence
    return result
