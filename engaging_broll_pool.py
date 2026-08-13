import json
import shutil
from pathlib import Path

from strict_broll_pool import source_property_videos_strict


VIDEO_PATTERNS = ("*.mp4", "*.mov", "*.m4v", "*.webm")


def _ai_clips(video_id: str) -> list[dict]:
    root = Path("assets/ai_broll") / video_id
    if not root.exists():
        return []
    clips = []
    for scene_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        scene = scene_dir.name
        candidates = [path for pattern in VIDEO_PATTERNS for path in scene_dir.glob(pattern)]
        candidates = [path for path in candidates if path.stat().st_size >= 100_000]
        if not candidates:
            continue
        source = max(candidates, key=lambda path: path.stat().st_size)
        clips.append({
            "local_file": str(source),
            "provider": "HF ZeroGPU AI representative",
            "license": "AI-generated representative visual",
            "media_kind": "video",
            "actual_property": False,
            "representative_ai": True,
            "scene": scene,
            "source_priority": 0,
            "selection_layer": "ai-tamilnadu-representative",
            "title": f"AI-generated representative {scene} visual",
            "source_url": "",
        })
    return clips


def _copy_ai(video_id: str, clips: list[dict]) -> list[dict]:
    destination = Path("assets/videos") / video_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in clips:
        scene = str(item["scene"])
        target_dir = destination / scene
        target_dir.mkdir(parents=True, exist_ok=True)
        source = Path(item["local_file"])
        target = target_dir / f"ai-{scene}.mp4"
        shutil.copy2(source, target)
        saved.append({**item, "local_file": str(target)})
    return saved


def _write_attribution(video_id: str, rows: list[dict]) -> None:
    path = Path("data/media_attribution") / f"{video_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                prior = [item for item in existing if item.get("media_kind") != "video"]
        except (OSError, json.JSONDecodeError):
            prior = []
    path.write_text(json.dumps(prior + rows, ensure_ascii=False, indent=2), encoding="utf-8")


def source_engaging_broll(job: dict) -> list[dict]:
    """Use copyright-safe AI representative visuals first.

    The AI stage generates custom Coimbatore/Tamil Nadu-style visuals from listing
    facts without copying another seller's listing media. Pexels/Pixabay and the
    existing strict stock pool are retained only as an emergency fallback when
    the AI stage produced no usable clips at all.
    """
    video_id = str(job["video_id"])
    ai = _ai_clips(video_id)
    if ai:
        saved = _copy_ai(video_id, ai)
        _write_attribution(video_id, saved)
        print(
            f"Engaging B-roll {video_id}: using {len(saved)} AI-generated representative "
            "Tamil Nadu/Coimbatore-style scene clips; stock search skipped"
        )
        return saved
    print(f"Engaging B-roll {video_id}: AI visuals unavailable; using emergency licensed stock fallback")
    return source_property_videos_strict(job)
