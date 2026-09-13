from __future__ import annotations

import json
import os
import re
import time

from google import genai


MODEL = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash")
TRANSIENT_RETRY_DELAYS = (35, 45, 60)


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Interior analysis did not return JSON")
    return json.loads(cleaned[start:end + 1])


def _is_transient_gemini_error(exc: Exception) -> bool:
    text = str(exc).casefold()
    return any(
        marker in text
        for marker in (
            "429",
            "too_many_requests",
            "quota exceeded",
            "rate limit",
            "resource exhausted",
            "500",
            "502",
            "503",
            "504",
            "server disconnected",
            "connection reset",
            "timed out",
            "timeout",
        )
    )


def _run_analysis(client: genai.Client, candidate: dict, prompt: str):
    last_error = None
    attempts = len(TRANSIENT_RETRY_DELAYS) + 1
    for attempt in range(1, attempts + 1):
        try:
            return client.interactions.create(
                model=MODEL,
                input=[
                    {"type": "video", "uri": candidate["url"]},
                    {"type": "text", "text": prompt},
                ],
            )
        except Exception as exc:
            last_error = exc
            if not _is_transient_gemini_error(exc) or attempt >= attempts:
                raise
            delay = TRANSIENT_RETRY_DELAYS[attempt - 1]
            print(
                f"Transient Gemini interior-analysis error for {candidate.get('video_id', '')}; "
                f"retry {attempt}/{attempts - 1} in {delay}s: {exc}"
            )
            time.sleep(delay)
    raise last_error or RuntimeError("Interior Gemini analysis failed")


def analyze_interior_video(candidate: dict) -> dict:
    prompt = f"""Analyse this public interior-design video using its audio, visuals and metadata.
Return exactly one JSON object. Never guess. The most important task is to distinguish the exact product/system from a visually similar generic substitute.

Required keys:
is_interior_topic (boolean), core_idea, system_type, installation_method, mechanism,
room_application, practical_benefit, required_components (array), verified_facts (array),
visual_identity, highlighted_innovations (array of 1 or 2 objects),
shot_subjects (array of exactly 7 visually supported subjects),
forbidden_substitutes (array), excluded_generic_scenes (array), limitations.

Each highlighted_innovations object must contain: name, why_notable, installation_method,
mechanism, practical_benefit, visual_evidence, forbidden_substitutes (array).

Rules:
- Explain how the system is installed and how it functions, not merely its broad product category.
- A complete-home tour is only a source container. Scan the entire video and select only the one or two strongest new interior updates, clever mechanisms, space-transforming features, smart hardware, movable systems, concealed installations or technically useful design solutions.
- Do not select an ordinary bedroom, bed, sofa, pool table, swing, wardrobe, lighting, false ceiling, decorative wall, colour palette or general room beauty unless it has a clearly demonstrated unusual mechanism, installation method or practical innovation.
- A walk-in wardrobe may qualify only when the source shows a notable planning, storage, access, lighting, concealment or hardware solution; describe that exact differentiator.
- When two strong innovations exist, preserve both. Do not let the general home tour hide the second innovation.
- If it connects to an AC, duct, cabinet, plumbing, electrical supply or building system, state that connection explicitly.
- forbidden_substitutes must name plausible but incorrect objects Gemini must not generate.
- excluded_generic_scenes must list visually attractive but non-innovative rooms/features from this source that must not appear in the generated reel.
- All seven shot_subjects must show only the selected highlighted innovations, divided between both when two are selected. Never use generic tour filler shots.
- Use only claims supported by the video/audio. Say "NOT CONFIRMED" when unclear.
- Ignore and do not reproduce the presenter, face, channel logo, captions or branding.

Title: {candidate.get('title', '')}
Description: {candidate.get('description', '')}
Channel: {candidate.get('creator', '')}
URL: {candidate.get('url', '')}
"""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    interaction = _run_analysis(client, candidate, prompt)
    result = _parse_json(interaction.output_text)
    if not result.get("is_interior_topic"):
        raise ValueError("Selected video was not confirmed as interior-related")
    verified = result.get("verified_facts") or []
    forbidden = result.get("forbidden_substitutes") or []
    highlights = result.get("highlighted_innovations") or []
    if not verified or not forbidden or not highlights or len(highlights) > 2 or str(result.get("system_type", "")).upper() in ("", "NOT CONFIRMED"):
        raise ValueError("Interior mechanism analysis was incomplete; refusing a generic prompt")
    for highlight in highlights:
        if not highlight.get("name") or not highlight.get("mechanism") or not highlight.get("practical_benefit"):
            raise ValueError("Highlighted innovation lacked mechanism or benefit")
    return result
