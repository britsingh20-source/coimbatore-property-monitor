import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_sources import (
    _allowed_scene_visual, _allowed_visual, _scene_video_queries,
    search_pexels_videos, source_property_media, source_property_videos,
)


class MediaSourceTests(unittest.TestCase):
    def test_religious_visual_urls_are_rejected(self):
        self.assertFalse(_allowed_visual({"source_url": "https://example.com/temple-aerial-video"}))
        self.assertFalse(_allowed_visual({"alt": "Road beside a church"}))
        self.assertTrue(_allowed_visual({"source_url": "https://example.com/residential-road-drone"}))

    @patch.dict(os.environ, {}, clear=True)
    def test_pexels_video_search_is_optional(self):
        self.assertEqual(search_pexels_videos("house"), [])

    @patch("media_sources.search_commons", return_value=[])
    @patch("media_sources.search_pexels", return_value=[])
    def test_sparse_search_generates_three_honest_vfx_plates(self, _pexels, _commons):
        job = {
            "video_id": "example",
            "source_url": "https://youtube.com/watch?v=example",
            "property_location": "Near Thudiyalur, Coimbatore",
            "property": {
                "property_type": "Plot",
                "land_area": "2.75 cents",
                "road_width": "30 ft road",
                "facing": "North",
            },
        }
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                media = source_property_media(job)
                self.assertEqual(len(media), 3)
                self.assertTrue(all(Path(item["local_file"]).exists() for item in media))
                self.assertTrue(all(item["actual_property"] is False for item in media))
                self.assertTrue(all("Autopilot" in item["provider"] for item in media))
            finally:
                os.chdir(original)

    def test_plot_broll_queries_are_split_by_scene(self):
        queries = _scene_video_queries({
            "property_location": "NGGO Colony, Coimbatore",
            "property": {"property_type": "Plot"},
        })
        self.assertIn("land", queries)
        self.assertIn("road", queries)
        self.assertIn("location", queries)
        self.assertNotEqual(queries["land"], queries["road"])
        self.assertTrue(all("road" in query.lower() for query in queries["road"]))

    def test_tea_estate_is_rejected_for_road_and_land_scenes(self):
        item = {"source_url": "https://www.pexels.com/video/aerial-tea-plantation-123/"}
        self.assertFalse(_allowed_scene_visual(item, "road"))
        self.assertFalse(_allowed_scene_visual(item, "land"))

    @patch("media_sources.download_media", return_value=[])
    @patch("media_sources.search_pexels_videos", return_value=[])
    def test_source_calls_separate_scene_queries(self, search, _download):
        source_property_videos({
            "video_id": "plot-example",
            "property_location": "NGGO Colony, Coimbatore",
            "property": {"property_type": "Plot"},
        })
        queries = " ".join(call.args[0] for call in search.call_args_list).lower()
        self.assertIn("plot", queries)
        self.assertIn("tar road", queries)


if __name__ == "__main__":
    unittest.main()
