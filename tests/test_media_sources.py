import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from media_sources import (
    _allowed_scene_visual, _allowed_visual, _own_footage_folder,
    _own_footage_prefixes, _scene_video_queries, search_pexels_videos,
    source_property_media, source_property_videos,
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

    def test_own_footage_folder_maps_villa_types_and_skips_plots(self):
        self.assertEqual(_own_footage_folder("Independent House / Duplex Villa"), "villas")
        self.assertEqual(_own_footage_folder("3BHK House"), "villas")
        self.assertIsNone(_own_footage_folder("Residential Plot"))
        self.assertEqual(_own_footage_prefixes("Villa", "interior"),
                          ["villas/bedroom/", "villas/dining & Kitchen/", "villas/living_room/"])
        self.assertEqual(_own_footage_prefixes("Villa", "road"), ["villas/Road/"])
        self.assertEqual(_own_footage_prefixes("Villa", "location"), [])  # no filmed folder for this scene
        self.assertEqual(_own_footage_prefixes("Plot", "exterior"), [])  # plots have no rooms

    @patch("media_sources.download_media", return_value=[])
    @patch("media_sources.search_pexels_videos")
    @patch("media_sources.search_pixabay_videos", return_value=[])
    @patch("media_sources.get_own_footage_clips")
    def test_own_footage_is_preferred_over_stock_apis(self, own_footage, pixabay, pexels, _download):
        own_footage.side_effect = lambda scene, property_type, limit: (
            [{"local_file": "clip.mp4", "scene": scene}] * limit if scene == "exterior" else []
        )
        pexels.return_value = []
        source_property_videos({
            "video_id": "villa-example",
            "property_location": "Vadavalli, Coimbatore",
            "property": {"property_type": "Villa"},
        }, per_scene=2)
        exterior_calls = [c for c in pixabay.call_args_list if "exterior" in c.args[0].lower()]
        self.assertEqual(exterior_calls, [])  # exterior fully covered by own footage, no API call
        self.assertTrue(pixabay.called)  # other scenes without own footage still search

    def test_r2_bucket_name_blank_does_not_silently_pass_through(self):
        """Regression test: the workflow previously read R2_BUCKET_NAME via
        ${{ vars.R2_BUCKET_NAME }} while the secret actually lived under Secrets,
        so the env var was PRESENT but EMPTY at runtime. os.environ.get(name, default)
        only falls back to `default` when the key is entirely absent, so a blank value
        slipped straight through to boto3 as Bucket="", and the bare except around it
        swallowed the resulting failure silently. Confirms the fixed accessor treats
        blank the same as unset."""
        from media_sources import _r2_bucket_name

        with patch.dict(os.environ, {"R2_BUCKET_NAME": ""}, clear=True):
            self.assertEqual(_r2_bucket_name(), "github")  # falls back, not ""

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_r2_bucket_name(), "github")  # unset -> same fallback

        with patch.dict(os.environ, {"R2_BUCKET_NAME": "my-real-bucket"}, clear=True):
            self.assertEqual(_r2_bucket_name(), "my-real-bucket")

    def test_generate_video_workflow_reads_r2_bucket_name_from_secrets(self):
        """Regression test for the actual root cause: the workflow YAML must read
        R2_BUCKET_NAME via secrets.*, matching where it's actually set in this repo
        (Settings -> Secrets and variables -> Actions -> Secrets), not vars.*."""
        workflow = Path(".github/workflows/generate-video.yml").read_text(encoding="utf-8")
        self.assertIn("R2_BUCKET_NAME: ${{ secrets.R2_BUCKET_NAME }}", workflow)
        self.assertNotIn("vars.R2_BUCKET_NAME", workflow)


if __name__ == "__main__":
    unittest.main()
