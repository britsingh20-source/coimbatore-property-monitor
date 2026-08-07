import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from broll_director import build_director_media


class BrollDirectorTests(unittest.TestCase):
    def setUp(self):
        self.scene_media = {
            "exterior": ["render/x/ext-1.mp4", "render/x/ext-2.mp4", "render/x/ext-3.mp4"],
            "road": ["render/x/road-1.mp4", "render/x/road-2.mp4", "render/x/road-3.mp4"],
            "living": ["render/x/living-1.mp4", "render/x/living-2.mp4"],
            "kitchen": ["render/x/kitchen-1.mp4"],
            "bedroom": ["render/x/bed-1.mp4"],
            "interior": ["render/x/living-1.mp4", "render/x/kitchen-1.mp4", "render/x/bed-1.mp4"],
        }
        self.job = {
            "video_id": "sample",
            "content_plan": {
                "scenes": [
                    {"name": "location", "broll": ["exterior", "road"], "avoid_broll": ["bedroom"]},
                    {"name": "builtUp", "broll": ["living_room", "kitchen", "bedroom"], "avoid_broll": ["road"]},
                    {"name": "road", "broll": ["road"], "avoid_broll": ["interior", "bedroom"]},
                    {"name": "cta", "broll": ["exterior", "living_room"], "avoid_broll": ["road"]},
                ]
            },
        }

    @patch("broll_director._duration_frames", return_value=300)
    def test_semantic_categories_are_respected(self, _duration):
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_director_media(self.job, self.scene_media, Path(tmp))
        self.assertTrue(plan["road"])
        self.assertTrue(all(shot["category"] == "road" for shot in plan["road"]))
        self.assertTrue(all(shot["category"] in {"living", "kitchen", "bedroom"} for shot in plan["builtUp"]))
        self.assertTrue(all(shot["category"] != "road" for shot in plan["cta"]))

    @patch("broll_director._duration_frames", return_value=300)
    def test_subclips_have_safe_offsets(self, _duration):
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_director_media(self.job, self.scene_media, Path(tmp))
        starts = [shot["startFrom"] for shots in plan.values() for shot in shots]
        self.assertTrue(all(0 <= start <= 228 for start in starts))
        self.assertTrue(all(start % 15 == 0 for start in starts))


if __name__ == "__main__":
    unittest.main()
