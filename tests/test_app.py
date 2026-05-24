import json
import re

import seo_growth.app as app_module
from seo_growth.app import create_app


TOKEN_KEY = "unit-test-token-encryption-secret"


def test_health_endpoint_is_safe_for_platform_checks(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    app = create_app()

    response = app.test_client().get("/healthz")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {"ok": True, "service": "open-seo-growth"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_public_crawler_assets_use_configured_base_url(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("APP_BASE_URL", "https://seo.example.com")
    app = create_app()
    client = app.test_client()

    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")
    llms = client.get("/llms.txt")

    assert robots.status_code == 200
    assert robots.mimetype == "text/plain"
    assert "Allow: /" in robots.text
    assert "Disallow: /api/" in robots.text
    assert "Sitemap: https://seo.example.com/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert sitemap.mimetype == "application/xml"
    assert "<loc>https://seo.example.com/</loc>" in sitemap.text
    assert "<loc>https://seo.example.com/llms.txt</loc>" in sitemap.text
    assert "<loc>https://seo.example.com/privacy</loc>" in sitemap.text
    assert "<loc>https://seo.example.com/terms</loc>" in sitemap.text
    assert llms.status_code == 200
    assert llms.mimetype == "text/plain"
    assert "# Open SEO Growth" in llms.text
    assert "SEO and GEO workbench" in llms.text
    assert "Privacy Policy: https://seo.example.com/privacy" in llms.text
    assert "Terms Of Service: https://seo.example.com/terms" in llms.text


def test_homepage_exposes_share_and_structured_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("APP_BASE_URL", "https://seo.example.com")
    app = create_app()

    response = app.test_client().get("/")
    html = response.text
    match = re.search(r'<script type="application/ld\+json">(.+?)</script>', html)

    assert response.status_code == 200
    assert '<link rel="canonical" href="https://seo.example.com/">' in html
    assert '<meta property="og:url" content="https://seo.example.com/">' in html
    assert '<meta name="twitter:card" content="summary">' in html
    assert '<meta name="robots" content="index,follow">' in html
    assert match is not None
    payload = json.loads(match.group(1))
    assert payload["@type"] == "SoftwareApplication"
    assert payload["name"] == "Open SEO Growth"
    assert payload["url"] == "https://seo.example.com/"
    assert payload["isAccessibleForFree"] is True
    assert payload["offers"]["price"] == "0"
    assert "GEO readiness scoring" in payload["featureList"]


def test_legal_pages_explain_google_data_and_terms(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("APP_BASE_URL", "https://seo.example.com")
    app = create_app()
    client = app.test_client()

    privacy = client.get("/privacy")
    terms = client.get("/terms")

    assert privacy.status_code == 200
    assert '<link rel="canonical" href="https://seo.example.com/privacy">' in privacy.text
    assert "Google User Data" in privacy.text
    assert "Google API Services User Data Policy" in privacy.text
    assert "Google data is not sold." in privacy.text
    assert "encrypted database-backed token storage" in privacy.text
    assert terms.status_code == 200
    assert '<link rel="canonical" href="https://seo.example.com/terms">' in terms.text
    assert "Terms Of Service" in terms.text
    assert "You should audit only websites you own, manage, or are authorized to review." in terms.text
    assert "MIT License" in terms.text


def test_session_endpoint_is_available_without_google(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    app = create_app()

    response = app.test_client().get("/api/session")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["oauth_ready"] is False
    assert payload["connected"] is False
    assert payload["platform_readiness"]["ready_for_google"] is False
    assert payload["platform_readiness"]["token_store"] == "plain_file"
    assert any(item["id"] == "token_store" for item in payload["platform_readiness"]["items"])
    assert payload["platform_readiness"]["audit_rate_limit_per_hour"] == 30
    assert any(item["id"] == "audit_rate_limit" for item in payload["platform_readiness"]["items"])


def test_session_reports_hosted_platform_readiness(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-that-is-not-default")
    monkeypatch.setenv("APP_BASE_URL", "https://seo.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-oauth-secret-value")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://seo.example.com/auth/google/callback")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", TOKEN_KEY)
    monkeypatch.delenv("ALLOW_INSECURE_OAUTH", raising=False)
    app = create_app()

    response = app.test_client().get("/api/session")
    payload = response.get_json()
    readiness = payload["platform_readiness"]

    assert response.status_code == 200
    assert payload["oauth_ready"] is True
    assert readiness["mode"] == "hosted_https"
    assert readiness["ready_for_google"] is True
    assert readiness["hosted_core_ready"] is True
    assert readiness["ready_for_hosted_saas"] is False
    assert "test-oauth-secret-value" not in str(readiness)


def test_session_uses_render_external_url_when_base_url_is_not_set(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-that-is-not-default")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://open-seo-growth-preview.onrender.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-oauth-secret-value")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", TOKEN_KEY)
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    monkeypatch.delenv("ALLOW_INSECURE_OAUTH", raising=False)
    app = create_app()

    response = app.test_client().get("/api/session")
    payload = response.get_json()
    readiness = payload["platform_readiness"]

    assert response.status_code == 200
    assert readiness["app_base_url"] == "https://open-seo-growth-preview.onrender.com"
    assert payload["redirect_uri"] == "https://open-seo-growth-preview.onrender.com/auth/google/callback"
    assert readiness["redirect_uri"] == "https://open-seo-growth-preview.onrender.com/auth/google/callback"
    assert readiness["ready_for_google"] is True


def test_api_audit_demo_returns_sample_audit(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    app = create_app()

    response = app.test_client().post("/api/audit", json={"demo": True})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["demo"] is True
    assert payload["score"] == 100
    assert payload["geo_report"]["score"] == 79


def test_api_audit_requires_url_when_not_demo(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    app = create_app()

    response = app.test_client().post("/api/audit", json={})
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["ok"] is False
    assert "website URL" in payload["message"]


def test_live_audit_rate_limit_blocks_repeated_public_scans(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("AUDIT_RATE_LIMIT_PER_HOUR", "1")
    monkeypatch.setattr(
        app_module,
        "instant_audit",
        lambda url: {"ok": True, "audited_url": url, "score": 88, "geo_report": {"score": 74}},
    )
    app = create_app()
    client = app.test_client()

    first = client.post("/api/audit", json={"url": "https://example.com/"}, environ_base={"REMOTE_ADDR": "198.51.100.10"})
    second = client.post("/api/audit", json={"url": "https://example.com/"}, environ_base={"REMOTE_ADDR": "198.51.100.10"})
    demo = client.post("/api/audit", json={"demo": True}, environ_base={"REMOTE_ADDR": "198.51.100.10"})

    assert first.status_code == 200
    assert first.get_json()["ok"] is True
    assert second.status_code == 429
    assert second.get_json()["error"] == "RateLimitExceeded"
    assert second.headers["Retry-After"]
    assert second.headers["X-RateLimit-Limit"] == "1"
    assert demo.status_code == 200
    assert demo.get_json()["demo"] is True


def test_demo_growth_report_does_not_require_google(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    app = create_app()

    response = app.test_client().post("/api/analyze", json={"demo": True})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["demo"] is True
    assert payload["gsc"]["summary"]["clicks"] > 0
    assert payload["gsc"]["summary"]["impressions"] > 0
    assert payload["scorecard"]["source_status"] == {"gsc": True, "ga4": True, "ecommerce": True}
    assert payload["scorecard"]["metrics"]["organic_sessions"] > 0
    assert payload["opportunities"]["low_hanging_queries"]
    assert payload["opportunities"]["ctr_opportunities"]
