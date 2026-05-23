import pytest

from seo_growth.instant_audit import PageSignals, SignalParser, build_audit_response, build_geo_report, normalize_url, sample_audit


def test_normalize_url_adds_scheme_and_root_path():
    assert normalize_url("example.com") == "https://example.com/"


def test_normalize_url_rejects_empty_value():
    with pytest.raises(ValueError, match="Enter a website URL first"):
        normalize_url("")


def test_signal_parser_collects_seo_and_geo_signals():
    html = """
    <!doctype html>
    <html>
      <head>
        <title>Practical SEO and GEO Audit Guide</title>
        <meta name="description" content="A practical guide that explains SEO and GEO audit signals for growing search visibility.">
        <meta name="author" content="Jordan Lee">
        <meta property="og:site_name" content="Search Lab">
        <meta property="article:modified_time" content="2026-05-20T10:00:00Z">
        <link rel="canonical" href="https://example.com/guide">
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": ["Article", "FAQPage"],
            "author": {"@type": "Person", "name": "Jordan Lee"},
            "datePublished": "2026-05-01"
          }
        </script>
      </head>
      <body>
        <h1>Practical SEO and GEO Audit Guide</h1>
        <h2>How should teams prepare pages for AI answers?</h2>
        <p>About this guide: it cites sources, explains authorship, and links to references.</p>
        <a href="/internal">Internal page</a>
        <a href="https://source.example/report">External source</a>
        <img src="/chart.png" alt="Search performance chart">
      </body>
    </html>
    """
    parser = SignalParser("https://example.com/guide")
    parser.feed(html)
    signals = parser.finalize()

    assert signals.title == "Practical SEO and GEO Audit Guide"
    assert signals.description.startswith("A practical guide")
    assert signals.author == "Jordan Lee"
    assert signals.site_name == "Search Lab"
    assert signals.date_published == "2026-05-01"
    assert signals.date_modified == "2026-05-20T10:00:00Z"
    assert signals.h1 == ["Practical SEO and GEO Audit Guide"]
    assert signals.question_headings == ["How should teams prepare pages for AI answers?"]
    assert signals.links_internal == 1
    assert signals.links_external == 1
    assert signals.images_missing_alt == 0
    assert set(signals.schema_types) >= {"Article", "FAQPage", "Person"}


def test_sample_audit_is_export_ready_and_has_geo_evidence():
    audit = sample_audit()
    geo = audit["geo_report"]
    geo_checks = {item["id"]: item for item in geo["checks"]}

    assert audit["ok"] is True
    assert audit["demo"] is True
    assert audit["score"] == 100
    assert audit["grade"] == "Strong"
    assert audit["summary"]["response_time_ms"] == 320
    assert audit["summary"]["html_kb"] == 47.1
    assert audit["summary"]["content_type"] == "text/html; charset=utf-8"
    assert geo["score"] == 79
    assert geo["grade"] == "Promising"
    assert geo_checks["llms_txt"]["experimental"] is True
    assert geo_checks["llms_txt"]["ok"] is False
    assert geo["signals"]["question_headings"]
    assert geo["signals"]["external_hosts"]
    assert geo["content_brief"]["title"] == "Prompt-safe GEO content brief"
    assert geo["content_brief"]["primary_topic"] == "Beginner Sourdough Classes in Portland"
    assert "private analytics data" in geo["content_brief"]["safe_prompt"]
    assert any(item["title"] == "Optional llms.txt handoff" for item in geo["content_brief"]["recommended_sections"])
    assert any(item["title"] == "Add freshness evidence" for item in geo["content_brief"]["recommended_sections"])


def test_audit_scores_response_time_and_html_payload():
    signals = PageSignals(
        title="Practical SEO Audit Service for Growing Teams",
        description="A practical SEO audit service that reviews indexability, content structure, analytics setup, and growth opportunities.",
        canonical="https://example.com/audit",
        robots_meta="index,follow",
        h1=["Practical SEO Audit Service"],
        body_text="This page explains technical SEO, content quality, analytics setup, and practical growth opportunities.",
        links_internal=2,
        schema_types=["Organization", "WebSite"],
        ga4_detected=True,
    )
    audit = build_audit_response(
        audited_url="https://example.com/audit",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
        response_time_ms=2500,
        html_bytes=650_000,
        content_type="text/html",
        final_url="https://example.com/audit",
    )
    checks = {item["id"]: item for item in audit["checks"]}

    assert audit["score"] == 94
    assert checks["response_time"]["ok"] is False
    assert checks["html_size"]["ok"] is False
    assert audit["summary"]["response_time_ms"] == 2500
    assert audit["summary"]["html_bytes"] == 650_000
    assert audit["summary"]["html_kb"] == 634.8
    assert "server response time" in checks["response_time"]["fix"]


def test_geo_content_brief_recommends_writer_actions_for_sparse_page():
    signals = PageSignals(
        title="Consulting",
        h1=["Consulting"],
        body_text="We help companies grow.",
        links_external=0,
        schema_types=[],
    )
    geo = build_geo_report(
        signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
    )
    brief = geo["content_brief"]
    section_titles = {item["title"] for item in brief["recommended_sections"]}

    assert geo["grade"] == "Needs structure"
    assert "Expand the main answer" in section_titles
    assert "Add question-led sections" in section_titles
    assert "Add JSON-LD" in brief["schema_recommendations"][0]
    assert brief["safe_prompt"].startswith("Rewrite and expand this")
