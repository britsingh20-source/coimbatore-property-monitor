import json
import os
import re
import unicodedata
from datetime import datetime, date
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo


CONFIG_PATH = Path("config/locations.json")
WEEKLY_FOCUS_PATH = Path(os.environ.get("WEEKLY_FOCUS_PATH", "config/weekly_focus.json"))


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^\w\u0b80-\u0bff]+", " ", value).strip()


@lru_cache(maxsize=1)
def load_locations() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_weekly_focus() -> dict:
    if not WEEKLY_FOCUS_PATH.exists():
        return {}
    with WEEKLY_FOCUS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def active_weekly_focus(today: date | None = None) -> dict:
    config = load_weekly_focus()
    if not config:
        return {}

    timezone = config.get("timezone", "Asia/Kolkata")
    if today is None:
        today = datetime.now(ZoneInfo(timezone)).date()

    start = _parse_date(config.get("week_start"))
    end = _parse_date(config.get("week_end"))
    if start and today < start:
        return {}
    if end and today > end:
        return {}
    return config


def _focus_match(text: str, focus_config: dict) -> tuple[list[str], list[str]]:
    matched_areas: list[str] = []
    matched_terms: list[str] = []

    for area in focus_config.get("focus_areas", []):
        name = str(area.get("name") or "").strip()
        terms = [name, *(area.get("aliases") or []), *(area.get("micro_localities") or [])]
        normalized_terms = [(term, normalize(str(term))) for term in terms if str(term).strip()]
        hits = [raw for raw, normalized_term in normalized_terms if normalized_term and normalized_term in text]
        if hits:
            if name:
                matched_areas.append(name)
            matched_terms.extend(hits)

    return matched_areas, matched_terms


def match_location(*values: str) -> dict:
    text = normalize(" ".join(value or "" for value in values))
    config = load_locations()
    matched = []

    for locality, aliases in config["target_localities"].items():
        if any(normalize(alias) in text for alias in aliases):
            matched.append(locality)

    city_match = any(
        normalize(alias) in text for alias in config.get("city_aliases", [])
    )

    focus_config = active_weekly_focus()
    focus_areas, focus_terms = _focus_match(text, focus_config) if focus_config else ([], [])
    focus_required = bool(
        focus_config.get("rules", {}).get("require_focus_match_for_prompt", False)
    ) if focus_config else False
    allow_citywide_fallback = bool(
        focus_config.get("rules", {}).get("allow_citywide_fallback", False)
    ) if focus_config else True

    if focus_required:
        is_target = bool(focus_areas)
        score = 1.0 if focus_areas else 0.0
    else:
        is_target = bool(matched or (city_match and allow_citywide_fallback))
        score = 1.0 if matched else (0.75 if city_match and allow_citywide_fallback else 0.0)

    return {
        "is_target_location": is_target,
        "matched_localities": matched,
        "city_match": city_match,
        "location_score": score,
        "weekly_focus_active": bool(focus_config),
        "weekly_focus_areas": [area.get("name") for area in focus_config.get("focus_areas", [])] if focus_config else [],
        "matched_focus_areas": focus_areas,
        "matched_focus_terms": focus_terms,
        "focus_week_start": focus_config.get("week_start") if focus_config else None,
        "focus_week_end": focus_config.get("week_end") if focus_config else None,
    }
