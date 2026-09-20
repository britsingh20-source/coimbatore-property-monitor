import metadata_prefilter


def video(video_id, title, description="", published_at="2026-08-09T00:00:00Z"):
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "published_at": published_at,
    }


def test_coimbatore_property_is_strong_target():
    signals = metadata_prefilter.metadata_score(
        video("a", "2BHK villa for sale in Saravanampatti Coimbatore 55 lakhs")
    )
    assert signals["strong_target"] is True
    assert signals["score"] >= 10


def test_generic_property_is_exploratory_not_strong():
    signals = metadata_prefilter.metadata_score(video("a", "3BHK independent house for sale"))
    assert signals["strong_target"] is False
    assert signals["exploratory"] is True


def test_coimbatore_without_focus_area_is_not_strong_target():
    signals = metadata_prefilter.metadata_score(
        video("a", "2BHK villa for sale in Coimbatore 55 lakhs")
    )
    assert signals["strong_target"] is False
    assert signals["location_hits"] == []


def test_focus_belt_micro_locality_is_a_strong_target():
    signals = metadata_prefilter.metadata_score(
        video("a", "3BHK independent villa in Teachers Colony for sale")
    )
    assert signals["strong_target"] is True
    assert "teachers colony" in signals["location_hits"]


def test_misspelled_focus_area_is_still_a_strong_target():
    for place in ("Idikarai", "Idigray", "Karmadai", "Periyanayakkanpalayam"):
        signals = metadata_prefilter.metadata_score(
            video("a", f"2BHK house for sale in {place}")
        )
        assert signals["strong_target"] is True
        assert signals["location_hits"]


def test_non_listing_is_filtered():
    signals = metadata_prefilter.metadata_score(video("a", "Real estate market update and property tips"))
    assert signals["strong_target"] is False
    assert signals["exploratory"] is False


def test_queue_prioritizes_recent_target_over_retry_and_exploratory(monkeypatch):
    monkeypatch.setattr(metadata_prefilter, "STRICT_TARGET_ONLY", False)
    monkeypatch.setattr(metadata_prefilter, "MAX_EXPLORATORY_PER_RUN", 1)
    rows = [
        video("retry-target", "Villa for sale in Karamadai Coimbatore"),
        video("recent-generic", "2BHK independent house for sale"),
        video("recent-target", "2BHK villa Idigarai Coimbatore for sale"),
    ]
    queue = metadata_prefilter.build_analysis_queue(rows, {"recent-generic", "recent-target"}, 3)
    assert [item["video_id"] for item in queue] == [
        "recent-target",
        "retry-target",
        "recent-generic",
    ]


def test_only_one_exploratory_candidate_is_used(monkeypatch):
    monkeypatch.setattr(metadata_prefilter, "STRICT_TARGET_ONLY", False)
    monkeypatch.setattr(metadata_prefilter, "MAX_EXPLORATORY_PER_RUN", 1)
    rows = [
        video("a", "2BHK independent house for sale"),
        video("b", "3BHK villa for sale"),
        video("c", "Residential plot for sale"),
    ]
    queue = metadata_prefilter.build_analysis_queue(rows, {"a", "b", "c"}, 3)
    assert len(queue) == 1


def test_strict_queue_keeps_only_explicit_focus_area(monkeypatch):
    monkeypatch.setattr(metadata_prefilter, "STRICT_TARGET_ONLY", True)
    rows = [
        video("focus", "2BHK villa in Periyanaickenpalayam for sale"),
        video("city", "3BHK villa in Coimbatore for sale"),
        video("other", "Villa in Vadavalli for sale"),
        video("sparse", "New property tour"),
    ]
    queue = metadata_prefilter.build_analysis_queue(rows, {row["video_id"] for row in rows}, 4)
    assert [item["video_id"] for item in queue] == ["focus"]
