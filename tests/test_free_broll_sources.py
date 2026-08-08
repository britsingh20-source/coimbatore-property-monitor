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


def item(provider: str, identity: str, **extra) -> dict:
    return {
        "provider": provider,
        "source_url": f"https://example.com/{identity}",
        "download_url": f"https://cdn.example.com/{identity}.mp4",
        "license": f"{provider} License",
        "media_kind": "video",
        **extra,
    }


class FreeBrollPriorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.old_gemini = os.environ.pop("GEMINI_API_KEY", None)
        broll.SESSION_USED_SOURCES.clear()

    def tearDown(self):
        if self.old_gemini is not None:
            os.environ["GEMINI_API_KEY"] = self.old_gemini
        else:
            os.environ.pop("GEMINI_API_KEY", None)
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
    def test_both_free_providers_are_searched_before_selection(self, _queries, download, pexels, pixabay, library, own, _cache):
        download.side_effect = self._download_passthrough
        pexels.return_value = [item("Pexels", f"p{i}-residential-road", title="residential road") for i in range(5)]
        pixabay.return_value = [item("Pixabay", f"x{i}-residential-road", title="residential road") for i in range(5)]

        result = broll.source_property_videos_free_first(JOB, per_scene=4)

        self.assertEqual(4, len(result))
        self.assertTrue(pexels.called)
        self.assertTrue(pixabay.called)
        library.assert_not_called()
        own.assert_not_called()

    @patch.object(broll, "add_to_library")
    @patch.object(broll, "get_own_footage_clips")
    @patch.object(broll, "get_library_clips")
    @patch.object(broll, "search_pixabay_videos")
    @patch.object(broll, "search_pexels_videos")
    @patch.object(broll, "download_media")
    @patch.object(broll, "_category_queries", return_value={"exterior": ["house query"]})
    def test_pixabay_can_outrank_pexels(self, _queries, download, pexels, pixabay, library, own, _cache):
        download.side_effect = self._download_passthrough
        pexels.return_value = [
            item("Pexels", f"p{i}-house", title="luxury apartment house exterior", width=1920, height=1080)
            for i in range(4)
        ]
        pixabay.return_value = [
            item("Pixabay", f"x{i}-indian-house", title="Tamil Nadu independent house villa exterior", width=1080, height=1920)
            for i in range(4)
        ]

        result = broll.source_property_videos_free_first(JOB, per_scene=2)

        self.assertEqual(["Pixabay", "Pixabay"], [row["provider"] for row in result])
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
        library.return_value = [item("Library cache (R2)", "library-residential-road", title="residential road")]
        own.return_value = [
            item("Advertiser supplied (own b-roll)", "own-road-1", title="residential road"),
            item("Advertiser supplied (own b-roll)", "own-road-2", title="residential road"),
        ]

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

    def test_indian_independent_house_ranks_above_foreign_generic_house(self):
        indian = item(
            "Pexels",
            "coimbatore-independent-house",
            alt="Modern Indian independent house exterior Tamil Nadu residential",
            width=1080,
            height=1920,
            duration_seconds=8,
        )
        generic = item(
            "Pexels",
            "generic-house",
            alt="Luxury European apartment house exterior",
            width=1920,
            height=1080,
            duration_seconds=8,
        )
        self.assertGreater(broll._quality_score(indian, "exterior"), broll._quality_score(generic, "exterior"))

    def test_people_food_flag_and_camera_are_hard_rejected(self):
        bad = [
            item("Pexels", "woman-kitchen", alt="woman cooking food in home kitchen"),
            item("Pexels", "india-flag", alt="Indian flag near residential road"),
            item("Pexels", "camera-man", alt="man holding camera outside house"),
        ]
        self.assertTrue(all(not broll._stock_allowed(row, "kitchen" if "kitchen" in row.get("alt", "") else "exterior") for row in bad))

    def test_scene_requires_provider_metadata_not_only_search_query(self):
        row = item("Pexels", "generic", search_query="Coimbatore Tamil Nadu residential road")
        self.assertFalse(broll._stock_allowed(row, "road"))
        self.assertEqual(0, sum(
            value for term, value in broll.REGIONAL_TERMS.items()
            if term in broll._metadata_text(row)
        ))


if __name__ == "__main__":
    unittest.main()
