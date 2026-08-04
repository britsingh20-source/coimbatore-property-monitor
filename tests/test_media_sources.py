import os
import unittest
from unittest.mock import patch

from media_sources import search_pexels_videos


class MediaSourceTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_pexels_video_search_is_optional(self):
        self.assertEqual(search_pexels_videos("house"), [])


if __name__ == "__main__":
    unittest.main()
