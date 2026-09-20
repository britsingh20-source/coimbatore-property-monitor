import unittest

from location_matcher import match_location


class LocationMatcherTests(unittest.TestCase):
    def test_english_alias(self):
        result = match_location("2BHK in Saravanampatti, Coimbatore")
        self.assertTrue(result["is_target_location"])
        self.assertIn("Saravanampatti", result["matched_localities"])

    def test_tamil_alias(self):
        result = match_location("இடிகரையில் கோவையில் வீடு விற்பனைக்கு")
        self.assertTrue(result["is_target_location"])
        self.assertIn("Idigarai", result["matched_localities"])

    def test_city_only_requires_review(self):
        result = match_location("House somewhere in Coimbatore")
        self.assertFalse(result["is_target_location"])
        self.assertTrue(result["city_match"])

    def test_all_permanent_focus_areas(self):
        cases = {
            "New villa at Saranampatti": "Saravanampatti",
            "House for sale at Edigarai": "Idigarai",
            "3BHK Karamadai": "Karamadai",
            "Plot in Periyanaicken Palayam": "Periyanaickenpalayam",
            "Home at Mettupalayam": "Mettupalayam",
            "Land on Annur to Mettupalayam Road": "Mettupalayam–Annur Road",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                result = match_location(title)
                self.assertTrue(result["is_target_location"])
                self.assertIn(expected, result["matched_localities"])

    def test_old_coimbatore_areas_are_rejected(self):
        result = match_location("Villa for sale in Vadavalli, Coimbatore")
        self.assertFalse(result["is_target_location"])
        self.assertEqual(result["matched_localities"], [])

    def test_focus_belt_micro_localities_keep_their_actual_name(self):
        cases = {
            "Villa in மணிகரம்பாளையம்": "Maniyakarampalayam",
            "Plot at Athipalayam Pirivu": "Athipalayam",
            "House in Urumandampalayam": "Urumandampalayam",
            "3BHK Teachers Colony": "Teachers Colony",
            "Land near Saandhimedu": "Shanthimedu",
            "Site in Narasimhanagar Palayam": "Narasimhanaickenpalayam",
            "Villa at Veeramandi Pirivu": "Veerapandi Pirivu",
            "Plot at NGGO Colony": "NGGO Colony",
            "Land at Pannirmadai": "Pannimadai",
            "House at Bellathi": "Bellathi",
            "Site in Chikkarampalayam": "Chikkarampalayam",
            "Villa at Kannarpalayam": "Kannarpalayam",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                result = match_location(title)
                self.assertTrue(result["is_target_location"])
                self.assertIn(expected, result["matched_localities"])


if __name__ == "__main__":
    unittest.main()
