import hashlib
import json
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


# This process-level set prevents the same stock URL being selected for two
# different properties during one GitHub Actions run.
SESSION_USED_SOURCES: set[str] = set()

# We deliberately ask for more footage than the renderer strictly needs. The
# semantic/subclip director can then choose unique shots instead of recycling
# two files throughout an entire reel.
DEFAULT_PER_CATEGORY = 4


SCENE_QUERIES = {
    "location": [
        "South India residential neighbourhood vertical video",
        "Indian residential street modern houses vertical",
        "Coimbatore residential neighbourhood road",
    ],
    "road": [
        "India residential asphalt road vertical",
        "South India residential street road",
        "Indian villa layout road vertical",
    ],
    "land": [
        "India residential plot land aerial",
        "Indian plotted development vacant land",
        "residential plots layout India drone",
    ],
    "exterior": [
        "modern Indian villa exterior vertical",
        "South India independent house exterior",
        "modern Indian house facade residential",
    ],
    "living": [
        "modern Indian living room vertical walkthrough",
        "Indian villa living room interior",
        "South India modern home living room",
    ],
    "kitchen": [
        "modern Indian modular kitchen vertical",
        "Indian house kitchen interior walkthrough",
        "South India modular kitchen home",
    ],
    "bedroom": [
        "modern Indian bedroom vertical interior",
        "Indian villa bedroom walkthrough",
        "South India modern home bedroom",
    ],
}


SCENE_REJECT_TERMS = {
    "location": {"mountain", "mountains", "alps", "snow", "forest", "tea", "plantation", "europe", "american"},
    "road": {"mountain", "mountains", "forest", "tea", "plantation", "highway", "freeway", "europe"},
    "land": {"mountain", "mountains", "forest", "tea", "plantation", "farm", "farmland"},
    "exterior": {"castle", "mansion", "europe", "american", "snow", "mountain"},
    "living": {"office", "hotel", "restaurant", "church", "temple", "mosque"},
    "kitchen": {"restaurant", "commercial", "hotel", "office"},
    "bedroom": {"hotel", "resort", "hospital", "hostel"},
}


def _source_identity(item: dict) -> str:
    return str(item.get("source_url") or item.get("download_url") or item.get("local_file") or "").strip()


def _historical_sources() -> set[str]:
    """Use committed attribution records as a soft global no-repeat memory."""
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


def _stock_allowed(item: dict, scene: str) -> bool:
    if not _allowed_scene_visual(item, scene if scene in {"location", "road", "land", "exterior", "interior"} else "interior"):
        return False
    searchable = " ".join(
        str(item.get(key, ""))
        for key in ("source_url", "title", "description", "alt", "search_query")
    ).lower()
    return not any(term in searchable for term in SCENE_REJECT_TERMS.get(scene, set()))


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
            # Exact locality search goes first. Providers may not have that exact
            # place, so broader South-India/India searches remain behind it.
            prefix = {
                "location": f"{location} Coimbatore residential neighbourhood",
                "road": f"{location} Coimbatore residential road",
                "exterior": f"{location} Coimbatore modern house exterior",
            }[category]
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
        if identity in historical:
            old.append(item)
        else:
            fresh.append(item)
    # Previously used stock is only considered after genuinely fresh provider
    # results have been exhausted.
    return fresh + old


def _provider_candidates(job: dict, scene: str, queries: list[str], provider: str, wanted: int, used: set[str]) -> list[dict]:
    if wanted <= 0:
        return []
    collected: list[dict] = []
    search = search_pexels_videos if provider == "pexels" else search_pixabay_videos
    for query in queries:
        # Search a larger pool than we consume so the no-repeat/blocked filters
        # have room to reject weak results.
        results = search(query, limit=max(8, wanted * 3))
        annotated = [{**item, "scene": scene, "search_query": query} for item in results]
        for item in _unique_candidates(annotated, scene, used | {_source_identity(x) for x in collected}):
            collected.append(item)
            if len(collected) >= wanted:
                return collected
    return collected


def _stable_download_names(items: list[dict]) -> list[dict]:
    """Rename generic 01-pexels.mp4 files before R2 caching to avoid collisions."""
    output = []
    for item in items:
        path = Path(item.get("local_file", ""))
        if not path.exists():
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


def _take_fallback(items: list[dict], scene: str, wanted: int, used: set[str]) -> list[dict]:
    chosen = []
    for item in items:
        identity = _source_identity(item)
        if not identity or identity in used:
            continue
        if not _stock_allowed(item, scene):
            continue
        chosen.append(item)
        if len(chosen) >= wanted:
            break
    return chosen


def source_property_videos_free_first(job: dict, per_scene: int = DEFAULT_PER_CATEGORY) -> list[dict]:
    """Source diverse B-roll with R2 as the last retrieval option.

    Priority for each semantic category:
      1. Pexels fresh portrait video
      2. Pixabay fresh video
      3. persistent stock library from R2/local cache
      4. advertiser-owned R2 B-roll as final fallback

    Actual property video files already bundled under assets/properties/<id>/ are
    still used directly because they are not an R2 fallback and are the most
    truthful representation of that listing.
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

        # 1. Pexels first: portrait results are especially useful for 9:16 reels.
        pexels = _provider_candidates(job, scene, queries, "pexels", per_scene, used)
        pexels_saved = _stable_download_names(
            download_media(pexels, destination / scene, limit=per_scene)
        )
        for item in pexels_saved:
            item.update({"actual_property": False, "scene": scene, "source_priority": 1})
        scene_items.extend(pexels_saved)
        used.update(_source_identity(item) for item in pexels_saved if _source_identity(item))

        # 2. Pixabay fills only what Pexels could not supply.
        missing = per_scene - len(scene_items)
        if missing > 0:
            pixabay = _provider_candidates(job, scene, queries, "pixabay", missing, used)
            pixabay_saved = _stable_download_names(
                download_media(pixabay, destination / scene, limit=missing)
            )
            for item in pixabay_saved:
                item.update({"actual_property": False, "scene": scene, "source_priority": 2})
            scene_items.extend(pixabay_saved)
            used.update(_source_identity(item) for item in pixabay_saved if _source_identity(item))

        # Cache successful free-provider results for resilience, but do NOT read
        # that cache until both live free providers have failed to fill the pool.
        add_to_library(scene if scene in {"location", "road", "land", "exterior", "interior"} else "interior", scene_items)

        # 3. R2/local stock cache is a late fallback, not the normal first source.
        missing = per_scene - len(scene_items)
        if missing > 0:
            library_scene = scene if scene in {"location", "road", "land", "exterior"} else "interior"
            library = _take_fallback(get_library_clips(library_scene, missing * 2), scene, missing, used)
            for item in library:
                item.update({"scene": scene, "source_priority": 3})
            scene_items.extend(library)
            used.update(_source_identity(item) for item in library if _source_identity(item))

        # 4. Advertiser-owned R2 clips are deliberately the final retrieval
        # option, per current pipeline policy.
        missing = per_scene - len(scene_items)
        if missing > 0:
            own_scene = "interior" if scene in {"living", "kitchen", "bedroom"} else scene
            own = _take_fallback(get_own_footage_clips(own_scene, property_type, missing * 2), scene, missing, used)
            for item in own:
                item.update({"scene": scene, "source_priority": 4})
            scene_items.extend(own)
            used.update(_source_identity(item) for item in own if _source_identity(item))

        print(
            f"B-roll {video_id}/{scene}: {len(scene_items)} clips; "
            f"providers={[item.get('provider') for item in scene_items]}"
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
