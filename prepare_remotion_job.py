import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path


PUBLIC = Path("professional_video/public/render")
PROPS = Path("data/remotion_props")


def _duration(path: Path) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def _copy(files: list[Path], destination: Path, prefix: str) -> list[str]:
    copied = []
    for index, source in enumerate(sorted(files), start=1):
        target = destination / f"{prefix}-{index:02d}{source.suffix.lower()}"
        shutil.copy2(source, target)
        copied.append(f"render/{destination.name}/{target.name}")
    return copied


def prepare(job_path: Path) -> Path:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    video_id = job["video_id"]
    destination = PUBLIC / video_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    property_folder = Path("assets/properties") / video_id
    stock_video_folder = Path("assets/videos") / video_id
    map_folder = Path("assets/maps") / video_id
    image_files = [path for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp") for path in property_folder.glob(pattern)]
    owned_clips = [path for pattern in ("*.mp4", "*.mov", "*.m4v", "*.webm") for path in property_folder.glob(pattern)]
    stock_clips = [path for pattern in ("*.mp4", "*.mov", "*.m4v", "*.webm") for path in stock_video_folder.glob(pattern)]
    map_files = list(map_folder.glob("map-*.jpg"))

    images = _copy(image_files, destination, "property")
    actual_videos = _copy(owned_clips, destination, "actual")
    representative_videos = _copy(stock_clips, destination, "stock")
    maps = _copy(map_files, destination, "map")
    audio_source = Path("assets/audio") / f"{video_id}.mp3"
    audio = None
    audio_seconds = 0.0
    if audio_source.exists() and audio_source.stat().st_size > 0:
        target = destination / "narration.mp3"
        shutil.copy2(audio_source, target)
        try:
            audio_seconds = _duration(target)
            audio = f"render/{video_id}/{target.name}"
        except (subprocess.CalledProcessError, ValueError):
            target.unlink(missing_ok=True)
            print(f"Ignoring invalid narration audio: {audio_source}")

    duration_seconds = max(48, min(75, math.ceil(audio_seconds + 2)))
    prop = job.get("property", {})
    data = {
        "videoId": video_id,
        "location": job.get("property_location", "Coimbatore"),
        "title": f"{prop.get('bhk', '')} {prop.get('property_type', 'Property')}".strip(),
        "price": prop.get("price", "Contact for price"),
        "facts": [
            {"label": "LAND", "value": prop.get("land_area", "Verify")},
            {"label": "BUILT-UP", "value": prop.get("built_up_area", "Verify")},
            {"label": "FACING", "value": prop.get("facing", "Verify")},
            {"label": "APPROVAL", "value": prop.get("approval", "Verify")},
        ],
        "maps": maps,
        "actualVideos": actual_videos,
        "representativeVideos": representative_videos,
        "images": images,
        "audio": audio,
        "durationInFrames": duration_seconds * 30,
        "isActualProperty": bool(actual_videos),
        "disclosure": job.get("disclosure", "Representative visuals; verify before purchase."),
        "brand": "SB BUILDERS",
        "cta": "Schedule a verified site visit",
    }
    if not images and not actual_videos and not representative_videos:
        raise RuntimeError(f"No property media prepared for {video_id}")
    PROPS.mkdir(parents=True, exist_ok=True)
    path = PROPS / f"{video_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    args = parser.parse_args()
    print(prepare(args.job))


if __name__ == "__main__":
    main()
