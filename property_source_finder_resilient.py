from __future__ import annotations

import argparse
import html
import json
import os
import re
from dataclasses import asdict
from pathlib import Path

import requests
from google import genai

import property_source_finder as base


MODEL = os.environ.get("PROPERTY_FINDER_GEMINI_MODEL", "gemini-3.6-flash")
MAX_GEMINI_CANDIDATES = int(os.environ.get("PROPERTY_FINDER_GEMINI_CANDIDATES", "8"))
MIN_FACT_PREFILTER = float(os.environ.get("PROPERTY_FINDER_GEMINI_MIN_FACT", "0.25"))


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini property-match response did not contain JSON")
    return json.loads(cleaned[start:end + 1])


def _gemini_compare(job: dict, image_urls: list[str], page_text: str, title: str) -> tuple[float, int, str]:
    if not image_urls:
        return 0.0, 0, "listing photos unavailable for Gemini comparison"

    prop = job.get("property") or {}
    prompt = f"""
You are matching a Coimbatore real-estate portal listing to the ORIGINAL YouTube property video.
Analyze the YouTube video frame-by-frame and compare it with the candidate listing photos supplied after this text.
Do not match on locality alone. Look for the same front elevation, gate, balcony, windows, wall/paint pattern,
parking, staircase, kitchen, rooms, flooring, compound, street context and other distinctive visual details.
Also check factual consistency: BHK, land area, built-up area, price, facing and approval.

ORIGINAL PROPERTY FACTS
Location: {job.get('property_location')}
Property type: {prop.get('property_type')}
BHK: {prop.get('bhk')}
Land: {prop.get('land_area')}
Built-up: {prop.get('built_up_area')}
Price: {prop.get('price')}
Facing: {prop.get('facing')}
Verified facts: {job.get('verified_facts')}

CANDIDATE TITLE
{title}

CANDIDATE PAGE TEXT EXCERPT
{page_text[:5000]}

Return one JSON object only:
{{
  "same_property": true,
  "confidence": 0.0,
  "matched_visual_features": ["specific visual matches"],
  "conflicts": ["specific contradictions"],
  "usable_photo_count": 0
}}

Rules:
- confidence 0.90+ only for very strong visual identity with multiple distinctive matches.
- 0.70-0.89 for probable same property with at least two distinctive visual matches and no major conflict.
- below 0.70 when evidence is generic, photos are weak, or facts conflict.
- same_property must be false when there is a clear contradictory elevation, land size, BHK, price or location.
"""
    inputs: list[dict] = [
        {"type": "video", "uri": str(job.get("source_url") or "")},
        {"type": "text", "text": prompt},
    ]
    for url in image_urls[:6]:
        inputs.append({"type": "image", "uri": url})

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    interaction = client.interactions.create(model=MODEL, input=inputs)
    result = _parse_json(interaction.output_text)
    confidence = float(result.get("confidence") or 0.0)
    if not result.get("same_property"):
        confidence = min(confidence, 0.49)
    count = int(result.get("usable_photo_count") or 0)
    evidence = "; ".join(str(x) for x in (result.get("matched_visual_features") or [])[:3])
    conflicts = "; ".join(str(x) for x in (result.get("conflicts") or [])[:2])
    note = evidence
    if conflicts:
        note = f"{note} | conflicts: {conflicts}" if note else f"conflicts: {conflicts}"
    return max(0.0, min(1.0, confidence)), count, note[:240]


def _inspect_without_local_frames(job: dict, portal: str, url: str, search_title: str, session: requests.Session):
    try:
        response = session.get(url, headers=base.HEADERS, timeout=base.REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        return base.ListingMatch(portal=portal, url=url, title=search_title, notes=f"page blocked/unavailable: {exc}")

    final_url = response.url
    raw_html = response.text[:4_000_000]
    page_text = base._clean_text(raw_html)
    title = base._extract_title(raw_html, search_title)
    poster_type = base._classify_poster(page_text)
    phone = base._public_phone(page_text, portal)
    images = base._extract_images(raw_html, final_url)
    fact_score = base._page_facts_score(job, f"{title} {page_text}")

    return {
        "match": base.ListingMatch(
            portal=portal,
            url=final_url,
            title=title,
            poster_type=poster_type,
            phone=phone,
            phone_public=bool(phone),
            fact_score=round(fact_score, 3),
            notes="awaiting Gemini direct-video visual comparison" if images else "listing photos not accessible in public HTML",
        ),
        "images": images,
        "page_text": page_text,
    }


def find_sources_resilient(job: dict) -> list[base.ListingMatch]:
    # First try the fast local-frame matcher. GitHub-hosted runners can be challenged by YouTube;
    # if that happens, fall back to Gemini reading the public YouTube video directly, exactly as
    # property_analyzer.py already does successfully.
    try:
        return base.find_sources(job)
    except Exception as exc:
        print(f"Local-frame finder unavailable; switching to Gemini direct-video fallback: {exc}")

    with requests.Session() as session:
        candidates = base.discover_candidates(job, session)
        inspected = []
        for portal, url, title in candidates:
            item = _inspect_without_local_frames(job, portal, url, title, session)
            if item is not None:
                inspected.append(item)

        inspected.sort(key=lambda item: item["match"].fact_score, reverse=True)
        gemini_budget = 0
        matches: list[base.ListingMatch] = []
        for item in inspected:
            match = item["match"]
            if item["images"] and match.fact_score >= MIN_FACT_PREFILTER and gemini_budget < MAX_GEMINI_CANDIDATES:
                gemini_budget += 1
                try:
                    visual, photo_count, note = _gemini_compare(
                        job, item["images"], item["page_text"], match.title
                    )
                    match.visual_score = round(visual, 3)
                    match.matched_images = photo_count
                    match.notes = note or "Gemini compared candidate photos against original YouTube video"
                except Exception as gemini_exc:
                    match.notes = f"Gemini visual fallback unavailable: {str(gemini_exc)[:160]}"

            if match.visual_score > 0:
                # Visual identity is primary; structured facts are corroboration.
                match.overall_score = round(0.72 * match.visual_score + 0.28 * match.fact_score, 3)
            else:
                match.overall_score = round(min(0.62, 0.62 * match.fact_score), 3)
            matches.append(match)

        matches.sort(key=lambda m: (m.overall_score, m.visual_score, m.fact_score), reverse=True)
        return matches


def main() -> None:
    parser = argparse.ArgumentParser(description="Resilient property-source finder")
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
    parser.add_argument("--video-id", default="")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--no-telegram", action="store_true")
    args = parser.parse_args()

    video_ids = [args.video_id.strip()] if args.video_id.strip() else base._ids(args.ids_file)
    if not video_ids:
        print("No property IDs supplied to source finder.")
        return

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    all_results: dict[str, list[dict]] = {}

    for video_id in video_ids:
        job_path = base.JOBS / f"{video_id}.json"
        if not job_path.exists():
            print(f"Property finder skipped missing job: {job_path}")
            continue
        job = json.loads(job_path.read_text(encoding="utf-8"))
        try:
            matches = find_sources_resilient(job)
            all_results[video_id] = [asdict(item) for item in matches]
            if not args.no_telegram and bot_token and chat_id:
                message_id = base.send_telegram_report(job, matches, bot_token, chat_id)
                print(f"Sent resilient property source finder report: {video_id} message_id={message_id}")
            else:
                print(base.format_telegram_report(job, matches))
        except Exception as exc:
            print(f"Resilient property source finder warning for {video_id}: {exc}")
            if not args.no_telegram and bot_token and chat_id:
                fallback = (
                    "🔎 <b>PROPERTY SOURCE FINDER</b>\n"
                    f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>\n"
                    "Search could not complete; the normal Gemini property prompt is unaffected.\n"
                    f"Reason: {html.escape(str(exc)[:350])}"
                )
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data={"chat_id": chat_id, "text": fallback, "parse_mode": "HTML"},
                    timeout=60,
                )

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(all_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
