import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path


CONFIG_PATH = Path("config/locations.json")
WEEKLY_FOCUS_PATH = Path(os.environ.get("WEEKLY_FOCUS_PATH", "config/weekly_focus.json"))


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^\w\u0b80-\u0bff]+", " ", value).strip()


@lru_cache(maxsize=1)
def load_locations() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def active_weekly_focus(*_args, **_kwargs) -> dict:
    """Return the Telegram-selected prompt focus; fail closed if it is unavailable."""
    if not WEEKLY_FOCUS_PATH.exists():
        return {}
    try:
        focus = json.loads(WEEKLY_FOCUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return focus if focus.get("focus_areas") else {}


def _active_candidates() -> list[tuple[str, list[str], list[str]]]:
    focus = active_weekly_focus()
    rows = []
    for area in focus.get("focus_areas", []):
        name = str(area.get("name") or "").strip()
        if not name:
            continue
        aliases = [name, *(str(item) for item in area.get("aliases", []) if str(item).strip())]
        micro = [str(item) for item in area.get("micro_localities", []) if str(item).strip()]
        rows.append((name, aliases, micro))
    return rows


def _edit_distance_within(left: str, right: str, limit: int) -> bool:
    """Return quickly when the words differ by no more than the allowed typo count."""
    if abs(len(left) - len(right)) > limit:
        return False
    previous = list(range(len(right) + 1))
    for row_index, left_char in enumerate(left, 1):
        current = [row_index]
        row_minimum = row_index
        for column_index, right_char in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[column_index] + 1,
                previous[column_index - 1] + (left_char != right_char),
            ))
            row_minimum = min(row_minimum, current[-1])
        if row_minimum > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _word_matches(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
    longest = max(len(actual), len(expected))
    if longest < 6:
        return False
    limit = 2 if longest >= 14 else 1
    return _edit_distance_within(actual, expected, limit)


def contains_phrase(text: str, candidate: str) -> bool:
    """Match exact aliases plus conservative Latin-script spelling mistakes."""
    haystack = normalize(text)
    needle = normalize(candidate)
    if not needle:
        return False

    # Tamil place names commonly take suffixes such as -இல்/-யில் in titles.
    # Keep Tamil matching exact so fuzzy Latin transliteration never affects it.
    if re.search(r"[\u0b80-\u0bff]", needle):
        return needle in haystack

    if f" {needle} " in f" {haystack} ":
        return True

    expected_words = needle.split()
    actual_words = haystack.split()
    width = len(expected_words)
    if not width or len(actual_words) < width:
        return False

    for start in range(len(actual_words) - width + 1):
        window = actual_words[start:start + width]
        if all(_word_matches(actual, expected) for actual, expected in zip(window, expected_words)):
            return True
    return False


def match_location(*values: str) -> dict:
    text = normalize(" ".join(value or "" for value in values))
    config = load_locations()
    matched = []
    matched_focus = []
    matched_terms = []

    for focus_name, aliases, micro_localities in _active_candidates():
        alias_hit = next((candidate for candidate in aliases if contains_phrase(text, candidate)), None)
        micro_hit = next(
            (candidate for candidate in micro_localities if contains_phrase(text, candidate)),
            None,
        )
        if alias_hit:
            matched.append(focus_name)
            matched_focus.append(focus_name)
            matched_terms.append(alias_hit)
        elif micro_hit:
            matched.append(micro_hit)
            matched_focus.append(focus_name)
            matched_terms.append(micro_hit)

    city_match = any(
        contains_phrase(text, alias) for alias in config.get("city_aliases", [])
    )

    # Coimbatore alone is deliberately not enough. A prompt is approved only
    # when the Telegram-selected focus area (or its configured micro-locality)
    # is explicitly found.
    is_target = bool(matched)
    score = 1.0 if matched else 0.0

    return {
        "is_target_location": is_target,
        "matched_localities": matched,
        "city_match": city_match,
        "location_score": score,
        "weekly_focus_active": bool(_active_candidates()),
        "weekly_focus_areas": [name for name, _, _ in _active_candidates()],
        "matched_focus_areas": matched_focus,
        "matched_focus_terms": matched_terms,
        "focus_week_start": active_weekly_focus().get("week_start"),
        "focus_week_end": active_weekly_focus().get("week_end"),
    }
