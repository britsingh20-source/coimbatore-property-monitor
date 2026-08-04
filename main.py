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
            ids.add(row["video_id"])

    return ids


def save_record(video, property_data):

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    exists = os.path.exists(OUTPUT_FILE)

    row = {
        "source_name": video["source_name"],
        "video_id": video["video_id"],
        "video_title": video["title"],
        "video_url": video["url"],
        "published_at": video["published_at"],
        "transcript_status": video.get("transcript_status", "unavailable"),
        "transcript_language": video.get("transcript_language", ""),
        **property_data
    }

    with open(
        OUTPUT_FILE,
        "a",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS
        )

        if not exists:
            writer.writeheader()

        writer.writerow({
            key: (
                ", ".join(value)
                if isinstance(value, list)
                else value
            )
            for key, value in row.items()
        })


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

        transcript_result = get_transcript(video_id)

        video["transcript_status"] = transcript_result["status"]
        video["transcript_language"] = transcript_result["language"]
        video["transcript"] = transcript_result["text"]

        print(
            f"Transcript: {transcript_result['status']} "
            f"({transcript_result['language'] or '-'})"
        )

        if transcript_result["error"]:
            print(
                f"Transcript note: {transcript_result['error']}"
            )

        property_data = extract_property(video)

        save_record(
            video,
            property_data
        )

        print(
            f"Saved: {video['title']}"
        )


if __name__ == "__main__":
    run()
