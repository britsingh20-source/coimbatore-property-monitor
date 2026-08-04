import unittest

from location_matcher import match_location


class LocationMatcherTests(unittest.TestCase):
    def test_english_alias(self):
        result = match_location("2BHK in Saravanampatti, Coimbatore")
        self.assertTrue(result["is_target_location"])
        self.assertIn("Saravanampatti", result["matched_localities"])

    def test_tamil_alias(self):
        result = match_location("வடவள்ளி கோவையில் வீடு விற்பனைக்கு")
        self.assertTrue(result["is_target_location"])
        self.assertIn("Vadavalli", result["matched_localities"])

    def test_city_only_requires_review(self):
        result = match_location("House somewhere in Coimbatore")
        self.assertFalse(result["is_target_location"])
        self.assertTrue(result["city_match"])


if __name__ == "__main__":
    unittest.main()
