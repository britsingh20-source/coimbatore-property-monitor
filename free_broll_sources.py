import hashlib
import json
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


# This process-level set prevents the same stock URL being selected for two
# different properties during one GitHub Actions run.
SESSION_USED_SOURCES: set[str] = set()

# We deliberately ask for more footage than the renderer strictly needs. The
# semantic/subclip director can then choose unique shots instead of recycling
# two files throughout an entire reel.
DEFAULT_PER_CATEGORY = 4


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


# Metadata-based hard rejects. These are intentionally conservative: stock
# footage is representative, so a clearly foreign/commercial/lifestyle shot is
# worse than using a later fallback that actually looks residential.
GLOBAL_REJECT_TERMS = {
    "church", "temple", "mosque", "cathedral", "chapel", "shrine",
    "mountain", "mountains", "alps", "snow", "ski", "forest",
    "tea plantation", "coffee plantation",
    "woman", "women", "man ", " men ", "person", "people", "couple",
    "family", "girl", "boy", "child", "children", "model", "portrait",
    "holding", "cooking", "chef", "dancing", "fitness", "selfie",
    "office", "coworking", "restaurant", "hotel", "resort", "hospital",
    "shopping", "store", "mall", "bar ", "cafe", "warehouse", "factory",
}

SCENE_REJECT_TERMS = {
    "location": {"highway", "freeway", "downtown", "city skyline", "europe", "american", "usa"},
    "road": {"highway", "freeway", "motorway", "race", "traffic jam", "europe", "american", "usa"},
    "land": {"farm", "farmland", "agriculture", "rice field", "paddy field", "desert"},
    "exterior": {"castle", "palace", "mansion", "apartment", "condo", "skyscraper", "europe", "american", "usa"},
    "living": {"conference", "lobby", "reception", "apartment tour"},
    "kitchen": {"commercial kitchen", "restaurant kitchen", "industrial kitchen"},
    "bedroom": {"dormitory", "hostel", "hotel room", "resort room"},
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

# Soft penalties: these do not automatically reject a useful clip, but push it
# below footage that looks like an ordinary Indian independent home.
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
    # search_query is deliberately excluded. A provider returning a result for an
    # India query does not prove the clip itself depicts India. We only reward
    # regional words that exist in provider metadata/URL.
    return " ".join(
        str(item.get(key, ""))
        for key in ("source_url", "title", "description", "alt", "tags")
    ).lower()


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


def _contains_term(text: str, term: str) -> bool:
    if " " in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _stock_allowed(item: dict, scene: str) -> bool:
    mapped_scene = scene if scene in {"location", "road", "land", "exterior", "interior"} else "interior"
    if not _allowed_scene_visual(item, mapped_scene):
        return False
    searchable = _metadata_text(item)
    if any(_contains_term(searchable, term.strip()) for term in GLOBAL_REJECT_TERMS):
        return False
    return not any(_contains_term(searchable, term) for term in SCENE_REJECT_TERMS.get(scene, set()))


def _quality_score(item: dict, scene: str) -> int:
    """Rank stock by Indian-residential fit, scene relevance and reel usability."""
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

    # Earlier query variants are more geographically/property-specific. Keep
    # this modest so actual provider metadata can still outrank query order.
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

    # Quality is the primary ordering inside each freshness tier. Previously
    # used stock remains a last resort even if it scores highly.
    fresh.sort(key=lambda row: (-int(row.get("quality_score", 0)), int(row.get("query_index", 99))))
    old.sort(key=lambda row: (-int(row.get("quality_score", 0)), int(row.get("query_index", 99))))
    return fresh + old


def _provider_candidates(job: dict, scene: str, queries: list[str], provider: str, wanted: int, used: set[str]) -> list[dict]:
    if wanted <= 0:
        return []
    collected: list[dict] = []
    search = search_pexels_videos if provider == "pexels" else search_pixabay_videos

    # Search all targeted variants, then rank globally. This avoids taking four
    # mediocre clips from the first broad query while a later South-India query
    # contains a much better house/road/interior result.
    raw: list[dict] = []
    for query_index, query in enumerate(queries):
        results = search(query, limit=max(10, wanted * 4))
        raw.extend({**item, "scene": scene, "search_query": query, "query_index": query_index} for item in results)

    ranked = _unique_candidates(raw, scene, used)
    for item in ranked:
        identity = _source_identity(item)
        if identity in {_source_identity(x) for x in collected}:
            continue
        collected.append(item)
        if len(collected) >= wanted:
            break
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
    eligible = []
    for item in items:
        identity = _source_identity(item)
        if not identity or identity in used:
            continue
        if not _stock_allowed(item, scene):
            continue
        eligible.append({**item, "quality_score": _quality_score(item, scene)})
    eligible.sort(key=lambda row: -int(row.get("quality_score", 0)))
    return eligible[:wanted]


def source_property_videos_free_first(job: dict, per_scene: int = DEFAULT_PER_CATEGORY) -> list[dict]:
    """Source diverse B-roll with R2 as the last retrieval option.

    Priority for each semantic category:
      1. Pexels fresh portrait video, ranked for Indian residential relevance
      2. Pixabay fresh video, ranked the same way
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
            library = _take_fallback(get_library_clips(library_scene, missing * 3), scene, missing, used)
            for item in library:
                item.update({"scene": scene, "source_priority": 3})
            scene_items.extend(library)
            used.update(_source_identity(item) for item in library if _source_identity(item))

        # 4. Advertiser-owned R2 clips are deliberately the final retrieval
        # option, per current pipeline policy.
        missing = per_scene - len(scene_items)
        if missing > 0:
            own_scene = "interior" if scene in {"living", "kitchen", "bedroom"} else scene
            own = _take_fallback(get_own_footage_clips(own_scene, property_type, missing * 3), scene, missing, used)
            for item in own:
                item.update({"scene": scene, "source_priority": 4})
            scene_items.extend(own)
            used.update(_source_identity(item) for item in own if _source_identity(item))

        print(
            f"B-roll {video_id}/{scene}: {len(scene_items)} clips; "
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
