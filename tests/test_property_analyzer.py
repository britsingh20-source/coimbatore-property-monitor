import unittest

from property_analyzer import _is_retryable_error


class PropertyAnalyzerTests(unittest.TestCase):
    def test_provider_high_demand_is_retryable(self):
        self.assertTrue(_is_retryable_error("500 api_error: currently experiencing high demand"))

    def test_daily_quota_is_retryable(self):
        self.assertTrue(_is_retryable_error("429 RESOURCE_EXHAUSTED quota exceeded"))

    def test_invalid_model_response_is_not_retryable(self):
        self.assertFalse(_is_retryable_error("response did not contain a JSON object"))


if __name__ == "__main__":
    unittest.main()
