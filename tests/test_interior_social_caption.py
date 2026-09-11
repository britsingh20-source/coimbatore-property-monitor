import unittest

from interior_social_autopilot import FORBIDDEN_PUBLIC_WORDING, _clean_hashtags


class InteriorSocialCaptionTests(unittest.TestCase):
    def test_hashtags_are_exactly_topic_brand_and_location(self):
        tags = _clean_hashtags(
            ["#SlidingTVWall", "#HomeDecor", "#AIReferenceVideo"],
            "Sliding TV wall",
        )
        self.assertEqual(
            tags,
            ["#SlidingTVWall", "#OliveTreeInteriors", "#CoimbatoreInteriors"],
        )

    def test_forbidden_public_wording_is_blocked(self):
        for text in (
            "This is a reference video",
            "Inspired by another creator",
            "AI-generated interior footage",
            "Artificial intelligence reconstruction",
        ):
            with self.subTest(text=text):
                self.assertRegex(text, FORBIDDEN_PUBLIC_WORDING)


if __name__ == "__main__":
    unittest.main()
