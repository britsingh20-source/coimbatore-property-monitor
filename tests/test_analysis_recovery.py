import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import analysis_recovery as recovery
import main
import property_analyzer
import develop_property_script as script_director
import state_store
from property_analyzer import RetryableAnalysisError

NOW = datetime(2026, 11, 5, 16, 0, tzinfo=timezone.utc)
VIDEO = {"video_id": "example1234", "title": "Villa for sale in Vadavalli", "url": "https://www.youtube.com/watch?v=example1234"}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = {"videos": {}}
        self.clock = patch.object(recovery, "now_utc", return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_rest_request_deadline_and_final_model_output(self):
        response = SimpleNamespace(ok=True, json=lambda: {"steps": [
            {"type": "user_input", "content": [{"type": "text", "text": "untrusted input"}]},
            {"type": "model_output", "content": [{"type": "text", "text": '{"is_property_listing": true}'}]},
        ]})
        with patch.dict(recovery.os.environ, {"GEMINI_API_KEY": "fake"}), patch.object(property_analyzer.requests, "post", return_value=response) as post:
            property_analyzer.analyze_property(VIDEO)
        self.assertEqual(post.call_args.kwargs["timeout"], (10, 90))
        self.assertEqual(post.call_args.kwargs["json"]["model"], property_analyzer.MODEL)
        self.assertEqual(post.call_count, 1)

    def test_rest_quota_error_is_retryable_and_redacted(self):
        response = SimpleNamespace(ok=False, status_code=429, json=lambda: {
            "error": {"message": "daily quota for secret-key projects/private-project"}
        })
        with patch.dict(recovery.os.environ, {"GEMINI_API_KEY": "secret-key"}), patch.object(property_analyzer.requests, "post", return_value=response):
            with self.assertRaises(RetryableAnalysisError) as caught:
                property_analyzer.analyze_property(VIDEO)
        self.assertNotIn("secret-key", str(caught.exception))
        self.assertNotIn("private-project", str(caught.exception))

    def test_rest_never_uses_user_input_as_analysis(self):
        response = SimpleNamespace(ok=True, json=lambda: {"steps": [
            {"type": "user_input", "content": [{"type": "text", "text": '{"is_property_listing": true}'}]}
        ]})
        with patch.dict(recovery.os.environ, {"GEMINI_API_KEY": "fake"}), patch.object(property_analyzer.requests, "post", return_value=response):
            with self.assertRaises(RetryableAnalysisError):
                property_analyzer.analyze_property(VIDEO)

    def test_primary_success_does_not_use_fallback(self):
        with patch.object(recovery, "analyze_property", return_value={"ok": True}) as call:
            self.assertEqual(recovery.analyze_with_recovery(VIDEO, self.state), {"ok": True})
        self.assertEqual(call.call_count, 1)

    def test_prompt_workflow_does_not_wait_for_optional_copywriting(self):
        with patch.dict(recovery.os.environ, {"PROPERTY_SCRIPT_MODE": "verified_template", "GEMINI_API_KEY": "fake"}), patch.object(script_director.genai, "Client") as client:
            plan = script_director.develop_property_script(
                {"location": "Karamadai", "property_type": "Villa"}, {"matched_localities": ["Karamadai"]}
            )
        client.assert_not_called()
        self.assertTrue(plan["scenes"])

    def test_transient_retry_then_success(self):
        with patch.object(recovery, "analyze_property", side_effect=[
            RetryableAnalysisError("503 high demand"), {"ok": True}
        ]) as call, patch.object(recovery.time, "sleep") as sleep:
            self.assertEqual(recovery.analyze_with_recovery(VIDEO, self.state), {"ok": True})
        self.assertEqual(call.call_count, 2)
        sleep.assert_called_once_with(5)

    def test_fallback_after_primary_outage(self):
        with patch.object(recovery, "analyze_property", side_effect=[
            RetryableAnalysisError("503 high demand"),
            RetryableAnalysisError("503 high demand"), {"ok": True}
        ]) as call, patch.object(recovery.time, "sleep"):
            self.assertEqual(recovery.analyze_with_recovery(VIDEO, self.state), {"ok": True})
        self.assertEqual(call.call_args.kwargs["model"], recovery.FALLBACK_MODEL)
        self.assertEqual(call.call_count, 3)

    def test_daily_quota_skips_primary_until_reset(self):
        with patch.object(recovery, "analyze_property", side_effect=[
            RetryableAnalysisError("429 limit 20 requests per day"), {"ok": True}, {"ok": True}
        ]) as call, patch.object(recovery.time, "sleep") as sleep:
            recovery.analyze_with_recovery(VIDEO, self.state)
            recovery.analyze_with_recovery(VIDEO, self.state)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(call.call_args.kwargs["model"], recovery.FALLBACK_MODEL)
        self.assertEqual(self.state["analysis_provider"]["models"][recovery.MODEL]["blocked_reason"], "daily_quota")
        sleep.assert_not_called()

    def test_both_models_blocked_make_no_more_calls(self):
        with patch.object(recovery, "analyze_property", side_effect=RetryableAnalysisError("429 daily quota")) as call:
            with self.assertRaises(RetryableAnalysisError):
                recovery.analyze_with_recovery(VIDEO, self.state)
            self.assertEqual(call.call_count, 2)
            with self.assertRaises(RetryableAnalysisError) as caught:
                recovery.analyze_with_recovery(VIDEO, self.state)
            self.assertEqual(call.call_count, 2)
        self.assertGreater(datetime.fromisoformat(caught.exception.retry_at), NOW)

    def test_local_budget_survives_runs(self):
        with patch.object(recovery, "DAILY_BUDGET", 1), patch.object(recovery, "analyze_property", return_value={}) as call:
            recovery.analyze_with_recovery(VIDEO, self.state)
            recovery.analyze_with_recovery(VIDEO, self.state)
            with self.assertRaises(RetryableAnalysisError):
                recovery.analyze_with_recovery(VIDEO, self.state)
        self.assertEqual(call.call_count, 2)

    def test_no_fallback_on_credentials_or_bad_data(self):
        with patch.object(recovery, "analyze_property", side_effect=RuntimeError("403 access denied")) as call:
            with self.assertRaises(RuntimeError):
                recovery.analyze_with_recovery(VIDEO, self.state)
        self.assertEqual(call.call_count, 1)

    def test_midnight_pacific_reset_handles_dst(self):
        summer = recovery.next_daily_reset(datetime(2026, 7, 1, 16, tzinfo=timezone.utc))
        winter = recovery.next_daily_reset(datetime(2026, 12, 1, 16, tzinfo=timezone.utc))
        self.assertEqual(summer.hour, 7)
        self.assertEqual(winter.hour, 8)

    def test_telegram_alert_is_throttled(self):
        response = SimpleNamespace(ok=True, json=lambda: {"ok": True})
        with patch.dict(recovery.os.environ, {"TELEGRAM_BOT_TOKEN": "fake", "TELEGRAM_CHAT_ID": "123"}), patch.object(recovery.requests, "post", return_value=response) as post:
            recovery.notify_blocked(self.state, "daily quota")
            recovery.notify_blocked(self.state, "daily quota")
        self.assertEqual(post.call_count, 1)
        self.assertIn("No new prompt delivery is being claimed", post.call_args.kwargs["json"]["text"])

    def test_failed_alert_is_not_recorded_as_delivered(self):
        with patch.dict(recovery.os.environ, {"TELEGRAM_BOT_TOKEN": "fake", "TELEGRAM_CHAT_ID": "123"}), patch.object(recovery.requests, "post", side_effect=RuntimeError("network")):
            recovery.notify_blocked(self.state, "daily quota")
        self.assertNotIn("last_alert_at", self.state.get("analysis_provider", {}))

    def test_video_cooldown_is_honored(self):
        state_store.register_videos(self.state, [VIDEO])
        row = self.state["videos"][VIDEO["video_id"]]
        row.update(status="retry_pending", last_error="503 high demand",
                   next_retry_at=(state_store.utc_now() + timedelta(hours=1)).isoformat())
        self.assertFalse(state_store.eligible(self.state, VIDEO))

    def test_monitor_raises_and_preserves_retry_when_provider_blocked(self):
        blocked = RetryableAnalysisError("All models are paused")
        blocked.retry_at = (NOW + timedelta(hours=5)).isoformat()
        with patch.object(main, "load_state", return_value=self.state), patch.object(main, "monitor_channels", return_value=[VIDEO]), patch.object(main, "legacy_retry_videos", return_value=[]), patch.object(main, "build_analysis_queue", return_value=[VIDEO]), patch.object(main, "analyze_with_recovery", side_effect=blocked), patch.object(main, "save_state"), patch.object(main, "notify_blocked") as notify, patch.object(main, "build_video_job") as build:
            with self.assertRaises(RuntimeError):
                main.run()
        notify.assert_called_once()
        build.assert_not_called()
        row = self.state["videos"][VIDEO["video_id"]]
        self.assertEqual(row["status"], "retry_pending")
        self.assertEqual(row["next_retry_at"], blocked.retry_at)


if __name__ == "__main__":
    unittest.main()
