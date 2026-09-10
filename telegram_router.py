from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from interior_social_autopilot import handle_update as handle_interior_update, interior_id
from telegram_r2_ingest import ingest as handle_property_updates

STATE_PATH = Path(os.environ.get("TELEGRAM_INGEST_STATE", "data/telegram_ingest_state.json"))


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def telegram(method: str, token: str, data: dict | None = None) -> dict:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data or {},
        timeout=60,
    )
    body = response.json()
    if not response.ok or not body.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {body.get('description') or body}")
    return body


def load_cursor() -> int:
    if not STATE_PATH.exists():
        return 0
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return int(state.get("last_update_id") or 0)
    except Exception:
        return 0


def advance_cursor(update_id: int) -> None:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {"files": {}}
    except Exception:
        state = {"files": {}}
    state["last_update_id"] = max(int(state.get("last_update_id") or 0), int(update_id or 0))
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def route_one(update: dict) -> None:
    message = update.get("message") or update.get("edited_message") or {}
    if interior_id(message):
        print(f"Routing Telegram update {update.get('update_id')} to Interior publisher")
        handle_interior_update(update)
        advance_cursor(int(update.get("update_id") or 0))
        return

    print(f"Routing Telegram update {update.get('update_id')} to Property publisher")
    old = os.environ.get("TELEGRAM_WEBHOOK_UPDATE_JSON")
    os.environ["TELEGRAM_WEBHOOK_UPDATE_JSON"] = json.dumps(update, ensure_ascii=False)
    try:
        handle_property_updates()
    finally:
        if old is None:
            os.environ.pop("TELEGRAM_WEBHOOK_UPDATE_JSON", None)
        else:
            os.environ["TELEGRAM_WEBHOOK_UPDATE_JSON"] = old


def main() -> None:
    supplied = os.environ.get("TELEGRAM_WEBHOOK_UPDATE_JSON", "").strip()
    if supplied:
        route_one(json.loads(supplied))
        return

    token = required("TELEGRAM_BOT_TOKEN")
    offset = load_cursor() + 1
    body = telegram(
        "getUpdates",
        token,
        {
            "offset": str(offset),
            "limit": "100",
            "timeout": "0",
            "allowed_updates": json.dumps(["message", "edited_message"]),
        },
    )
    updates = body.get("result") or []
    if not updates:
        print("No new Telegram messages for router.")
        return

    for update in updates:
        route_one(update)


if __name__ == "__main__":
    main()
