import json

from send_telegram_prompts import _queue_prompt


def test_queue_prompt_allows_mobile_filename_pairing(tmp_path):
    queue_path = tmp_path / "queue.json"
    _queue_prompt(queue_path, {"video_id": "property-123"})
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    assert data["prompts"][0]["video_id"] == "property-123"
    assert data["prompts"][0]["status"] == "pending_mobile_upload"


def test_queue_prompt_does_not_duplicate_video_id(tmp_path):
    queue_path = tmp_path / "queue.json"
    _queue_prompt(queue_path, {"video_id": "property-123"})
    _queue_prompt(queue_path, {"video_id": "property-123"})
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    assert len(data["prompts"]) == 1


def test_router_self_heals_queue_from_exact_existing_job(tmp_path):
    from telegram_router import ensure_known_prompt_registered

    jobs = tmp_path / "video_jobs"
    jobs.mkdir()
    (jobs / "AbCdEf12345.json").write_text(
        json.dumps({"video_id": "AbCdEf12345", "property_location": "Karamadai"}),
        encoding="utf-8",
    )
    queue_path = tmp_path / "queue.json"

    assert ensure_known_prompt_registered("AbCdEf12345", queue_path, jobs)
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    assert data["prompts"][0]["status"] == "pending_mobile_upload"
    assert data["prompts"][0]["recovered_from_job_registry"] is True


def test_router_will_not_register_unknown_or_malformed_id(tmp_path):
    from telegram_router import ensure_known_prompt_registered

    jobs = tmp_path / "video_jobs"
    jobs.mkdir()
    queue_path = tmp_path / "queue.json"

    assert not ensure_known_prompt_registered("NotAValidId", queue_path, jobs)
    assert not ensure_known_prompt_registered("AbCdEf12345", queue_path, jobs)
    assert not queue_path.exists()
