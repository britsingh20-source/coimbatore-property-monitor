import json
import os
from google import genai

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


PROPERTY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_property_listing": {
            "type": "boolean"
        },
        "location": {
            "type": "string"
        },
        "property_type": {
            "type": "string"
        },
        "bhk": {
            "type": "string"
        },
        "land_area": {
            "type": "string"
        },
        "built_up_area": {
            "type": "string"
        },
        "price": {
            "type": "string"
        },
        "facing": {
            "type": "string"
        },
        "road_width": {
            "type": "string"
        },
        "floors": {
            "type": "string"
        },
        "bedrooms": {
            "type": "string"
        },
        "bathrooms": {
            "type": "string"
        },
        "parking": {
            "type": "string"
        },
        "approval": {
            "type": "string"
        },
        "amenities": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "nearby_landmarks": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "contact_details": {
            "type": "string"
        },
        "missing_fields": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "source_facts": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "is_property_listing",
        "location",
        "property_type",
        "bhk",
        "land_area",
        "built_up_area",
        "price",
        "facing",
        "road_width",
        "floors",
        "bedrooms",
        "bathrooms",
        "parking",
        "approval",
        "amenities",
        "nearby_landmarks",
        "contact_details",
        "missing_fields",
        "source_facts"
    ]
}


MAX_TRANSCRIPT_CHARS = 15000


def extract_property(video):

    transcript_status = video.get("transcript_status", "unavailable")
    transcript_text = video.get("transcript", "") or ""

    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        transcript_text = transcript_text[:MAX_TRANSCRIPT_CHARS] + " ...[truncated]"

    if transcript_status == "available" and transcript_text:
        transcript_block = transcript_text
    else:
        transcript_block = "(no transcript available for this video)"

    prompt = f"""
You are a real-estate data extraction system.

Analyze the following YouTube property listing metadata, and the video
transcript when one is available.

IMPORTANT RULES:

1. Extract ONLY information explicitly present.
2. NEVER guess missing property information.
3. If a field is unavailable, return "NOT SPECIFIED".
4. Preserve numbers exactly where possible.
5. Preserve units such as:
   - cents
   - sq.ft
   - lakhs
   - crores
   - feet
6. Distinguish land area from built-up area.
7. Distinguish asking price from other prices.
8. Identify the exact locality mentioned.
9. If multiple properties are discussed, identify that fact.
10. source_facts must contain the factual statements used for extraction.
11. The transcript may be unavailable for this video (transcript_status
    below will say so). In that case, base the analysis only on the
    title and description. Do not treat a missing transcript as missing
    property information by itself.
12. When both the transcript and the title/description are available,
    prefer the transcript for specific facts (numbers, prices, area)
    since it is spoken detail, but use the title/description for
    anything the transcript does not cover.

VIDEO TITLE:
{video["title"]}

VIDEO DESCRIPTION:
{video["description"]}

CHANNEL:
{video["channel_title"]}

PUBLISHED:
{video["published_at"]}

VIDEO URL:
{video["url"]}

TRANSCRIPT STATUS:
{transcript_status}

TRANSCRIPT:
{transcript_block}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": PROPERTY_SCHEMA
        }
    )

    return json.loads(response.text)
