import unittest
from unittest.mock import patch

import strict_broll_pool as pool


class StrictBrollPoolTests(unittest.TestCase):
    def setUp(self):
        pool.SESSION_USED_SOURCES.clear()

    def _item(self, provider: str, slug: str, **extra):
        return {
            "provider": provider,
            "source_url": f"https://example.com/{slug}",
            "download_url": f"https://cdn.example.com/{slug}.mp4",
            "media_kind": "video",
            **extra,
        }

    def test_rejects_indian_flag_even_for_location(self):
        item = self._item("Pexels", "indian-flag-waving")
        self.assertFalse(pool.strict_candidate_allowed(item, "location"))

    def test_rejects_food_even_for_kitchen(self):
        item = self._item("Pixabay", "chef-cooking-food-in-kitchen", tags="food, cooking, kitchen")
        self.assertFalse(pool.strict_candidate_allowed(item, "kitchen"))

    def test_rejects_city_highway_for_road(self):
        item = self._item("Pexels", "busy-city-highway-traffic-road")
        self.assertFalse(pool.strict_candidate_allowed(item, "road"))

    def test_accepts_residential_road(self):
        item = self._item("Pixabay", "quiet-residential-road-houses", tags="residential road, houses, street")
        self.assertTrue(pool.strict_candidate_allowed(item, "road"))

    def test_accepts_empty_modular_kitchen(self):
        item = self._item("Pexels", "modern-home-modular-kitchen-empty", title="Modern home modular kitchen")
        self.assertTrue(pool.strict_candidate_allowed(item, "kitchen"))

    @patch.object(pool, "search_pixabay_videos")
    @patch.object(pool, "search_pexels_videos")
    def test_combines_both_providers_before_ranking(self, pexels, pixabay):
        pexels.return_value = [
            self._item("Pexels", "generic-residential-road", title="Residential road"),
            self._item("Pexels", "indian-flag-residential", title="Indian flag"),
        ]
        pixabay.return_value = [
            self._item("Pixabay", "quiet-residential-road-houses", tags="residential road houses street"),
        ]

        result = pool.combined_provider_candidates("road", ["residential road"], 2, set())

        self.assertEqual(2, len(result))
        self.assertEqual("Pixabay", result[0]["provider"])
        self.assertNotIn("flag", " ".join(row["source_url"] for row in result))
        pexels.assert_called()
        pixabay.assert_called()

    def test_requires_provider_metadata_to_match_scene(self):
        # The search query is not enough. An opaque/non-property result must not
        # pass merely because it was returned by a property search.
        item = self._item("Pexels", "123456789", search_query="Indian villa exterior")
        self.assertFalse(pool.strict_candidate_allowed(item, "exterior"))


if __name__ == "__main__":
    unittest.main()
