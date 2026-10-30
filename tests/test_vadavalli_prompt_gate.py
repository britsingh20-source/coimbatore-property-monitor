from main import _authoritative_location_values
from send_telegram_prompts import _is_vadavalli_job


def test_extracted_location_overrides_vadavalli_marketing_keyword():
    video = {
        "title": "Near Vadavalli villa",
        "description": "Vadavalli side property",
    }
    result = {"location": "Somayampalayam, Coimbatore"}
    assert _authoritative_location_values(video, result) == (
        "Somayampalayam, Coimbatore",
    )


def test_telegram_gate_accepts_vadavalli_job():
    assert _is_vadavalli_job({"property_location": "Vadavalli, Coimbatore"})


def test_telegram_gate_rejects_every_other_job():
    assert not _is_vadavalli_job({"property_location": "Saravanampatti, Coimbatore"})
    assert not _is_vadavalli_job({"property_location": "Somayampalayam, Coimbatore"})
