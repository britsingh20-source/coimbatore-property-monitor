import unittest
import state_store


class StateStoreTests(unittest.TestCase):
    def test_failed_items_remain_retryable(self):
        state = {"videos": {}}
        video = {"video_id": "abc"}
        state_store.register_videos(state, [video])
        state_store.mark_failure(state, "abc", RuntimeError("429 quota"))
        self.assertEqual(state["videos"]["abc"]["status"], "retry_pending")

    def test_success_is_not_eligible(self):
        state = {"videos": {}}
        video = {"video_id": "abc"}
        state_store.register_videos(state, [video])
        state_store.mark_success(state, "abc", True)
        self.assertFalse(state_store.eligible(state, video))


if __name__ == "__main__":
    unittest.main()
