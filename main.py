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


def load_existing_ids() -> set[str]:
    """Load video IDs that have already been processed."""

    if not os.path.exists(OUTPUT_FILE):
        return set()

    ids = set()

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            video_id = row.get("video_id", "").strip()

            if video_id:
                ids.add(video_id)

    return ids


def save_record(
    video: dict,
    property_data: dict
) -> None:
    """Append one processed video record to the CSV database."""

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    file_exists = os.path.exists(OUTPUT_FILE)

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

    # Convert lists into readable CSV values.
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
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDS,
            extrasaction="ignore"
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


def build_failed_property_result(
    error: Exception
) -> dict:
    """Return a safe record when Gemini property extraction fails."""

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
            "Gemini property analysis failed"
        ],
        "source_facts": [],
        "gemini_status": "failed_retry_later",
        "gemini_error": str(error)
    }


def run() -> None:
    """Run the complete property-monitor workflow."""

    existing_ids = load_existing_ids()
    recent_videos = monitor_channels()

    new_videos = [
        video
        for video in recent_videos
        if video.get("video_id") not in existing_ids
    ]

    print(
        f"Total recent videos checked: "
        f"{len(recent_videos)}"
    )

    print(
        f"New videos to process: "
        f"{len(new_videos)}"
    )

    if not new_videos:
        print("No new videos found.")
        return

    for index, video in enumerate(
        new_videos,
        start=1
    ):
        video_id = video.get("video_id", "")
        video_url = video.get("url", "")

        print("")
        print(
            f"Processing {index}/{len(new_videos)}"
        )
        print(
            f"NEW VIDEO: {video.get('title', 'UNTITLED')}"
        )

        # -----------------------------
        # TRANSCRIPT
        # -----------------------------

        try:
            # IMPORTANT:
            # Send the complete YouTube URL,
            # not only the video ID.
            transcript_result = get_transcript(
                video_url
            )

        except Exception as error:
            print(
                f"Transcript exception: {error}"
            )

            transcript_result = {
                "status": "error",
                "language": "",
                "text": "",
                "error": str(error)
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
            "Transcript: "
            f"{video['transcript_status']} "
            f"({video['transcript_language'] or '-'})"
        )

        transcript_error = transcript_result.get(
            "error",
            ""
        )

        if transcript_error:
            print(
                f"Transcript note: {transcript_error}"
            )

        # -----------------------------
        # PROPERTY EXTRACTION
        # -----------------------------

        try:
            property_data = extract_property(
                video
            )

        except Exception as error:
            print(
                f"Gemini property exception: {error}"
            )

            property_data = (
                build_failed_property_result(
                    error
                )
            )

        # -----------------------------
        # SAVE
        # -----------------------------

        try:
            save_record(
                video,
                property_data
            )

            existing_ids.add(video_id)

            print(
                f"Saved: "
                f"{video.get('title', 'UNTITLED')}"
            )

        except Exception as error:
            print(
                f"CSV save failed for "
                f"{video_id}: {error}"
            )

            # Continue with other videos.
            continue

    print("")
    print("Property-monitor run completed.")


if __name__ == "__main__":
    run()
