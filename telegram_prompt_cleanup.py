from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import requests


QUEUE_PATH = Path(os.environ.get("TELEGRAM_PROMPT_QUEUE", "data/telegram_prompt_queue.json"))


def _save(queue: dict) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("Telegram prompt cleanup skipped: bot token/chat id unavailable")
        return
    if not QUEUE_PATH.exists():
        print("Telegram prompt cleanup skipped: queue not found")
        return

    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    changed = False
    deleted = 0

    for item in queue.get("prompts", []):
        if item.get("status") != "published":
            continue
        if item.get("prompt_deleted_at"):
            continue

        message_id = item.get("prompt_message_id")
        if not isinstance(message_id, int):
            # Older prompts were sent before message IDs were tracked. Never guess
            # a Telegram message ID because that could delete the uploaded video or
            # the separate VIDEO_ID message.
            continue

        video_id = str(item.get("video_id") or "").strip()
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/deleteMessage",
                json={"chat_id": chat_id, "message_id": message_id},
                timeout=30,
            )
            body = response.json() if response.content else {}
            if response.ok and body.get("ok"):
                item["prompt_deleted_at"] = datetime.now(timezone.utc).isoformat()
                item.pop("prompt_delete_error", None)
                deleted += 1
                changed = True
                print(f"Deleted published Telegram prompt: {video_id} message_id={message_id}")
            else:
                detail = str(body.get("description") or response.text)[:500]
                item["prompt_delete_error"] = detail
                changed = True
                print(f"Prompt cleanup deferred for {video_id}: {detail}")
        except Exception as error:
            item["prompt_delete_error"] = str(error)[:500]
            changed = True
            print(f"Prompt cleanup deferred for {video_id}: {error}")

    if changed:
        _save(queue)
    print(f"Telegram published-prompt cleanup complete: deleted={deleted}")


if __name__ == "__main__":
    main()
