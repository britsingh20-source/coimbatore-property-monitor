import pytest

from manual_video_intake import (
    build_manual_job,
    manual_publish_requested,
    manual_video_id,
)
from social_content import build_social_content


def test_manual_publish_requires_explicit_caption():
    assert manual_publish_requested({"caption": "MANUAL_PUBLISH"})
    assert manual_publish_requested({"caption": "MODE: MANUAL"})
    assert not manual_publish_requested({"caption": "VIDEO_ID: abc123def45"})
    assert not manual_publish_requested({"caption": ""})


def test_manual_video_id_is_stable_and_safe():
    assert manual_video_id("AgAD abc/123") == "manual-AgAD-abc-123"


def test_manual_job_requires_core_spoken_facts():
    with pytest.raises(ValueError):
        build_manual_job("manual-file", {
            "property_location": "Vadavalli",
            "property_type": "Villa",
        })


def test_manual_job_and_social_copy_use_only_extracted_details():
    job = build_manual_job("manual-file", {
        "transcript": "Three BHK villa in Vadavalli, 95 lakhs, 3.5 cents.",
        "property_location": "Vadavalli, Coimbatore",
        "property_type": "Villa",
        "bhk": "3 BHK",
        "price": "₹95 Lakhs",
        "land_area": "3.5 Cents",
        "built_up_area": "",
        "facing": "",
        "road_width": "",
        "parking": "Covered car parking",
        "approval": "DTCP Approved",
        "amenities": ["Borewell"],
        "nearby_landmarks": ["Marudhamalai Road"],
        "selling_points": ["Ready for site visit"],
        "contact_number": "9003787621",
        "marketing_hook": "Explore this 3 BHK villa in Vadavalli at ₹95 Lakhs.",
        "spoken_facts": [
            "3 BHK villa",
            "Vadavalli",
            "₹95 Lakhs",
            "3.5 Cents",
        ],
    })
    assert job["source_type"] == "manual_audio"
    assert job["property"]["price"] == "₹95 Lakhs"
    content = build_social_content(job)
    assert content["caption"].startswith(
        "🏠 Explore this 3 BHK villa in Vadavalli at ₹95 Lakhs."
    )
    assert "✨ Highlights:" in content["caption"]
    assert "📌 Nearby:" in content["caption"]
    assert "9003787621" in content["caption"]
    assert len(content["hashtags"]) > 3
    assert "#Shorts" in content["youtube_description"]
