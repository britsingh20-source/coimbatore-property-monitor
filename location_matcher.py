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
    score = 1.0 if matched else (0.45 if city_match else 0.0)
    return {
        "is_target_location": bool(matched),
        "matched_localities": matched,
        "city_match": city_match,
        "location_score": score,
    }
