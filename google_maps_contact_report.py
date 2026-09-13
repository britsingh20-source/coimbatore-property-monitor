from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
from urllib.parse import quote_plus

import requests

import property_source_finder as base
from google_maps_source_finder import find_google_maps_contacts


JOBS = Path("data/video_jobs")


def _ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _video_contact(job: dict) -> str:
    text = f"{job.get('verified_facts') or ''} {job.get('contact_details') or ''}"
    match = base.PHONE_RE.search(text)
    return base._normalise_phone(match.group(0)) if match else ""


def _maps_search_url(job: dict) -> str:
    query = str(job.get("property_location") or "Coimbatore").strip()
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def format_report(job: dict) -> str:
    contacts = find_google_maps_contacts(job)
    video_id = str(job.get("video_id") or "")
    location = str(job.get("property_location") or "Coimbatore")
    video_phone = _video_contact(job)
    maps_url = _maps_search_url(job)

    lines = [
        "🗺️ <b>MAPS / PUBLIC CONTACT ENRICHMENT</b>",
        f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>",
        f"<b>Location:</b> {html.escape(location)}",
    ]
    if video_phone:
        lines.append(f"<b>Video contact:</b> <code>{html.escape(video_phone)}</code> — source: original video; role not assumed")
    lines.append(f'<a href="{html.escape(maps_url, quote=True)}">Open Google Maps search</a>')
    lines.append("")

    if not contacts:
        lines.extend([
            "No additional complete public phone number was found automatically in indexed Maps/web text for this property.",
            "The Maps search link is included so board/photo contacts can still be checked manually.",
            "Status: public Maps-image OCR not yet available from an accessible image payload in this run.",
        ])
        return "\n".join(lines)

    # Deduplicate numbers across search engines; keep strongest classification/confidence.
    best: dict[str, object] = {}
    for item in contacts:
        existing = best.get(item.phone)
        if existing is None or item.confidence > existing.confidence:
            best[item.phone] = item

    lines.append("<b>Public contacts found:</b>")
    for item in sorted(best.values(), key=lambda x: x.confidence, reverse=True)[:8]:
        pct = int(round(item.confidence * 100))
        lines.extend([
            f"• <code>{html.escape(item.phone)}</code> — {html.escape(item.classification)} — {pct}% source confidence",
            f"  Source: {html.escape(item.source)}",
        ])
        if item.evidence:
            lines.append(f"  Evidence: {html.escape(item.evidence[:180])}")

    if video_phone and video_phone in best:
        lines.append("")
        lines.append("✅ One public-source number matches the original video contact.")
    elif video_phone:
        lines.append("")
        lines.append("ℹ️ Public-source contacts differ from the original video contact; treat them as separate owner/builder/agent leads until verified.")

    lines.append("")
    lines.append("Only complete phone numbers already exposed in public text are returned; no OTP/login/masked-number bypass is attempted.")
    return "\n".join(lines)


def send_report(job: dict, token: str, chat_id: str) -> int:
    text = format_report(job)
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram rejected Maps contact report: {body}")
    return int((body.get("result") or {}).get("message_id") or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Maps/public source phone enrichment")
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
    parser.add_argument("--video-id", default="")
    parser.add_argument("--no-telegram", action="store_true")
    args = parser.parse_args()

    ids = [args.video_id.strip()] if args.video_id.strip() else _ids(args.ids_file)
    if not ids:
        print("No property IDs supplied to Maps enrichment.")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    for video_id in ids:
        path = JOBS / f"{video_id}.json"
        if not path.exists():
            print(f"Maps enrichment skipped missing job: {path}")
            continue
        job = json.loads(path.read_text(encoding="utf-8"))
        if args.no_telegram or not token or not chat_id:
            print(format_report(job))
        else:
            message_id = send_report(job, token, chat_id)
            print(f"Sent Maps/public contact report: {video_id} message_id={message_id}")


if __name__ == "__main__":
    main()
