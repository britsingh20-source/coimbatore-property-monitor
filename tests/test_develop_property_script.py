from develop_property_script import _fallback_plan


def test_fallback_uses_extracted_property_location_before_keyword_matches():
    property_data = {
        "location": "Thoppampatti Pirivu, Near D-Mart, Thudiyalur",
        "property_type": "Villa",
        "bhk": "3 BHK",
    }
    location = {
        "matched_localities": ["Saravanampatti", "Thudiyalur"],
    }

    plan = _fallback_plan(property_data, location)
    voice = plan["scenes"][0]["voice"]

    assert voice.startswith("Thoppampatti Pirivu, Near D-Mart, Thudiyalur")
    assert "Saravanampatti சைட்ல" not in voice
