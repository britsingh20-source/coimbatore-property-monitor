import json

from map_assets import render_map_sequence
from media_sources import source_property_media, source_property_videos
from tamil_voiceover import create_voiceover
from video_pipeline import JOBS, approved_ids


def main() -> None:
    approvals = approved_ids()
    if not approvals:
        print("No approved IDs. Nothing prepared.")
        return
    failures = []
    for video_id in approvals:
        try:
            job = json.loads((JOBS / f"{video_id}.json").read_text(encoding="utf-8"))
            media = source_property_media(job)
            clips = source_property_videos(job)
            maps = render_map_sequence(job)
            voice = create_voiceover(job)
            print(f"Prepared {video_id}: {len(media)} images, {len(clips)} clips, {len(maps)} maps, voice={voice}")
        except Exception as error:
            failures.append(f"{video_id}: {error}")
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
