import pytest

from seo_growth.instant_audit import (
    PageSignals,
    SignalParser,
    build_audit_response,
    evaluate_canonical,
    build_geo_report,
    evaluate_robots_access,
    evaluate_sitemap_coverage,
    evaluate_x_robots_tag,
    normalize_url,
    sample_audit,
    validate_auditable_url,
)


def test_normalize_url_adds_scheme_and_root_path():
    assert normalize_url("example.com") == "https://example.com/"


def test_normalize_url_rejects_empty_value():
    with pytest.raises(ValueError, match="Enter a website URL first"):
        normalize_url("")


def test_validate_auditable_url_rejects_private_network_targets():
    with pytest.raises(ValueError, match="publicly reachable"):
        validate_auditable_url("http://127.0.0.1/")

    with pytest.raises(ValueError, match="publicly reachable"):
        validate_auditable_url("http://[::1]/")


def test_validate_auditable_url_rejects_non_web_schemes_and_custom_ports():
    with pytest.raises(ValueError, match="Only http and https"):
        validate_auditable_url("ftp://example.com/")

    with pytest.raises(ValueError, match="standard web ports"):
        validate_auditable_url("https://93.184.216.34:8443/")


def test_validate_auditable_url_rejects_embedded_credentials():
    with pytest.raises(ValueError, match="embedded credentials"):
        validate_auditable_url("https://user:password@93.184.216.34/")


def test_validate_auditable_url_allows_global_standard_web_targets():
    assert validate_auditable_url("https://93.184.216.34/") == "https://93.184.216.34/"


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
    assert signals.json_ld_scripts == 1
    assert signals.json_ld_valid_scripts == 1
    assert signals.json_ld_parse_errors == []


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
    assert audit["summary"]["canonical_status"]["status"] == "Self-referencing"
    assert audit["summary"]["robots_access"]["allowed"] is True
    assert audit["summary"]["sitemap_coverage"]["status"] == "Listed"
    assert audit["summary"]["x_robots_tag"]["status"] == "Not declared"
    assert audit["summary"]["json_ld_scripts"] == 3
    assert audit["summary"]["json_ld_valid_scripts"] == 3
    assert audit["summary"]["json_ld_parse_errors"] == []
    assert audit["no_google_report"]["starter_offer"]["name"] == "Starter SEO and GEO cleanup sprint"
    assert "GA4 and Search Console setup plan" in audit["no_google_report"]["starter_offer"]["deliverables"][-1]
    assert "clicks, impressions, CTR" in audit["no_google_report"]["starter_offer"]["upgrade_trigger"]
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

    assert audit["score"] == 95
    assert checks["response_time"]["ok"] is False
    assert checks["html_size"]["ok"] is False
    assert audit["summary"]["response_time_ms"] == 2500
    assert audit["summary"]["html_bytes"] == 650_000
    assert audit["summary"]["html_kb"] == 634.8
    assert "server response time" in checks["response_time"]["fix"]


def test_canonical_target_flags_canonicalized_page():
    status = evaluate_canonical("/preferred-page/", "https://example.com/current-page")
    signals = PageSignals(
        title="Current SEO Audit Page for Growing Teams",
        description="A practical SEO audit page with a canonical tag that points to another preferred search URL.",
        canonical="/preferred-page/",
        robots_meta="index,follow",
        h1=["Current SEO Audit Page"],
        body_text="This page explains technical SEO, content quality, analytics setup, and practical growth opportunities.",
        links_internal=2,
        schema_types=["Organization", "WebSite"],
        ga4_detected=True,
    )
    audit = build_audit_response(
        audited_url="https://example.com/current-page",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
        robots_access={"checked": True, "allowed": True, "status": "Allowed"},
        response_time_ms=320,
        html_bytes=48_200,
        content_type="text/html",
        final_url="https://example.com/current-page",
    )
    checks = {item["id"]: item for item in audit["checks"]}

    assert status["normalized_url"] == "https://example.com/preferred-page/"
    assert status["ok"] is False
    assert checks["canonical"]["ok"] is True
    assert checks["canonical_target"]["ok"] is False
    assert audit["summary"]["canonical_status"]["status"] == "Canonicalizes elsewhere"
    assert audit["score"] == 96


def test_sitemap_coverage_flags_missing_audited_url():
    sitemap_text = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/other-page</loc></url>
    </urlset>
    """
    sitemap_coverage = evaluate_sitemap_coverage(
        {"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        sitemap_text,
        "https://example.com/current-page",
    )
    signals = PageSignals(
        title="Current SEO Audit Page for Growing Teams",
        description="A practical SEO audit page that should be discoverable in the XML sitemap.",
        canonical="https://example.com/current-page",
        robots_meta="index,follow",
        h1=["Current SEO Audit Page"],
        body_text="This page explains technical SEO, content quality, analytics setup, and practical growth opportunities.",
        links_internal=2,
        schema_types=["Organization", "WebSite"],
        ga4_detected=True,
    )
    audit = build_audit_response(
        audited_url="https://example.com/current-page",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
        robots_access={"checked": True, "allowed": True, "status": "Allowed"},
        sitemap_coverage=sitemap_coverage,
        response_time_ms=320,
        html_bytes=48_200,
        content_type="text/html",
        final_url="https://example.com/current-page",
    )
    checks = {item["id"]: item for item in audit["checks"]}

    assert sitemap_coverage["included"] is False
    assert sitemap_coverage["status"] == "Not listed"
    assert checks["sitemap"]["ok"] is True
    assert checks["sitemap_coverage"]["ok"] is False
    assert audit["summary"]["sitemap_coverage"]["url_count"] == 1
    assert audit["score"] == 97


def test_x_robots_tag_noindex_blocks_search_access():
    x_robots = evaluate_x_robots_tag("googlebot: noindex, nofollow")
    signals = PageSignals(
        title="Header Blocked SEO Audit Page for Growing Teams",
        description="A practical SEO audit page that is blocked by an HTTP X-Robots-Tag header.",
        canonical="https://example.com/header-blocked",
        robots_meta="index,follow",
        h1=["Header Blocked SEO Audit Page"],
        body_text="This page explains technical SEO, content quality, analytics setup, and practical growth opportunities.",
        links_internal=2,
        schema_types=["Organization", "WebSite"],
        ga4_detected=True,
    )
    audit = build_audit_response(
        audited_url="https://example.com/header-blocked",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
        robots_access={"checked": True, "allowed": True, "status": "Allowed"},
        sitemap_coverage={"checked": True, "included": True, "status": "Listed"},
        x_robots_tag="googlebot: noindex, nofollow",
        response_time_ms=320,
        html_bytes=48_200,
        content_type="text/html",
        final_url="https://example.com/header-blocked",
    )
    checks = {item["id"]: item for item in audit["checks"]}
    geo_checks = {item["id"]: item for item in audit["geo_report"]["checks"]}

    assert x_robots["ok"] is False
    assert x_robots["blocking_directives"] == ["noindex"]
    assert checks["x_robots_tag"]["ok"] is False
    assert geo_checks["search_access"]["ok"] is False
    assert audit["summary"]["x_robots_tag"]["status"] == "Blocks indexing"
    assert audit["score"] == 94


def test_malformed_json_ld_is_reported_as_schema_error():
    html = """
    <!doctype html>
    <html>
      <head>
        <title>Broken Schema SEO Audit Page</title>
        <meta name="description" content="A practical SEO audit page with malformed JSON-LD that should be fixed before launch.">
        <link rel="canonical" href="https://example.com/broken-schema">
        <script type="application/ld+json">{"@type": "Article", "headline": "Broken"</script>
      </head>
      <body>
        <h1>Broken Schema SEO Audit Page</h1>
        <p>This page explains technical SEO, content quality, analytics setup, and practical growth opportunities.</p>
      </body>
    </html>
    """
    parser = SignalParser("https://example.com/broken-schema")
    parser.feed(html)
    signals = parser.finalize()
    signals.links_internal = 2
    signals.ga4_detected = True

    audit = build_audit_response(
        audited_url="https://example.com/broken-schema",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
        robots_access={"checked": True, "allowed": True, "status": "Allowed"},
        sitemap_coverage={"checked": True, "included": True, "status": "Listed"},
        response_time_ms=320,
        html_bytes=48_200,
        content_type="text/html",
        final_url="https://example.com/broken-schema",
    )
    checks = {item["id"]: item for item in audit["checks"]}

    assert signals.json_ld_scripts == 1
    assert signals.json_ld_valid_scripts == 0
    assert signals.json_ld_parse_errors
    assert "Article" in signals.schema_types
    assert checks["schema"]["ok"] is True
    assert checks["json_ld_valid"]["ok"] is False
    assert audit["summary"]["json_ld_parse_errors"]
    assert audit["score"] == 98


def test_robots_access_blocks_exact_audited_url():
    robots_text = """
    User-agent: *
    Disallow: /private/
    """
    robots_access = evaluate_robots_access(
        {"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        robots_text,
        "https://example.com/private/page",
    )
    signals = PageSignals(
        title="Private SEO Audit Page for Growing Teams",
        description="A practical SEO audit page that should not be blocked if it is meant to earn search visibility.",
        canonical="https://example.com/private/page",
        robots_meta="index,follow",
        h1=["Private SEO Audit Page"],
        body_text="This page explains technical SEO, content quality, analytics setup, and practical growth opportunities.",
        links_internal=2,
        schema_types=["Organization", "WebSite"],
        ga4_detected=True,
    )
    audit = build_audit_response(
        audited_url="https://example.com/private/page",
        status_code=200,
        signals=signals,
        robots={"ok": True, "status_code": 200, "url": "https://example.com/robots.txt"},
        sitemap={"ok": True, "status_code": 200, "url": "https://example.com/sitemap.xml"},
        llms_txt={"ok": False, "status_code": 404, "url": "https://example.com/llms.txt"},
        robots_access=robots_access,
        response_time_ms=320,
        html_bytes=48_200,
        content_type="text/html",
        final_url="https://example.com/private/page",
    )
    checks = {item["id"]: item for item in audit["checks"]}
    geo_checks = {item["id"]: item for item in audit["geo_report"]["checks"]}

    assert robots_access["allowed"] is False
    assert checks["robots_rules"]["ok"] is False
    assert geo_checks["search_access"]["ok"] is False
    assert audit["summary"]["robots_access"]["status"] == "Blocked"
    assert audit["score"] == 95


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
