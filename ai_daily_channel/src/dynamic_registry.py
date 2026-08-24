from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse


SOURCE_STATES = {
    "candidate", "quarantined", "verified", "trusted", "degraded", "retired"
}
TOOL_STATES = {
    "candidate", "verified_free", "changed", "review_required",
    "unavailable", "archived"
}


@dataclass(frozen=True)
class PromotionEvidence:
    official_domain: bool
    identity_match: bool
    original_content: bool
    primary_evidence: bool
    successful_fetches: int


def normalize_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().strip(".")
    return host[4:] if host.startswith("www.") else host


def source_can_be_promoted(evidence: PromotionEvidence) -> bool:
    return (
        evidence.official_domain
        and evidence.identity_match
        and evidence.original_content
        and evidence.primary_evidence
        and evidence.successful_fetches >= 2
    )


def next_reverification(free_type: str, checked_at: datetime) -> datetime:
    days = {
        "open_source": 14,
        "completely_free": 7,
        "free_tier": 7,
        "credits": 1,
        "trial": 1,
        "unavailable": 30,
    }.get(free_type, 1)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    return checked_at + timedelta(days=days)


def detect_material_change(old: dict, new: dict) -> list[str]:
    protected = (
        "free_type", "price", "credit_limit", "card_required", "watermark",
        "commercial_use", "licence", "region", "export_limit", "availability"
    )
    return [key for key in protected if old.get(key) != new.get(key)]
