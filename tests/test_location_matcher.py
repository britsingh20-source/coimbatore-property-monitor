import unittest
from location_matcher import match_location


class LocationMatcherTests(unittest.TestCase):
    def test_vadavalli_english_aliases(self):
        for title in (
            "2BHK in Vadavalli, Coimbatore",
            "Villa for sale in Vadavali",
            "House at Vada Valli",
            "Property in Wadawalli",
        ):
            with self.subTest(title=title):
                result = match_location(title)
                self.assertTrue(result["is_target_location"])
                self.assertEqual(result["matched_localities"], ["Vadavalli"])

    def test_vadavalli_tamil_alias(self):
        result = match_location("வடவள்ளியில் வீடு விற்பனைக்கு")
        self.assertTrue(result["is_target_location"])
        self.assertEqual(result["matched_localities"], ["Vadavalli"])

    def test_city_only_is_accepted_without_area_filter(self):
        result = match_location("House somewhere in Coimbatore")
        self.assertTrue(result["is_target_location"])
        self.assertTrue(result["city_match"])

    def test_all_configured_areas_are_accepted(self):
        for title in (
            "Villa in Saravanampatti",
            "House for sale at Idigarai",
            "3BHK Karamadai",
            "Plot in Periyanaicken Palayam",
            "Home at Mettupalayam",
            "Land on Annur to Mettupalayam Road",
            "Villa at Thudiyalur",
            "House in Somayampalayam",
            "Property at Bommanampalayam",
        ):
            with self.subTest(title=title):
                result = match_location(title)
                self.assertTrue(result["is_target_location"])

    def test_unknown_area_is_not_blocked(self):
        result = match_location("Villa for sale in Somayampalayam")
        self.assertTrue(result["is_target_location"])
        self.assertFalse(result["weekly_focus_active"])


if __name__ == "__main__":
    unittest.main()
