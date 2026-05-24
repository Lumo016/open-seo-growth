from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_documents_single_web_service():
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "type: web" in blueprint
    assert "runtime: docker" in blueprint
    assert "plan: free" in blueprint
    assert "healthCheckPath: /healthz" in blueprint
    assert "generateValue: true" in blueprint
    assert "AUDIT_RATE_LIMIT_PER_HOUR" in blueprint
    assert "TOKEN_ENCRYPTION_KEY" in blueprint
    assert "APP_BASE_URL" not in blueprint
    assert "GOOGLE_REDIRECT_URI" not in blueprint
    assert "GOOGLE_CLIENT_SECRET" not in blueprint


def test_render_deployment_doc_links_runtime_and_oauth_steps():
    doc = (ROOT / "docs" / "render-deployment.md").read_text(encoding="utf-8")

    assert "GET /healthz" in doc
    assert "Load sample audit" in doc
    assert "RENDER_EXTERNAL_URL" in doc
    assert "GOOGLE_CLIENT_ID" in doc
    assert "encrypted database-backed token storage" in doc
