import pytest

from seo_growth.instant_audit import SignalParser, normalize_url, sample_audit


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
        <link rel="canonical" href="https://example.com/guide">
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": ["Article", "FAQPage"],
            "author": {"@type": "Person", "name": "Jordan Lee"}
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
    assert geo["score"] == 79
    assert geo["grade"] == "Promising"
    assert geo_checks["llms_txt"]["experimental"] is True
    assert geo_checks["llms_txt"]["ok"] is False
    assert geo["signals"]["question_headings"]
    assert geo["signals"]["external_hosts"]
