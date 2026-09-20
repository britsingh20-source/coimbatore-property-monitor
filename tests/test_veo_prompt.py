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


def test_prompt_filters_personal_religious_and_loose_furniture_details():
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

    assert "ARCHITECTURE-ONLY RECONSTRUCTION FILTER — MANDATORY" in prompt
    assert "This exclusion rule applies EVEN IF those objects are present" in prompt
    assert "NEVER generate religious imagery" in prompt
    assert "NEVER generate cots, beds, mattresses or loose furniture beside/under a staircase" in prompt
    assert "Do not replace a removed object with another decorative object" in prompt
    assert "the staircase and surrounding architecture must remain clear and unobstructed" in prompt
    assert "Do NOT reproduce televisions, deity photos, religious images" in prompt
    assert "ZERO-TOLERANCE RELIGION-NEUTRAL OBJECT FILTER" in prompt
    assert "plain uninterrupted floor tiles" in prompt
    assert "blank neutral wall or empty built-in panel" in prompt
    assert "perform three mandatory audits" in prompt
    assert "discard that entire shot" in prompt


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
