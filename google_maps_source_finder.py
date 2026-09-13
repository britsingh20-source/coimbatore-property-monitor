from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import asdict, dataclass
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s.-]?)?([6-9]\d{4}[\s.-]?\d{5})(?!\d)")
REQUEST_TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

# Public-source discovery only. A source may be searched/indexed even when its own contact UI is protected.
PUBLIC_SOURCES = {
    "Google Maps": ("google.com", "maps.google.com"),
    "OLX": ("olx.in",),
    "Housing": ("housing.com",),
    "RealEstateIndia": ("realestateindia.com",),
    "99acres": ("99acres.com",),
    "MagicBricks": ("magicbricks.com",),
    "Facebook": ("facebook.com",),
    "Instagram": ("instagram.com",),
    "YouTube": ("youtube.com", "youtu.be"),
}


@dataclass
class MapSourceContact:
    source: str
    query: str
    url: str
    phone: str = ""
    classification: str = "UNKNOWN"
    confidence: float = 0.0
    evidence: str = ""
    public_phone: bool = False
    protected_contact: bool = False


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
    # Explicit owner wording outranks generic layout/developer words.
    if any(x in lower for x in ("direct owner", "posted by owner", "owner property", "owner listing", "property owner")):
        return "OWNER"
    if any(x in lower for x in ("builder", "developer", "promoter", "layout promoter", "project sales", "site sale")):
        return "BUILDER/DEVELOPER"
    if any(x in lower for x in ("broker", "agent", "consultant", "channel partner", "property dealer")):
        return "BROKER/AGENT"
    if "owner" in lower:
        return "POSSIBLE OWNER"
    return "UNKNOWN"


def _project_name(job: dict) -> str:
    facts = str(job.get("verified_facts") or "")
    match = re.search(r"Project\s*Name\s*:\s*([^,;|]+)", facts, flags=re.I)
    if match:
        return match.group(1).strip()
    location = str(job.get("property_location") or "").strip()
    # Preserve a named enclave/nagar/layout in the location if the analyzer already identified it.
    first = location.split(",")[0].strip()
    return first if any(k in first.lower() for k in ("enclave", "nagar", "garden", "layout", "avenue", "township")) else ""


def _search_terms(job: dict) -> list[str]:
    location = str(job.get("property_location") or "Coimbatore").strip()
    project = _project_name(job)
    prop = job.get("property") or {}
    terms = [location]
    if project and project.lower() not in location.lower():
        terms.insert(0, f"{project} {location}")
    land = str(prop.get("land_area") or "").replace("NOT SPECIFIED", "").strip()
    price = str(prop.get("price") or "").replace("NOT SPECIFIED", "").strip()
    if project:
        terms.append(f"{project} Coimbatore {land} {price}".strip())
    # Deduplicate while retaining order.
    out: list[str] = []
    seen: set[str] = set()
    for item in terms:
        item = re.sub(r"\s+", " ", item).strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out[:4]


def _source_for_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for label, domains in PUBLIC_SOURCES.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return label
    return "Public web"


def _unwrap_search_url(url: str) -> str:
    url = html.unescape(url or "")
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc:
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target) if target else url
    if "bing.com" in parsed.netloc and parsed.path.startswith("/ck/"):
        return url
    return url


def _extract_result_urls(raw: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', raw or "", flags=re.I):
        url = _unwrap_search_url(href)
        if not url.startswith("http"):
            continue
        host = (urlparse(url).hostname or "").lower()
        if any(x in host for x in ("bing.com", "duckduckgo.com", "microsoft.com")):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls[:80]


def _extract_contacts_from_text(source: str, query: str, url: str, text: str) -> list[MapSourceContact]:
    contacts: list[MapSourceContact] = []
    seen: set[str] = set()
    for match in PHONE_RE.finditer(text or ""):
        phone = _normalize_phone(match.group(0))
        if not phone or phone in seen:
            continue
        seen.add(phone)
        around = (text[max(0, match.start() - 220): match.end() + 220] or "").strip()
        classification = _classify(around)
        confidence = 0.66
        if classification == "OWNER":
            confidence = 0.88
        elif classification == "POSSIBLE OWNER":
            confidence = 0.76
        elif classification == "BUILDER/DEVELOPER":
            confidence = 0.82
        elif classification == "BROKER/AGENT":
            confidence = 0.78
        contacts.append(MapSourceContact(
            source=source,
            query=query,
            url=url,
            phone=phone,
            classification=classification,
            confidence=confidence,
            evidence=around[:320],
            public_phone=True,
        ))
    return contacts


def _protected_hint(text: str) -> bool:
    lower = (text or "").lower()
    return any(x in lower for x in (
        "contact owner", "view phone", "show phone", "get phone", "login to view", "sign in to view",
        "contact seller", "chat with seller", "get contact", "request callback",
    ))


def _search_html(endpoint: str, query: str, session: requests.Session) -> tuple[str, str]:
    response = session.get(endpoint, params={"q": query}, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.url, response.text


def _source_queries(job: dict) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    terms = _search_terms(job)
    for term in terms:
        # General discovery captures builder sites and public business pages too.
        queries.extend([
            ("Public web", f'"{term}" phone'),
            ("Public web", f'"{term}" contact owner'),
            ("Public web", f'"{term}" builder developer contact'),
        ])
        for source, domains in PUBLIC_SOURCES.items():
            # One primary domain is enough for site: discovery; aliases are caught when result URLs are parsed.
            queries.append((source, f'site:{domains[0]} "{term}"'))
            if source in {"OLX", "Housing", "RealEstateIndia", "99acres", "MagicBricks"}:
                queries.append((source, f'site:{domains[0]} "{term}" owner'))
    # Keep query count controlled for scheduled runs.
    seen: set[str] = set()
    output: list[tuple[str, str]] = []
    for source, query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            output.append((source, query))
    return output[:42]


def _inspect_public_page(source: str, query: str, url: str, session: requests.Session) -> list[MapSourceContact]:
    try:
        response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException:
        return []
    raw = response.text[:4_000_000]
    text = _clean_text(raw)
    contacts = _extract_contacts_from_text(source, query, response.url, text)
    if contacts:
        return contacts
    if _protected_hint(text):
        return [MapSourceContact(
            source=source,
            query=query,
            url=response.url,
            classification=_classify(text),
            confidence=0.42,
            evidence="Public listing found, but phone is not exposed in accessible page text.",
            protected_contact=True,
        )]
    return []


def find_google_maps_contacts(job: dict) -> list[MapSourceContact]:
    """Discover complete public phone numbers and exact public listing URLs across owner-source paths.

    Historical name retained so existing imports/workflows remain compatible. No OTP/login/CAPTCHA or masked-number
    bypass is attempted. Search-index snippets and publicly accessible pages are the only sources inspected.
    """
    endpoints = [
        ("Bing", "https://www.bing.com/search"),
        ("DuckDuckGo", "https://html.duckduckgo.com/html/"),
    ]
    contacts: list[MapSourceContact] = []
    seen_contacts: set[tuple[str, str, str]] = set()
    seen_pages: set[str] = set()

    with requests.Session() as session:
        for intended_source, sq in _source_queries(job):
            for engine, endpoint in endpoints:
                try:
                    result_url, raw = _search_html(endpoint, sq, session)
                except requests.RequestException:
                    continue

                # Search-result text itself can contain a public phone in the snippet.
                result_text = _clean_text(raw)
                for item in _extract_contacts_from_text(f"{engine} indexed {intended_source}", sq, result_url, result_text):
                    key = (item.phone, item.source, item.url)
                    if key not in seen_contacts:
                        seen_contacts.add(key)
                        contacts.append(item)

                # Inspect exact candidate pages when they are publicly reachable.
                for candidate in _extract_result_urls(raw)[:12]:
                    if candidate in seen_pages:
                        continue
                    seen_pages.add(candidate)
                    actual_source = _source_for_url(candidate)
                    if intended_source != "Public web" and actual_source not in {intended_source, "Public web"}:
                        continue
                    for item in _inspect_public_page(actual_source, sq, candidate, session):
                        key = (item.phone, item.source, item.url)
                        if key not in seen_contacts:
                            seen_contacts.add(key)
                            contacts.append(item)

        # Direct public Maps search remains a final source; useful when phone/place text exists in HTML payload.
        base_term = _search_terms(job)[0] if _search_terms(job) else "Coimbatore"
        maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(base_term)}"
        try:
            response = session.get(maps_url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if response.ok:
                text = _clean_text(response.text[:4_000_000])
                for item in _extract_contacts_from_text("Google Maps public page", base_term, response.url, text):
                    key = (item.phone, item.source, item.url)
                    if key not in seen_contacts:
                        seen_contacts.add(key)
                        contacts.append(item)
        except requests.RequestException:
            pass

    # Cross-source corroboration increases confidence without changing the role label to OWNER automatically.
    phone_source_counts: Counter[str] = Counter()
    for item in contacts:
        if item.phone:
            phone_source_counts[item.phone] += 1
    for item in contacts:
        if item.phone and phone_source_counts[item.phone] >= 2:
            item.confidence = min(0.96, item.confidence + 0.08)
            item.evidence = (item.evidence + f" | corroborated across {phone_source_counts[item.phone]} public hits").strip(" |")

    contacts.sort(key=lambda x: (bool(x.phone), x.confidence, x.classification == "OWNER"), reverse=True)
    return contacts[:30]


def as_jsonable(contacts: list[MapSourceContact]) -> list[dict]:
    return [asdict(item) for item in contacts]
