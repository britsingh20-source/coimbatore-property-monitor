import hashlib
import json
from pathlib import Path

from veo_prompt import build_veo_prompt, telegram_filename


def test_prompt_contains_dynamic_facts_and_fixed_contact():
    job = {
        "video_id": "abc123",
        "source_url": "https://www.youtube.com/watch?v=abc123",
        "property_location": "Karamadai",
        "property": {
            "property_type": "Independent Villa",
            "bhk": 2,
            "land_area": "3.5 Cents",
            "built_up_area": "1,300 sq.ft.",
            "price": "₹67 Lakhs",
            "facing": "East",
            "parking": "Covered parking",
            "approval": "DTCP Approved",
        },
        "verified_facts": "2 BHK villa on 3.5 cents",
    }
    prompt = build_veo_prompt(job)
    assert "Karamadai" in prompt
    assert "₹67 Lakhs" in prompt
    assert "9003787621" in prompt
    assert "exactly 10-second" in prompt
    assert "never invent room connections" in prompt
    assert "PRICE: ₹67 Lakhs  |  LAND: 3.5 Cents" in prompt
    assert "Karamadai  |  SITE VISIT: 9003787621" in prompt
    assert "0.3 TO 10 SECONDS" in prompt
    assert "without covering, altering or imitating any provider provenance mark" in prompt
    assert telegram_filename(job) == "abc123-gemini-veo-prompt.txt"


def test_prompt_uses_the_proven_september_10_source_first_rules():
    job = {
        "video_id": "clean-architecture",
        "source_url": "https://www.youtube.com/watch?v=clean-architecture",
        "property_location": "Coimbatore",
        "property": {
            "property_type": "Independent House",
            "bhk": 3,
            "built_up_area": "1600 sq.ft",
        },
        "verified_facts": "Hall, staircase, kitchen and bedrooms visually confirmed",
    }
    prompt = build_veo_prompt(job)

    assert "First analyse that linked YouTube property video frame-by-frame" in prompt
    assert "never change floor count, exterior, room dimensions, furniture or amenities" in prompt
    assert "no religious imagery" in prompt
    assert "FLOOR-COUNT / BHK LAYOUT LOCK" not in prompt
    assert "PROPERTY SCALE / MARKET-REALISM LOCK" not in prompt
    assert "ARCHITECTURE-ONLY RECONSTRUCTION FILTER" not in prompt


def test_echf_prompt_matches_the_september_10_reference_exactly():
    job = json.loads(Path("data/video_jobs/eChfOB4E7uw.json").read_text(encoding="utf-8"))
    prompt = build_veo_prompt(job)

    assert len(prompt) == 7977
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == (
        "6bfd6235aa1bf8f54d7acf091760473ae75efc688258c69d09f64d2d1398a930"
    )


def test_missing_values_are_explicitly_omitted():
    prompt = build_veo_prompt({
        "video_id": "missing",
        "property_location": "Coimbatore",
        "property": {"property_type": "Villa", "bhk": 3},
    })
    assert "Not specified — omit from video" in prompt


def test_contaminated_entrance_uses_door_free_parking_shot():
    prompt = build_veo_prompt({
        "video_id": "contaminated-entrance",
        "source_url": "https://www.youtube.com/watch?v=contaminated-entrance",
        "property_location": "Maniakarampalayam",
        "entrance_contaminated": True,
        "property": {
            "property_type": "Independent House",
            "bhk": "3 BHK",
            "floors": "G+1 duplex",
        },
        "verified_facts": "Ground floor one bedroom; first floor two bedrooms",
    })

    assert "GATE / PARKING STRUCTURE ONLY" in prompt
    assert "Keep the main entrance door, doorframe, lintel and threshold completely outside" in prompt
    assert "blank uninterrupted wall or tile finishes" in prompt
    assert "Do not point the camera toward the entrance" in prompt


def test_clean_entrance_preserves_standard_parking_shot():
    prompt = build_veo_prompt({
        "video_id": "clean-entrance",
        "source_url": "https://www.youtube.com/watch?v=clean-entrance",
        "property_location": "Karamadai",
        "property": {"property_type": "Independent House", "bhk": "2 BHK"},
    })

    assert "SHOT 2 — 1.4 TO 2.8 SECONDS — PARKING OR PORTICO" in prompt
    assert "GATE / PARKING STRUCTURE ONLY" not in prompt
