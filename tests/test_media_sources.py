import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_sources import search_pexels_videos, source_property_media


class MediaSourceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
