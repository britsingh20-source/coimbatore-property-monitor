import json
import os
from pathlib import Path

from location_matcher import contains_phrase, normalize


LOCATION_CONFIG = Path("config/locations.json")
MAX_EXPLORATORY_PER_RUN = int(os.environ.get("MAX_EXPLORATORY_PER_RUN", "1"))
SPARSE_RECENT_FALLBACK = int(os.environ.get("SPARSE_RECENT_FALLBACK", "1"))
STRICT_TARGET_ONLY = os.environ.get("STRICT_TARGET_ONLY", "1").strip().casefold() not in {
    "0", "false", "no", "off",
}

PROPERTY_TERMS = (
    "villa", "house", "home", "property", "plot", "land", "site", "2bhk", "3bhk", "4bhk",
    "duplex", "independent house", "வீடு", "வில்லா", "ப்ளாட்", "மனை", "சென்ட்", "sqft", "sq.ft",
)

STRONG_SALE_TERMS = (
    "sale", "for sale", "selling", "price", "lakhs", "lakh", "crore", "cent", "cents",
    "dtcp", "rera", "ready to move", "விற்பனை", "லட்சம்", "கோடி",
)

OBVIOUS_NON_LISTING_TERMS = (
    "news", "interview", "podcast", "motivation", "comedy", "song", "short film", "recipe",
    "review only", "market update", "tips", "how to", "construction tips", "interior tips",
)


def _normalize(value: str) -> str:
    return normalize(value)


def _location_candidates() -> tuple[tuple[str, tuple[str, ...]], ...]:
    config = json.loads(LOCATION_CONFIG.read_text(encoding="utf-8"))
    rows = []
    for canonical, aliases in (config.get("target_localities") or {}).items():
        candidates = (canonical, *(aliases or []))
        rows.append((canonical, tuple(str(term) for term in candidates if str(term).strip())))
    return tuple(rows)


def _location_hits(text: str) -> list[str]:
    hits = []
    for canonical, candidates in _location_candidates():
        if any(contains_phrase(text, candidate) for candidate in candidates):
            hits.append(_normalize(canonical))
    return hits


def metadata_score(video: dict) -> dict:
    title = _normalize(video.get("title", ""))
    description = _normalize(video.get("description", ""))
    text = f"{title} {description}"

    location_hits = _location_hits(text)
    property_hits = [term for term in PROPERTY_TERMS if term in text]
    sale_hits = [term for term in STRONG_SALE_TERMS if term in text]
    negative_hits = [term for term in OBVIOUS_NON_LISTING_TERMS if term in text]

    score = 0
    if location_hits:
        score += 6
    if property_hits:
        score += 4
    if sale_hits:
        score += 2
    if negative_hits:
        score -= 8

    strong_target = bool(location_hits and property_hits and not negative_hits)
    exploratory = bool(property_hits and not negative_hits)

    return {
        "score": score,
        "strong_target": strong_target,
        "exploratory": exploratory,
        "location_hits": location_hits[:5],
        "property_hits": property_hits[:5],
        "sale_hits": sale_hits[:5],
        "negative_hits": negative_hits[:5],
    }


def build_analysis_queue(videos: list[dict], recent_ids: set[str], max_per_run: int) -> list[dict]:
    ranked = []
    sparse_recent = []
    for index, video in enumerate(videos):
        signals = metadata_score(video)
        recent = video.get("video_id") in recent_ids
        if STRICT_TARGET_ONLY and not signals["strong_target"]:
            continue
        if not signals["exploratory"] and not signals["strong_target"]:
            if recent and not signals["negative_hits"]:
                sparse_recent.append((video, signals, index))
            continue
        ranked.append((video, signals, index))

    strong_recent = []
    strong_retry = []
    exploratory_recent = []
    exploratory_retry = []

    for video, signals, index in ranked:
        item = (video, signals, index)
        recent = video.get("video_id") in recent_ids
        if signals["strong_target"]:
            (strong_recent if recent else strong_retry).append(item)
        else:
            (exploratory_recent if recent else exploratory_retry).append(item)

    def sort_key(item):
        video, signals, index = item
        return (-int(signals["score"]), index, str(video.get("published_at", "")))

    for bucket in (strong_recent, strong_retry, exploratory_recent, exploratory_retry, sparse_recent):
        bucket.sort(key=sort_key)

    selected = strong_recent + strong_retry
    remaining = max(0, max_per_run - len(selected))
    if remaining and MAX_EXPLORATORY_PER_RUN > 0:
        exploratory = exploratory_recent + exploratory_retry
        take = exploratory[: min(remaining, MAX_EXPLORATORY_PER_RUN)]
        selected.extend(take)
        remaining = max(0, max_per_run - len(selected))

    if remaining and SPARSE_RECENT_FALLBACK > 0:
        selected_ids = {item[0].get("video_id") for item in selected}
        fallback = [item for item in sparse_recent if item[0].get("video_id") not in selected_ids]
        selected.extend(fallback[: min(remaining, SPARSE_RECENT_FALLBACK)])

    queue = []
    for video, signals, _ in selected[:max_per_run]:
        enriched = dict(video)
        enriched["metadata_prefilter"] = signals
        if not signals["exploratory"] and not signals["strong_target"]:
            enriched["metadata_prefilter"]["fallback_reason"] = "recent_property_channel_sparse_metadata"
        queue.append(enriched)
    return queue
