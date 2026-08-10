import unittest

from social_caption import build_caption


class SocialCaptionTests(unittest.TestCase):
    def test_caption_has_exactly_three_hashtags_and_verified_facts(self):
        job = {
            "property_location": "Saravanampatti, Coimbatore",
            "property": {
                "property_type": "2 BHK Villa",
                "bhk": "2 BHK",
                "land_area": "2.5 cents",
                "built_up_area": "1000 sq.ft",
                "price": "₹55 lakh",
                "facing": "North",
                "road_width": "23 ft",
                "approval": "DTCP approved",
            },
        }
        caption = build_caption(job)
        self.assertIn("Saravanampatti", caption)
        self.assertIn("₹55 lakh", caption)
        self.assertEqual(caption.count("#"), 3)
        self.assertIn("Verify documents", caption)

    def test_missing_values_are_not_printed(self):
        job = {
            "property_location": "Coimbatore",
            "property": {"property_type": "Plot", "price": "NOT SPECIFIED"},
        }
        caption = build_caption(job)
        self.assertNotIn("NOT SPECIFIED", caption)
        self.assertNotIn("Price:", caption)
        self.assertEqual(caption.count("#"), 3)


if __name__ == "__main__":
    unittest.main()
