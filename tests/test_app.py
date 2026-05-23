from seo_growth.app import create_app


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
