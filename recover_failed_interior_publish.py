from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from interior_social_autopilot import (
    R2_PREFIX,
    analyze_publish_content,
    load_state,
    publish_instagram_reel,
    publish_instagram_story,
    publish_youtube_short,
    r2_client,
    required,
    save_state,
    send_message,
)


def analyze_with_retry(path: Path, attempts: int = 5):
    last = None
    for attempt in range(1, attempts + 1):
        try:
            return analyze_publish_content(path)
        except Exception as exc:
            last = exc
            text = str(exc).lower()
            transient = any(x in text for x in ("503", "unavailable", "high demand", "429", "resource_exhausted", "timeout"))
            if not transient or attempt == attempts:
                raise
            delay = min(60, 10 * attempt)
            print(f"Transient Gemini failure on attempt {attempt}/{attempts}; retrying in {delay}s: {exc}")
            time.sleep(delay)
    raise last


def main():
    source_id = os.environ.get("RECOVER_INTERIOR_ID", "2aky3zpEAMU").strip()
    token = required("TELEGRAM_BOT_TOKEN")
    chat_id = required("TELEGRAM_CHAT_ID")
    state = load_state()
    matches = [(k, v) for k, v in state.get("objects", {}).items() if str(v.get("source_id")) == source_id]
    if not matches:
        raise RuntimeError(f"No saved R2 record found for INTERIOR_ID {source_id}")
    key, record = matches[-1]
    print(f"Recovering {source_id} from {key}")

    client = r2_client()
    bucket = required("R2_BUCKET_NAME")
    with tempfile.NamedTemporaryFile(prefix="interior-recovery-", suffix=".mp4") as handle:
        client.download_file(bucket, key, handle.name)
        video_url = client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=21600)

        content = record.get("content") or {}
        if content.get("status") == "failed" or not content.get("instagram_caption"):
            content = analyze_with_retry(Path(handle.name))
            record["content"] = content
            save_state(state)

        if record.get("instagram", {}).get("status") != "published":
            record["instagram"] = {"status": "published", **publish_instagram_reel(video_url, content["instagram_caption"])}
            save_state(state)

        if record.get("instagram_story", {}).get("status") != "published":
            record["instagram_story"] = {"status": "published", **publish_instagram_story(video_url)}
            save_state(state)

        if record.get("youtube", {}).get("status") != "published":
            record["youtube"] = {"status": "published", **publish_youtube_short(Path(handle.name), content)}
            save_state(state)

    # Synchronize the Telegram-file record only after recovery succeeds.
    for unique_id, telegram_record in state.get("telegram_files", {}).items():
        if str(telegram_record.get("source_id")) == source_id:
            state["telegram_files"][unique_id] = record
    save_state(state)
    send_message(token, chat_id, f"✅ Recovered and published Interior video\nINTERIOR_ID: {source_id}\nDestinations: Instagram Reel + Instagram Story + YouTube Short")
    print(f"Recovery publish completed for {source_id}")


if __name__ == "__main__":
    main()
