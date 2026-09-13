from __future__ import annotations

import argparse
import html
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests
from google import genai

import property_source_finder as base


MODEL = os.environ.get("PROPERTY_FINDER_GEMINI_MODEL", "gemini-3.6-flash")
MAX_GEMINI_CANDIDATES = int(os.environ.get("PROPERTY_FINDER_GEMINI_CANDIDATES", "8"))
MIN_FACT_PREFILTER = float(os.environ.get("PROPERTY_FINDER_GEMINI_MIN_FACT", "0.20"))
BING_ENDPOINT = "https://www.bing.com/search"


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini property-match response did not contain JSON")
    return json.loads(cleaned[start:end + 1])


def _bing_search(query: str, session: requests.Session) -> list[tuple[str, str]]:
    response = session.get(
        BING_ENDPOINT,
        params={"q": query, "count": "20"},
        headers=base.HEADERS,
        timeout=base.REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    body = response.text
    results: list[tuple[str, str]] = []
    for block in re.findall(r'<li[^>]+class=["\']b_algo["\'][^>]*>(.*?)</li>', body, flags=re.I | re.S):
        anchor = re.search(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not anchor:
            continue
        url = html.unescape(anchor.group(1))
        title = base._clean_text(anchor.group(2))
        results.append((url, title))
    return results


def _discovery_queries(job: dict, portal: str) -> list[str]:
    domain = base.PORTALS[portal][0]
    prop = job.get("property") or {}
    locality = str(job.get("property_location") or "Coimbatore").split(",")[0].strip()
    nearby = base._locality_terms(job)
    bhk = str(prop.get("bhk") or "").replace("NOT SPECIFIED", "").strip()
    land = str(prop.get("land_area") or "").replace("NOT SPECIFIED", "").strip()
    built = str(prop.get("built_up_area") or "").replace("NOT SPECIFIED", "").strip()
    price = str(prop.get("price") or "").replace("NOT SPECIFIED", "").strip()
    ptype = str(prop.get("property_type") or "property").strip()

    queries: list[str] = []
    for place in nearby[:4] or [locality]:
        queries.append(f'site:{domain} "{place}" Coimbatore "{ptype}" {bhk} {land} {built} {price}'.strip())
        queries.append(f'site:{domain} "{place}" Coimbatore {bhk} {land} {price}'.strip())
    # Broader query catches listings whose locality label differs from the broker/video wording.
    queries.append(f'site:{domain} Coimbatore {bhk} {land} {built} {price} {ptype}'.strip())

    seen: set[str] = set()
    output: list[str] = []
    for query in queries:
        compact = re.sub(r"\s+", " ", query).strip()
        if compact and compact.lower() not in seen:
            seen.add(compact.lower())
            output.append(compact)
    return output[:10]


def discover_candidates_resilient(job: dict, session: requests.Session) -> tuple[list[tuple[str, str, str]], dict]:
    found: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    diagnostics: dict[str, dict] = {
        portal: {"queries": 0, "search_hits": 0, "candidate_urls": 0, "engines": set()}
        for portal in base.PORTALS
    }

    for portal in base.PORTALS:
        limit = max(base.MAX_RESULTS_PER_PORTAL, 8)
        for query in _discovery_queries(job, portal):
            diagnostics[portal]["queries"] += 1
            engine_results: list[tuple[str, str, str]] = []
            try:
                for url, title in base._search_web(query, session):
                    engine_results.append((url, title, "DuckDuckGo"))
            except requests.RequestException as exc:
                print(f"Finder DuckDuckGo warning [{portal}]: {exc}")

            # Bing is intentionally additive, not only fallback. Property portals are inconsistently indexed.
            try:
                for url, title in _bing_search(query, session):
                    engine_results.append((url, title, "Bing"))
            except requests.RequestException as exc:
                print(f"Finder Bing warning [{portal}]: {exc}")

            diagnostics[portal]["search_hits"] += len(engine_results)
            for url, title, engine in engine_results:
                actual_portal = base._portal_for_url(url)
                if actual_portal != portal or url in seen:
                    continue
                parsed = urlparse(url)
                if parsed.path.lower() in {"", "/"}:
                    continue
                seen.add(url)
                found.append((portal, url, title))
                diagnostics[portal]["candidate_urls"] += 1
                diagnostics[portal]["engines"].add(engine)
                if diagnostics[portal]["candidate_urls"] >= limit:
                    break
            if diagnostics[portal]["candidate_urls"] >= limit:
                break

    for portal in diagnostics:
        diagnostics[portal]["engines"] = sorted(diagnostics[portal]["engines"])
    return found, diagnostics


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
        return {
            "match": base.ListingMatch(portal=portal, url=url, title=search_title, notes=f"page blocked/unavailable: {exc}"),
            "images": [],
            "page_text": "",
            "page_accessible": False,
        }

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
        "page_accessible": True,
    }


def find_sources_resilient(job: dict) -> tuple[list[base.ListingMatch], dict]:
    diagnostics: dict = {"mode": "local_frames", "portals": {}}
    try:
        matches = base.find_sources(job)
        for portal in base.PORTALS:
            pmatches = [m for m in matches if m.portal == portal]
            diagnostics["portals"][portal] = {
                "candidate_urls": len(pmatches),
                "pages_accessible": sum(1 for m in pmatches if "blocked/unavailable" not in m.notes),
                "photo_candidates": sum(1 for m in pmatches if m.visual_score > 0),
                "best_score": max((m.overall_score for m in pmatches), default=0.0),
            }
        return matches, diagnostics
    except Exception as exc:
        diagnostics["mode"] = "gemini_direct_video"
        diagnostics["local_frame_error"] = str(exc)[:220]
        print(f"Local-frame finder unavailable; switching to Gemini direct-video fallback: {exc}")

    with requests.Session() as session:
        candidates, discovery_diag = discover_candidates_resilient(job, session)
        inspected = []
        for portal, url, title in candidates:
            item = _inspect_without_local_frames(job, portal, url, title, session)
            inspected.append(item)

        inspected.sort(key=lambda item: item["match"].fact_score, reverse=True)
        gemini_budget = 0
        matches: list[base.ListingMatch] = []
        for item in inspected:
            match = item["match"]
            if item["images"] and match.fact_score >= MIN_FACT_PREFILTER and gemini_budget < MAX_GEMINI_CANDIDATES:
                gemini_budget += 1
                try:
                    visual, photo_count, note = _gemini_compare(job, item["images"], item["page_text"], match.title)
                    match.visual_score = round(visual, 3)
                    match.matched_images = photo_count
                    match.notes = note or "Gemini compared candidate photos against original YouTube video"
                except Exception as gemini_exc:
                    match.notes = f"Gemini visual fallback unavailable: {str(gemini_exc)[:160]}"

            if match.visual_score > 0:
                match.overall_score = round(0.72 * match.visual_score + 0.28 * match.fact_score, 3)
            else:
                match.overall_score = round(min(0.62, 0.62 * match.fact_score), 3)
            matches.append(match)

        matches.sort(key=lambda m: (m.overall_score, m.visual_score, m.fact_score), reverse=True)
        diagnostics["portals"] = {}
        for portal in base.PORTALS:
            pmatches = [m for m in matches if m.portal == portal]
            accessible = [i for i in inspected if i["match"].portal == portal and i["page_accessible"]]
            photo_items = [i for i in accessible if i["images"]]
            diagnostics["portals"][portal] = {
                **discovery_diag[portal],
                "pages_accessible": len(accessible),
                "photo_candidates": len(photo_items),
                "gemini_compared": sum(1 for m in pmatches if m.visual_score > 0 or "Gemini compared" in m.notes),
                "best_score": max((m.overall_score for m in pmatches), default=0.0),
                "best_fact_score": max((m.fact_score for m in pmatches), default=0.0),
            }
        diagnostics["gemini_budget_used"] = gemini_budget
        return matches, diagnostics


def _video_advertised_phone(job: dict) -> str:
    text = str(job.get("verified_facts") or "") + " " + str(job.get("contact_details") or "")
    match = base.PHONE_RE.search(text)
    return base._normalise_phone(match.group(0)) if match else ""


def format_diagnostic_report(job: dict, matches: list[base.ListingMatch], diagnostics: dict) -> str:
    video_id = str(job.get("video_id") or "").strip()
    prop = job.get("property") or {}
    lines = [
        "🔎 <b>PROPERTY SOURCE FINDER</b>",
        f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>",
        f"<b>Location:</b> {html.escape(str(job.get('property_location') or 'Coimbatore'))}",
    ]
    summary = " | ".join(
        str(prop.get(key)) for key in ("bhk", "land_area", "built_up_area", "price")
        if base._present(prop.get(key))
    )
    if summary:
        lines.append(f"<b>Facts:</b> {html.escape(summary)}")
    advertised = _video_advertised_phone(job)
    if advertised:
        lines.append(f"<b>Video-advertised contact:</b> <code>{html.escape(advertised)}</code> (not assumed owner)")
    lines.append("")

    reportable = [m for m in matches if m.overall_score >= base.MIN_REPORT_SCORE][:8]
    if reportable:
        for index, match in enumerate(reportable, 1):
            confidence = int(round(match.overall_score * 100))
            visual = int(round(match.visual_score * 100))
            facts = int(round(match.fact_score * 100))
            marker = "✅" if match.overall_score >= base.HIGH_CONFIDENCE_SCORE else "🟡"
            lines.extend([
                f"{marker} <b>{index}. {base._portal_label(match.portal)}</b>",
                f"Match: <b>{confidence}%</b> | Photo: {visual}% | Facts: {facts}%",
                f"Posted by: <b>{html.escape(match.poster_type)}</b>",
            ])
            if match.phone_public:
                lines.append(f"Public phone: <code>{html.escape(match.phone)}</code>")
            else:
                lines.append("Phone: not publicly exposed")
            lines.append(f'<a href="{base._safe_telegram_url(match.url)}">Open exact listing</a>')
            if match.notes:
                lines.append(f"Note: {html.escape(match.notes[:150])}")
            lines.append("")
    else:
        lines.append("<b>No verified high-confidence source yet.</b>")
        lines.append("")

    lines.append("<b>SEARCH DIAGNOSTICS</b>")
    for portal in base.PORTALS:
        d = (diagnostics.get("portals") or {}).get(portal, {})
        best = int(round(float(d.get("best_score") or 0) * 100))
        engines = ",".join(d.get("engines") or []) or "default"
        lines.append(
            f"{base._portal_label(portal)}: "
            f"{int(d.get('candidate_urls') or 0)} URLs → "
            f"{int(d.get('pages_accessible') or 0)} pages → "
            f"{int(d.get('photo_candidates') or 0)} photo candidates → best {best}% "
            f"[{html.escape(engines)}]"
        )

    # Always expose a few rejected possibilities so we can tell discovery failure from matching failure.
    rejected = [m for m in matches if m.overall_score < base.MIN_REPORT_SCORE]
    rejected.sort(key=lambda m: (m.overall_score, m.fact_score), reverse=True)
    if rejected:
        lines.append("")
        lines.append("<b>Top possible/rejected candidates</b>")
        for m in rejected[:4]:
            lines.append(
                f"• {base._portal_label(m.portal)} — {int(round(m.overall_score*100))}% "
                f"(facts {int(round(m.fact_score*100))}%, photo {int(round(m.visual_score*100))}%)"
            )
            lines.append(f'<a href="{base._safe_telegram_url(m.url)}">Open candidate</a>')

    lines.append("")
    lines.append("Only complete phone numbers already public on fetched pages are returned; masked/login/OTP contacts are not bypassed.")
    return "\n".join(lines)


def _send_report(job: dict, matches: list[base.ListingMatch], diagnostics: dict, bot_token: str, chat_id: str) -> int:
    text = format_diagnostic_report(job, matches, diagnostics)
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram rejected diagnostic property source report: {body}")
    return int((body.get("result") or {}).get("message_id") or 0)


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
    all_results: dict[str, dict] = {}

    for video_id in video_ids:
        job_path = base.JOBS / f"{video_id}.json"
        if not job_path.exists():
            print(f"Property finder skipped missing job: {job_path}")
            continue
        job = json.loads(job_path.read_text(encoding="utf-8"))
        try:
            matches, diagnostics = find_sources_resilient(job)
            all_results[video_id] = {
                "matches": [asdict(item) for item in matches],
                "diagnostics": diagnostics,
            }
            if not args.no_telegram and bot_token and chat_id:
                message_id = _send_report(job, matches, diagnostics, bot_token, chat_id)
                print(f"Sent diagnostic property source finder report: {video_id} message_id={message_id}")
            else:
                print(format_diagnostic_report(job, matches, diagnostics))
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
