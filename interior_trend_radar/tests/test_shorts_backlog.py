import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from interior_trend_radar.shorts_backlog import discover_shorts, process


class ShortsBacklogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.config, self.state, self.output = [str(root / name) for name in ("config.json", "state.json", "pack.json")]
        Path(self.config).write_text(json.dumps({"shorts_backlog": {"enabled": True, "handle": "havenhaus1", "daily_limit": 2}}))
        self.env = patch.dict(os.environ, {"YOUTUBE_API_KEY": "test", "TELEGRAM_BOT_TOKEN": "test", "TELEGRAM_CHAT_ID": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.candidates = [{"video_id": str(i), "url": f"https://www.youtube.com/shorts/{i}"} for i in range(5)]
        self.discover = MagicMock(return_value=self.candidates)
        self.analyze = MagicMock(return_value={})
        self.send = MagicMock()
        self.today = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)

    def run_backlog(self, deliver=True, now=None):
        return process(self.config, self.state, self.output, deliver, discover=self.discover,
                       analyze=self.analyze, send=self.send, now=now or self.today)

    def test_two_daily_even_with_manual_reruns_and_resume_next_day(self):
        self.run_backlog()
        self.run_backlog()
        self.assertEqual(2, self.send.call_count)
        self.assertEqual(["0", "1"], [call.args[1]["video_id"] for call in self.send.call_args_list])
        # 18:30 UTC is already tomorrow in India, so the allowance resets.
        self.run_backlog(now=datetime(2026, 10, 23, 18, 30, tzinfo=timezone.utc))
        self.assertEqual(["0", "1", "2", "3"], [call.args[1]["video_id"] for call in self.send.call_args_list])

    def test_first_success_survives_second_analysis_failure(self):
        self.analyze.side_effect = [{}, RuntimeError("analysis failed")]
        with self.assertRaisesRegex(RuntimeError, "analysis failed"):
            self.run_backlog()
        state = json.loads(Path(self.state).read_text())
        self.assertEqual(["0"], [item["video_id"] for item in state["history"]])
        self.assertEqual("1", state["queue"][0]["video_id"])
        self.analyze.side_effect = None
        self.run_backlog()
        self.assertEqual(2, self.send.call_count)

    def test_uncertain_delivery_blocks_duplicates(self):
        self.send.side_effect = RuntimeError("timeout")
        with self.assertRaisesRegex(RuntimeError, "timeout"):
            self.run_backlog()
        with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
            self.run_backlog()
        self.assertEqual(1, self.send.call_count)
        self.assertEqual([], json.loads(Path(self.state).read_text())["history"])

    def test_preview_never_consumes_or_sends(self):
        self.run_backlog(deliver=False)
        self.send.assert_not_called()
        self.assertFalse(Path(self.state).exists())

    @patch("interior_trend_radar.shorts_backlog._resolve_handle", return_value="channel")
    @patch("interior_trend_radar.shorts_backlog._json")
    @patch("yt_dlp.YoutubeDL")
    def test_only_shorts_tab_with_full_history_sorted_by_api_date(self, youtube, api, resolve):
        youtube.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [{"id": "new"}, {"id": "old"}, {"id": "old"}]}
        api.return_value = {"items": [
            {"id": "new", "snippet": {"channelId": "channel", "publishedAt": "2026-10-23T00:00:00Z"}},
            {"id": "old", "snippet": {"channelId": "channel", "publishedAt": "2020-01-01T00:00:00Z"}},
        ]}
        candidates = discover_shorts("havenhaus1", "test")
        self.assertEqual(["old", "new"], [item["video_id"] for item in candidates])
        youtube.return_value.__enter__.return_value.extract_info.assert_called_once_with(
            "https://www.youtube.com/@havenhaus1/shorts", download=False)
        self.assertTrue(all("/shorts/" in item["url"] for item in candidates))
        api.return_value["items"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            discover_shorts("havenhaus1", "test")


if __name__ == "__main__":
    unittest.main()
