from social_content import build_social_content


def test_social_content_uses_verified_property_facts_and_exactly_three_hashtags():
    job = {
        "property_location": "Karamadai",
        "property": {
            "property_type": "Independent Villa",
            "bhk": 2,
            "land_area": "3.5 Cents",
            "built_up_area": "1,300 sq.ft.",
            "price": "₹67 Lakhs",
            "facing": "East",
            "parking": "Covered",
            "approval": "DTCP",
        },
    }
    result = build_social_content(job)
    assert result["title"].startswith("₹67 Lakhs 2 BHK Independent Villa in Karamadai")
    assert "9003787621" in result["title"]
    assert "Land: 3.5 Cents" in result["caption"]
    assert len(result["hashtags"]) == 3
    assert result["caption"].count("#") == 3
    assert result["youtube_description"].count("#") == 3


def test_social_content_omits_missing_values():
    result = build_social_content({
        "property_location": "Coimbatore",
        "property": {"property_type": "Villa", "bhk": 3},
    })
    assert "Price:" not in result["caption"]
    assert "Land:" not in result["caption"]
    assert "NOT SPECIFIED" not in result["caption"]
