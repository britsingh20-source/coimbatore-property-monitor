import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path


CONFIG_PATH = Path("config/locations.json")


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^\w\u0b80-\u0bff]+", " ", value).strip()


@lru_cache(maxsize=1)
def load_locations() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def active_weekly_focus(*_args, **_kwargs) -> dict:
    """Dynamic weekly focus is disabled; the static locality whitelist is authoritative."""
    return {}


def contains_phrase(text: str, candidate: str) -> bool:
    """Match a normalized alias as complete words instead of as a substring."""
    needle = normalize(candidate)
    # Tamil place names commonly take suffixes such as -இல்/-யில் in titles;
    # substring matching preserves those grammatical forms safely.
    if re.search(r"[\u0b80-\u0bff]", needle):
        return needle in text
    return bool(needle and f" {needle} " in f" {text} ")


def match_location(*values: str) -> dict:
    text = normalize(" ".join(value or "" for value in values))
    config = load_locations()
    matched = []

    for locality, aliases in config["target_localities"].items():
        if any(contains_phrase(text, alias) for alias in aliases):
            matched.append(locality)

    city_match = any(
        contains_phrase(text, alias) for alias in config.get("city_aliases", [])
    )

    # Coimbatore alone is deliberately not enough. A prompt is approved only
    # when one of the permanent focus localities/corridors is explicitly found.
    is_target = bool(matched)
    score = 1.0 if matched else 0.0

    return {
        "is_target_location": is_target,
        "matched_localities": matched,
        "city_match": city_match,
        "location_score": score,
        "weekly_focus_active": False,
        "weekly_focus_areas": [],
        "matched_focus_areas": [],
        "matched_focus_terms": [],
        "focus_week_start": None,
        "focus_week_end": None,
    }
