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


def test_missing_values_are_explicitly_omitted():
    prompt = build_veo_prompt({
        "video_id": "missing",
        "property_location": "Coimbatore",
        "property": {"property_type": "Villa", "bhk": 3},
    })
    assert "Not specified — omit from video" in prompt
