import unittest

from map_assets import geocode_candidates, geocode_query, location_label


class MapAssetsTests(unittest.TestCase):
    def test_query_adds_geographic_context(self):
        query = geocode_query({"property_location": "Pattanam"})
        self.assertEqual(query, "Pattanam, Coimbatore, Tamil Nadu, India")

    def test_nggo_colony_is_the_target_not_pattanam_or_nearby_area(self):
        job = {
            "property_location": "Near Thudiyalur, NGGO Colony, Mettupalayam Road, Coimbatore, Tamil Nadu"
        }
        self.assertEqual(location_label(job), "NGGO Colony")
        self.assertEqual(
            geocode_query(job),
            "NGGO Colony, Coimbatore, Tamil Nadu, India",
        )
        self.assertTrue(all("Pattanam" not in query for query in geocode_candidates(job)))

    def test_distance_prefix_is_removed_from_pattanam_label(self):
        job = {"property_location": "1.50 kms from Pattanam, Coimbatore, Tamil Nadu"}
        self.assertEqual(location_label(job), "Pattanam")

    def test_query_does_not_duplicate_coimbatore(self):
        candidates = geocode_candidates({"property_location": "Pattanam, Coimbatore"})
        self.assertTrue(all("Coimbatore, Coimbatore" not in query for query in candidates))


if __name__ == "__main__":
    unittest.main()
