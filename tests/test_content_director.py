import os
import unittest
from unittest.mock import patch

from develop_property_script import develop_property_script
from tamil_voiceover import build_voice_segments


class ContentDirectorTests(unittest.TestCase):
    def test_fallback_develops_conversational_script_and_skips_missing(self):
        property_data = {
            "location": "Pattanam",
            "property_type": "House",
            "bhk": "2BHK",
            "land_area": "2.75 cents",
            "built_up_area": "1050 sqft",
            "price": "65 lakhs",
            "facing": "North",
            "road_width": "30 ft",
            "approval": "DTCP",
            "parking": "NOT SPECIFIED",
            "source_facts": ["2.75 cents", "1050 sqft", "65 lakhs", "30 ft", "DTCP"],
        }
        location = {"matched_localities": ["Pattanam"]}
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            plan = develop_property_script(property_data, location)

        names = [scene["name"] for scene in plan["scenes"]]
        self.assertEqual("location", names[0])
        self.assertEqual("cta", names[-1])
        self.assertIn("road", names)
        self.assertNotIn("parking", names)
        road = next(scene for scene in plan["scenes"] if scene["name"] == "road")
        self.assertEqual(["road"], road["broll"])
        self.assertIn("முக்கியமான", road["voice"])

    def test_voiceover_uses_developed_scene_order_and_words(self):
        job = {
            "content_plan": {
                "scenes": [
                    {"name": "location", "voice": "ஒரு நல்ல ஹுக்.", "broll": ["exterior"]},
                    {"name": "price", "voice": "விலை இங்க முக்கியமான பாயிண்ட்.", "broll": ["exterior"]},
                    {"name": "cta", "voice": "சைட் விசிட்டுக்கு கால் பண்ணுங்க.", "broll": ["exterior"]},
                ]
            }
        }
        segments = build_voice_segments(job)
        self.assertEqual(["location", "price", "cta"], [item["scene"] for item in segments])
        self.assertEqual("விலை இங்க முக்கியமான பாயிண்ட்.", segments[1]["text"])
        self.assertEqual(["exterior"], segments[1]["broll"])


if __name__ == "__main__":
    unittest.main()
