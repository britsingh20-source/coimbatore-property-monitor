from __future__ import annotations

import html
import re
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus, urlparse

import requests


PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s.-]?)?([6-9]\d{4}[\s.-]?\d{5})(?!\d)")
REQUEST_TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}


@dataclass
class MapSourceContact:
    source: str
    query: str
    url: str
    phone: str
    classification: str = "UNKNOWN"
    confidence: float = 0.0
    evidence: str = ""


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits if len(digits) == 10 and digits[0] in "6789" else ""


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _classify(text: str) -> str:
    lower = (text or "").lower()
    if any(x in lower for x in ("builder", "developer", "promoter", "layout", "enclave", "site sale")):
        return "BUILDER/DEVELOPER"
    if any(x in lower for x in ("owner", "direct owner", "owner property")):
        return "OWNER"
    if any(x in lower for x in ("broker", "agent", "consultant", "real estate")):
        return "BROKER/AGENT"
    return "UNKNOWN"


def _location_query(job: dict) -> str:
    location = str(job.get("property_location") or "Coimbatore").strip()
    verified = str(job.get("verified_facts") or "")
    # Prefer named layout/project terms when present in the location string.
    return f"{location} {verified[:180]}".strip()


def _extract_contacts_from_text(source: str, query: str, url: str, text: str) -> list[MapSourceContact]:
    contacts: list[MapSourceContact] = []
    classification = _classify(text)
    seen: set[str] = set()
    for match in PHONE_RE.finditer(text or ""):
        phone = _normalize_phone(match.group(0))
        if not phone or phone in seen:
            continue
        seen.add(phone)
        around = (text[max(0, match.start() - 180): match.end() + 180] or "").strip()
        confidence = 0.72
        if classification == "BUILDER/DEVELOPER":
            confidence = 0.82
        elif classification == "OWNER":
            confidence = 0.86
        contacts.append(MapSourceContact(
            source=source,
            query=query,
            url=url,
            phone=phone,
            classification=classification,
            confidence=confidence,
            evidence=around[:260],
        ))
    return contacts


def _search_html(endpoint: str, query: str, session: requests.Session) -> tuple[str, str]:
    if "bing.com" in endpoint:
        response = session.get(endpoint, params={"q": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    else:
        response = session.get(endpoint, params={"q": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.url, response.text


def find_google_maps_contacts(job: dict) -> list[MapSourceContact]:
    query = _location_query(job)
    search_queries = [
        f'"{query}" phone',
        f'"{query}" contact',
        f'"{query}" Google Maps',
        f'site:google.com/maps "{query}"',
        f'site:maps.google.com "{query}"',
    ]
    endpoints = [
        ("Bing", "https://www.bing.com/search"),
        ("DuckDuckGo", "https://html.duckduckgo.com/html/"),
    ]

    contacts: list[MapSourceContact] = []
    seen: set[tuple[str, str]] = set()

    with requests.Session() as session:
        for label, endpoint in endpoints:
            for sq in search_queries:
                try:
                    result_url, raw = _search_html(endpoint, sq, session)
                except requests.RequestException:
                    continue
                text = _clean_text(raw)
                for item in _extract_contacts_from_text(f"{label} indexed Maps/web", sq, result_url, text):
                    key = (item.phone, item.source)
                    if key not in seen:
                        seen.add(key)
                        contacts.append(item)

        # Try the public Google Maps search result page directly. It is JS-heavy, but some place text
        # and phone values are occasionally present in the HTML payload and can be captured safely.
        maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
        try:
            response = session.get(maps_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if response.ok:
                text = _clean_text(response.text[:4_000_000])
                for item in _extract_contacts_from_text("Google Maps public page", query, response.url, text):
                    key = (item.phone, item.source)
                    if key not in seen:
                        seen.add(key)
                        contacts.append(item)
        except requests.RequestException:
            pass

    # Prefer higher-confidence source/classification first.
    contacts.sort(key=lambda x: (x.confidence, x.classification != "UNKNOWN"), reverse=True)
    return contacts[:12]


def as_jsonable(contacts: list[MapSourceContact]) -> list[dict]:
    return [asdict(item) for item in contacts]
