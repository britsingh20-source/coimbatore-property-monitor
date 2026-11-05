import json
import os
import re

import requests


MODEL = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.5-flash-lite")


class RetryableAnalysisError(RuntimeError):
    pass


def _is_retryable_error(message: str) -> bool:
    normalized = (message or "").lower()
    retryable_markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "quota",
        "resource_exhausted",
        "too_many_requests",
        "timeout",
        "timed out",
        "high demand",
        "api_error",
        "temporarily unavailable",
        "internal server error",
        "server disconnected",
        "connection reset",
        "connection aborted",
        "connection closed",
        "connection error",
        "remote protocol",
        "network error",
        "incomplete read",
    )
    return any(marker in normalized for marker in retryable_markers)


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini response did not contain a JSON object")
    return json.loads(cleaned[start:end + 1])


def _video_analysis(video: dict, prompt: str, model: str) -> str:
    """Use the same deadline-bound REST transport as the working interior queue."""
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
            json={"model": model, "input": [
                {"type": "text", "text": prompt},
                {"type": "video", "uri": video["url"]},
            ]},
            timeout=(10, 90),
        )
    except requests.RequestException as error:
        raise RetryableAnalysisError(
            f"Property video HTTP timeout/network error ({type(error).__name__})"
        ) from None
    if not response.ok:
        try:
            detail = str(response.json().get("error", {}).get("message", ""))
        except (ValueError, AttributeError):
            detail = "Provider returned a non-JSON error"
        for name in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
            secret = os.environ.get(name, "")
            if secret:
                detail = detail.replace(secret, "[redacted]")
        detail = re.sub(r"AIza[A-Za-z0-9_-]+", "[redacted]", detail)
        detail = re.sub(r"projects/[A-Za-z0-9_-]+", "projects/[redacted]", detail)
        message = f"Property video analysis HTTP {response.status_code}: {detail[:1000]}"
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableAnalysisError(message)
        raise RuntimeError(message)
    body = response.json()
    text = body.get("output_text") or "\n".join(
        part.get("text", "") for part in body.get("outputs", [])
        if part.get("type") == "text"
    )
    if not text:
        for step in reversed(body.get("steps") or []):
            if step.get("type") == "user_input":
                break
            if step.get("type") == "model_output":
                text = "".join(part.get("text", "") for part in step.get("content", [])
                               if part.get("type") == "text")
                if text:
                    break
    if not text:
        raise RetryableAnalysisError("Property video analysis temporarily returned no final model text")
    return text


def analyze_property(video: dict, *, model: str | None = None) -> dict:
    prompt = f"""
Analyze this public property video using its audio, visible details and metadata.
Return one JSON object only. Never guess. Use "NOT SPECIFIED" for missing text fields.

Required keys:
is_property_listing (boolean), location, property_type, bhk, land_area,
built_up_area, price, facing, road_width, floors, bedrooms, bathrooms,
parking, approval, amenities (array), nearby_landmarks (array),
contact_details, missing_fields (array), source_facts (array),
layout_distribution, visual_style, exterior_description, neighbourhood_description,
entrance_contaminated (boolean).

Classification rules:
- property_type must describe one primary listing only. Never combine categories such as "House / Villa / Plot".
- Use "Residential Plot" or "Vacant Land" when land/sites are being sold, even when an optional house-construction package is advertised.
- Use "Independent House", "Villa" or "Apartment" only when that completed or under-construction dwelling itself is the listing.
- For a plot listing, never place house-construction package pricing in the price field. Use the confirmed plot price or "NOT SPECIFIED", and put the separate construction offer in source_facts.
- For plots, interiors, BHK and built-up area must be "NOT SPECIFIED" unless the listing is actually selling a dwelling.
- Determine HABITABLE floor count from the complete visual walkthrough and narration, not from a casual marketing label alone. Use precise values such as "single-storey", "G+1 duplex", or "G+2 residence".
- An open roof terrace, stair headroom, water-tank level or small terrace utility room is not a full residential floor. For example, ground-floor rooms + first-floor rooms + an open terrace utility must be classified as "G+1 duplex with open terrace utility", not G+2.
- layout_distribution must state the verified floor-by-floor room allocation, including which floor contains each bedroom/living area and whether the roof level is only open terrace/utility. Never compress rooms from multiple floors onto one floor and never promote a terrace utility to a residential storey.
- When narration and visible evidence conflict, describe the visually verified habitable layout in floors and layout_distribution and note the wording conflict in source_facts.
- entrance_contaminated must be true when any doorway, portico, doorframe, lintel, threshold, adjacent entrance wall or entrance floor contains personal, ceremonial or religious imagery or markings, or when the entrance is partly obscured and cannot be verified as visually clean. Otherwise use false.

Title: {video.get('title', '')}
Description: {video.get('description', '')}
Channel: {video.get('channel_title', '')}
Published: {video.get('published_at', '')}
"""
    try:
        print(f"Analyzing property video {video.get('video_id', '')} with {model or MODEL}", flush=True)
        result = _parse_json(_video_analysis(video, prompt, model or MODEL))
        if not isinstance(result.get("is_property_listing"), bool):
            raise ValueError("Property analysis did not return a verified listing classification")
        result["analysis_model"] = model or MODEL
        result["gemini_status"] = "success"
        result["gemini_error"] = ""
        result["transcript_status"] = "analyzed_from_video"
        return result
    except Exception as error:
        message = str(error)
        if _is_retryable_error(message):
            raise RetryableAnalysisError(message) from error
        raise
