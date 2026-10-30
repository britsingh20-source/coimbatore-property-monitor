import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import location_matcher
from location_matcher import match_location


class LocationMatcherTests(unittest.TestCase):
    def test_vadavalli_english_aliases(self):
        for title in (
            "2BHK in Vadavalli, Coimbatore",
            "Villa for sale in Vadavali",
            "House at Vada Valli",
            "Property in Wadawalli",
        ):
            with self.subTest(title=title):
                result = match_location(title)
                self.assertTrue(result["is_target_location"])
                self.assertEqual(result["matched_localities"], ["Vadavalli"])

    def test_vadavalli_tamil_alias(self):
        result = match_location("வடவள்ளியில் வீடு விற்பனைக்கு")
        self.assertTrue(result["is_target_location"])
        self.assertEqual(result["matched_localities"], ["Vadavalli"])

    def test_city_only_is_rejected(self):
        result = match_location("House somewhere in Coimbatore")
        self.assertFalse(result["is_target_location"])
        self.assertTrue(result["city_match"])

    def test_every_other_previous_focus_area_is_rejected(self):
        for title in (
            "Villa in Saravanampatti",
            "House for sale at Idigarai",
            "3BHK Karamadai",
            "Plot in Periyanaicken Palayam",
            "Home at Mettupalayam",
            "Land on Annur to Mettupalayam Road",
            "Villa at Thudiyalur",
            "House in Somayampalayam",
            "Property at Bommanampalayam",
        ):
            with self.subTest(title=title):
                result = match_location(title)
                self.assertFalse(result["is_target_location"])
                self.assertEqual(result["matched_localities"], [])

    def test_telegram_selection_switches_future_prompt_area(self):
        focus = {
            "focus_areas": [{
                "name": "Karamadai",
                "aliases": ["karamadai", "karmadai"],
                "micro_localities": ["Teachers Colony"],
            }],
            "week_start": "2026-10-25",
            "week_end": "2026-10-31",
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "focus.json"
            path.write_text(json.dumps(focus), encoding="utf-8")
            with patch.object(location_matcher, "WEEKLY_FOCUS_PATH", path):
                inside = match_location("Villa in Karamadai")
                micro = match_location("House in Teachers Colony")
                outside = match_location("Villa in Vadavalli")
        self.assertTrue(inside["is_target_location"])
        self.assertEqual(inside["matched_focus_areas"], ["Karamadai"])
        self.assertTrue(micro["is_target_location"])
        self.assertEqual(micro["matched_focus_areas"], ["Karamadai"])
        self.assertFalse(outside["is_target_location"])


if __name__ == "__main__":
    unittest.main()
