from telegram_r2_ingest import _resolve_supplied_video_id


def test_exact_published_video_id_can_be_reused():
    queue = {
        "prompts": [
            {"video_id": "czrxkmFHWn4", "status": "published"},
            {"video_id": "xTvjrweqpy4", "status": "pending_mobile_upload"},
        ]
    }

    assert _resolve_supplied_video_id("czrxkmFHWn4", queue) == "czrxkmFHWn4"


def test_mobile_glyph_correction_stays_limited_to_pending_ids():
    queue = {
        "prompts": [
            {"video_id": "icWK1jhUiU0", "status": "pending_mobile_upload"},
            {"video_id": "oldVideo0O0", "status": "published"},
        ]
    }

    assert _resolve_supplied_video_id("icWK1jhUiUO", queue) == "icWK1jhUiU0"
