import os
import unittest

import visual_broll_validator as validator


class VisualBrollValidatorTests(unittest.TestCase):
    def test_clean_residential_kitchen_is_accepted(self):
        item = {"provider": "Pexels", "local_file": "x.mp4", "quality_score": 20}
        result = validator._normalized_result({
            "scene_match": "kitchen",
            "scene_ok": True,
            "score": 91,
            "people_dominant": False,
            "food_or_cooking": False,
            "flag_or_political_symbol": False,
            "religious": False,
            "commercial": False,
            "hotel_or_resort": False,
            "highway_or_heavy_traffic": False,
            "mountain_or_plantation": False,
            "non_residential": False,
            "reason": "empty residential modular kitchen",
        }, item, "kitchen")
        self.assertTrue(result["visual_accepted"])
        self.assertEqual(91, result["visual_score"])

    def test_food_or_people_reject_even_high_score(self):
        item = {"provider": "Pixabay", "local_file": "x.mp4"}
        result = validator._normalized_result({
            "scene_match": "kitchen",
            "scene_ok": True,
            "score": 98,
            "people_dominant": True,
            "food_or_cooking": True,
        }, item, "kitchen")
        self.assertFalse(result["visual_accepted"])
        self.assertIn("people_dominant", result["visual_reject_flags"])
        self.assertIn("food_or_cooking", result["visual_reject_flags"])

    def test_flag_rejects_location_clip(self):
        item = {"provider": "Pexels", "local_file": "x.mp4"}
        result = validator._normalized_result({
            "scene_match": "location",
            "scene_ok": True,
            "score": 90,
            "flag_or_political_symbol": True,
        }, item, "location")
        self.assertFalse(result["visual_accepted"])

    def test_highway_rejects_road_clip(self):
        item = {"provider": "Pexels", "local_file": "x.mp4"}
        result = validator._normalized_result({
            "scene_match": "road",
            "scene_ok": True,
            "score": 90,
            "highway_or_heavy_traffic": True,
        }, item, "road")
        self.assertFalse(result["visual_accepted"])

    def test_low_score_is_rejected(self):
        item = {"provider": "Pexels", "local_file": "x.mp4"}
        result = validator._normalized_result({
            "scene_match": "exterior",
            "scene_ok": True,
            "score": validator.MIN_VISUAL_SCORE - 1,
        }, item, "exterior")
        self.assertFalse(result["visual_accepted"])

    def test_no_key_returns_unvalidated_metadata_fallback(self):
        old = os.environ.pop("GEMINI_API_KEY", None)
        try:
            result = validator.validate_downloaded_clips("road", [{"quality_score": 17, "local_file": "missing.mp4"}])
            self.assertFalse(result[0]["visual_validated"])
            self.assertEqual(17, result[0]["visual_score"])
        finally:
            if old is not None:
                os.environ["GEMINI_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()
