"""Bounded video-analysis recovery and persistent provider quota protection."""
import os
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from property_analyzer import MODEL, RetryableAnalysisError, analyze_property

PACIFIC = ZoneInfo("America/Los_Angeles")
FALLBACK_MODEL = os.environ.get("GEMINI_ANALYSIS_FALLBACK_MODEL", "gemini-3.6-flash")
# Zero means no additional local daily cap. Real provider quotas/cooldowns still apply.
DAILY_BUDGET = max(0, int(os.environ.get("PROPERTY_ANALYSIS_DAILY_BUDGET", "0")))
TRANSIENT_RETRY_SECONDS = 5


def now_utc():
    return datetime.now(timezone.utc)


def next_daily_reset(now):
    local = now.astimezone(PACIFIC)
    tomorrow = local.date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), PACIFIC).astimezone(timezone.utc) + timedelta(minutes=2)


def _daily_quota(message):
    lower = message.lower()
    return any(term in lower for term in ("per day", "per_day", "daily", "requestsperday", "rpd"))


def _rate_limit(message):
    lower = message.lower()
    return any(term in lower for term in ("429", "quota", "resource_exhausted", "too_many_requests"))


def _record(state, model, now):
    records = state.setdefault("analysis_provider", {}).setdefault("models", {})
    record = records.setdefault(model, {})
    day = now.astimezone(PACIFIC).date().isoformat()
    if record.get("budget_day") != day:
        record.update(budget_day=day, requests=0)
    # A retired/reconfigured local cap must not leave a stale all-day lock.
    # Never clear actual provider quota or outage cooldowns here.
    if record.get("blocked_reason") == "daily_budget" and (
        not DAILY_BUDGET or record["requests"] < DAILY_BUDGET
    ):
        record.pop("blocked_reason", None)
        record.pop("blocked_until", None)
    return record


def _retry_time(record):
    value = record.get("blocked_until")
    return datetime.fromisoformat(value) if value else None


def _block(record, message, now):
    if _daily_quota(message):
        until = next_daily_reset(now)
        reason = "daily_quota"
    elif _rate_limit(message):
        until = now + timedelta(minutes=5)
        reason = "rate_limit"
    else:
        until = now + timedelta(minutes=10)
        reason = "provider_unavailable"
    record.update(blocked_until=until.isoformat(), blocked_reason=reason, last_error=message[:1000])
    return until


def analyze_with_recovery(video, state):
    """At most two primary calls and one fallback call, with persistent cooldowns."""
    models = list(dict.fromkeys(model for model in (MODEL, FALLBACK_MODEL) if model))
    retry_times = []
    reasons = []
    for model_index, model in enumerate(models):
        now = now_utc()
        record = _record(state, model, now)
        blocked = _retry_time(record)
        if blocked and blocked > now:
            retry_times.append(blocked)
            reasons.append(f"{model}: {record.get('blocked_reason', 'cooldown')}")
            continue
        if DAILY_BUDGET and record["requests"] >= DAILY_BUDGET:
            until = next_daily_reset(now)
            record.update(blocked_until=until.isoformat(), blocked_reason="daily_budget")
            retry_times.append(until)
            reasons.append(f"{model}: local_daily_budget")
            continue

        attempts = 2 if model_index == 0 else 1
        for attempt in range(attempts):
            # Count requests, including failed attempts, against the local daily cap.
            if DAILY_BUDGET and record["requests"] >= DAILY_BUDGET:
                until = next_daily_reset(now_utc())
                record.update(blocked_until=until.isoformat(), blocked_reason="daily_budget")
                retry_times.append(until)
                reasons.append(f"{model}: local_daily_budget")
                break
            record["requests"] += 1
            try:
                result = analyze_property(video, model=model)
                record.pop("blocked_until", None)
                record.pop("blocked_reason", None)
                return result
            except RetryableAnalysisError as error:
                message = str(error)
                if not _rate_limit(message) and attempt + 1 < attempts:
                    print(f"Temporary analysis failure on {model}; retrying once after a short delay.")
                    time.sleep(TRANSIENT_RETRY_SECONDS)
                    continue
                retry_times.append(_block(record, message, now_utc()))
                reasons.append(f"{model}: {record['blocked_reason']}")
                print(f"Analysis model {model} paused: {record['blocked_reason']}; {message}")
                break
    until = min(retry_times) if retry_times else now_utc() + timedelta(minutes=10)
    error = RetryableAnalysisError(
        "Property video analysis paused: " + ", ".join(sorted(set(reasons))) +
        ". Next eligible retry: " + until.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %I:%M %p IST")
    )
    error.retry_at = until.isoformat()
    raise error


def notify_blocked(state, message):
    """One Telegram warning per six hours, persisted with monitor state."""
    provider = state.setdefault("analysis_provider", {})
    now = now_utc()
    previous = provider.get("last_alert_at")
    if previous and now - datetime.fromisoformat(previous) < timedelta(hours=6):
        print("Analysis warning already delivered recently; suppressing duplicate alert.")
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("::warning::Telegram credentials unavailable for analysis health warning.")
        return
    run_url = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "") + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "")
    text = (
        "⚠️ Property prompt generation is blocked or delayed.\n"
        + str(message)[:500] +
        "\nPending videos are retained for automatic retry. All areas remain enabled."
        "\nNo new prompt delivery is being claimed.\nRun: " + run_url
    )
    # Do not expose a token-bearing request URL in exception/log output.
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text}, timeout=20,
        )
        if not response.ok or not response.json().get("ok"):
            print("::warning::Telegram analysis warning could not be delivered.")
            return
    except Exception:
        print("::warning::Telegram analysis warning request failed.")
        return
    provider["last_alert_at"] = now.isoformat()
    print("Telegram analysis health warning delivered.")
