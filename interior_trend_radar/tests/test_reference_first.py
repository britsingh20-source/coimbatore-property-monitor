import unittest

from interior_trend_radar.reference_first import build_reference_prompt, _select_daily


class ReferenceFirstPromptTests(unittest.TestCase):
    def test_prompt_has_property_monitor_structure_and_brand(self):
        candidate = {"url": "https://www.youtube.com/watch?v=abcdefghijk", "creator": "Test", "video_id": "abcdefghijk"}
        analysis = {"core_idea": "Corner mechanism", "system_type": "cabinet mechanism", "installation_method": "inside corner cabinet", "mechanism": "pull-out", "shot_subjects": ["wide kitchen"], "verified_facts": ["warm wood cabinets"], "forbidden_substitutes": ["ordinary shelf"]}
        prompt = build_reference_prompt(candidate, analysis, {"brand": "Olive Tree Interiors"})
        self.assertIn("MANDATORY OUTPUT FORMAT LOCK", prompt)
        self.assertIn("REFERENCE-FIRST INSTRUCTION", prompt)
        self.assertIn("SHOT 7", prompt)
        self.assertIn("OLIVE TREE INTERIORS", prompt)
        self.assertIn("Exactly 10 seconds", prompt)
        self.assertIn("no glossy CGI", prompt)
        self.assertNotIn("attached reference frames", prompt)
        self.assertIn("linked YouTube interior video", prompt)
        self.assertIn("CRITICAL WRONG-SUBSTITUTE LOCK", prompt)
        self.assertIn("ordinary shelf", prompt)
        self.assertIn("INVISIBLE-CAMERA LOCK", prompt)
        self.assertIn("Never show a cameraman", prompt)
        self.assertNotIn("smartphone-gimbal push-in", prompt)

    def test_selects_one_unused_video_per_channel(self):
        config = {"daily_prompt_limit": 5, "monitored_youtube_channels": [{"name": "A"}, {"name": "B"}]}
        candidates = [
            {"creator": "A", "video_id": "used"}, {"creator": "A", "video_id": "fresh-a"},
            {"creator": "B", "video_id": "fresh-b"}, {"creator": "B", "video_id": "older-b"},
        ]
        selected = _select_daily(candidates, config, {"used_video_ids": ["used"]})
        self.assertEqual(["fresh-a", "fresh-b"], [item["video_id"] for item in selected])

    def test_scheduled_slot_selects_one_preferred_channel(self):
        config = {"daily_prompt_limit": 5, "monitored_youtube_channels": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}
        candidates = [{"creator": name, "video_id": name.lower()} for name in ("A", "B", "C")]
        selected = _select_daily(candidates, config, {"used_video_ids": []}, "afternoon")
        self.assertEqual(["b"], [item["video_id"] for item in selected])


if __name__ == "__main__": unittest.main()
