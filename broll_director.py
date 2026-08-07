import hashlib
import subprocess
from pathlib import Path
from typing import Any


FPS = 30
SHOT_SAFETY_FRAMES = 72
CATEGORY_ALIAS = {
    "living_room": "living",
    "living": "living",
    "kitchen": "kitchen",
    "bedroom": "bedroom",
    "interior": "interior",
    "exterior": "exterior",
    "road": "road",
    "land": "land",
}

DEFAULT_PREFERENCES = {
    "location": ["exterior", "road", "land"],
    "land": ["land", "exterior"],
    "builtUp": ["living", "kitchen", "bedroom", "interior"],
    "price": ["exterior", "living", "kitchen", "bedroom"],
    "facing": ["exterior", "land"],
    "road": ["road"],
    "approval": ["exterior", "living", "interior"],
    "verify": ["exterior", "living", "kitchen", "bedroom", "interior", "land"],
    "cta": ["exterior", "living", "kitchen", "bedroom"],
}

DEFAULT_AVOID = {
    "location": {"bedroom", "kitchen"},
    "land": {"living", "kitchen", "bedroom", "interior"},
    "builtUp": {"road", "land"},
    "price": {"road"},
    "facing": {"living", "kitchen", "bedroom", "interior"},
    "road": {"exterior", "land", "living", "kitchen", "bedroom", "interior"},
    "approval": {"road"},
    "verify": {"road"},
    "cta": {"road"},
}

SHOT_COUNTS = {
    "location": 4,
    "land": 2,
    "builtUp": 3,
    "price": 2,
    "facing": 2,
    "road": 3,
    "approval": 2,
    "verify": 3,
    "cta": 2,
}


def _duration_frames(path: Path) -> int:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return max(1, int(float(result.stdout.strip()) * FPS))
    except (OSError, ValueError, subprocess.CalledProcessError):
        return SHOT_SAFETY_FRAMES


def _content_scene_map(job: dict) -> dict[str, dict]:
    plan = job.get("content_plan") or {}
    result: dict[str, dict] = {}
    for item in plan.get("scenes") or []:
        if isinstance(item, dict) and item.get("name"):
            result[str(item["name"])] = item
    return result


def _scene_order(job: dict) -> list[str]:
    planned = [
        str(item.get("name"))
        for item in (job.get("content_plan") or {}).get("scenes", [])
        if isinstance(item, dict) and item.get("name")
    ]
    return planned or [
        "location", "land", "builtUp", "price", "facing", "road", "approval", "verify", "cta"
    ]


def _category_preferences(scene: str, plan_item: dict | None) -> tuple[list[str], set[str]]:
    requested = []
    avoided = set(DEFAULT_AVOID.get(scene, set()))
    if plan_item:
        for category in plan_item.get("broll") or []:
            normalized = CATEGORY_ALIAS.get(str(category))
            if normalized and normalized not in requested:
                requested.append(normalized)
        for category in plan_item.get("avoid_broll") or []:
            normalized = CATEGORY_ALIAS.get(str(category))
            if normalized:
                avoided.add(normalized)
    preferences = requested or list(DEFAULT_PREFERENCES.get(scene, ["exterior"]))
    preferences = [category for category in preferences if category not in avoided]
    return preferences, avoided


def _safe_start(video_id: str, scene: str, src: str, use_count: int, duration_frames: int) -> int:
    safe_max = max(0, duration_frames - SHOT_SAFETY_FRAMES)
    if safe_max <= 0:
        return 0
    digest = hashlib.sha1(f"{video_id}:{scene}:{src}".encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)
    base = seed % (safe_max + 1)
    # Reuse only after the library has been exhausted; when it happens, move to
    # a genuinely different part of the source instead of restarting at frame 0.
    shifted = (base + use_count * 75) % (safe_max + 1)
    return int(round(shifted / 15.0) * 15)


def build_director_media(job: dict, scene_media: dict[str, list[str]], destination: Path) -> dict[str, list[dict[str, Any]]]:
    """Build scene-specific B-roll using the content director and unique time windows.

    Selection rules:
    - obey the content director's preferred and avoided categories;
    - never use room footage for road/land/facing scenes;
    - prefer a source never used earlier in the reel;
    - keep a source out for at least three subsequent scenes (~12-15 seconds);
    - only after relevant unique footage is exhausted may a source be reused;
    - reused files start from a different safe timestamp.
    """
    video_id = str(job.get("video_id", "property"))
    plan_map = _content_scene_map(job)
    order = _scene_order(job)
    all_categories = {
        CATEGORY_ALIAS.get(category, category): list(items)
        for category, items in scene_media.items()
    }

    duration_cache: dict[str, int] = {}
    use_count: dict[str, int] = {}
    last_scene: dict[str, int] = {}
    result: dict[str, list[dict[str, Any]]] = {}

    def duration_for(src: str) -> int:
        if src not in duration_cache:
            duration_cache[src] = _duration_frames(destination / Path(src).name)
        return duration_cache[src]

    for scene_index, scene in enumerate(order):
        preferences, avoided = _category_preferences(scene, plan_map.get(scene))
        candidates: list[tuple[str, str, int]] = []
        seen_src: set[str] = set()
        for rank, category in enumerate(preferences):
            if category in avoided:
                continue
            for src in all_categories.get(category, []):
                if src in seen_src:
                    continue
                seen_src.add(src)
                candidates.append((src, category, rank))

        # Semantic fallback is deliberately conservative. A road scene never gets
        # an interior/exterior fallback; land/facing stay exterior/land only.
        if not candidates and scene not in {"road", "land", "facing", "builtUp"}:
            for category in DEFAULT_PREFERENCES.get(scene, ["exterior"]):
                if category in avoided:
                    continue
                for src in all_categories.get(category, []):
                    if src not in seen_src:
                        seen_src.add(src)
                        candidates.append((src, category, 99))

        def score(item: tuple[str, str, int]) -> tuple[int, int, int, str]:
            src, _category, rank = item
            previous = last_scene.get(src, -1000)
            age = scene_index - previous
            never_used = src not in use_count
            cooldown_ok = age >= 4
            freshness = 0 if never_used else (1 if cooldown_ok else 2)
            return (freshness, rank, use_count.get(src, 0), src)

        candidates.sort(key=score)
        target_count = SHOT_COUNTS.get(scene, 2)
        chosen: list[tuple[str, str, int]] = []
        chosen_src: set[str] = set()

        # Pass 1: unique or cooled-down clips only.
        for item in candidates:
            src = item[0]
            age = scene_index - last_scene.get(src, -1000)
            if src in chosen_src or (src in use_count and age < 4):
                continue
            chosen.append(item)
            chosen_src.add(src)
            if len(chosen) >= target_count:
                break

        # Pass 2: only when the semantic pool cannot satisfy the scene.
        if len(chosen) < target_count:
            for item in candidates:
                src = item[0]
                if src in chosen_src:
                    continue
                chosen.append(item)
                chosen_src.add(src)
                if len(chosen) >= target_count:
                    break

        shots: list[dict[str, Any]] = []
        for src, category, _rank in chosen:
            count = use_count.get(src, 0)
            start_from = _safe_start(video_id, scene, src, count, duration_for(src))
            shots.append({"src": src, "startFrom": start_from, "category": category})
            use_count[src] = count + 1
            last_scene[src] = scene_index
        if shots:
            result[scene] = shots

    return result
