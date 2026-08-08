import json
import shutil
from pathlib import Path

from free_broll_sources import (
    DEFAULT_PER_CATEGORY,
    SESSION_USED_SOURCES,
    _category_queries,
    _historical_sources,
    _quality_score,
    _source_identity,
    _stable_download_names,
    _stock_allowed,
    _take_fallback,
)
from media_sources import (
    add_to_library,
    download_media,
    get_library_clips,
    get_own_footage_clips,
    search_pexels_videos,
    search_pixabay_videos,
)


# These are not merely low-score terms. If provider metadata says a clip is one
# of these, it is never appropriate representative property B-roll.
HARD_REJECT_TERMS = {
    "flag", "national flag", "tricolor", "tricolour", "patriot", "patriotic",
    "food", "meal", "dish", "cooking", "cook", "chef", "recipe", "restaurant",
    "people", "person", "woman", "women", "man", "men", "couple", "family",
    "girl", "boy", "child", "children", "selfie", "portrait", "model",
    "highway", "freeway", "motorway", "flyover", "overpass", "expressway",
    "metro", "subway", "train", "railway", "traffic jam", "intersection",
    "downtown", "city centre", "city center", "skyline", "boulevard",
    "shopping mall", "mall", "office", "coworking", "warehouse", "factory",
    "hotel", "resort", "hostel", "hospital", "commercial building",
    "church", "temple", "mosque", "cathedral", "shrine",
    "mountain", "mountains", "snow", "tea estate", "tea plantation",
    "coffee plantation", "farm", "farmland", "agriculture",
}

# A returned search result must describe the requested property category in its
# own provider metadata/URL. The search query itself is intentionally not used
# as proof: searching "Indian house" does not make an Indian flag a house clip.
REQUIRED_SCENE_TERMS = {
    "location": {
        "residential", "neighbourhood", "neighborhood", "street", "houses",
        "house", "villa", "home", "residence", "housing",
    },
    "road": {
        "residential road", "residential street", "street", "road", "lane",
        "layout", "paved", "asphalt", "tar road", "neighbourhood", "neighborhood",
    },
    "land": {
        "plot", "plots", "residential land", "vacant land", "layout", "site",
        "property land", "housing plot",
    },
    "exterior": {
        "house", "villa", "home", "residence", "residential", "facade",
        "exterior", "independent house",
    },
    "living": {"living room", "living-room", "lounge", "home interior", "house interior"},
    "kitchen": {"kitchen", "modular kitchen", "home kitchen", "house kitchen"},
    "bedroom": {"bedroom", "bed room", "home bedroom", "house bedroom"},
}


SCENE_STRONG_BONUS = {
    "location": {"residential": 10, "neighbourhood": 9, "neighborhood": 9, "villa": 6, "house": 6},
    "road": {"residential road": 14, "residential street": 13, "layout": 7, "road": 6, "street": 6},
    "land": {"residential plot": 14, "plot": 10, "plots": 10, "layout": 8, "vacant land": 8},
    "exterior": {"independent house": 15, "villa": 11, "house": 9, "facade": 8, "exterior": 7},
    "living": {"living room": 16, "home interior": 8, "house interior": 8},
    "kitchen": {"modular kitchen": 18, "home kitchen": 11, "house kitchen": 11, "kitchen": 8},
    "bedroom": {"bedroom": 16, "home bedroom": 11, "house bedroom": 11},
}


def _metadata_text(item: dict) -> str:
    return " ".join(
        str(item.get(key, ""))
        for key in ("source_url", "title", "description", "alt", "tags")
    ).lower()


def _contains(text: str, term: str) -> bool:
    return term.lower() in text


def strict_candidate_allowed(item: dict, scene: str) -> bool:
    if not _stock_allowed(item, scene):
        return False
    text = _metadata_text(item)
    if any(_contains(text, term) for term in HARD_REJECT_TERMS):
        return False
    required = REQUIRED_SCENE_TERMS.get(scene, set())
    if required and not any(_contains(text, term) for term in required):
        return False
    return True


def strict_quality_score(item: dict, scene: str) -> int:
    score = _quality_score(item, scene)
    text = _metadata_text(item)
    for term, bonus in SCENE_STRONG_BONUS.get(scene, {}).items():
        if term in text:
            score += bonus

    # Prefer provider results that expose useful descriptive metadata; opaque
    # numeric-only URLs are less trustworthy for automatic property matching.
    descriptive_fields = sum(bool(str(item.get(key, "")).strip()) for key in ("title", "description", "alt", "tags"))
    score += descriptive_fields * 2
    return score


def combined_provider_candidates(scene: str, queries: list[str], wanted: int, used: set[str]) -> list[dict]:
    """Search Pexels and Pixabay together, then choose the best property clips.

    No provider gets to fill the quota before the other provider is searched.
    This keeps both services free-first while allowing a strong Pixabay result to
    beat a weak Pexels result (and vice versa).
    """
    if wanted <= 0:
        return []

    raw: list[dict] = []
    limit = max(12, wanted * 5)
    for query_index, query in enumerate(queries):
        for provider_name, search in (("Pexels", search_pexels_videos), ("Pixabay", search_pixabay_videos)):
            for item in search(query, limit=limit):
                raw.append({
                    **item,
                    "scene": scene,
                    "search_query": query,
                    "query_index": query_index,
                    "live_provider": provider_name,
                })

    historical = _historical_sources()
    deduped: dict[str, dict] = {}
    for item in raw:
        identity = _source_identity(item)
        if not identity or identity in used or identity in deduped:
            continue
        if not strict_candidate_allowed(item, scene):
            continue
        deduped[identity] = {
            **item,
            "quality_score": strict_quality_score(item, scene),
            "historical": identity in historical,
        }

    ranked = sorted(
        deduped.values(),
        key=lambda row: (
            bool(row.get("historical")),
            -int(row.get("quality_score", 0)),
            int(row.get("query_index", 99)),
            str(row.get("provider", "")),
        ),
    )
    return ranked[:wanted]


def source_property_videos_strict(job: dict, per_scene: int = DEFAULT_PER_CATEGORY) -> list[dict]:
    """Property-only free B-roll with R2 kept as the final retrieval fallback."""
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

        # 1. Search BOTH free providers, hard-filter to property semantics, then
        # rank the combined pool. Neither Pexels nor Pixabay can monopolize a
        # scene simply because it was queried first.
        live = combined_provider_candidates(scene, queries, per_scene, used)
        live_saved = _stable_download_names(
            download_media(live, destination / scene, limit=per_scene)
        )
        for item in live_saved:
            item.update({"actual_property": False, "scene": scene, "source_priority": 1})
        scene_items.extend(live_saved)
        used.update(_source_identity(item) for item in live_saved if _source_identity(item))

        # Cache approved live-provider footage for resilience. Reading cached
        # stock still happens only if BOTH live providers cannot fill the scene.
        cache_scene = scene if scene in {"location", "road", "land", "exterior", "interior"} else "interior"
        add_to_library(cache_scene, scene_items)

        # 2. Cached stock is a late fallback.
        missing = per_scene - len(scene_items)
        if missing > 0:
            library = _take_fallback(get_library_clips(cache_scene, missing * 4), scene, missing, used)
            library = [item for item in library if strict_candidate_allowed(item, scene)]
            for item in library:
                item.update({"scene": scene, "source_priority": 3})
            scene_items.extend(library[:missing])
            used.update(_source_identity(item) for item in library[:missing] if _source_identity(item))

        # 3. Advertiser-owned R2 footage remains the final retrieval option.
        # Own footage may lack stock metadata, so it is not subjected to the
        # provider-metadata semantic gate; it is already curated by the owner.
        missing = per_scene - len(scene_items)
        if missing > 0:
            own_scene = "interior" if scene in {"living", "kitchen", "bedroom"} else scene
            own = get_own_footage_clips(own_scene, property_type, missing * 4)
            chosen = []
            for item in own:
                identity = _source_identity(item)
                if not identity or identity in used:
                    continue
                chosen.append(item)
                if len(chosen) >= missing:
                    break
            for item in chosen:
                item.update({"scene": scene, "source_priority": 4})
            scene_items.extend(chosen)
            used.update(_source_identity(item) for item in chosen if _source_identity(item))

        print(
            f"Strict B-roll {video_id}/{scene}: {len(scene_items)} clips; "
            f"providers={[item.get('provider') for item in scene_items]}; "
            f"scores={[item.get('quality_score') for item in scene_items]}"
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
