import json
import os
import time

from google import genai
from google.genai import errors


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

MAX_RETRIES = 4

RETRY_DELAYS = [
    5,
    15,
    30,
    60
]


def extract_property(video):

    transcript_status = video.get(
        "transcript_status",
        "unavailable"
    )

    transcript_text = video.get(
        "transcript",
        ""
    ) or ""

    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        transcript_text = (
            transcript_text[:MAX_TRANSCRIPT_CHARS]
            + " ...[truncated]"
        )

    if transcript_status == "available" and transcript_text:
        transcript_block = transcript_text
    else:
        transcript_block = (
            "(no transcript available for this video)"
        )

    prompt = f"""
You are a real-estate data extraction system.

Analyze the following YouTube property listing metadata,
and the video transcript when one is available.

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
10. source_facts must contain the factual statements used
    for extraction.
11. If transcript is unavailable, use only title and description.
12. Never invent information.

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

    last_error = None

    for attempt in range(MAX_RETRIES):

        try:

            print(
                f"Gemini attempt "
                f"{attempt + 1}/{MAX_RETRIES}: "
                f"{video['title']}"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": PROPERTY_SCHEMA
                }
            )

            if not response.text:
                raise RuntimeError(
                    "Gemini returned an empty response"
                )

            result = json.loads(response.text)

            result["gemini_status"] = "success"

            return result

        except errors.ServerError as e:

            last_error = e

            print(
                f"Gemini server error "
                f"(attempt {attempt + 1}): {e}"
            )

            if attempt < MAX_RETRIES - 1:

                delay = RETRY_DELAYS[attempt]

                print(
                    f"Waiting {delay} seconds "
                    f"before retry..."
                )

                time.sleep(delay)

        except Exception as e:

            last_error = e

            print(
                f"Gemini error "
                f"(attempt {attempt + 1}): {e}"
            )

            break

    print(
        f"Gemini failed after {MAX_RETRIES} attempts "
        f"for video: {video['title']}"
    )

    return {
        "is_property_listing": False,
        "location": "NOT SPECIFIED",
        "property_type": "NOT SPECIFIED",
        "bhk": "NOT SPECIFIED",
        "land_area": "NOT SPECIFIED",
        "built_up_area": "NOT SPECIFIED",
        "price": "NOT SPECIFIED",
        "facing": "NOT SPECIFIED",
        "road_width": "NOT SPECIFIED",
        "floors": "NOT SPECIFIED",
        "bedrooms": "NOT SPECIFIED",
        "bathrooms": "NOT SPECIFIED",
        "parking": "NOT SPECIFIED",
        "approval": "NOT SPECIFIED",
        "amenities": [],
        "nearby_landmarks": [],
        "contact_details": "NOT SPECIFIED",
        "missing_fields": [
            "Gemini analysis failed"
        ],
        "source_facts": [],
        "gemini_status": "failed_retry_later",
        "gemini_error": str(last_error)
    }
