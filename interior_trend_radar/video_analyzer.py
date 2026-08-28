from __future__ import annotations

import json
import os
import re

from google import genai


MODEL = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash")


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start: raise ValueError("Interior analysis did not return JSON")
    return json.loads(cleaned[start:end + 1])


def analyze_interior_video(candidate: dict) -> dict:
    prompt = f"""Analyse this public interior-design video using its audio, visuals and metadata.
Return exactly one JSON object. Never guess. The most important task is to distinguish the exact product/system from a visually similar generic substitute.

Required keys:
is_interior_topic (boolean), core_idea, system_type, installation_method, mechanism,
room_application, practical_benefit, required_components (array), verified_facts (array),
visual_identity, shot_subjects (array of exactly 7 visually supported subjects),
forbidden_substitutes (array), limitations.

Rules:
- Explain how the system is installed and how it functions, not merely its broad product category.
- If it connects to an AC, duct, cabinet, plumbing, electrical supply or building system, state that connection explicitly.
- forbidden_substitutes must name plausible but incorrect objects Gemini must not generate.
- Use only claims supported by the video/audio. Say "NOT CONFIRMED" when unclear.
- Ignore and do not reproduce the presenter, face, channel logo, captions or branding.

Title: {candidate.get('title', '')}
Description: {candidate.get('description', '')}
Channel: {candidate.get('creator', '')}
URL: {candidate.get('url', '')}
"""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    interaction = client.interactions.create(
        model=MODEL,
        input=[{"type": "video", "uri": candidate["url"]}, {"type": "text", "text": prompt}],
    )
    result = _parse_json(interaction.output_text)
    if not result.get("is_interior_topic"):
        raise ValueError("Selected video was not confirmed as interior-related")
    verified = result.get("verified_facts") or []
    forbidden = result.get("forbidden_substitutes") or []
    if not verified or not forbidden or str(result.get("system_type", "")).upper() in ("", "NOT CONFIRMED"):
        raise ValueError("Interior mechanism analysis was incomplete; refusing a generic prompt")
    return result
