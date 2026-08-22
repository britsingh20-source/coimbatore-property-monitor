import json
import os
import re

from google import genai


MODEL = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash")


class RetryableAnalysisError(RuntimeError):
    pass


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini response did not contain a JSON object")
    return json.loads(cleaned[start:end + 1])


def analyze_property(video: dict) -> dict:
    prompt = f"""
Analyze this public property video using its audio, visible details and metadata.
Return one JSON object only. Never guess. Use "NOT SPECIFIED" for missing text fields.

Required keys:
is_property_listing (boolean), location, property_type, bhk, land_area,
built_up_area, price, facing, road_width, floors, bedrooms, bathrooms,
parking, approval, amenities (array), nearby_landmarks (array),
contact_details, missing_fields (array), source_facts (array),
visual_style, exterior_description, neighbourhood_description,
visual_blueprint (object with keys: confidence, visible_floors, building_form,
roof_style, facade_colours, facade_materials, gate_style, compound_wall,
parking_layout, plot_shape, front_setback, road_surface, road_context,
neighbouring_buildings, vegetation, living_room, kitchen, bedrooms,
bathrooms, distinctive_features, prohibited_inferences).

For visual_blueprint, describe only characteristics actually visible in the video.
Do not copy a frame or request an identical recreation. Capture factual geometry,
materials, colours and local context so a new similar-but-distinct representative
property can be generated from different camera angles. BHK means bedroom count,
not floor count. If floors are not visibly clear, use "NOT SPECIFIED".

Title: {video.get('title', '')}
Description: {video.get('description', '')}
Channel: {video.get('channel_title', '')}
Published: {video.get('published_at', '')}
"""
    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        interaction = client.interactions.create(
            model=MODEL,
            input=[
                {"type": "video", "uri": video["url"]},
                {"type": "text", "text": prompt},
            ],
        )
        result = _parse_json(interaction.output_text)
        result["gemini_status"] = "success"
        result["gemini_error"] = ""
        result["transcript_status"] = "analyzed_from_video"
        return result
    except Exception as error:
        message = str(error)
        if any(token in message.lower() for token in ("429", "quota", "resource_exhausted", "timeout", "503")):
            raise RetryableAnalysisError(message) from error
        raise
