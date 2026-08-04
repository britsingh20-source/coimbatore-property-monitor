import csv
import os

from youtube_monitor import main as monitor_channels
from transcript import get_transcript
from property_extractor import extract_property


OUTPUT_FILE = "data/properties.csv"


FIELDS = [
    "source_name",
    "video_id",
    "video_title",
    "video_url",
    "published_at",

    "transcript_status",
    "transcript_language",

    "gemini_status",
    "gemini_error",

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


def load_existing_ids():

    if not os.path.exists(OUTPUT_FILE):
        return set()

    ids = set()

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            video_id = row.get("video_id")

            if video_id:
                ids.add(video_id)

    return ids


def save_record(video, property_data):

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    exists = os.path.exists(OUTPUT_FILE)

    row = {
        "source_name": video.get(
            "source_name",
            "NOT SPECIFIED"
        ),

        "video_id": video.get(
            "video_id",
            "NOT SPECIFIED"
        ),

        "video_title": video.get(
            "title",
            "NOT SPECIFIED"
        ),

        "video_url": video.get(
            "url",
            "NOT SPECIFIED"
        ),

        "published_at": video.get(
            "published_at",
            "NOT SPECIFIED"
        ),

        "transcript_status": video.get(
            "transcript_status",
            "unavailable"
        ),

        "transcript_language": video.get(
            "transcript_language",
            "NOT SPECIFIED"
        ),

        "gemini_status": property_data.get(
            "gemini_status",
            "unknown"
        ),

        "gemini_error": property_data.get(
            "gemini_error",
            ""
        ),

        "is_property_listing": property_data.get(
            "is_property_listing",
            False
        ),

        "location": property_data.get(
            "location",
            "NOT SPECIFIED"
        ),

        "property_type": property_data.get(
            "property_type",
            "NOT SPECIFIED"
        ),

        "bhk": property_data.get(
            "bhk",
            "NOT SPECIFIED"
        ),

        "land_area": property_data.get(
            "land_area",
            "NOT SPECIFIED"
        ),

        "built_up_area": property_data.get(
            "built_up_area",
            "NOT SPECIFIED"
        ),

        "price": property_data.get(
            "price",
            "NOT SPECIFIED"
        ),

        "facing": property_data.get(
            "facing",
            "NOT SPECIFIED"
        ),

        "road_width": property_data.get(
            "road_width",
            "NOT SPECIFIED"
        ),

        "floors": property_data.get(
            "floors",
            "NOT SPECIFIED"
        ),

        "bedrooms": property_data.get(
            "bedrooms",
            "NOT SPECIFIED"
        ),

        "bathrooms": property_data.get(
            "bathrooms",
            "NOT SPECIFIED"
        ),

        "parking": property_data.get(
            "parking",
            "NOT SPECIFIED"
        ),

        "approval": property_data.get(
            "approval",
            "NOT SPECIFIED"
        ),

        "amenities": property_data.get(
            "amenities",
            []
        ),

        "nearby_landmarks": property_data.get(
            "nearby_landmarks",
            []
        ),

        "contact_details": property_data.get(
            "contact_details",
            "NOT SPECIFIED"
        ),

        "missing_fields": property_data.get(
            "missing_fields",
            []
        ),

        "source_facts": property_data.get(
            "source_facts",
            []
        )
    }

    # Convert lists into CSV-friendly text.
    for key, value in row.items():

        if isinstance(value, list):
            row[key] = " | ".join(
                str(item)
                for item in value
            )

    with open(
        OUTPUT_FILE,
        "a",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            extrasaction="ignore"
        )

        if not exists:
            writer.writeheader()

        writer.writerow(row)


def run():

    existing_ids = load_existing_ids()

    videos = monitor_channels()

    for video in videos:

        video_id = video["video_id"]

        if video_id in existing_ids:

            print(
                f"Already processed: {video_id}"
            )

            continue

        print(
            f"NEW VIDEO: {video['title']}"
        )

        # -----------------------------
        # TRANSCRIPT
        # -----------------------------

        try:

            transcript_result = get_transcript(
                video_id
            )

        except Exception as e:

            print(
                f"Transcript exception: {e}"
            )

            transcript_result = {
                "status": "error",
                "language": "",
                "text": "",
                "error": str(e)
            }

        video["transcript_status"] = (
            transcript_result.get(
                "status",
                "unavailable"
            )
        )

        video["transcript_language"] = (
            transcript_result.get(
                "language",
                ""
            )
        )

        video["transcript"] = (
            transcript_result.get(
                "text",
                ""
            )
        )

        print(
            f"Transcript: "
            f"{video['transcript_status']} "
            f"({video['transcript_language'] or '-'})"
        )

        if transcript_result.get("error"):

            print(
                f"Transcript note: "
                f"{transcript_result['error']}"
            )

        # -----------------------------
        # GEMINI
        # -----------------------------

        try:

            property_data = extract_property(
                video
            )

        except Exception as e:

            print(
                f"Gemini exception: {e}"
            )

            property_data = {
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
                "gemini_error": str(e)
            }

        # -----------------------------
        # SAVE
        # -----------------------------

        save_record(
            video,
            property_data
        )

        existing_ids.add(video_id)

        print(
            f"Saved: {video['title']}"
        )


if __name__ == "__main__":
    run()
