from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from google import genai
from google.genai import types

import google_maps_source_finder as public_search


MODEL = os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash")
MAX_PAGES = int(os.environ.get("PUBLIC_IMAGE_MAX_PAGES", "8"))
MAX_IMAGES = int(os.environ.get("PUBLIC_IMAGE_MAX_IMAGES", "12"))
MAX_IMAGE_BYTES = 6 * 1024 * 1024
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s.-]?)?([6-9]\d{4}[\s.-]?\d{5})(?!\d)")


@dataclass
class ImageContact:
    source: str
    query: str
    url: str
    phone: str
    classification: str
    confidence: float
    evidence: str
    public_phone: bool = True
    protected_contact: bool = False


def _normalise_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits if len(digits) == 10 and digits[0] in "6789" else ""


def _project_query(job: dict) -> str:
    aliases = public_search._project_aliases(job)
    if aliases:
        return aliases[0]
    return str(job.get("property_location") or "Coimbatore").split(",")[0].strip()


def _candidate_pages(job: dict, session: requests.Session) -> list[tuple[str, str]]:
    base = _project_query(job)
    location = str(job.get("property_location") or "Coimbatore")
    queries = [
        f'"{base}" {location}',
        f'"{base}" Coimbatore villa',
        f'"{base}" Coimbatore property',
        f'"{base}" phone',
    ]
    pages: list[tuple[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        for endpoint in ("https://www.bing.com/search", "https://html.duckduckgo.com/html/"):
            try:
                _, raw = public_search._search_html(endpoint, query, session)
            except requests.RequestException:
                continue
            for url in public_search._extract_result_urls(raw):
                if url in seen:
                    continue
                seen.add(url)
                pages.append((query, url))
                if len(pages) >= MAX_PAGES:
                    return pages
    return pages


def _image_urls(page_url: str, raw: str) -> list[str]:
    found: list[str] = []
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        r'<img[^>]+src=["\']([^"\']+)',
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for value in re.findall(pattern, raw or "", flags=re.I):
            url = urljoin(page_url, value.strip())
            if not url.startswith("http") or url in seen:
                continue
            seen.add(url)
            found.append(url)
            if len(found) >= 10:
                return found
    return found


def _download_image(session: requests.Session, url: str) -> tuple[bytes, str] | None:
    try:
        response = session.get(url, headers=public_search.HEADERS, timeout=public_search.REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException:
        return None
    content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        return None
    payload = response.content
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        return None
    return payload, content_type


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return {}


def _vision_extract(image_bytes: bytes, mime_type: str, job: dict) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prop = job.get("property") or {}
    prompt = f"""
Inspect this PUBLIC real-estate image only for visible signboard/contact evidence.
Return JSON only with keys:
phones: array of complete phone numbers visibly readable in the image,
project_name: string,
business_name: string,
role: one of OWNER, POSSIBLE OWNER, BUILDER/DEVELOPER, BROKER/AGENT, UNKNOWN,
confidence: number 0 to 1,
evidence: short description of exactly what is visibly present.

Rules:
- Never reconstruct or guess a hidden/blurred/masked/incomplete number.
- Only return a phone if every digit is visibly readable.
- A project/developer board phone is BUILDER/DEVELOPER unless the image explicitly says owner/direct owner.
- Use UNKNOWN when role is not visible.

Property context for relevance only, not for guessing:
Location: {job.get('property_location') or ''}
Type: {prop.get('property_type') or ''}
Land: {prop.get('land_area') or ''}
Built-up: {prop.get('built_up_area') or ''}
Price: {prop.get('price') or ''}
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return _parse_json(response.text or "")


def find_public_image_contacts(job: dict) -> list[ImageContact]:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        return []
    contacts: list[ImageContact] = []
    seen_phones: set[tuple[str, str]] = set()
    image_count = 0
    with requests.Session() as session:
        for query, page_url in _candidate_pages(job, session):
            try:
                page = session.get(page_url, headers=public_search.HEADERS, timeout=public_search.REQUEST_TIMEOUT, allow_redirects=True)
                page.raise_for_status()
            except requests.RequestException:
                continue
            for image_url in _image_urls(page.url, page.text[:4_000_000]):
                if image_count >= MAX_IMAGES:
                    return contacts
                downloaded = _download_image(session, image_url)
                if not downloaded:
                    continue
                image_count += 1
                payload, mime_type = downloaded
                try:
                    result = _vision_extract(payload, mime_type, job)
                except Exception:
                    continue
                role = str(result.get("role") or "UNKNOWN").upper()
                if role not in {"OWNER", "POSSIBLE OWNER", "BUILDER/DEVELOPER", "BROKER/AGENT", "UNKNOWN"}:
                    role = "UNKNOWN"
                confidence = float(result.get("confidence") or 0.0)
                evidence = str(result.get("evidence") or "Visible public signboard/contact in source image.")[:320]
                for raw_phone in result.get("phones") or []:
                    phone = _normalise_phone(str(raw_phone))
                    if not phone or (phone, page.url) in seen_phones:
                        continue
                    # Final format check independent of the model output.
                    if not PHONE_RE.search(phone):
                        continue
                    seen_phones.add((phone, page.url))
                    contacts.append(ImageContact(
                        source="Public image/signboard via Gemini vision",
                        query=query,
                        url=page.url,
                        phone=phone,
                        classification=role,
                        confidence=max(0.55, min(0.96, confidence)),
                        evidence=evidence,
                    ))
    return contacts
