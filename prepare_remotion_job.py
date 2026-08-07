import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from broll_director import build_director_media
from map_assets import location_label


PUBLIC = Path("professional_video/public/render")
PROPS = Path("data/remotion_props")
DEFAULT_PHONE = "9003787621"
VIDEO_PATTERNS = ("*.mp4", "*.mov", "*.m4v", "*.webm")
DIALOGUE_GAP_SECONDS = 0.35
FPS = 30


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


def _normalize_scene_name(name: str) -> str:
    """Map R2/stock folder names to the semantic categories used by Remotion."""
    token = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    if any(word in token for word in ("road", "street", "access")):
        return "road"
    if any(word in token for word in ("bedroom", "bed room")):
        return "bedroom"
    if any(word in token for word in ("living", "hall")):
        return "living"
    if any(word in token for word in ("kitchen", "dining")):
        return "kitchen"
    if any(word in token for word in ("exterior", "facade", "front", "elevation", "outside")):
        return "exterior"
    if any(word in token for word in ("land", "plot", "site")):
        return "land"
    if "interior" in token:
        return "interior"
    return token.replace(" ", "_") or "other"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _scene_video_files(source_root: Path) -> dict[str, list[Path]]:
    """Collect scene-grouped clips from direct or nested folders."""
    grouped: dict[str, list[Path]] = {}
    if not source_root.exists():
        return grouped
    for folder in sorted(path for path in source_root.rglob("*") if path.is_dir()):
        files = [path for pattern in VIDEO_PATTERNS for path in folder.glob(pattern)]
        if files:
            scene = _normalize_scene_name(folder.name)
            grouped.setdefault(scene, []).extend(sorted(files))
    return grouped


def _copy_scene_videos(
    source_roots: list[tuple[Path, str]], destination: Path
) -> dict[str, list[str]]:
    """Copy R2 and stock clips into Remotion public assets, R2 first."""
    scene_media: dict[str, list[str]] = {}
    seen_sources: set[str] = set()
    for source_root, source_label in source_roots:
        for scene, files in _scene_video_files(source_root).items():
            copied = scene_media.setdefault(scene, [])
            for source in files:
                identity = str(source.resolve())
                if identity in seen_sources:
                    continue
                seen_sources.add(identity)
                index = len(copied) + 1
                safe_label = source_label.replace(" ", "-").lower()
                target = destination / (
                    f"{safe_label}-{scene}-{index:02d}{source.suffix.lower()}"
                )
                shutil.copy2(source, target)
                copied.append(f"render/{destination.name}/{target.name}")

    interior = _dedupe(
        scene_media.get("living", [])
        + scene_media.get("kitchen", [])
        + scene_media.get("bedroom", [])
        + scene_media.get("interior", [])
    )
    if interior:
        scene_media["interior"] = interior
    return {scene: _dedupe(clips) for scene, clips in scene_media.items() if clips}


def _value(prop: dict, key: str, fallback: str = "Verify during visit") -> str:
    value = str(prop.get(key, "")).strip()
    return value if value and value.upper() != "NOT SPECIFIED" else fallback


def _present(prop: dict, key: str) -> bool:
    return bool(_value(prop, key, ""))


def prepare(job_path: Path) -> Path:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    video_id = job["video_id"]
    destination = PUBLIC / video_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    property_folder = Path("assets/properties") / video_id
    stock_video_folder = Path("assets/videos") / video_id
    r2_own_footage_folder = Path("assets/own_footage_cache")
    map_folder = Path("assets/maps") / video_id
    image_files = [
        path
        for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp")
        for path in property_folder.glob(pattern)
    ]
    owned_clips = [
        path for pattern in VIDEO_PATTERNS for path in property_folder.glob(pattern)
    ]
    map_files = list(map_folder.glob("map-*.jpg"))

    images = _copy(image_files, destination, "property")
    actual_videos = _copy(owned_clips, destination, "actual")
    scene_media = _copy_scene_videos(
        [
            (r2_own_footage_folder, "r2-own"),
            (stock_video_folder, "stock"),
        ],
        destination,
    )
    representative_videos = _dedupe(
        [src for scene in sorted(scene_media) for src in scene_media[scene]]
    )
    director_media = build_director_media(job, scene_media, destination)
    r2_count = sum(
        1
        for clips in _scene_video_files(r2_own_footage_folder).values()
        for _ in clips
    )
    print(
        f"Prepared Remotion media for {video_id}: "
        f"R2 own B-roll={r2_count}, unique scene clips={len(representative_videos)}, "
        f"images={len(images)}, actual property clips={len(actual_videos)}, "
        f"categories={sorted(scene_media)}, directed scenes={sorted(director_media)}"
    )
    if r2_count and not any("r2-own-" in src for src in representative_videos):
        raise RuntimeError("R2 clips were downloaded but not exposed to Remotion")

    maps = _copy(map_files, destination, "map")
    audio_source = Path("assets/audio") / f"{video_id}.mp3"
    audio = None
    if audio_source.exists() and audio_source.stat().st_size > 0:
        target = destination / "narration.mp3"
        shutil.copy2(audio_source, target)
        try:
            audio = f"render/{video_id}/{target.name}"
        except (subprocess.CalledProcessError, ValueError):
            target.unlink(missing_ok=True)
            print(f"Ignoring invalid narration audio: {audio_source}")

    prop = job.get("property", {})
    property_type = _value(prop, "property_type", "property").lower()
    template_variant = (
        "plot"
        if any(word in property_type for word in ("plot", "land", "site"))
        else "home"
    )
    manifest_path = Path("assets/audio") / video_id / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else []
    )
    minimum_frames = {
        "location": 75,
        "land": 60,
        "builtUp": 60,
        "price": 60,
        "facing": 60,
        "road": 60,
        "approval": 60,
        "verify": 75,
        "cta": 90,
    }
    voice_segments = []
    scene_order = []
    scene_durations = {}
    gap_frames = max(1, int(round(DIALOGUE_GAP_SECONDS * FPS)))
    for item in manifest:
        source = Path("assets/audio") / video_id / item["file"]
        if not source.exists():
            continue
        target = destination / f"voice-{item['scene']}.mp3"
        shutil.copy2(source, target)
        scene = item["scene"]
        speech_frames = max(1, int(round(float(item["duration_seconds"]) * FPS)))
        trailing = 4 if scene == "cta" else gap_frames
        duration = max(speech_frames + trailing, minimum_frames.get(scene, 60))
        scene_order.append(scene)
        scene_durations[scene] = duration
        voice_segments.append(
            {
                "scene": scene,
                "src": f"render/{video_id}/{target.name}",
                "text": item.get("text", ""),
                "durationInFrames": speech_frames,
            }
        )
    if not scene_order:
        scene_order = [
            "location",
            "land",
            "builtUp",
            "price",
            "facing",
            "road",
            "approval",
            "verify",
            "cta",
        ]
        scene_durations = {scene: minimum_frames[scene] for scene in scene_order}
    duration_frames = sum(scene_durations[scene] for scene in scene_order)
    data = {
        "videoId": video_id,
        "location": job.get("property_location", "Coimbatore"),
        "locationLabel": location_label(job),
        "title": f"{_value(prop, 'bhk', '')} {_value(prop, 'property_type', 'Property')}".strip(),
        "price": _value(prop, "price", "Contact for price"),
        "facts": [
            {"label": "LAND", "value": _value(prop, "land_area")},
            {"label": "BUILT-UP", "value": _value(prop, "built_up_area")},
            {"label": "FACING", "value": _value(prop, "facing")},
            {"label": "ROAD", "value": _value(prop, "road_width")},
            {"label": "PARKING", "value": _value(prop, "parking")},
            {"label": "APPROVAL", "value": _value(prop, "approval")},
        ],
        "maps": maps,
        "actualVideos": actual_videos,
        "representativeVideos": representative_videos,
        "sceneMedia": scene_media,
        "directorMedia": director_media,
        "images": images,
        "audio": audio,
        "voiceSegments": voice_segments,
        "sceneOrder": scene_order,
        "sceneDurations": scene_durations,
        "templateVariant": template_variant,
        "styleVariant": job.get("style_variant"),
        "durationInFrames": duration_frames,
        "isActualProperty": bool(job.get("media_is_actual_property", False)),
        "disclosure": job.get(
            "disclosure", "Representative visuals; verify before purchase."
        ),
        "brand": "COIMBATOREVEEDU BUILDERS",
        "cta": "Schedule a verified site visit",
        "phone": str(job.get("contact_number") or DEFAULT_PHONE),
    }
    if data["isActualProperty"] and not (actual_videos or images):
        raise RuntimeError(
            "media_is_actual_property is true but no authorized property media exists"
        )
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
