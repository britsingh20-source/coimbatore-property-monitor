import json
import os
from pathlib import Path

from free_broll_sources import source_property_videos_free_first
from map_assets import render_map_sequence
from media_sources import source_property_media
from tamil_voiceover import create_voiceover
from video_pipeline import JOBS


def queued_ids() -> set[str]:
    path = Path(os.environ.get("VIDEO_IDS_FILE", "data/render_queue.txt"))
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def main() -> None:
    queue = queued_ids()
    if not queue:
        print("No queued IDs. Nothing prepared.")
        return
    failure_path = Path(os.environ.get("ASSET_FAILURES_FILE", "outputs/asset-failure-ids.txt"))
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    failure_path.write_text("", encoding="utf-8")
    failures = []
    for video_id in queue:
        try:
            job = json.loads((JOBS / f"{video_id}.json").read_text(encoding="utf-8"))
            media = source_property_media(job)
            clips = source_property_videos_free_first(job)
            maps = render_map_sequence(job)
            voice = create_voiceover(job)
            print(f"Prepared {video_id}: {len(media)} images, {len(clips)} clips, {len(maps)} maps, voice={voice}")
        except Exception as error:
            failures.append(f"{video_id}: {error}")
            with failure_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{video_id}\n")
    if failures:
        raise RuntimeError("\n".join(failures))


if __name__ == "__main__":
    main()
