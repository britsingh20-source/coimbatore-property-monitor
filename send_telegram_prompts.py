from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import io
import json
import os
from pathlib import Path
import tempfile

import requests

from reference_frames import extract_reference_frames, send_reference_frames
from veo_prompt import build_veo_prompt, telegram_filename


JOBS = Path("data/video_jobs")
DEFAULT_QUEUE = Path("data/telegram_prompt_queue.json")


def _ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _telegram_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:500] or "No response body"
    return str(body.get("description") or body)[:500]


def _queue_prompt(queue_path: Path, job: dict, delivery: dict) -> None:
    queue = {"prompts": []}
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    prompts = queue.setdefault("prompts", [])
    video_id = str(job.get("video_id") or "").strip()
    existing = next((item for item in prompts if item.get("video_id") == video_id), None)
    update = {
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_mobile_upload",
        "reference_frame_count": int(delivery.get("reference_frame_count") or 0),
        "reference_status": str(delivery.get("reference_status") or "unknown"),
    }
    error = str(delivery.get("reference_error") or "").strip()
    if error:
        update["reference_error"] = error[-500:]
    if existing is None:
        prompts.append({"video_id": video_id, **update})
    elif existing.get("status") != "published":
        existing.update(update)
        existing.pop("r2_key", None)
        if not error:
            existing.pop("reference_error", None)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def send_prompt(job: dict, bot_token: str, chat_id: str) -> dict:
    prompt = build_veo_prompt(job)
    prop = job.get("property") or {}
    location = str(job.get("property_location") or "Coimbatore")
    video_id = str(job.get("video_id") or "").strip()
    title = " ".join(
        part
        for part in (
            str(prop.get("bhk") or "").strip(),
            str(prop.get("property_type") or "Property").strip(),
        )
        if part and part.upper() != "NOT SPECIFIED"
    )

    reference_count = 0
    reference_error = ""
    with tempfile.TemporaryDirectory(prefix=f"property-{video_id}-") as temp_dir:
        try:
            frame_paths = extract_reference_frames(job, Path(temp_dir), target_count=5)
            send_reference_frames(frame_paths, bot_token, chat_id, video_id)
            reference_count = len(frame_paths)
        except Exception as exc:
            reference_error = str(exc)[-500:]
            print(f"Reference-frame warning for {video_id}: {reference_error}")

    if reference_count == 5:
        instructions = (
            "<b>Reference frames:</b> 5/5 sent above.\n\n"
            "Save all five images. Open Gemini → Videos, attach all five images together, "
            "then paste the attached prompt. After generation, send the downloaded MP4 "
            "to this bot as a file."
        )
        reference_status = "sent"
    else:
        instructions = (
            f"<b>Reference frames:</b> {reference_count}/5 — extraction needs attention.\n"
            f"<b>Warning:</b> {html.escape(reference_error or 'Incomplete reference set')}\n\n"
            "Do not generate a generic video from this prompt. Wait until the corrected "
            "five-frame reference set is delivered."
        )
        reference_status = "failed"

    caption = (
        "<b>New 10-second Gemini/Veo property prompt</b>\n"
        f"<b>Property:</b> {html.escape(title)}\n"
        f"<b>Location:</b> {html.escape(location)}\n"
        f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>\n"
        "<b>Site visit:</b> 9003787621\n\n"
        f"{instructions}\n\n"
        f"Add this exact caption when returning it: <code>VIDEO_ID: {html.escape(video_id)}</code>. "
        "The mobile filename can remain unchanged."
    )
    payload = io.BytesIO(prompt.encode("utf-8"))
    payload.name = telegram_filename(job)
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
        files={"document": (payload.name, payload, "text/plain; charset=utf-8")},
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(
            f"Telegram sendDocument failed for {video_id} "
            f"(HTTP {response.status_code}): {_telegram_error(response)}"
        )
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(
            f"Telegram rejected prompt for {video_id}: {_telegram_error(response)}"
        )
    return {
        "reference_frame_count": reference_count,
        "reference_status": reference_status,
        "reference_error": reference_error,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
    parser.add_argument("--queue-file", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    if not chat_id.lstrip("-").isdigit():
        raise SystemExit("TELEGRAM_CHAT_ID must be the numeric chat id returned by getUpdates")

    video_ids = _ids(args.ids_file)
    if not video_ids:
        print("No new property prompts to send.")
        return

    for video_id in video_ids:
        path = JOBS / f"{video_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing video job: {path}")
        job = json.loads(path.read_text(encoding="utf-8"))
        delivery = send_prompt(job, bot_token, chat_id)
        _queue_prompt(args.queue_file, job, delivery)
        print(
            "Sent Gemini/Veo prompt to Telegram and queued mobile upload: "
            f"{video_id} (reference frames: {delivery['reference_frame_count']}/5)"
        )


if __name__ == "__main__":
    main()
