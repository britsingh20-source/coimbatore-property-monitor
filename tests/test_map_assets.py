import unittest

from map_assets import geocode_query


class MapAssetsTests(unittest.TestCase):
    def test_query_adds_geographic_context(self):
        query = geocode_query({"property_location": "Pattanam"})
        self.assertEqual(query, "Pattanam, Coimbatore, Tamil Nadu, India")

    def test_query_does_not_duplicate_coimbatore(self):
        query = geocode_query({"property_location": "Pattanam, Coimbatore"})
        self.assertEqual(query, "Pattanam, Coimbatore, Tamil Nadu, India")


if __name__ == "__main__":
    unittest.main()
