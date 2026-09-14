from __future__ import annotations

import argparse
import html
import json
import os
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus

import requests

import property_source_finder as base
from google_maps_source_finder import find_google_maps_contacts
from public_image_contact_finder import find_public_image_contacts


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


def _dedupe_public_contacts(contacts):
    best: dict[str, object] = {}
    for item in contacts:
        if not item.phone:
            continue
        existing = best.get(item.phone)
        if existing is None or item.confidence > existing.confidence:
            best[item.phone] = item
    return best


def _source_summary(contacts) -> str:
    counts = Counter(item.source.split(" indexed ")[-1] if " indexed " in item.source else item.source for item in contacts)
    if not counts:
        return "none"
    return ", ".join(f"{name}:{count}" for name, count in counts.most_common(8))


def _all_contacts(job: dict):
    contacts = list(find_google_maps_contacts(job))
    try:
        image_contacts = find_public_image_contacts(job)
        contacts.extend(image_contacts)
        print(
            f"PUBLIC_IMAGE_CONTACT_SCAN video_id={job.get('video_id') or ''} "
            f"complete_public_numbers={len({item.phone for item in image_contacts if item.phone})}"
        )
    except Exception as exc:
        print(f"PUBLIC_IMAGE_CONTACT_SCAN_FAILED video_id={job.get('video_id') or ''} error={exc}")
    return contacts


def _format_report_from_contacts(job: dict, contacts) -> str:
    video_id = str(job.get("video_id") or "")
    location = str(job.get("property_location") or "Coimbatore")
    video_phone = _video_contact(job)
    maps_url = _maps_search_url(job)
    best = _dedupe_public_contacts(contacts)
    protected = [item for item in contacts if not item.phone and item.protected_contact]

    lines = [
        "🔎 <b>PUBLIC OWNER / SOURCE ENRICHMENT</b>",
        f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>",
        f"<b>Location:</b> {html.escape(location)}",
    ]
    if video_phone:
        lines.append(f"<b>Video contact:</b> <code>{html.escape(video_phone)}</code> — original video; role not assumed")
    lines.append(f'<a href="{html.escape(maps_url, quote=True)}">Open Google Maps search</a>')
    lines.append("")

    if best:
        lines.append("<b>Complete public phone numbers found:</b>")
        for item in sorted(best.values(), key=lambda x: x.confidence, reverse=True)[:10]:
            pct = int(round(item.confidence * 100))
            lines.extend([
                f"• <code>{html.escape(item.phone)}</code> — {html.escape(item.classification)} — {pct}% evidence confidence",
                f"  Source: {html.escape(item.source)}",
            ])
            if item.url:
                lines.append(f'  <a href="{html.escape(item.url, quote=True)}">Open source</a>')
            if item.evidence:
                lines.append(f"  Evidence: {html.escape(item.evidence[:180])}")
    else:
        lines.append("No additional complete public phone number was found automatically after text + public image/signboard checks.")

    if protected:
        lines.append("")
        lines.append("<b>Listings found where contact is protected:</b>")
        seen_urls: set[str] = set()
        for item in protected:
            if not item.url or item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            lines.append(f'• {html.escape(item.source)} — <a href="{html.escape(item.url, quote=True)}">open exact listing/source</a>')
            if len(seen_urls) >= 8:
                break

    if video_phone and video_phone in best:
        lines.append("")
        lines.append("✅ At least one independent public-source hit matches the original video contact.")
    elif video_phone and best:
        lines.append("")
        lines.append("ℹ️ Public-source contacts differ from the original video contact. Keep them as separate owner/builder/agent leads until role is verified.")

    lines.extend([
        "",
        "Sources searched include Google Maps/public web, public property/project images and signboards, OLX, Housing, RealEstateIndia, 99acres, MagicBricks, Facebook, Instagram and YouTube-indexed public pages.",
        "Only complete phone numbers already exposed publicly are returned. Masked/login/OTP/CAPTCHA-protected contacts are not bypassed; an exact public URL is returned when available.",
    ])
    return "\n".join(lines)


def format_report(job: dict) -> str:
    return _format_report_from_contacts(job, _all_contacts(job))


def send_report(job: dict, token: str, chat_id: str) -> tuple[int, list]:
    contacts = _all_contacts(job)
    text = _format_report_from_contacts(job, contacts)
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram rejected public contact report: {body}")
    return int((body.get("result") or {}).get("message_id") or 0), contacts


def _log_summary(video_id: str, contacts: list) -> None:
    best = _dedupe_public_contacts(contacts)
    protected = [item for item in contacts if item.protected_contact and not item.phone]
    roles = Counter(item.classification for item in best.values())
    role_text = ", ".join(f"{role}:{count}" for role, count in roles.items()) or "none"
    print(
        f"PUBLIC_CONTACT_SUMMARY video_id={video_id} complete_public_numbers={len(best)} "
        f"protected_links={len({item.url for item in protected if item.url})} roles=[{role_text}] "
        f"sources=[{_source_summary(contacts)}]"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Maps/OLX/property-portal public phone enrichment")
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
    parser.add_argument("--video-id", default="")
    parser.add_argument("--no-telegram", action="store_true")
    args = parser.parse_args()

    ids = [args.video_id.strip()] if args.video_id.strip() else _ids(args.ids_file)
    if not ids:
        print("No property IDs supplied to public contact enrichment.")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    for video_id in ids:
        path = JOBS / f"{video_id}.json"
        if not path.exists():
            print(f"Public contact enrichment skipped missing job: {path}")
            continue
        job = json.loads(path.read_text(encoding="utf-8"))
        if args.no_telegram or not token or not chat_id:
            contacts = _all_contacts(job)
            print(_format_report_from_contacts(job, contacts))
            _log_summary(video_id, contacts)
        else:
            message_id, contacts = send_report(job, token, chat_id)
            _log_summary(video_id, contacts)
            print(f"Sent public owner/source enrichment report: {video_id} message_id={message_id}")


if __name__ == "__main__":
    main()
