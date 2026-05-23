from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from .analytics import demo_report, list_connections, run_growth_report
from .config import load_settings
from .google_oauth import FileTokenStore, authorized_session, current_session_id, ensure_credentials, make_flow
from .instant_audit import instant_audit, sample_audit


ROOT = Path(__file__).resolve().parents[1]


def create_app() -> Flask:
    settings = load_settings(ROOT)
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.secret_key = settings.secret_key
    token_store = FileTokenStore(settings.token_store_dir)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/session")
    def api_session():
        credentials = ensure_credentials(settings, token_store)
        return jsonify(
            {
                "ok": True,
                "oauth_ready": settings.oauth_ready,
                "connected": bool(credentials),
                "redirect_uri": settings.google_redirect_uri,
                "report_days": settings.report_days,
                "lag_days": settings.lag_days,
            }
        )

    @app.get("/auth/google/start")
    def google_start():
        if not settings.oauth_ready:
            return jsonify({"ok": False, "message": "Google OAuth is not configured."}), 400
        current_session_id()
        flow = make_flow(settings)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        session["oauth_state"] = state
        return redirect(authorization_url)

    @app.get("/auth/google/callback")
    def google_callback():
        if not settings.oauth_ready:
            return jsonify({"ok": False, "message": "Google OAuth is not configured."}), 400
        flow = make_flow(settings, state=session.get("oauth_state"))
        flow.fetch_token(authorization_response=request.url)
        token_store.save(current_session_id(), flow.credentials)
        return redirect(url_for("index", connected="1"))

    @app.post("/auth/logout")
    def logout():
        token_store.clear(current_session_id())
        session.pop("oauth_state", None)
        return jsonify({"ok": True})

    @app.get("/api/connections")
    def api_connections():
        credentials = ensure_credentials(settings, token_store)
        if not credentials:
            return jsonify({"ok": False, "message": "Connect Google first."}), 401
        try:
            return jsonify({"ok": True, **list_connections(authorized_session(credentials))})
        except Exception as exc:
            return jsonify({"ok": False, "error": exc.__class__.__name__, "message": str(exc)}), 500

    @app.post("/api/audit")
    def api_audit():
        payload = request.get_json(silent=True) or {}
        if payload.get("demo"):
            return jsonify(sample_audit())
        try:
            return jsonify(instant_audit(str(payload.get("url") or "")))
        except Exception as exc:
            return jsonify({"ok": False, "error": exc.__class__.__name__, "message": str(exc)}), 400

    @app.post("/api/analyze")
    def api_analyze():
        payload = request.get_json(silent=True) or {}
        if payload.get("demo"):
            return jsonify(demo_report())
        credentials = ensure_credentials(settings, token_store)
        if not credentials:
            return jsonify({"ok": False, "message": "Connect Google first or run the demo report."}), 401
        gsc_site_url = str(payload.get("gsc_site_url") or "").strip()
        ga4_property_id = str(payload.get("ga4_property_id") or "").strip()
        if not gsc_site_url or not ga4_property_id:
            return jsonify({"ok": False, "message": "Choose both a Search Console property and a GA4 property."}), 400
        try:
            data = run_growth_report(
                authorized_session(credentials),
                settings,
                gsc_site_url=gsc_site_url,
                ga4_property_id=ga4_property_id,
                target_url=str(payload.get("target_url") or ""),
                days=int(payload.get("days") or settings.report_days),
                lag_days=int(payload.get("lag_days") if payload.get("lag_days") is not None else settings.lag_days),
            )
            return jsonify(data)
        except Exception as exc:
            return jsonify({"ok": False, "error": exc.__class__.__name__, "message": str(exc)}), 500

    return app
