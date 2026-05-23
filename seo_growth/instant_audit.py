from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


USER_AGENT = "OpenSEOGrowthBot/0.1 (+https://github.com/open-seo-growth)"
TIMEOUT = 12
QUESTION_RE = re.compile(r"(^|\s)(who|what|when|where|why|how|can|does|do|is|are|should|which)\b|\?", re.I)
TRUST_RE = re.compile(r"\b(about us|about|contact|privacy|terms|editorial|author|reviewed by|sources|references)\b", re.I)


def normalize_schema_type(value: str) -> str:
    item = str(value or "").strip()
    if not item:
        return ""
    if "/" in item:
        item = item.rstrip("/").rsplit("/", 1)[-1]
    if "#" in item:
        item = item.rsplit("#", 1)[-1]
    return item.strip()


def collect_schema_types(value: Any) -> list[str]:
    found: list[str] = []

    def add(raw: Any) -> None:
        if isinstance(raw, str):
            item = normalize_schema_type(raw)
            if item and item not in found:
                found.append(item)
        elif isinstance(raw, list):
            for child in raw:
                add(child)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            add(node.get("@type"))
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return found


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
    headings: dict[str, list[str]] = field(default_factory=lambda: {"h2": [], "h3": [], "h4": []})
    body_text: str = ""
    question_headings: list[str] = field(default_factory=list)
    author: str = ""
    site_name: str = ""
    images: int = 0
    images_missing_alt: int = 0
    links_internal: int = 0
    links_external: int = 0
    external_hosts: list[str] = field(default_factory=list)
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
        self._heading_tag = ""
        self._heading_parts: list[str] = []
        self._body_parts: list[str] = []
        self._json_ld = False
        self._json_ld_parts: list[str] = []
        self._ignore_text_depth = 0

    def add_schema_type(self, raw: str) -> None:
        item = normalize_schema_type(raw)
        if item and item not in self.signals.schema_types:
            self.signals.schema_types.append(item)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        for raw_item in re.split(r"\s+", attrs_map.get("itemtype", "")):
            if "schema.org" in raw_item:
                self.add_schema_type(raw_item)
        for raw_item in re.split(r"\s+", attrs_map.get("typeof", "")):
            self.add_schema_type(raw_item)
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
            self._h1_parts = []
        elif tag in self.signals.headings:
            self._heading_tag = tag
            self._heading_parts = []
        elif tag == "meta":
            name = (attrs_map.get("name") or attrs_map.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.signals.description:
                self.signals.description = attrs_map.get("content", "").strip()
            if name == "robots":
                self.signals.robots_meta = attrs_map.get("content", "").strip()
            if name in {"author", "article:author"} and not self.signals.author:
                self.signals.author = attrs_map.get("content", "").strip()
            if name == "og:site_name" and not self.signals.site_name:
                self.signals.site_name = attrs_map.get("content", "").strip()
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
                if resolved.netloc not in self.signals.external_hosts:
                    self.signals.external_hosts.append(resolved.netloc)
        elif tag == "script":
            src = attrs_map.get("src", "")
            if "googletagmanager.com/gtag/js" in src:
                self.signals.ga4_detected = True
            if "googletagmanager.com/gtm.js" in src:
                self.signals.gtm_detected = True
            if attrs_map.get("type", "").lower() == "application/ld+json":
                self._json_ld = True
                self._json_ld_parts = []
            else:
                self._ignore_text_depth += 1
        elif tag in {"style", "noscript", "template"}:
            self._ignore_text_depth += 1

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
        elif tag == self._heading_tag:
            text = " ".join("".join(self._heading_parts).split())
            if text:
                self.signals.headings[self._heading_tag].append(text)
            self._heading_tag = ""
            self._heading_parts = []
        elif tag == "script" and self._json_ld:
            self._json_ld = False
            raw = "".join(self._json_ld_parts)
            try:
                for schema_type in collect_schema_types(json.loads(raw)):
                    self.add_schema_type(schema_type)
            except json.JSONDecodeError:
                for match in re.findall(r'"@type"\s*:\s*"([^"]+)"', raw):
                    self.add_schema_type(match)
        elif tag in {"script", "style", "noscript", "template"} and self._ignore_text_depth:
            self._ignore_text_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._in_h1:
            self._h1_parts.append(data)
        if self._heading_tag:
            self._heading_parts.append(data)
        if self._json_ld:
            self._json_ld_parts.append(data)
        if not self._json_ld and not self._ignore_text_depth:
            clean = " ".join(data.split())
            if clean:
                self._body_parts.append(clean)
        if "G-" in data or "gtag(" in data:
            self.signals.ga4_detected = True
        if "GTM-" in data:
            self.signals.gtm_detected = True

    def finalize(self) -> PageSignals:
        self.signals.body_text = " ".join(" ".join(self._body_parts).split())
        headings = self.signals.h1 + self.signals.headings["h2"] + self.signals.headings["h3"] + self.signals.headings["h4"]
        self.signals.question_headings = [item for item in headings if QUESTION_RE.search(item)]
        return self.signals


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


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def schema_has_entity_type(schema_types: list[str]) -> bool:
    useful_types = {
        "Organization",
        "LocalBusiness",
        "Person",
        "WebSite",
        "WebPage",
        "Article",
        "BlogPosting",
        "NewsArticle",
        "Product",
        "SoftwareApplication",
        "FAQPage",
        "HowTo",
        "BreadcrumbList",
    }
    return any(item in useful_types for item in schema_types)


def build_geo_report(signals: PageSignals, robots: dict[str, Any], llms_txt: dict[str, Any]) -> dict[str, Any]:
    words = word_count(signals.body_text)
    trust_matches = sorted({match.group(0).lower() for match in TRUST_RE.finditer(signals.body_text)})
    has_faq_signal = "FAQPage" in signals.schema_types or bool(signals.question_headings) or "frequently asked" in signals.body_text.lower()
    checks = [
        {
            "id": "crawlable_text",
            "label": "Crawlable main content is substantial",
            "ok": words >= 300,
            "weight": 15,
            "fix": "Add enough visible, crawlable explanation for an AI answer engine to summarize the page.",
        },
        {
            "id": "answerable_heading",
            "label": "Title and H1 make the page topic explicit",
            "ok": bool(signals.title and signals.h1),
            "weight": 12,
            "fix": "Use a specific title and one clear H1 that name the entity, product, or question being answered.",
        },
        {
            "id": "structured_data",
            "label": "Structured data is present",
            "ok": bool(signals.schema_types),
            "weight": 14,
            "fix": "Add JSON-LD schema that accurately represents the visible page content.",
        },
        {
            "id": "entity_schema",
            "label": "Schema includes useful entity or content types",
            "ok": schema_has_entity_type(signals.schema_types),
            "weight": 10,
            "fix": "Use relevant types such as Organization, WebSite, Article, Product, FAQPage, HowTo, or LocalBusiness.",
        },
        {
            "id": "answer_blocks",
            "label": "Question or answer-oriented sections are detectable",
            "ok": has_faq_signal,
            "weight": 10,
            "fix": "Add concise question-led sections, FAQs, or clearly labeled answers for important user intents.",
        },
        {
            "id": "trust_evidence",
            "label": "Trust, ownership, or source signals are visible",
            "ok": bool(signals.author or signals.site_name or trust_matches),
            "weight": 10,
            "fix": "Expose author, organization, about, contact, privacy, sources, or editorial information on the page.",
        },
        {
            "id": "external_references",
            "label": "External references or citations exist",
            "ok": signals.links_external >= 2,
            "weight": 8,
            "fix": "Where appropriate, cite authoritative external sources instead of leaving claims unsupported.",
        },
        {
            "id": "search_access",
            "label": "Page is not blocked by robots meta",
            "ok": "noindex" not in signals.robots_meta.lower(),
            "weight": 8,
            "fix": "Remove noindex unless this page should stay out of search and AI discovery surfaces.",
        },
        {
            "id": "meta_summary",
            "label": "Meta description summarizes the page",
            "ok": 70 <= len(signals.description) <= 170,
            "weight": 7,
            "fix": "Write a concise meta description that states who the page is for and what it answers.",
        },
        {
            "id": "llms_txt",
            "label": "Optional llms.txt is reachable",
            "ok": bool(llms_txt.get("ok")),
            "weight": 6,
            "fix": "Optional: publish /llms.txt with concise links to your best documentation or evergreen pages.",
            "experimental": True,
        },
    ]
    score = sum(score_check(item["ok"], item["weight"]) for item in checks)
    missing = [item for item in sorted(checks, key=lambda item: (item["ok"], -item["weight"])) if not item["ok"]]
    return {
        "score": score,
        "grade": "Strong" if score >= 80 else "Promising" if score >= 60 else "Needs structure",
        "summary": (
            "This is a heuristic GEO readiness scan. It checks whether the page is understandable, citable, "
            "and structured enough for AI answer surfaces, but it does not guarantee inclusion or ranking."
        ),
        "signals": {
            "visible_word_count": words,
            "question_headings": signals.question_headings[:8],
            "schema_types": signals.schema_types,
            "trust_signals": trust_matches[:8],
            "author": signals.author,
            "site_name": signals.site_name,
            "external_hosts": signals.external_hosts[:8],
            "llms_txt": llms_txt,
        },
        "checks": checks,
        "quick_wins": [
            {
                "title": item["label"],
                "action": item["fix"],
                "impact": "High" if item["weight"] >= 12 else "Medium" if item["weight"] >= 8 else "Low",
                "experimental": bool(item.get("experimental")),
            }
            for item in missing[:5]
        ],
    }


def build_audit_response(
    *,
    audited_url: str,
    status_code: int,
    signals: PageSignals,
    robots: dict[str, Any],
    sitemap: dict[str, Any],
    llms_txt: dict[str, Any],
    demo: bool = False,
) -> dict[str, Any]:
    title_len = len(signals.title)
    description_len = len(signals.description)
    geo_report = build_geo_report(signals, robots, llms_txt)
    checks = [
        {"id": "http_ok", "label": "Homepage returns a successful response", "ok": status_code < 400, "weight": 12, "fix": "Fix server errors or redirect loops before optimizing content."},
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
        "demo": demo,
        "audited_url": audited_url,
        "status_code": status_code,
        "score": score,
        "grade": "Strong" if score >= 80 else "Developing" if score >= 60 else "Needs setup",
        "summary": {
            "title": signals.title,
            "title_length": title_len,
            "description": signals.description,
            "description_length": description_len,
            "h1": signals.h1,
            "headings": signals.headings,
            "body_word_count": word_count(signals.body_text),
            "question_headings": signals.question_headings,
            "author": signals.author,
            "site_name": signals.site_name,
            "canonical": signals.canonical,
            "robots_meta": signals.robots_meta,
            "images": signals.images,
            "images_missing_alt": signals.images_missing_alt,
            "internal_links": signals.links_internal,
            "external_links": signals.links_external,
            "external_hosts": signals.external_hosts,
            "schema_types": signals.schema_types,
            "ga4_detected": signals.ga4_detected,
            "gtm_detected": signals.gtm_detected,
            "robots": robots,
            "sitemap": sitemap,
            "llms_txt": llms_txt,
        },
        "checks": checks,
        "blockers": blockers,
        "next_steps": next_steps,
        "quick_wins": quick_wins,
        "geo_report": geo_report,
        "no_google_report": no_google_report,
        "google_data_ready": signals.ga4_detected or signals.gtm_detected,
        "message": "Instant audit completed. Connect Google when you want verified clicks, impressions, rankings, and sessions.",
    }


def instant_audit(raw_url: str) -> dict[str, Any]:
    url = normalize_url(raw_url)
    response = fetch_url(url)
    html = response.text[:1_500_000]
    parser = SignalParser(response.url)
    parser.feed(html)
    signals = parser.finalize()
    parsed = urlparse(response.url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots = fetch_optional(urljoin(origin, "/robots.txt"))
    sitemap = fetch_optional(urljoin(origin, "/sitemap.xml"))
    llms_txt = fetch_optional(urljoin(origin, "/llms.txt"))
    return build_audit_response(
        audited_url=response.url,
        status_code=response.status_code,
        signals=signals,
        robots=robots,
        sitemap=sitemap,
        llms_txt=llms_txt,
    )


def sample_audit() -> dict[str, Any]:
    body_text = """
    Luma Bake Studio sells small-batch sourdough classes for first-time home bakers, busy parents, and local food lovers
    who want a reliable weekend recipe. The page explains who the class is for, what students learn, what equipment is
    included, how long the workshop takes, and why the method works. It names the instructor, links to an about page,
    shows privacy and contact information, and cites practical food-safety guidance from public sources. Students can
    compare beginner, intermediate, and gift-card options, then book a date without calling the shop. The page also
    answers common questions about gluten, starter maintenance, refunds, accessibility, and whether students need prior
    baking experience. This sample keeps enough gaps to make the audit useful: the page has strong schema and trust
    signals, but it still needs more crawlable depth and an optional llms.txt file before the GEO score is excellent.
    """
    signals = PageSignals(
        title="Beginner Sourdough Classes in Portland | Luma Bake Studio",
        description="Learn beginner sourdough in a small Portland workshop with tools, starter care, clear steps, and take-home baking notes.",
        canonical="https://demo.open-seo-growth.local/classes/beginner-sourdough",
        robots_meta="index,follow",
        h1=["Beginner Sourdough Classes in Portland"],
        headings={
            "h2": [
                "What will I learn in the sourdough class?",
                "How does the beginner workshop work?",
                "Who teaches the class?",
            ],
            "h3": [
                "What should students bring?",
                "Can I join without baking experience?",
            ],
            "h4": [],
        },
        body_text=body_text,
        question_headings=[
            "What will I learn in the sourdough class?",
            "How does the beginner workshop work?",
            "Who teaches the class?",
            "What should students bring?",
            "Can I join without baking experience?",
        ],
        author="Mia Chen",
        site_name="Luma Bake Studio",
        images=5,
        images_missing_alt=0,
        links_internal=12,
        links_external=3,
        external_hosts=["foodsafety.gov", "kingarthurbaking.com", "extension.oregonstate.edu"],
        schema_types=["Organization", "WebSite", "WebPage", "FAQPage", "LocalBusiness", "BreadcrumbList"],
        ga4_detected=True,
        gtm_detected=True,
    )
    return build_audit_response(
        audited_url="https://demo.open-seo-growth.local/classes/beginner-sourdough",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://demo.open-seo-growth.local/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://demo.open-seo-growth.local/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://demo.open-seo-growth.local/llms.txt"},
        demo=True,
    )
