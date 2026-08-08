import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from media_sources import (
    _allowed_scene_visual,
    add_to_library,
    download_media,
    get_library_clips,
    get_own_footage_clips,
    search_pexels_videos,
    search_pixabay_videos,
)
from visual_broll_validator import validate_downloaded_clips


SESSION_USED_SOURCES: set[str] = set()
DEFAULT_PER_CATEGORY = 4
LIVE_CANDIDATE_MULTIPLIER = 2


SCENE_QUERIES = {
    "location": [
        "Coimbatore Tamil Nadu residential neighbourhood road",
        "South India residential neighbourhood modern houses",
        "Indian residential street independent houses",
        "Tamil Nadu residential street houses",
    ],
    "road": [
        "Coimbatore Tamil Nadu residential road",
        "South India residential street asphalt road",
        "India residential layout tar road",
        "Indian villa layout road",
    ],
    "land": [
        "Tamil Nadu residential plot land aerial",
        "India residential plotted development vacant land",
        "residential plots layout India drone",
        "South India house plot layout",
    ],
    "exterior": [
        "Tamil Nadu modern independent house exterior",
        "South India independent villa exterior",
        "modern Indian house facade residential",
        "Indian independent house exterior",
    ],
    "living": [
        "modern Indian home living room walkthrough",
        "South India house living room interior",
        "Indian villa living room empty interior",
        "Tamil Nadu modern home living room",
    ],
    "kitchen": [
        "modern Indian modular kitchen empty walkthrough",
        "South India house modular kitchen interior",
        "Indian home kitchen interior no people",
        "Tamil Nadu modular kitchen home",
    ],
    "bedroom": [
        "modern Indian home bedroom empty interior",
        "South India house bedroom walkthrough",
        "Indian villa bedroom no people",
        "Tamil Nadu modern home bedroom",
    ],
}


GLOBAL_REJECT_TERMS = {
    "church", "temple", "mosque", "cathedral", "chapel", "shrine",
    "flag", "national flag", "patriotic", "political", "parliament", "rally",
    "mountain", "mountains", "alps", "snow", "ski", "forest",
    "tea plantation", "coffee plantation",
    "food", "meal", "cooking", "cook", "chef", "restaurant", "recipe", "jar", "spice",
    "woman", "women", "man", "men", "person", "people", "couple",
    "family", "girl", "boy", "child", "children", "model", "selfie",
    "holding", "dancing", "fitness", "camera", "photographer",
    "office", "coworking", "hotel", "resort", "hospital",
    "shopping", "store", "mall", "bar", "cafe", "warehouse", "factory",
    "tourism", "tourist", "beach", "festival",
}

SCENE_REJECT_TERMS = {
    "location": {"highway", "freeway", "flyover", "overpass", "metro", "downtown", "city skyline", "traffic", "europe", "american", "usa"},
    "road": {"highway", "freeway", "motorway", "flyover", "overpass", "metro", "race", "traffic jam", "arterial", "europe", "american", "usa"},
    "land": {"farm", "farmland", "agriculture", "rice field", "paddy field", "desert"},
    "exterior": {"castle", "palace", "mansion", "apartment", "condo", "skyscraper", "europe", "american", "usa"},
    "living": {"conference", "lobby", "reception", "apartment tour"},
    "kitchen": {"commercial kitchen", "restaurant kitchen", "industrial kitchen"},
    "bedroom": {"dormitory", "hostel", "hotel room", "resort room"},
}

# A free-provider result must describe the requested property category in its
# own provider metadata/URL. The search query itself is deliberately excluded.
SCENE_REQUIRED_TERMS = {
    "location": {"residential", "neighbourhood", "neighborhood", "street", "houses", "house", "villa", "home"},
    "road": {"residential", "road", "street", "asphalt", "paved", "layout", "villa"},
    "land": {"plot", "plots", "land", "layout", "vacant", "site", "residential"},
    "exterior": {"house", "villa", "home", "residential", "exterior", "facade", "independent"},
    "living": {"living", "living room", "interior", "home", "house"},
    "kitchen": {"kitchen", "modular kitchen", "interior", "home", "house"},
    "bedroom": {"bedroom", "bed room", "interior", "home", "house"},
}

REGIONAL_TERMS = {
    "coimbatore": 14,
    "tamil nadu": 12,
    "tamilnadu": 12,
    "south india": 10,
    "south indian": 10,
    "india": 7,
    "indian": 7,
}

SCENE_PREFER_TERMS = {
    "location": {"residential": 8, "neighbourhood": 8, "neighborhood": 8, "street": 5, "houses": 5, "villa": 4},
    "road": {"residential": 8, "road": 8, "street": 7, "asphalt": 5, "tar": 5, "layout": 5, "paved": 4},
    "land": {"residential": 7, "plot": 9, "plots": 9, "land": 7, "layout": 6, "vacant": 4, "site": 4},
    "exterior": {"independent": 9, "house": 8, "villa": 8, "exterior": 7, "facade": 7, "residential": 5, "home": 4},
    "living": {"living room": 10, "living": 7, "home": 5, "house": 5, "interior": 4, "empty": 4},
    "kitchen": {"modular kitchen": 12, "kitchen": 9, "home": 5, "house": 5, "interior": 4, "empty": 4},
    "bedroom": {"bedroom": 10, "home": 5, "house": 5, "interior": 4, "empty": 4},
}

SOFT_PENALTY_TERMS = {
    "luxury": 2,
    "penthouse": 8,
    "apartment": 7,
    "condo": 9,
    "loft": 6,
    "studio": 5,
    "western": 8,
    "european": 10,
    "american": 12,
    "new york": 12,
    "london": 12,
}


def _source_identity(item: dict) -> str:
    return str(item.get("source_url") or item.get("download_url") or item.get("local_file") or "").strip()


def _metadata_text(item: dict) -> str:
    return " ".join(
        str(item.get(key, ""))
        for key in ("source_url", "title", "description", "alt", "tags")
    ).lower()


def _historical_sources() -> set[str]:
    result: set[str] = set()
    directory = Path("data/media_attribution")
    if not directory.exists():
        return result
    for path in directory.glob("*.json"):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rows, list):
            continue
        for item in rows:
            if isinstance(item, dict):
                identity = _source_identity(item)
                if identity:
                    result.add(identity)
    return result


def _contains_term(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _stock_allowed(item: dict, scene: str) -> bool:
    mapped_scene = scene if scene in {"location", "road", "land", "exterior", "interior"} else "interior"
    if not _allowed_scene_visual(item, mapped_scene):
        return False
    searchable = _metadata_text(item)
    if any(_contains_term(searchable, term) for term in GLOBAL_REJECT_TERMS):
        return False
    if any(_contains_term(searchable, term) for term in SCENE_REJECT_TERMS.get(scene, set())):
        return False
    required = SCENE_REQUIRED_TERMS.get(scene, set())
    return not required or any(_contains_term(searchable, term) for term in required)


def _quality_score(item: dict, scene: str) -> int:
    text = _metadata_text(item)
    score = 0

    for term, value in REGIONAL_TERMS.items():
        if term in text:
            score += value
    for term, value in SCENE_PREFER_TERMS.get(scene, {}).items():
        if term in text:
            score += value
    for term, value in SOFT_PENALTY_TERMS.items():
        if term in text:
            score -= value

    width = item.get("width") or item.get("video_width") or 0
    height = item.get("height") or item.get("video_height") or 0
    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        width = height = 0
    if width and height:
        if height > width:
            score += 6
        elif height == width:
            score += 1
        else:
            score -= 2
        if min(width, height) >= 720:
            score += 2

    duration = item.get("duration_seconds")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = None
    if duration is not None:
        if 4 <= duration <= 20:
            score += 4
        elif duration < 2:
            score -= 5
        elif duration > 45:
            score -= 2

    query_index = item.get("query_index")
    if isinstance(query_index, int):
        score += max(0, 4 - query_index)
    return score


def _category_queries(job: dict) -> dict[str, list[str]]:
    prop = job.get("property") or {}
    property_type = str(prop.get("property_type") or "property").lower()
    location = str(job.get("property_location") or "Coimbatore").split(",")[0].strip()

    if any(word in property_type for word in ("plot", "land", "site")):
        categories = ("location", "road", "land", "exterior")
    else:
        categories = ("location", "road", "exterior", "living", "kitchen", "bedroom")

    result: dict[str, list[str]] = {}
    for category in categories:
        base = list(SCENE_QUERIES[category])
        if category in {"location", "road", "exterior"} and location:
            prefix = {
                "location": f"{location} Coimbatore Tamil Nadu residential neighbourhood",
                "road": f"{location} Coimbatore Tamil Nadu residential road",
                "exterior": f"{location} Coimbatore Tamil Nadu independent house exterior",
            }[category]
            if not base or base[0] != prefix:
                base.insert(0, prefix)
        result[category] = base
    return result


def _unique_candidates(items: list[dict], scene: str, used: set[str]) -> list[dict]:
    historical = _historical_sources()
    fresh: list[dict] = []
    old: list[dict] = []
    local_seen: set[str] = set()
    for item in items:
        identity = _source_identity(item)
        if not identity or identity in used or identity in local_seen:
            continue
        local_seen.add(identity)
        if not _stock_allowed(item, scene):
            continue
        scored = {**item, "quality_score": _quality_score(item, scene)}
        if identity in historical:
            old.append(scored)
        else:
            fresh.append(scored)
    fresh.sort(key=lambda row: (-int(row.get("quality_score", 0)), int(row.get("query_index", 99))))
    old.sort(key=lambda row: (-int(row.get("quality_score", 0)), int(row.get("query_index", 99))))
    return fresh + old


def _search_provider(scene: str, queries: list[str], provider: str, used: set[str], pool_limit: int) -> list[dict]:
    search = search_pexels_videos if provider == "pexels" else search_pixabay_videos
    raw: list[dict] = []
    for query_index, query in enumerate(queries):
        results = search(query, limit=max(10, pool_limit * 2))
        raw.extend(
            {
                **item,
                "scene": scene,
                "search_query": query,
                "query_index": query_index,
                "live_provider": provider,
            }
            for item in results
        )
    return _unique_candidates(raw, scene, used)


def _combined_live_candidates(scene: str, queries: list[str], used: set[str], pool_limit: int) -> list[dict]:
    # Both free providers are searched before selection. Provider identity is not
    # a ranking advantage: the best property-relevant clip wins.
    combined = [
        *_search_provider(scene, queries, "pexels", used, pool_limit),
        *_search_provider(scene, queries, "pixabay", used, pool_limit),
    ]
    ranked = _unique_candidates(combined, scene, used)
    return ranked[:pool_limit]


def _stable_download_names(items: list[dict]) -> list[dict]:
    output = []
    for item in items:
        path = Path(item.get("local_file", ""))
        if not path.exists() or not path.name:
            output.append(item)
            continue
        identity = _source_identity(item) or str(path)
        digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12]
        provider = str(item.get("provider") or "stock").lower().replace(" ", "-")
        target = path.with_name(f"{provider}-{digest}{path.suffix.lower()}")
        if target != path:
            if target.exists():
                path.unlink(missing_ok=True)
            else:
                path.rename(target)
        output.append({**item, "local_file": str(target)})
    return output


def _visually_select(scene: str, items: list[dict], wanted: int) -> tuple[list[dict], list[dict]]:
    validated = validate_downloaded_clips(scene, items)
    visual_enabled = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    if visual_enabled:
        accepted = [item for item in validated if item.get("visual_accepted") is True]
        rejected = [item for item in validated if item.get("visual_accepted") is not True]
    else:
        # Backward-compatible mode for local/test environments without Gemini.
        accepted = validated
        rejected = []
    accepted.sort(
        key=lambda row: (
            -int(row.get("visual_score", 0) or 0),
            -int(row.get("quality_score", 0) or 0),
        )
    )
    chosen = accepted[:wanted]
    overflow = accepted[wanted:]
    rejected.extend(overflow)
    return chosen, rejected


def _remove_rejected_files(items: list[dict]) -> None:
    for item in items:
        path = Path(str(item.get("local_file", "")))
        try:
            if path.exists() and "assets/videos" in path.as_posix():
                path.unlink()
        except OSError:
            pass


def _take_fallback(items: list[dict], scene: str, wanted: int, used: set[str]) -> list[dict]:
    eligible = []
    for item in items:
        identity = _source_identity(item)
        if not identity or identity in used:
            continue
        if not _stock_allowed(item, scene):
            continue
        eligible.append({**item, "quality_score": _quality_score(item, scene)})
    eligible.sort(key=lambda row: -int(row.get("quality_score", 0)))
    return eligible[: max(wanted * 2, wanted)]


def source_property_videos_free_first(job: dict, per_scene: int = DEFAULT_PER_CATEGORY) -> list[dict]:
    """Source free B-roll with actual-frame QA and R2 only as fallback.

    Order:
      1. Search Pexels + Pixabay together.
      2. Metadata hard-filter and rank a candidate pool.
      3. Download candidates and inspect real frames with Gemini Vision.
      4. Keep only visually approved residential scene matches.
      5. Use visually checked cached stock only if live providers are short.
      6. Use advertiser-owned R2 B-roll last.

    Actual property files bundled with a job remain first because they are the
    truthful listing media rather than representative stock.
    """
    video_id = str(job["video_id"])
    owned_folder = Path("assets/properties") / video_id
    actual = []
    for pattern in ("*.mp4", "*.mov", "*.webm", "*.m4v"):
        actual.extend(owned_folder.glob(pattern))
    if actual:
        return [{
            "local_file": str(path),
            "provider": "Advertiser supplied",
            "license": "Owner supplied",
            "media_kind": "video",
            "actual_property": True,
            "scene": "actual",
        } for path in sorted(actual)]

    destination = Path("assets/videos") / video_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    property_type = str((job.get("property") or {}).get("property_type") or "property")
    used = set(SESSION_USED_SOURCES)
    saved: list[dict] = []

    for scene, queries in _category_queries(job).items():
        scene_items: list[dict] = []
        pool_limit = max(per_scene * LIVE_CANDIDATE_MULTIPLIER, 8)

        # Search Pexels and Pixabay before choosing anything. This fixes the old
        # behaviour where four mediocre Pexels clips could prevent a much better
        # Pixabay match from ever being considered.
        live_candidates = _combined_live_candidates(scene, queries, used, pool_limit)
        live_downloaded = _stable_download_names(
            download_media(live_candidates, destination / scene, limit=pool_limit)
        )
        live_selected, live_rejected = _visually_select(scene, live_downloaded, per_scene)
        _remove_rejected_files(live_rejected)
        for item in live_selected:
            item.update({
                "actual_property": False,
                "scene": scene,
                "source_priority": 1,
                "selection_layer": "live-free-provider-visual-qa",
            })
        scene_items.extend(live_selected)
        used.update(_source_identity(item) for item in live_selected if _source_identity(item))

        # Cache ONLY visually accepted provider footage. Rejected clips never
        # contaminate the persistent library.
        library_scene = scene if scene in {"location", "road", "land", "exterior"} else "interior"
        add_to_library(library_scene, live_selected)

        # Cached stock is still before owner R2, but it also passes the same frame
        # inspection so bad clips cached by older runs are not resurrected.
        missing = per_scene - len(scene_items)
        if missing > 0:
            library_candidates = _take_fallback(
                get_library_clips(library_scene, max(missing * 4, 8)),
                scene,
                missing,
                used,
            )
            library_selected, _library_rejected = _visually_select(scene, library_candidates, missing)
            for item in library_selected:
                item.update({
                    "scene": scene,
                    "source_priority": 2,
                    "selection_layer": "cached-stock-visual-qa",
                })
            scene_items.extend(library_selected)
            used.update(_source_identity(item) for item in library_selected if _source_identity(item))

        # Advertiser-owned R2 remains the final retrieval fallback. It is trusted
        # owner-supplied footage and does not consume Gemini validation calls.
        missing = per_scene - len(scene_items)
        if missing > 0:
            own_scene = "interior" if scene in {"living", "kitchen", "bedroom"} else scene
            own = _take_fallback(
                get_own_footage_clips(own_scene, property_type, max(missing * 3, 6)),
                scene,
                missing,
                used,
            )[:missing]
            for item in own:
                item.update({
                    "scene": scene,
                    "source_priority": 3,
                    "selection_layer": "owner-r2-last-fallback",
                })
            scene_items.extend(own)
            used.update(_source_identity(item) for item in own if _source_identity(item))

        print(
            f"B-roll {video_id}/{scene}: {len(scene_items)} clips; "
            f"providers={[item.get('provider') for item in scene_items]}; "
            f"metadata_scores={[item.get('quality_score') for item in scene_items]}; "
            f"visual_scores={[item.get('visual_score') for item in scene_items]}"
        )
        saved.extend(scene_items)

    SESSION_USED_SOURCES.update(used)

    attribution_path = Path("data/media_attribution") / f"{video_id}.json"
    attribution_path.parent.mkdir(parents=True, exist_ok=True)
    prior = []
    if attribution_path.exists():
        try:
            prior = [
                item for item in json.loads(attribution_path.read_text(encoding="utf-8"))
                if item.get("media_kind") != "video"
            ]
        except (OSError, json.JSONDecodeError):
            prior = []
    attribution_path.write_text(
        json.dumps(prior + saved, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return saved
