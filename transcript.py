import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    YouTubeTranscriptApiException
)

# Preference order: Tamil first, then English.
PREFERRED_LANGUAGES = ["ta", "en"]


def _clean(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_transcript(video_id):
    """
    Attempt to obtain a transcript/caption track for a YouTube video.

    Preference order:
      1. Manually-created Tamil transcript
      2. Manually-created English transcript
      3. Auto-generated Tamil transcript
      4. Auto-generated English transcript
      5. Any other available transcript track (whatever language)

    This function never raises. Any failure (no captions, disabled
    captions, video unavailable, network error, unexpected library
    error, etc.) is caught and reported back as a status so the
    calling pipeline can log it and continue to the next video.

    Returns a dict:
        {
            "status": "available" | "unavailable" | "empty" | "error",
            "language": <language code, e.g. "ta"/"en", or "">,
            "is_generated": <bool>,
            "text": <transcript text, or "">,
            "error": <string description, "" if none>
        }
    """
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as exc:
        return {
            "status": "unavailable",
            "language": "",
            "is_generated": False,
            "text": "",
            "error": str(exc)
        }
    except (YouTubeTranscriptApiException, Exception) as exc:
        # Covers rate limiting, network issues, blocked requests, malformed
        # video IDs, or any other unexpected failure. The workflow must
        # keep going regardless.
        return {
            "status": "error",
            "language": "",
            "is_generated": False,
            "text": "",
            "error": str(exc)
        }

    tracks = list(transcript_list)

    if not tracks:
        return {
            "status": "unavailable",
            "language": "",
            "is_generated": False,
            "text": "",
            "error": "No transcript tracks found"
        }

    ordered = []

    # Manually-created tracks first: Tamil, then English.
    for lang in PREFERRED_LANGUAGES:
        ordered.extend(
            t for t in tracks
            if t.language_code == lang and not t.is_generated
        )

    # Auto-generated tracks next: Tamil, then English.
    for lang in PREFERRED_LANGUAGES:
        ordered.extend(
            t for t in tracks
            if t.language_code == lang and t.is_generated
        )

    # Fallback: any other track in whatever order the API returned.
    ordered.extend(t for t in tracks if t not in ordered)

    track = ordered[0]

    try:
        fetched = track.fetch()
    except Exception as exc:
        return {
            "status": "error",
            "language": track.language_code,
            "is_generated": track.is_generated,
            "text": "",
            "error": str(exc)
        }

    parts = []
    for item in fetched:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text", "")
        if text:
            parts.append(text)

    text = _clean(" ".join(parts))

    if not text:
        return {
            "status": "empty",
            "language": track.language_code,
            "is_generated": track.is_generated,
            "text": "",
            "error": "Transcript track returned no text"
        }

    return {
        "status": "available",
        "language": track.language_code,
        "is_generated": track.is_generated,
        "text": text,
        "error": ""
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = get_transcript(sys.argv[1])
        print(f"status: {result['status']}")
        print(f"language: {result['language'] or '-'}")
        print(f"is_generated: {result['is_generated']}")
        if result["error"]:
            print(f"note: {result['error']}")
        print(result["text"][:500])
    else:
        print("Usage: python transcript.py <video_id>")
