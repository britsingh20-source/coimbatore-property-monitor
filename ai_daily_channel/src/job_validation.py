from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

LANGUAGES = {"ta", "hi", "en"}
STATUSES = {
    "discovered", "verified", "pack_ready", "pack_delivered",
    "final_uploaded", "validated", "correction_required",
    "approved", "publishing", "published",
}
VERIFIED_STATUSES = STATUSES - {"discovered"}


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_job(job: dict) -> list[str]:
    errors: list[str] = []
    job_id = str(job.get("job_id", ""))
    if not re.fullmatch(r"[a-z0-9-]{8,80}", job_id):
        errors.append("job_id must be 8-80 lowercase letters, digits or hyphens")

    if job.get("language") not in LANGUAGES:
        errors.append("language must be ta, hi or en")
    if job.get("status") not in STATUSES:
        errors.append("invalid status")

    tool = job.get("tool") or {}
    for key in ("name", "official_url", "free_claim", "verified_at", "evidence"):
        if not tool.get(key):
            errors.append(f"tool.{key} is required")
    if tool.get("official_url") and not _is_url(tool["official_url"]):
        errors.append("tool.official_url must be http(s)")
    try:
        datetime.fromisoformat(str(tool.get("verified_at", "")).replace("Z", "+00:00"))
    except ValueError:
        errors.append("tool.verified_at must be ISO-8601")
    evidence = tool.get("evidence") or []
    if not evidence:
        errors.append("at least one evidence item is required")
    for index, item in enumerate(evidence):
        if not _is_url(str(item.get("url", ""))) or not item.get("claim"):
            errors.append(f"tool.evidence[{index}] needs url and claim")

    if job.get("status") in VERIFIED_STATUSES:
        for key in ("card_required", "watermark", "commercial_use"):
            if key not in tool:
                errors.append(f"verified jobs require tool.{key}")

    script = job.get("script") or {}
    if len(str(script.get("exact_text", "")).strip()) < 40:
        errors.append("script.exact_text is too short")
    if not script.get("segments"):
        errors.append("script.segments is required")

    prompts = job.get("prompts") or {}
    for key in ("cinematic_hook", "ai_broll"):
        if len(str(prompts.get(key, "")).strip()) < 80:
            errors.append(f"prompts.{key} is missing or too short")

    publishing = job.get("publishing") or {}
    hashtags = publishing.get("hashtags") or []
    if len(hashtags) != 3:
        errors.append("publishing.hashtags must contain exactly three entries")

    return errors


def main(path: str) -> int:
    job = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_job(job)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(f"VALID: {job['job_id']}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1]))
