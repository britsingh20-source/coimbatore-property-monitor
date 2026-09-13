import unittest

import cv2
import numpy as np

from property_source_finder import (
    _classify_poster,
    _page_facts_score,
    _portal_for_url,
    _public_phone,
    format_telegram_report,
    image_similarity,
    ListingMatch,
)


class PropertySourceFinderTests(unittest.TestCase):
    def setUp(self):
        self.job = {
            "video_id": "abc123",
            "property_location": "Thudiyalur, Coimbatore",
            "property": {
                "property_type": "Independent House",
                "bhk": "3 BHK",
                "land_area": "2.5 cents",
                "built_up_area": "1650 sq.ft",
                "price": "73 lakh",
                "facing": "North",
            },
        }

    def test_portal_detection(self):
        self.assertEqual(_portal_for_url("https://housing.com/in/buy/x"), "housing")
        self.assertEqual(_portal_for_url("https://www.99acres.com/x"), "99acres")
        self.assertEqual(_portal_for_url("https://www.magicbricks.com/x"), "magicbricks")
        self.assertEqual(_portal_for_url("https://www.realestateindia.com/x"), "realestateindia")
        self.assertIsNone(_portal_for_url("https://example.com/x"))

    def test_owner_broker_builder_classification(self):
        self.assertEqual(_classify_poster("This property is posted by owner"), "OWNER")
        self.assertEqual(_classify_poster("Posted by Agent ABC Properties"), "BROKER")
        self.assertEqual(_classify_poster("Posted by Builder XYZ Developers"), "BUILDER")

    def test_public_phone_only_complete_number(self):
        text = "Contact owner 98765 43210 for this house"
        self.assertEqual(_public_phone(text, "housing"), "9876543210")
        self.assertEqual(_public_phone("Contact 98765XXXXX", "housing"), "")
        self.assertEqual(_public_phone("Customer care 9876543210", "housing"), "")

    def test_fact_score_rewards_exact_property_details(self):
        score = _page_facts_score(
            self.job,
            "3 BHK house in Thudiyalur Coimbatore, 2.5 cents, 1650 sq ft, 73 lakh, North facing",
        )
        self.assertGreater(score, 0.8)

    def test_image_similarity_identical_is_high(self):
        image = np.zeros((300, 400, 3), dtype=np.uint8)
        cv2.rectangle(image, (50, 50), (350, 250), (255, 255, 255), 5)
        cv2.line(image, (50, 150), (350, 150), (255, 255, 255), 3)
        self.assertGreater(image_similarity(image, image.copy()), 0.85)

    def test_telegram_report_never_claims_protected_phone(self):
        match = ListingMatch(
            portal="99acres",
            url="https://www.99acres.com/example",
            poster_type="OWNER",
            visual_score=0.9,
            fact_score=0.9,
            overall_score=0.9,
        )
        report = format_telegram_report(self.job, [match])
        self.assertIn("protected/not publicly exposed", report)
        self.assertIn("Open exact listing", report)


if __name__ == "__main__":
    unittest.main()
