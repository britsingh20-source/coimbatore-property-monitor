from telegram_r2_ingest import (
    _explicit_video_id,
    _is_retryable_preupload_rejection,
    _resolve_supplied_video_id,
)


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


def test_spaced_mobile_id_is_compacted():
    assert _explicit_video_id({"text": "n8Tl4Rmg 7 pU"}) == "n8Tl4Rmg7pU"


def test_zero_width_mobile_id_is_compacted():
    assert _explicit_video_id({"text": "n8Tl4Rmg\u200b7\u200bpU"}) == "n8Tl4Rmg7pU"


def test_sentence_is_not_mistaken_for_video_id():
    assert _explicit_video_id({"text": "please publish n8Tl4Rmg7pU"}) == ""



def test_preupload_invalid_video_id_can_be_retried():
    assert _is_retryable_preupload_rejection({
        "status": "rejected_invalid_video_id",
        "provided_video_id": "mF6BdMsC0hs",
    })


def test_preupload_no_pending_prompt_can_be_retried_after_queue_recovers():
    assert _is_retryable_preupload_rejection({
        "status": "ignored_no_pending_prompt",
    })


def test_uploaded_or_r2_backed_duplicate_is_never_reuploaded():
    assert not _is_retryable_preupload_rejection({
        "status": "uploaded_exact_video_id",
        "r2_key": "social-ready/mF6BdMsC0hs.mp4",
    })


def test_rejected_record_with_r2_key_is_not_retried_as_new_upload():
    assert not _is_retryable_preupload_rejection({
        "status": "rejected_invalid_video_id",
        "r2_key": "social-ready/telegram-existing.mp4",
    })
