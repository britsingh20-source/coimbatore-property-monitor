import unittest

from interior_trend_radar.reference_first import build_reference_prompt


class ReferenceFirstPromptTests(unittest.TestCase):
    def test_prompt_has_property_monitor_structure_and_brand(self):
        candidate = {"url": "https://www.youtube.com/watch?v=abcdefghijk", "creator": "Test", "video_id": "abcdefghijk"}
        analysis = {"trend_name": "Corner mechanism", "shot_subjects": ["wide kitchen"], "verified_visual_facts": ["warm wood cabinets"]}
        prompt = build_reference_prompt(candidate, analysis, {"brand": "Olive Tree Interiors"})
        self.assertIn("MANDATORY OUTPUT FORMAT LOCK", prompt)
        self.assertIn("REFERENCE-FIRST INSTRUCTION", prompt)
        self.assertIn("SHOT 7", prompt)
        self.assertIn("OLIVE TREE INTERIORS", prompt)
        self.assertIn("Exactly 10 seconds", prompt)
        self.assertIn("no glossy CGI", prompt)


if __name__ == "__main__": unittest.main()
