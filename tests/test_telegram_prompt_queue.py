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
