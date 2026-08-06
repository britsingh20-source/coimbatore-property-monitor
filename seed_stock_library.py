"""One-off/occasional helper: pre-seed assets/library/ from the same licensed free
sources (Pixabay, Wikimedia Commons, Pexels) the render pipeline already trusts,
using a handful of representative property jobs that together cover every scene
category (location, road, exterior, interior, land).

This doesn't touch any new source — it just calls the existing, already-filtered
source_property_media()/source_property_videos() functions from media_sources.py
directly, so every content/license/attribution rule already in place still applies.
Anything downloaded is automatically copied into assets/library/<category>/ by
those functions (see add_to_library()), which is the only thing this script's
caller should commit — NOT the per-video working folders under assets/properties/
or assets/videos/, which stay untracked scratch space.
"""

import json
from pathlib import Path

from media_sources import source_property_media, source_property_videos

# One house/villa-type job and one plot/land-type job is enough to cover all five
# scene categories (location, road, exterior, interior, land) between them.
SEED_JOB_IDS = [
    "4QM0yDap_Gw",  # Independent House / Duplex Villa -> location, road, exterior, interior
    "G8fsvbuFTZs",  # Plot -> location, road, land
]


def main() -> None:
    for video_id in SEED_JOB_IDS:
        job_path = Path("data/video_jobs") / f"{video_id}.json"
        job = json.loads(job_path.read_text(encoding="utf-8"))
        property_type = (job.get("property") or {}).get("property_type", "unknown")
        print(f"Seeding library from {video_id} ({property_type})")
        media = source_property_media(job)
        clips = source_property_videos(job)
        print(f"  -> {len(media)} images, {len(clips)} clips considered for the library")


if __name__ == "__main__":
    main()
