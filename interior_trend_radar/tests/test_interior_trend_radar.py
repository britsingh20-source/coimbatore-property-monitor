import json
import tempfile
import unittest
from pathlib import Path

from interior_trend_radar.analyzer import _fallback
from interior_trend_radar.telegram_pack import format_pack


class InteriorTrendRadarTests(unittest.TestCase):
    def test_fallback_has_four_vertical_prompts(self):
        job = _fallback([{"title": "Kitchen idea", "url": "https://example.com/v"}], {})
        self.assertEqual(4, len(job["google_video_prompts"]))
        self.assertTrue(all("9:16" in prompt for prompt in job["google_video_prompts"]))

    def test_pack_contains_script_and_sources(self):
        job = _fallback([{"title": "Kitchen idea", "url": "https://example.com/v"}], {})
        text = format_pack(job)
        self.assertIn("ORIGINAL TAMIL-ENGLISH CONTENT", text)
        self.assertIn("https://example.com/v", text)


if __name__ == "__main__": unittest.main()
