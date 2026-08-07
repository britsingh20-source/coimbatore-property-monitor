import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import free_broll_sources as broll


JOB = {
    "video_id": "test-video",
    "property_location": "Pattanam, Coimbatore",
    "property": {"property_type": "villa"},
}


def item(provider: str, identity: str) -> dict:
    return {
        "provider": provider,
        "source_url": f"https://example.com/{identity}",
        "download_url": f"https://cdn.example.com/{identity}.mp4",
        "license": f"{provider} License",
        "media_kind": "video",
    }


class FreeBrollPriorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp.name)
        broll.SESSION_USED_SOURCES.clear()

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.temp.cleanup()

    def _download_passthrough(self, items, destination, limit=6):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        saved = []
        for index, row in enumerate(items[:limit], start=1):
            path = destination / f"{index:02d}.mp4"
            path.write_bytes(b"test")
            saved.append({**row, "local_file": str(path)})
        return saved

    @patch.object(broll, "add_to_library")
    @patch.object(broll, "get_own_footage_clips")
    @patch.object(broll, "get_library_clips")
    @patch.object(broll, "search_pixabay_videos")
    @patch.object(broll, "search_pexels_videos")
    @patch.object(broll, "download_media")
    @patch.object(broll, "_category_queries", return_value={"road": ["road query"]})
    def test_pexels_fills_before_any_fallback(self, _queries, download, pexels, pixabay, library, own, _cache):
        download.side_effect = self._download_passthrough
        pexels.return_value = [item("Pexels", f"p{i}") for i in range(5)]

        result = broll.source_property_videos_free_first(JOB, per_scene=4)

        self.assertEqual(4, len(result))
        self.assertTrue(all(row["provider"] == "Pexels" for row in result))
        pixabay.assert_not_called()
        library.assert_not_called()
        own.assert_not_called()

    @patch.object(broll, "add_to_library")
    @patch.object(broll, "get_own_footage_clips")
    @patch.object(broll, "get_library_clips")
    @patch.object(broll, "search_pixabay_videos")
    @patch.object(broll, "search_pexels_videos")
    @patch.object(broll, "download_media")
    @patch.object(broll, "_category_queries", return_value={"road": ["road query"]})
    def test_pixabay_is_second_and_r2_is_not_used_when_enough(self, _queries, download, pexels, pixabay, library, own, _cache):
        download.side_effect = self._download_passthrough
        pexels.return_value = [item("Pexels", "p1")]
        pixabay.return_value = [item("Pixabay", f"x{i}") for i in range(5)]

        result = broll.source_property_videos_free_first(JOB, per_scene=4)

        self.assertEqual(["Pexels", "Pixabay", "Pixabay", "Pixabay"], [row["provider"] for row in result])
        library.assert_not_called()
        own.assert_not_called()

    @patch.object(broll, "add_to_library")
    @patch.object(broll, "get_own_footage_clips")
    @patch.object(broll, "get_library_clips")
    @patch.object(broll, "search_pixabay_videos", return_value=[])
    @patch.object(broll, "search_pexels_videos", return_value=[])
    @patch.object(broll, "download_media")
    @patch.object(broll, "_category_queries", return_value={"road": ["road query"]})
    def test_r2_library_then_owned_r2_are_last_resorts(self, _queries, download, _pexels, _pixabay, library, own, _cache):
        download.side_effect = self._download_passthrough
        library.return_value = [item("Library cache (R2)", "library1")]
        own.return_value = [item("Advertiser supplied (own b-roll)", "own1"), item("Advertiser supplied (own b-roll)", "own2")]

        result = broll.source_property_videos_free_first(JOB, per_scene=3)

        self.assertEqual(
            ["Library cache (R2)", "Advertiser supplied (own b-roll)", "Advertiser supplied (own b-roll)"],
            [row["provider"] for row in result],
        )
        library.assert_called_once()
        own.assert_called_once()

    def test_house_queries_have_separate_room_categories(self):
        queries = broll._category_queries(JOB)
        self.assertIn("living", queries)
        self.assertIn("kitchen", queries)
        self.assertIn("bedroom", queries)
        self.assertIn("road", queries)
        self.assertIn("exterior", queries)


if __name__ == "__main__":
    unittest.main()
