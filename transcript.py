import os
import time

from google import genai
from google.genai import errors, types


client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

TRANSCRIPT_MODEL = os.environ.get(
    "GEMINI_TRANSCRIPT_MODEL",
    "gemini-3.6-flash"
)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]


def get_transcript(video_url: str) -> dict:
    """
    Ask Gemini to transcribe the spoken content from a public
    YouTube video URL.

    Returns:
        {
            "status": "available" | "unavailable" | "error",
            "language": str,
            "text": str,
            "error": str
        }
    """

    if not video_url:
        return {
            "status": "unavailable",
            "language": "",
            "text": "",
            "error": "Video URL is missing"
        }

    prompt = """
Transcribe the spoken content of this YouTube video accurately.

Instructions:

1. Preserve Tamil speech in Tamil script.
2. Preserve English words and property terms as spoken.
3. Include every property specification mentioned, including:
   - location
   - price
   - BHK
   - land area
   - built-up area
   - cents
   - square feet
   - facing
   - road width
   - approval
   - parking
   - landmarks
   - phone number
4. Do not summarize.
5. Do not invent missing speech.
6. Ignore background music and unrelated sound.
7. Return only the transcript text.
"""

    last_error = None

    for attempt in range(MAX_RETRIES):

        try:
            print(
                f"Gemini transcript attempt "
                f"{attempt + 1}/{MAX_RETRIES}"
            )

            response = client.models.generate_content(
                model=TRANSCRIPT_MODEL,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(
                                file_data=types.FileData(
                                    file_uri=video_url
                                )
                            ),
                            types.Part(
                                text=prompt
                            )
                        ]
                    )
                ]
            )

            transcript_text = (
                response.text or ""
            ).strip()

            if not transcript_text:
                return {
                    "status": "unavailable",
                    "language": "",
                    "text": "",
                    "error": (
                        "Gemini returned an empty transcript"
                    )
                }

            language = detect_language_label(
                transcript_text
            )

            return {
                "status": "available",
                "language": language,
                "text": transcript_text,
                "error": ""
            }

        except errors.ServerError as error:
            last_error = error

            print(
                f"Gemini transcript server error: "
                f"{error}"
            )

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]

                print(
                    f"Waiting {delay} seconds "
                    "before transcript retry..."
                )

                time.sleep(delay)

        except Exception as error:
            last_error = error

            print(
                f"Gemini transcript error: {error}"
            )

            break

    return {
        "status": "error",
        "language": "",
        "text": "",
        "error": str(last_error)
    }


def detect_language_label(text: str) -> str:
    """
    Simple label for CSV visibility.
    This does not alter or translate the transcript.
    """

    tamil_count = sum(
        1
        for character in text
        if "\u0B80" <= character <= "\u0BFF"
    )

    latin_count = sum(
        1
        for character in text
        if character.isascii()
        and character.isalpha()
    )

    if tamil_count > 0 and latin_count > 0:
        return "ta-en"

    if tamil_count > 0:
        return "ta"

    if latin_count > 0:
        return "en"

    return "unknown"
