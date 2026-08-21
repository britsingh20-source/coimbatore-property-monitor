from video_property_matcher import _parse_json


def test_parse_content_match_json():
    result = _parse_json(
        '```json\n{"video_id":"abc","confidence":0.94,"evidence":["price","location"]}\n```'
    )
    assert result["video_id"] == "abc"
    assert result["confidence"] == 0.94
    assert len(result["evidence"]) == 2
