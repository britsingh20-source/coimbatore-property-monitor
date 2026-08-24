import unittest
from datetime import datetime, timezone

from ai_daily_channel.src.dynamic_registry import (
    PromotionEvidence,
    detect_material_change,
    next_reverification,
    normalize_domain,
    source_can_be_promoted,
)


class DynamicRegistryTests(unittest.TestCase):
    def test_source_requires_primary_evidence(self):
        evidence = PromotionEvidence(True, True, True, False, 3)
        self.assertFalse(source_can_be_promoted(evidence))

    def test_source_requires_repeat_fetch(self):
        evidence = PromotionEvidence(True, True, True, True, 1)
        self.assertFalse(source_can_be_promoted(evidence))

    def test_valid_source_promotes(self):
        evidence = PromotionEvidence(True, True, True, True, 2)
        self.assertTrue(source_can_be_promoted(evidence))

    def test_free_tier_rechecks_weekly(self):
        checked = datetime(2026, 8, 24, tzinfo=timezone.utc)
        self.assertEqual((next_reverification("free_tier", checked) - checked).days, 7)

    def test_material_free_claim_change(self):
        changes = detect_material_change(
            {"card_required": False, "watermark": False},
            {"card_required": True, "watermark": False},
        )
        self.assertEqual(changes, ["card_required"])

    def test_domain_normalization(self):
        self.assertEqual(normalize_domain("https://www.example.ai/news"), "example.ai")


if __name__ == "__main__":
    unittest.main()
