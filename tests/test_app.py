from seo_growth.app import create_app


def test_health_endpoint_is_safe_for_platform_checks(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    app = create_app()

    response = app.test_client().get("/healthz")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {"ok": True, "service": "open-seo-growth"}


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
    assert payload["platform_readiness"]["token_store"] == "file"
    assert any(item["id"] == "token_store" for item in payload["platform_readiness"]["items"])


def test_session_reports_hosted_platform_readiness(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_STORE_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-that-is-not-default")
    monkeypatch.setenv("APP_BASE_URL", "https://seo.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-oauth-secret-value")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://seo.example.com/auth/google/callback")
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
