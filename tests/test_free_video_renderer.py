import unittest

from free_video_renderer import _timestamp, caption_lines


class FreeRendererTests(unittest.TestCase):
    def test_timestamp_handles_minutes(self):
        self.assertEqual(_timestamp(66), "00:01:06,000")

    def test_caption_count_matches_images(self):
        job = {
            "property_location": "Vadavalli",
            "verified_facts": "3BHK, 4 cents, north facing",
            "disclosure": "Verify all details",
        }
        self.assertEqual(len(caption_lines(job, 5)), 5)


if __name__ == "__main__":
    unittest.main()
