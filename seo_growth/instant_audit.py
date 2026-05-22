from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


USER_AGENT = "OpenSEOGrowthBot/0.1 (+https://github.com/open-seo-growth)"
TIMEOUT = 12


def normalize_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValueError("Enter a website URL first.")
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if not parsed.netloc:
        raise ValueError("Enter a valid website URL.")
    path = parsed.path or "/"
    return parsed._replace(path=path, params="", fragment="").geturl()


@dataclass
class PageSignals:
    title: str = ""
    description: str = ""
    canonical: str = ""
    robots_meta: str = ""
    h1: list[str] = field(default_factory=list)
    images: int = 0
    images_missing_alt: int = 0
    links_internal: int = 0
    links_external: int = 0
    schema_types: list[str] = field(default_factory=list)
    ga4_detected: bool = False
    gtm_detected: bool = False


class SignalParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.signals = PageSignals()
        self._in_title = False
        self._in_h1 = False
        self._title_parts: list[str] = []
        self._h1_parts: list[str] = []
        self._json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
            self._h1_parts = []
        elif tag == "meta":
            name = (attrs_map.get("name") or attrs_map.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.signals.description:
                self.signals.description = attrs_map.get("content", "").strip()
            if name == "robots":
                self.signals.robots_meta = attrs_map.get("content", "").strip()
        elif tag == "link":
            if attrs_map.get("rel", "").lower() == "canonical":
                self.signals.canonical = attrs_map.get("href", "").strip()
        elif tag == "img":
            self.signals.images += 1
            if not attrs_map.get("alt", "").strip():
                self.signals.images_missing_alt += 1
        elif tag == "a":
            href = attrs_map.get("href", "").strip()
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                return
            resolved = urlparse(urljoin(self.base_url, href))
            base = urlparse(self.base_url)
            if resolved.netloc and resolved.netloc == base.netloc:
                self.signals.links_internal += 1
            elif resolved.netloc:
                self.signals.links_external += 1
        elif tag == "script":
            src = attrs_map.get("src", "")
            if "googletagmanager.com/gtag/js" in src:
                self.signals.ga4_detected = True
            if "googletagmanager.com/gtm.js" in src:
                self.signals.gtm_detected = True
            if attrs_map.get("type", "").lower() == "application/ld+json":
                self._json_ld = True
                self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            self.signals.title = " ".join("".join(self._title_parts).split())
        elif tag == "h1":
            self._in_h1 = False
            text = " ".join("".join(self._h1_parts).split())
            if text:
                self.signals.h1.append(text)
        elif tag == "script" and self._json_ld:
            self._json_ld = False
            raw = "".join(self._json_ld_parts)
            for match in re.findall(r'"@type"\s*:\s*"([^"]+)"', raw):
                if match not in self.signals.schema_types:
                    self.signals.schema_types.append(match)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._in_h1:
            self._h1_parts.append(data)
        if self._json_ld:
            self._json_ld_parts.append(data)
        if "G-" in data or "gtag(" in data:
            self.signals.ga4_detected = True
        if "GTM-" in data:
            self.signals.gtm_detected = True


def fetch_url(url: str) -> requests.Response:
    response = requests.get(
        url,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def fetch_optional(url: str) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
        return {"ok": response.status_code < 400, "status_code": response.status_code, "url": response.url}
    except Exception as exc:
        return {"ok": False, "error": exc.__class__.__name__, "message": str(exc), "url": url}


def score_check(ok: bool, weight: int) -> int:
    return weight if ok else 0


def instant_audit(raw_url: str) -> dict[str, Any]:
    url = normalize_url(raw_url)
    response = fetch_url(url)
    html = response.text[:1_500_000]
    parser = SignalParser(response.url)
    parser.feed(html)
    signals = parser.signals
    parsed = urlparse(response.url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots = fetch_optional(urljoin(origin, "/robots.txt"))
    sitemap = fetch_optional(urljoin(origin, "/sitemap.xml"))

    title_len = len(signals.title)
    description_len = len(signals.description)
    checks = [
        {"id": "http_ok", "label": "Homepage returns a successful response", "ok": response.status_code < 400, "weight": 12, "fix": "Fix server errors or redirect loops before optimizing content."},
        {"id": "title", "label": "Title tag is present and within a useful range", "ok": 20 <= title_len <= 65, "weight": 12, "fix": "Write a specific title around 45-60 characters."},
        {"id": "description", "label": "Meta description is present", "ok": 70 <= description_len <= 170, "weight": 10, "fix": "Add a concise search snippet that explains the page value."},
        {"id": "h1", "label": "Exactly one H1 found", "ok": len(signals.h1) == 1, "weight": 10, "fix": "Use one clear H1 that matches the page intent."},
        {"id": "canonical", "label": "Canonical URL is declared", "ok": bool(signals.canonical), "weight": 8, "fix": "Add a canonical link to the preferred URL."},
        {"id": "robots_meta", "label": "Page is not blocked by robots meta", "ok": "noindex" not in signals.robots_meta.lower(), "weight": 10, "fix": "Remove noindex unless the page should stay out of Google."},
        {"id": "robots_txt", "label": "robots.txt is reachable", "ok": bool(robots.get("ok")), "weight": 7, "fix": "Expose robots.txt at the site root."},
        {"id": "sitemap", "label": "sitemap.xml is reachable", "ok": bool(sitemap.get("ok")), "weight": 7, "fix": "Publish a sitemap and submit it in Search Console."},
        {"id": "image_alt", "label": "Images have alt text", "ok": signals.images == 0 or signals.images_missing_alt == 0, "weight": 6, "fix": "Add descriptive alt text to important images."},
        {"id": "internal_links", "label": "Internal links exist", "ok": signals.links_internal > 0, "weight": 6, "fix": "Add links to important pages so Google and users can continue."},
        {"id": "schema", "label": "Structured data is present", "ok": bool(signals.schema_types), "weight": 6, "fix": "Add Organization, WebSite, Article, Product, or relevant schema."},
        {"id": "analytics", "label": "Analytics tag is detectable", "ok": signals.ga4_detected or signals.gtm_detected, "weight": 6, "fix": "Install GA4 or Google Tag Manager before expecting traffic reports."},
    ]
    score = sum(score_check(item["ok"], item["weight"]) for item in checks)
    blockers = [item for item in checks if not item["ok"] and item["weight"] >= 10]
    next_steps = [
        item["fix"]
        for item in sorted(checks, key=lambda item: (item["ok"], -item["weight"]))
        if not item["ok"]
    ][:5]
    quick_wins = [
        {
            "title": item["label"],
            "action": item["fix"],
            "impact": "High" if item["weight"] >= 10 else "Medium" if item["weight"] >= 7 else "Low",
        }
        for item in sorted(checks, key=lambda item: (item["ok"], -item["weight"]))
        if not item["ok"]
    ][:6]
    no_google_report = {
        "title": "No-Google SEO starter report",
        "positioning": "Use this as the first deliverable before the customer has GA4 or Search Console connected.",
        "what_you_can_sell_now": [
            "Technical and on-page readiness audit",
            "Indexability and metadata cleanup plan",
            "Analytics/Search Console installation checklist",
            "A follow-up measurement plan for the first 30 days after setup",
        ],
        "limits": [
            "No verified Google clicks, impressions, CTR, or ranking history yet.",
            "No GA4 sessions or conversion history unless a tag is already installed.",
        ],
        "handoff": [
            "Fix the readiness gaps first.",
            "Install GA4 and verify Search Console.",
            "Wait for data to accrue, then run the growth dashboard.",
        ],
    }
    return {
        "ok": True,
        "audited_url": response.url,
        "status_code": response.status_code,
        "score": score,
        "grade": "Strong" if score >= 80 else "Developing" if score >= 60 else "Needs setup",
        "summary": {
            "title": signals.title,
            "title_length": title_len,
            "description": signals.description,
            "description_length": description_len,
            "h1": signals.h1,
            "canonical": signals.canonical,
            "robots_meta": signals.robots_meta,
            "images": signals.images,
            "images_missing_alt": signals.images_missing_alt,
            "internal_links": signals.links_internal,
            "external_links": signals.links_external,
            "schema_types": signals.schema_types,
            "ga4_detected": signals.ga4_detected,
            "gtm_detected": signals.gtm_detected,
            "robots": robots,
            "sitemap": sitemap,
        },
        "checks": checks,
        "blockers": blockers,
        "next_steps": next_steps,
        "quick_wins": quick_wins,
        "no_google_report": no_google_report,
        "google_data_ready": signals.ga4_detected or signals.gtm_detected,
        "message": "Instant audit completed. Connect Google when you want verified clicks, impressions, rankings, and sessions.",
    }
