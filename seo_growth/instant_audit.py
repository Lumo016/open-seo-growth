from __future__ import annotations

import json
import re
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


USER_AGENT = "OpenSEOGrowthBot/0.1 (+https://github.com/open-seo-growth)"
ROBOTS_USER_AGENT = USER_AGENT.split("/", 1)[0]
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


def collect_schema_dates(value: Any) -> dict[str, str]:
    found = {"published": "", "modified": ""}

    def pick(raw: Any) -> str:
        if isinstance(raw, str):
            return raw.strip()
        return ""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if not found["published"]:
                found["published"] = pick(node.get("datePublished") or node.get("dateCreated"))
            if not found["modified"]:
                found["modified"] = pick(node.get("dateModified") or node.get("dateUpdated"))
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


def comparable_url(value: str) -> str:
    parsed = urlparse(value or "")
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        port = None
    netloc = f"{hostname}:{port}" if port else hostname
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return parsed._replace(scheme=scheme, netloc=netloc, path=path, params="", query="", fragment="").geturl()


def evaluate_canonical(canonical: str, audited_url: str) -> dict[str, Any]:
    raw = (canonical or "").strip()
    if not raw:
        return {
            "declared": False,
            "ok": False,
            "status": "Missing",
            "url": "",
            "normalized_url": "",
            "self_referencing": False,
            "same_host": None,
            "reason": "No canonical URL is declared.",
        }
    normalized = urljoin(audited_url, raw)
    canonical_parsed = urlparse(normalized)
    audited_parsed = urlparse(audited_url)
    same_host = bool(canonical_parsed.netloc and canonical_parsed.netloc.lower() == audited_parsed.netloc.lower())
    self_referencing = comparable_url(normalized) == comparable_url(audited_url)
    return {
        "declared": True,
        "ok": self_referencing,
        "status": "Self-referencing" if self_referencing else "Canonicalizes elsewhere",
        "url": raw,
        "normalized_url": normalized,
        "self_referencing": self_referencing,
        "same_host": same_host,
        "reason": "Canonical points to the audited URL." if self_referencing else "Canonical points to a different URL than the audited page.",
    }


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def evaluate_sitemap_coverage(sitemap: dict[str, Any], sitemap_text: str, audited_url: str) -> dict[str, Any]:
    if not sitemap.get("ok"):
        return {
            "checked": False,
            "included": None,
            "status": "Not checked",
            "type": "missing",
            "reason": "sitemap.xml was not reachable, so URL coverage could not be verified.",
            "url_count": 0,
            "child_sitemap_count": 0,
            "child_sitemaps": [],
        }
    try:
        root = ET.fromstring(sitemap_text or "")
    except ET.ParseError:
        return {
            "checked": False,
            "included": None,
            "status": "Parse error",
            "type": "unknown",
            "reason": "sitemap.xml was reachable but could not be parsed as XML.",
            "url_count": 0,
            "child_sitemap_count": 0,
            "child_sitemaps": [],
        }
    sitemap_type = local_name(root.tag)
    locs = [
        " ".join((node.text or "").split())
        for node in root.iter()
        if local_name(node.tag) == "loc" and (node.text or "").strip()
    ]
    if sitemap_type == "sitemapindex":
        return {
            "checked": False,
            "included": None,
            "status": "Sitemap index",
            "type": "sitemapindex",
            "reason": "Root sitemap is an index. Child sitemaps need to be checked for exact URL coverage.",
            "url_count": 0,
            "child_sitemap_count": len(locs),
            "child_sitemaps": locs[:20],
        }
    if sitemap_type != "urlset":
        return {
            "checked": False,
            "included": None,
            "status": "Unknown sitemap",
            "type": sitemap_type or "unknown",
            "reason": "Sitemap XML type was not recognized as urlset or sitemapindex.",
            "url_count": len(locs),
            "child_sitemap_count": 0,
            "child_sitemaps": [],
        }
    audited = comparable_url(audited_url)
    included = any(comparable_url(url) == audited for url in locs)
    return {
        "checked": True,
        "included": included,
        "status": "Listed" if included else "Not listed",
        "type": "urlset",
        "reason": "The audited URL appears in sitemap.xml." if included else "The audited URL was not found in sitemap.xml.",
        "url_count": len(locs),
        "child_sitemap_count": 0,
        "child_sitemaps": [],
    }


def evaluate_x_robots_tag(value: str) -> dict[str, Any]:
    raw = " ".join((value or "").split())
    if not raw:
        return {
            "declared": False,
            "ok": True,
            "status": "Not declared",
            "value": "",
            "blocking_directives": [],
            "reason": "No X-Robots-Tag header was detected.",
        }
    lowered = raw.lower()
    blocking = []
    for directive in ("noindex", "none"):
        if re.search(rf"\b{re.escape(directive)}\b", lowered):
            blocking.append(directive)
    return {
        "declared": True,
        "ok": not blocking,
        "status": "Blocks indexing" if blocking else "Allows indexing",
        "value": raw,
        "blocking_directives": blocking,
        "reason": "X-Robots-Tag contains an indexing blocker." if blocking else "X-Robots-Tag does not contain noindex or none.",
    }


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
    date_published: str = ""
    date_modified: str = ""
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

    def add_published_date(self, raw: str) -> None:
        if raw and not self.signals.date_published:
            self.signals.date_published = raw.strip()

    def add_modified_date(self, raw: str) -> None:
        if raw and not self.signals.date_modified:
            self.signals.date_modified = raw.strip()

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
            if name in {"article:published_time", "date", "dc.date", "dc.date.issued", "publishdate"}:
                self.add_published_date(attrs_map.get("content", ""))
            if name in {"article:modified_time", "og:updated_time", "last-modified", "lastmod", "date.modified", "datemodified"}:
                self.add_modified_date(attrs_map.get("content", ""))
        elif tag == "link":
            if "canonical" in re.split(r"\s+", attrs_map.get("rel", "").lower()):
                self.signals.canonical = attrs_map.get("href", "").strip()
        elif tag == "time":
            self.add_published_date(attrs_map.get("datetime", ""))
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
                payload = json.loads(raw)
                for schema_type in collect_schema_types(payload):
                    self.add_schema_type(schema_type)
                dates = collect_schema_dates(payload)
                self.add_published_date(dates.get("published", ""))
                self.add_modified_date(dates.get("modified", ""))
            except json.JSONDecodeError:
                for match in re.findall(r'"@type"\s*:\s*"([^"]+)"', raw):
                    self.add_schema_type(match)
                published = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw)
                modified = re.search(r'"dateModified"\s*:\s*"([^"]+)"', raw)
                if published:
                    self.add_published_date(published.group(1))
                if modified:
                    self.add_modified_date(modified.group(1))
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


def fetch_optional(url: str, *, include_text: bool = False) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
        payload = {"ok": response.status_code < 400, "status_code": response.status_code, "url": response.url}
        if include_text and payload["ok"]:
            payload["text"] = response.text[:500_000]
        return payload
    except Exception as exc:
        return {"ok": False, "error": exc.__class__.__name__, "message": str(exc), "url": url}


def evaluate_robots_access(robots: dict[str, Any], robots_text: str, audited_url: str) -> dict[str, Any]:
    if not robots.get("ok"):
        status_code = robots.get("status_code")
        assumed_allowed = status_code == 404
        return {
            "checked": False,
            "allowed": True if assumed_allowed else None,
            "status": "Assumed allowed" if assumed_allowed else "Not checked",
            "user_agent": ROBOTS_USER_AGENT,
            "reason": "robots.txt returned 404, which crawlers normally treat as no declared crawl restrictions." if assumed_allowed else "robots.txt was not reachable, so exact crawl permission could not be verified.",
        }
    try:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(str(robots.get("url") or ""))
        parser.parse((robots_text or "").splitlines())
        allowed = parser.can_fetch(ROBOTS_USER_AGENT, audited_url)
        return {
            "checked": True,
            "allowed": allowed,
            "status": "Allowed" if allowed else "Blocked",
            "user_agent": ROBOTS_USER_AGENT,
            "reason": "robots.txt allows this bot to fetch the audited URL." if allowed else "robots.txt disallows this bot from fetching the audited URL.",
        }
    except Exception as exc:
        return {
            "checked": False,
            "allowed": None,
            "status": "Parse error",
            "user_agent": ROBOTS_USER_AGENT,
            "reason": f"robots.txt could not be parsed: {exc.__class__.__name__}.",
        }


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


def infer_page_type(schema_types: list[str]) -> str:
    if "Product" in schema_types:
        return "product or offer page"
    if "LocalBusiness" in schema_types:
        return "local business page"
    if any(item in schema_types for item in {"Article", "BlogPosting", "NewsArticle"}):
        return "editorial content page"
    if "FAQPage" in schema_types:
        return "question-and-answer page"
    if "SoftwareApplication" in schema_types:
        return "software application page"
    return "general website page"


def build_content_brief(signals: PageSignals, checks: list[dict[str, Any]], llms_txt: dict[str, Any]) -> dict[str, Any]:
    check_map = {item["id"]: item for item in checks}
    topic = (signals.h1[0] if signals.h1 else signals.title).strip() or "Primary page topic"
    page_type = infer_page_type(signals.schema_types)
    sections: list[dict[str, str]] = []

    def missing(check_id: str) -> bool:
        return not check_map.get(check_id, {}).get("ok")

    if missing("crawlable_text"):
        sections.append({
            "title": "Expand the main answer",
            "priority": "High",
            "reason": "The page has limited visible text. Add a clear who, what, why, how, proof, and next-step explanation.",
        })
    else:
        sections.append({
            "title": "Keep the summary easy to quote",
            "priority": "Medium",
            "reason": "The page has enough visible text. Make the first section concise enough for humans and answer systems to summarize.",
        })

    if missing("answerable_heading"):
        sections.append({
            "title": "Make the page topic explicit",
            "priority": "High",
            "reason": "Rewrite the title and H1 so they name the entity, offer, location, or problem directly.",
        })

    if missing("answer_blocks"):
        sections.append({
            "title": "Add question-led sections",
            "priority": "High",
            "reason": "Add headings that match real user questions and answer each one in one or two clear paragraphs.",
        })
    elif signals.question_headings:
        sections.append({
            "title": "Strengthen existing Q&A sections",
            "priority": "Medium",
            "reason": f"Keep answers under the detected questions specific, factual, and easy to cite. First detected question: {signals.question_headings[0]}",
        })

    if missing("trust_evidence"):
        sections.append({
            "title": "Add trust and ownership proof",
            "priority": "High",
            "reason": "Add author, organization, contact, about, privacy, editorial, or source information where it is visible to users.",
        })

    if missing("external_references"):
        sections.append({
            "title": "Support claims with references",
            "priority": "Medium",
            "reason": "Add relevant authoritative references for claims that benefit from evidence.",
        })

    if missing("freshness_signals"):
        sections.append({
            "title": "Add freshness evidence",
            "priority": "Medium",
            "reason": "Show a published or updated date when freshness matters, and keep the date aligned with the visible page content.",
        })

    if not llms_txt.get("ok"):
        sections.append({
            "title": "Optional llms.txt handoff",
            "priority": "Low",
            "reason": "If useful for the site, publish /llms.txt with concise links to the best evergreen pages or documentation.",
        })

    if missing("structured_data"):
        schema_recommendations = [
            "Add JSON-LD that matches visible page content.",
            "Start with Organization, WebSite, WebPage, Article, Product, FAQPage, HowTo, or LocalBusiness when relevant.",
            "Do not mark up claims, reviews, prices, or FAQs that are not visible on the page.",
        ]
    elif missing("entity_schema"):
        schema_recommendations = [
            "Keep existing structured data, but add a more specific entity or content type that matches the page.",
            "Use only schema fields that are supported by visible page content.",
        ]
    else:
        schema_recommendations = [
            f"Review the detected schema types for accuracy: {', '.join(signals.schema_types[:8])}.",
            "Keep schema aligned with visible content after any content rewrite.",
        ]

    trust_recommendations = [
        "Name the author, owner, organization, or responsible entity when appropriate.",
        "Keep contact, about, privacy, terms, source, or editorial links easy to find.",
    ]
    if signals.author:
        trust_recommendations.insert(0, f"Preserve visible author attribution: {signals.author}.")
    if signals.site_name:
        trust_recommendations.insert(0, f"Preserve visible site attribution: {signals.site_name}.")

    citation_recommendations = [
        "Cite authoritative external sources for factual claims, comparisons, methods, safety guidance, pricing context, or statistics.",
        "Prefer sources that a reader can inspect directly.",
    ]
    if signals.external_hosts:
        citation_recommendations.insert(0, f"Review detected external hosts for quality: {', '.join(signals.external_hosts[:5])}.")

    section_titles = "; ".join(item["title"] for item in sections[:5])
    safe_prompt = (
        f"Rewrite and expand this {page_type} about '{topic}' using only public information that is visible on the audited page. "
        f"Prioritize these sections: {section_titles}. "
        "Make the page easier for users, search engines, and AI answer surfaces to understand. "
        "Do not invent rankings, traffic, reviews, prices, credentials, citations, or private analytics data. "
        "Keep recommendations factual, source-aware, and aligned with visible page content."
    )

    return {
        "title": "Prompt-safe GEO content brief",
        "primary_topic": topic,
        "page_type": page_type,
        "audience": "Searchers and AI answer surfaces that need a clear, citable answer from the public page.",
        "recommended_sections": sections[:6],
        "schema_recommendations": schema_recommendations,
        "trust_recommendations": trust_recommendations[:4],
        "citation_recommendations": citation_recommendations[:4],
        "safe_prompt": safe_prompt,
        "handoff_notes": [
            "Use this brief as editorial guidance, not as a ranking promise.",
            "Validate any schema against the final visible page content.",
            "Reconnect Google data later to measure clicks, impressions, CTR, position, sessions, and conversions.",
        ],
    }


def build_geo_report(
    signals: PageSignals,
    robots: dict[str, Any],
    llms_txt: dict[str, Any],
    robots_access: dict[str, Any] | None = None,
    x_robots_tag: dict[str, Any] | None = None,
) -> dict[str, Any]:
    words = word_count(signals.body_text)
    trust_matches = sorted({match.group(0).lower() for match in TRUST_RE.finditer(signals.body_text)})
    has_faq_signal = "FAQPage" in signals.schema_types or bool(signals.question_headings) or "frequently asked" in signals.body_text.lower()
    has_freshness_signal = bool(signals.date_published or signals.date_modified)
    robots_access = robots_access or {}
    x_robots_tag = x_robots_tag or {}
    robots_rules_ok = robots_access.get("allowed") is not False
    x_robots_ok = x_robots_tag.get("ok") is not False
    search_access_ok = "noindex" not in signals.robots_meta.lower() and robots_rules_ok and x_robots_ok
    checks = [
        {
            "id": "crawlable_text",
            "label": "Crawlable main content is substantial",
            "ok": words >= 300,
            "weight": 14,
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
            "label": "Page is not blocked by robots meta, X-Robots-Tag, or robots.txt",
            "ok": search_access_ok,
            "weight": 8,
            "fix": "Remove noindex, X-Robots-Tag, or robots.txt disallow rules unless this page should stay out of search and AI discovery surfaces.",
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
            "weight": 3,
            "fix": "Optional: publish /llms.txt with concise links to your best documentation or evergreen pages.",
            "experimental": True,
        },
        {
            "id": "freshness_signals",
            "label": "Published or updated date is visible",
            "ok": has_freshness_signal,
            "weight": 4,
            "fix": "Add a visible published or updated date, and mirror it in JSON-LD when appropriate.",
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
            "date_published": signals.date_published,
            "date_modified": signals.date_modified,
            "external_hosts": signals.external_hosts[:8],
            "robots_access": robots_access,
            "x_robots_tag": x_robots_tag,
            "llms_txt": llms_txt,
        },
        "checks": checks,
        "content_brief": build_content_brief(signals, checks, llms_txt),
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
    robots_access: dict[str, Any] | None = None,
    sitemap_coverage: dict[str, Any] | None = None,
    x_robots_tag: str = "",
    response_time_ms: int | None = None,
    html_bytes: int | None = None,
    content_type: str = "",
    final_url: str = "",
    redirected: bool = False,
    demo: bool = False,
) -> dict[str, Any]:
    title_len = len(signals.title)
    description_len = len(signals.description)
    robots_access = robots_access or {}
    sitemap_coverage = sitemap_coverage or {}
    canonical_status = evaluate_canonical(signals.canonical, final_url or audited_url)
    x_robots_status = evaluate_x_robots_tag(x_robots_tag)
    geo_report = build_geo_report(signals, robots, llms_txt, robots_access=robots_access, x_robots_tag=x_robots_status)
    html_kb = round(html_bytes / 1024, 1) if html_bytes is not None else None
    response_time_ok = response_time_ms is not None and response_time_ms <= 2000
    html_size_ok = html_bytes is not None and html_bytes <= 500_000
    robots_rules_ok = robots_access.get("allowed") is not False
    sitemap_coverage_ok = sitemap_coverage.get("included") is not False
    checks = [
        {"id": "http_ok", "label": "Homepage returns a successful response", "ok": status_code < 400, "weight": 12, "fix": "Fix server errors or redirect loops before optimizing content."},
        {"id": "title", "label": "Title tag is present and within a useful range", "ok": 20 <= title_len <= 65, "weight": 12, "fix": "Write a specific title around 45-60 characters."},
        {"id": "description", "label": "Meta description is present", "ok": 70 <= description_len <= 170, "weight": 10, "fix": "Add a concise search snippet that explains the page value."},
        {"id": "h1", "label": "Exactly one H1 found", "ok": len(signals.h1) == 1, "weight": 10, "fix": "Use one clear H1 that matches the page intent."},
        {"id": "canonical", "label": "Canonical URL is declared", "ok": canonical_status["declared"], "weight": 4, "fix": "Add a canonical link to the preferred URL."},
        {"id": "canonical_target", "label": "Canonical points to the audited URL", "ok": canonical_status["ok"], "weight": 4, "fix": "Update the canonical tag if this page should be indexed as its own search result."},
        {"id": "robots_meta", "label": "Page is not blocked by robots meta", "ok": "noindex" not in signals.robots_meta.lower(), "weight": 8, "fix": "Remove noindex unless the page should stay out of Google."},
        {"id": "x_robots_tag", "label": "X-Robots-Tag header does not block indexing", "ok": x_robots_status["ok"], "weight": 6, "fix": "Remove X-Robots-Tag noindex or none unless this URL should stay out of search."},
        {"id": "robots_txt", "label": "robots.txt is reachable", "ok": bool(robots.get("ok")), "weight": 5, "fix": "Expose robots.txt at the site root."},
        {"id": "robots_rules", "label": "Audited URL is allowed by robots.txt", "ok": robots_rules_ok, "weight": 5, "fix": "Update robots.txt so search crawlers can fetch this URL, or choose a page that should be indexable."},
        {"id": "sitemap", "label": "sitemap.xml is reachable", "ok": bool(sitemap.get("ok")), "weight": 4, "fix": "Publish a sitemap and submit it in Search Console."},
        {"id": "sitemap_coverage", "label": "Audited URL is represented in sitemap", "ok": sitemap_coverage_ok, "weight": 3, "fix": "Add this URL to the sitemap, or verify the child sitemap where it should appear."},
        {"id": "image_alt", "label": "Images have alt text", "ok": signals.images == 0 or signals.images_missing_alt == 0, "weight": 3, "fix": "Add descriptive alt text to important images."},
        {"id": "internal_links", "label": "Internal links exist", "ok": signals.links_internal > 0, "weight": 3, "fix": "Add links to important pages so Google and users can continue."},
        {"id": "schema", "label": "Structured data is present", "ok": bool(signals.schema_types), "weight": 3, "fix": "Add Organization, WebSite, Article, Product, or relevant schema."},
        {"id": "analytics", "label": "Analytics tag is detectable", "ok": signals.ga4_detected or signals.gtm_detected, "weight": 3, "fix": "Install GA4 or Google Tag Manager before expecting traffic reports."},
        {"id": "response_time", "label": "Initial HTML response is reasonably fast", "ok": response_time_ok, "weight": 4, "fix": "Improve server response time, redirects, caching, or hosting until the initial HTML returns in under two seconds."},
        {"id": "html_size", "label": "HTML payload is not unusually heavy", "ok": html_size_ok, "weight": 1, "fix": "Reduce server-rendered HTML weight, inline scripts, or bloated markup so the initial document stays under 500 KB."},
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
            "response_time_ms": response_time_ms,
            "html_bytes": html_bytes,
            "html_kb": html_kb,
            "content_type": content_type,
            "final_url": final_url or audited_url,
            "redirected": redirected,
            "h1": signals.h1,
            "headings": signals.headings,
            "body_word_count": word_count(signals.body_text),
            "question_headings": signals.question_headings,
            "author": signals.author,
            "site_name": signals.site_name,
            "date_published": signals.date_published,
            "date_modified": signals.date_modified,
            "canonical": signals.canonical,
            "canonical_status": canonical_status,
            "robots_meta": signals.robots_meta,
            "x_robots_tag": x_robots_status,
            "images": signals.images,
            "images_missing_alt": signals.images_missing_alt,
            "internal_links": signals.links_internal,
            "external_links": signals.links_external,
            "external_hosts": signals.external_hosts,
            "schema_types": signals.schema_types,
            "ga4_detected": signals.ga4_detected,
            "gtm_detected": signals.gtm_detected,
            "robots": robots,
            "robots_access": robots_access,
            "sitemap": sitemap,
            "sitemap_coverage": sitemap_coverage,
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
    response_time_ms = int(response.elapsed.total_seconds() * 1000) if response.elapsed else None
    html_bytes = len(response.content)
    parser = SignalParser(response.url)
    parser.feed(html)
    signals = parser.finalize()
    parsed = urlparse(response.url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots = fetch_optional(urljoin(origin, "/robots.txt"), include_text=True)
    robots_text = str(robots.pop("text", "") or "")
    robots_access = evaluate_robots_access(robots, robots_text, response.url)
    sitemap = fetch_optional(urljoin(origin, "/sitemap.xml"), include_text=True)
    sitemap_text = str(sitemap.pop("text", "") or "")
    sitemap_coverage = evaluate_sitemap_coverage(sitemap, sitemap_text, response.url)
    llms_txt = fetch_optional(urljoin(origin, "/llms.txt"))
    return build_audit_response(
        audited_url=response.url,
        status_code=response.status_code,
        signals=signals,
        robots=robots,
        sitemap=sitemap,
        llms_txt=llms_txt,
        robots_access=robots_access,
        sitemap_coverage=sitemap_coverage,
        x_robots_tag=response.headers.get("x-robots-tag", ""),
        response_time_ms=response_time_ms,
        html_bytes=html_bytes,
        content_type=response.headers.get("content-type", ""),
        final_url=response.url,
        redirected=bool(response.history),
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
        robots_access={
            "checked": True,
            "allowed": True,
            "status": "Allowed",
            "user_agent": ROBOTS_USER_AGENT,
            "reason": "Sample robots.txt allows the audited URL.",
        },
        sitemap_coverage={
            "checked": True,
            "included": True,
            "status": "Listed",
            "type": "urlset",
            "reason": "Sample sitemap includes the audited URL.",
            "url_count": 18,
            "child_sitemap_count": 0,
            "child_sitemaps": [],
        },
        x_robots_tag="",
        response_time_ms=320,
        html_bytes=48_200,
        content_type="text/html; charset=utf-8",
        final_url="https://demo.open-seo-growth.local/classes/beginner-sourdough",
        redirected=False,
        demo=True,
    )
