from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import cv2
import numpy as np
import requests

from reference_frames import extract_reference_frames


JOBS = Path("data/video_jobs")
PORTALS = {
    "housing": ("housing.com",),
    "realestateindia": ("realestateindia.com",),
    "99acres": ("99acres.com",),
    "magicbricks": ("magicbricks.com",),
}
SEARCH_ENDPOINT = os.environ.get("PROPERTY_FINDER_SEARCH_URL", "https://html.duckduckgo.com/html/").strip()
MAX_RESULTS_PER_PORTAL = int(os.environ.get("PROPERTY_FINDER_MAX_RESULTS_PER_PORTAL", "5"))
MIN_REPORT_SCORE = float(os.environ.get("PROPERTY_FINDER_MIN_SCORE", "0.50"))
HIGH_CONFIDENCE_SCORE = float(os.environ.get("PROPERTY_FINDER_HIGH_CONFIDENCE", "0.78"))
REQUEST_TIMEOUT = int(os.environ.get("PROPERTY_FINDER_HTTP_TIMEOUT", "20"))
USER_AGENT = os.environ.get(
    "PROPERTY_FINDER_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36",
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"}
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s.-]?)?([6-9]\d{4}[\s.-]?\d{5})(?!\d)")
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp)(?:\?|$)", re.I)


NEARBY_LOCALITIES = {
    "thudiyalur": ["Pannimadai", "Appanaickenpalayam", "Vadamadurai", "NGGO Colony", "VSK Nagar", "Narasimhanaickenpalayam"],
    "pannimadai": ["Thudiyalur", "Appanaickenpalayam", "Vadamadurai", "Narasimhanaickenpalayam"],
    "vadavalli": ["Somayampalayam", "Bommanampalayam", "Marudhamalai Road"],
    "kalapatti": ["Nehru Nagar", "Civil Aerodrome", "SITRA", "Codissia"],
    "saravanampatti": ["Kovilpalayam", "Keeranatham", "CHIL SEZ", "Vilankurichi"],
    "karamadai": ["Teachers Colony", "Mettupalayam Road", "Periyanaickenpalayam"],
    "sulur": ["Kannampalayam", "Ravathur", "Pattanam", "Papampatti"],
    "pattanam": ["Sulur", "Papampatti", "Nadupalayam"],
}


@dataclass
class ListingMatch:
    portal: str
    url: str
    title: str = ""
    poster_type: str = "UNKNOWN"
    phone: str = ""
    phone_public: bool = False
    visual_score: float = 0.0
    fact_score: float = 0.0
    overall_score: float = 0.0
    matched_images: int = 0
    notes: str = ""


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _present(value: object) -> bool:
    return str(value or "").strip().upper() not in {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def _normalise_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits if len(digits) == 10 and digits[0] in "6789" else ""


def _decode_search_url(href: str) -> str:
    href = html.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if "uddg" in query:
        return unquote(query["uddg"][0])
    return href


def _portal_for_url(url: str) -> str | None:
    host = urlparse(url).netloc.lower().split(":")[0]
    for portal, domains in PORTALS.items():
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            return portal
    return None


def _locality_terms(job: dict) -> list[str]:
    raw = str(job.get("property_location") or "Coimbatore").strip()
    primary = raw.split(",")[0].strip() or "Coimbatore"
    terms = [primary]
    key = primary.lower()
    terms.extend(NEARBY_LOCALITIES.get(key, []))
    seen: set[str] = set()
    result: list[str] = []
    for item in terms:
        normalized = item.strip()
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            result.append(normalized)
    return result[:7]


def _query_tokens(job: dict) -> list[str]:
    prop = job.get("property") or {}
    values = []
    for key in ("bhk", "land_area", "built_up_area", "price", "facing"):
        value = prop.get(key)
        if _present(value):
            values.append(str(value).strip())
    ptype = prop.get("property_type")
    if _present(ptype):
        values.append(str(ptype).strip())
    return values[:5]


def _search_queries(job: dict, portal: str) -> list[str]:
    domain = PORTALS[portal][0]
    facts = _query_tokens(job)
    compact_facts = " ".join(facts[:4])
    queries = []
    for locality in _locality_terms(job)[:4]:
        queries.append(f'site:{domain} "{locality}" Coimbatore {compact_facts}'.strip())
    return queries


def _search_web(query: str, session: requests.Session) -> list[tuple[str, str]]:
    response = session.get(
        SEARCH_ENDPOINT,
        params={"q": query},
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    body = response.text
    results: list[tuple[str, str]] = []
    anchor_re = re.compile(
        r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.I | re.S,
    )
    for href, title_html in anchor_re.findall(body):
        url = _decode_search_url(href)
        if not url.startswith("http"):
            continue
        title = _clean_text(title_html)
        results.append((url, title))
    return results


def discover_candidates(job: dict, session: requests.Session) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for portal in PORTALS:
        portal_count = 0
        for query in _search_queries(job, portal):
            try:
                results = _search_web(query, session)
            except requests.RequestException as exc:
                print(f"Finder search warning [{portal}]: {exc}")
                continue
            for url, title in results:
                actual_portal = _portal_for_url(url)
                if actual_portal != portal or url in seen:
                    continue
                parsed = urlparse(url)
                path = parsed.path.lower()
                if path in {"", "/"}:
                    continue
                seen.add(url)
                found.append((portal, url, title))
                portal_count += 1
                if portal_count >= MAX_RESULTS_PER_PORTAL:
                    break
            if portal_count >= MAX_RESULTS_PER_PORTAL:
                break
    return found


def _extract_title(raw_html: str, fallback: str) -> str:
    for pattern in (
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<title[^>]*>(.*?)</title>',
    ):
        match = re.search(pattern, raw_html, flags=re.I | re.S)
        if match:
            return _clean_text(match.group(1))[:180]
    return fallback[:180]


def _extract_images(raw_html: str, base_url: str) -> list[str]:
    candidates: list[str] = []
    patterns = (
        r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
        r'["\'](?:image|imageUrl|image_url|original|large)["\']\s*:\s*["\'](https?://[^"\']+)["\']',
    )
    for pattern in patterns:
        candidates.extend(re.findall(pattern, raw_html, flags=re.I | re.S))
    candidates.extend(URL_RE.findall(raw_html))

    seen: set[str] = set()
    output: list[str] = []
    for raw in candidates:
        url = html.unescape(raw).replace("\\/", "/").strip()
        if not url.startswith("http") or not IMAGE_EXT_RE.search(url):
            continue
        if any(token in url.lower() for token in ("logo", "sprite", "icon", "avatar", "favicon")):
            continue
        if url in seen:
            continue
        seen.add(url)
        output.append(url)
        if len(output) >= 18:
            break
    return output


def _classify_poster(text: str) -> str:
    lower = text.lower()
    owner_signals = (
        "posted by owner", "owner property", "contact owner", "individual owner",
        "property owner", "listed by owner", "owner :", "owner:",
    )
    builder_signals = ("posted by builder", "builder", "developer", "promoter")
    broker_signals = (
        "posted by agent", "agent", "broker", "dealer", "real estate consultant",
        "property consultant", "agency",
    )
    if any(signal in lower for signal in owner_signals):
        return "OWNER"
    if any(signal in lower for signal in builder_signals):
        return "BUILDER"
    if any(signal in lower for signal in broker_signals):
        return "BROKER"
    return "UNKNOWN"


def _public_phone(text: str, portal: str) -> str:
    # Only return a complete number that is already present in the public HTML.
    # Never attempt login, OTP, reveal-number APIs or masked-number reconstruction.
    for match in PHONE_RE.finditer(text):
        phone = _normalise_phone(match.group(0))
        if not phone:
            continue
        surrounding = text[max(0, match.start() - 120): match.end() + 120].lower()
        if any(token in surrounding for token in ("customer care", "helpline", "support", "toll free")):
            continue
        return phone
    return ""


def _page_facts_score(job: dict, page_text: str) -> float:
    prop = job.get("property") or {}
    haystack = re.sub(r"[^a-z0-9]+", " ", page_text.lower())
    checks: list[float] = []

    for locality in _locality_terms(job)[:3]:
        needle = re.sub(r"[^a-z0-9]+", " ", locality.lower()).strip()
        if needle:
            checks.append(1.0 if needle in haystack else 0.0)
            if checks[-1] == 1.0:
                break

    for key in ("bhk", "land_area", "built_up_area", "price", "facing"):
        value = prop.get(key)
        if not _present(value):
            continue
        raw = str(value).lower()
        words = [w for w in re.findall(r"[a-z0-9]+", raw) if len(w) >= 2]
        numeric = re.findall(r"\d+(?:\.\d+)?", raw)
        if numeric:
            hit = any(number.replace(".0", "") in haystack for number in numeric)
        else:
            hit = bool(words) and sum(word in haystack for word in words) >= max(1, len(words) // 2)
        checks.append(1.0 if hit else 0.0)

    if not checks:
        return 0.0
    return float(sum(checks) / len(checks))


def _read_image(path: Path) -> np.ndarray | None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return None
    h, w = image.shape[:2]
    if max(h, w) > 900:
        scale = 900.0 / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image


def _decode_remote_image(data: bytes) -> np.ndarray | None:
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)


def _phash(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(small)[:8, :8]
    flat = dct.flatten()
    median = np.median(flat[1:])
    return flat > median


def _phash_similarity(a: np.ndarray, b: np.ndarray) -> float:
    ha, hb = _phash(a), _phash(b)
    return float(1.0 - np.count_nonzero(ha != hb) / ha.size)


def _orb_similarity(a: np.ndarray, b: np.ndarray) -> float:
    gray_a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=900)
    kp_a, des_a = orb.detectAndCompute(gray_a, None)
    kp_b, des_b = orb.detectAndCompute(gray_b, None)
    if des_a is None or des_b is None or len(kp_a) < 8 or len(kp_b) < 8:
        return 0.0
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(des_a, des_b, k=2)
    good = [first for first, second in pairs if first.distance < 0.72 * second.distance]
    denominator = max(12, min(len(kp_a), len(kp_b)))
    return float(min(1.0, len(good) / denominator * 3.0))


def image_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # pHash is strong for resized/cropped copies; ORB helps with alternate crops/angles.
    phash = _phash_similarity(a, b)
    orb = _orb_similarity(a, b)
    return float(max(phash * 0.92, 0.45 * phash + 0.55 * orb))


def _visual_score(
    reference_images: list[np.ndarray],
    image_urls: list[str],
    session: requests.Session,
) -> tuple[float, int]:
    best_scores: list[float] = []
    matched_images = 0
    for image_url in image_urls[:12]:
        try:
            response = session.get(image_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            if len(response.content) > 8_000_000:
                continue
            candidate = _decode_remote_image(response.content)
        except requests.RequestException:
            continue
        if candidate is None or min(candidate.shape[:2]) < 160:
            continue
        score = max((image_similarity(ref, candidate) for ref in reference_images), default=0.0)
        best_scores.append(score)
        if score >= 0.72:
            matched_images += 1
    if not best_scores:
        return 0.0, 0
    best_scores.sort(reverse=True)
    strongest = best_scores[:3]
    # Use the strongest photo heavily; multiple matching photos add confidence.
    aggregate = strongest[0]
    if len(strongest) > 1:
        aggregate = 0.75 * strongest[0] + 0.25 * (sum(strongest[1:]) / len(strongest[1:]))
    return float(min(1.0, aggregate)), matched_images


def inspect_candidate(
    job: dict,
    portal: str,
    url: str,
    search_title: str,
    reference_images: list[np.ndarray],
    session: requests.Session,
) -> ListingMatch | None:
    try:
        response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        return ListingMatch(portal=portal, url=url, title=search_title, notes=f"page blocked/unavailable: {exc}")

    final_url = response.url
    raw_html = response.text[:4_000_000]
    page_text = _clean_text(raw_html)
    title = _extract_title(raw_html, search_title)
    poster_type = _classify_poster(page_text)
    phone = _public_phone(page_text, portal)
    images = _extract_images(raw_html, final_url)
    visual_score, matched_images = _visual_score(reference_images, images, session)
    fact_score = _page_facts_score(job, f"{title} {page_text}")

    if visual_score > 0:
        overall = 0.68 * visual_score + 0.32 * fact_score
    else:
        # Text-only candidates remain useful as links but cannot be called a photo match.
        overall = min(0.62, 0.62 * fact_score)

    notes = ""
    if not images:
        notes = "listing photos not accessible in public HTML"
    elif visual_score < 0.55:
        notes = "photos available but no strong visual match"

    return ListingMatch(
        portal=portal,
        url=final_url,
        title=title,
        poster_type=poster_type,
        phone=phone,
        phone_public=bool(phone),
        visual_score=round(visual_score, 3),
        fact_score=round(fact_score, 3),
        overall_score=round(overall, 3),
        matched_images=matched_images,
        notes=notes,
    )


def find_sources(job: dict) -> list[ListingMatch]:
    with requests.Session() as session, tempfile.TemporaryDirectory(prefix="property-finder-") as tmp:
        frames = extract_reference_frames(job, Path(tmp) / "reference", target_count=7)
        reference_images = [image for path in frames if (image := _read_image(path)) is not None]
        if not reference_images:
            raise RuntimeError("Property finder could not read any original YouTube reference frames")

        candidates = discover_candidates(job, session)
        matches: list[ListingMatch] = []
        for portal, url, title in candidates:
            match = inspect_candidate(job, portal, url, title, reference_images, session)
            if match is not None:
                matches.append(match)
        matches.sort(key=lambda item: (item.overall_score, item.visual_score, item.fact_score), reverse=True)
        return matches


def _portal_label(portal: str) -> str:
    return {
        "housing": "Housing.com",
        "realestateindia": "RealEstateIndia",
        "99acres": "99acres",
        "magicbricks": "MagicBricks",
    }.get(portal, portal)


def _safe_telegram_url(url: str) -> str:
    return html.escape(url, quote=True)


def format_telegram_report(job: dict, matches: list[ListingMatch]) -> str:
    video_id = str(job.get("video_id") or "").strip()
    prop = job.get("property") or {}
    lines = [
        "🔎 <b>PROPERTY SOURCE FINDER</b>",
        f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>",
        f"<b>Location:</b> {html.escape(str(job.get('property_location') or 'Coimbatore'))}",
    ]
    summary = " | ".join(
        str(prop.get(key))
        for key in ("bhk", "land_area", "built_up_area", "price")
        if _present(prop.get(key))
    )
    if summary:
        lines.append(f"<b>Facts:</b> {html.escape(summary)}")
    lines.append("")

    reportable = [m for m in matches if m.overall_score >= MIN_REPORT_SCORE][:8]
    if not reportable:
        lines.extend([
            "No high-confidence owner/listing source found on Housing, RealEstateIndia, 99acres or MagicBricks.",
            "The finder did not expose or reconstruct any protected phone number.",
        ])
        return "\n".join(lines)

    for index, match in enumerate(reportable, 1):
        confidence = int(round(match.overall_score * 100))
        visual = int(round(match.visual_score * 100))
        facts = int(round(match.fact_score * 100))
        marker = "✅" if match.overall_score >= HIGH_CONFIDENCE_SCORE else "🟡"
        lines.extend([
            f"{marker} <b>{index}. {_portal_label(match.portal)}</b>",
            f"Match: <b>{confidence}%</b> | Photo: {visual}% | Facts: {facts}%",
            f"Posted by: <b>{html.escape(match.poster_type)}</b>",
        ])
        if match.phone_public:
            lines.append(f"Public phone: <code>{html.escape(match.phone)}</code>")
        elif match.portal in {"99acres", "magicbricks"}:
            lines.append("Phone: protected/not publicly exposed — use exact listing link")
        else:
            lines.append("Phone: not publicly exposed in the fetched page")
        lines.append(f'<a href="{_safe_telegram_url(match.url)}">Open exact listing</a>')
        if match.notes:
            lines.append(f"Note: {html.escape(match.notes[:160])}")
        lines.append("")

    best = reportable[0]
    lines.append(
        f"<b>Best source:</b> {_portal_label(best.portal)} — "
        f"{html.escape(best.poster_type)} — {int(round(best.overall_score * 100))}%"
    )
    lines.append("Only complete phone numbers already visible in public page HTML are returned; masked/login/OTP contacts are never bypassed.")
    return "\n".join(lines)


def send_telegram_report(job: dict, matches: list[ListingMatch], bot_token: str, chat_id: str) -> int:
    text = format_telegram_report(job, matches)
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram rejected property source report: {body}")
    return int((body.get("result") or {}).get("message_id") or 0)


def _ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Match original YouTube property frames to public portal listings")
    parser.add_argument("--ids-file", type=Path, default=Path("data/new_render_ids.txt"))
    parser.add_argument("--video-id", default="")
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--no-telegram", action="store_true")
    args = parser.parse_args()

    video_ids = [args.video_id.strip()] if args.video_id.strip() else _ids(args.ids_file)
    if not video_ids:
        print("No property IDs supplied to source finder.")
        return

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    all_results: dict[str, list[dict]] = {}

    for video_id in video_ids:
        job_path = JOBS / f"{video_id}.json"
        if not job_path.exists():
            print(f"Property finder skipped missing job: {job_path}")
            continue
        job = json.loads(job_path.read_text(encoding="utf-8"))
        try:
            matches = find_sources(job)
            all_results[video_id] = [asdict(item) for item in matches]
            if not args.no_telegram and bot_token and chat_id:
                message_id = send_telegram_report(job, matches, bot_token, chat_id)
                print(f"Sent property source finder report: {video_id} message_id={message_id}")
            else:
                print(format_telegram_report(job, matches))
        except Exception as exc:
            print(f"Property source finder warning for {video_id}: {exc}")
            if not args.no_telegram and bot_token and chat_id:
                fallback = (
                    "🔎 <b>PROPERTY SOURCE FINDER</b>\n"
                    f"<b>Video ID:</b> <code>{html.escape(video_id)}</code>\n"
                    "Finder could not complete this search. The normal Gemini property prompt is unaffected.\n"
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
