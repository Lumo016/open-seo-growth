from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

from .analytics import demo_report, list_connections, run_growth_report
from .config import build_platform_readiness, load_settings
from .google_oauth import FileTokenStore, authorized_session, current_session_id, ensure_credentials, make_flow
from .instant_audit import instant_audit, sample_audit
from .rate_limit import InMemoryRateLimiter


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Open SEO Growth"
APP_DESCRIPTION = (
    "Open SEO Growth helps beginners audit SEO and GEO readiness, connect Google, "
    "and turn GA4 plus Search Console data into search growth actions."
)
APP_REPOSITORY = "https://github.com/Lumo016/open-seo-growth"
LEGAL_PAGES = {
    "privacy": {
        "title": "Privacy Policy",
        "description": "How Open SEO Growth handles URL audits, Google OAuth data, analytics metrics, exports, and local demo storage.",
        "sections": [
            {
                "heading": "Summary",
                "items": [
                    "Open SEO Growth is an open-source SEO and GEO workbench.",
                    "The starter app can run sample reports without collecting Google data.",
                    "If Google OAuth is configured, the app requests read-only access to Search Console and GA4 data selected by the signed-in user.",
                    "The starter does not sell user data or include advertising trackers.",
                ],
            },
            {
                "heading": "Data The App May Process",
                "items": [
                    "Website URLs submitted for live audits.",
                    "Public HTML, HTTP headers, robots.txt, sitemap.xml, and llms.txt signals fetched from submitted public websites.",
                    "Google Search Console sites, clicks, impressions, CTR, average position, queries, and pages when a user connects Google.",
                    "Google Analytics 4 properties, sessions, channel groups, landing pages, events, and ecommerce metrics when a user connects Google.",
                    "OAuth tokens required to refresh the connected Google session.",
                    "Browser-generated exports such as Markdown, JSON, content briefs, and task queues.",
                ],
            },
            {
                "heading": "How Data Is Used",
                "items": [
                    "To render SEO and GEO audit reports.",
                    "To discover available Search Console and GA4 properties.",
                    "To calculate growth metrics and opportunity queues.",
                    "To generate exports requested by the user.",
                    "To operate, secure, debug, and improve the app.",
                ],
            },
            {
                "heading": "Google User Data",
                "items": [
                    "Google data is used only to provide visible SEO, GEO, and growth analysis features in this app.",
                    "Use and transfer of information received from Google APIs should adhere to the Google API Services User Data Policy, including the Limited Use requirements.",
                    "Google data is not sold.",
                    "Google data is not used for advertising.",
                    "Google data is not transferred to third parties except as required to provide the app, comply with law, or protect against abuse.",
                    "The starter requests read-only Google scopes and does not modify Search Console or GA4 properties.",
                ],
            },
            {
                "heading": "Storage And Retention",
                "items": [
                    "The open-source starter stores OAuth tokens in files under instance/oauth_tokens for local demos and private single-user trials.",
                    "If TOKEN_ENCRYPTION_KEY is configured, token files are encrypted at rest before they are written to disk.",
                    "Public multi-user deployments should replace the file token store with encrypted database-backed token storage.",
                    "Browser exports are created client-side and are not written to the Flask server by default.",
                    "Server logs may contain request metadata depending on the hosting platform.",
                ],
            },
            {
                "heading": "User Controls",
                "items": [
                    "Users can disconnect Google by using the logout endpoint in the app.",
                    "Self-hosters can delete OAuth token files under the configured token store directory.",
                    "Hosted operators should provide a user data deletion path before serving multiple users.",
                ],
            },
        ],
    },
    "terms": {
        "title": "Terms Of Service",
        "description": "Terms for using Open SEO Growth as an open-source SEO and GEO audit workbench.",
        "sections": [
            {
                "heading": "Use Of The App",
                "items": [
                    "Open SEO Growth is provided as an open-source starter for SEO and GEO analysis.",
                    "You are responsible for how you deploy, configure, and operate your instance.",
                    "You should audit only websites you own, manage, or are authorized to review.",
                    "Do not use the app to probe private networks, abuse public websites, bypass access controls, or overload third-party services.",
                ],
            },
            {
                "heading": "Reports And Recommendations",
                "items": [
                    "SEO and GEO scores are heuristics, not guarantees of rankings, clicks, revenue, AI citations, or traffic.",
                    "Reports are informational and should be reviewed before client delivery or implementation.",
                    "The app does not provide legal, financial, or professional compliance advice.",
                ],
            },
            {
                "heading": "Google Connections",
                "items": [
                    "If Google OAuth is enabled, users must authorize access through Google's consent flow.",
                    "The starter uses read-only scopes for Search Console and GA4 analysis.",
                    "Operators must configure OAuth consent, authorized domains, privacy policy URLs, and any required verification before public use.",
                ],
            },
            {
                "heading": "Open-Source License",
                "items": [
                    "The repository is distributed under the MIT License.",
                    "Third-party services such as Google APIs, Render, and GitHub are governed by their own terms.",
                    "Contributions are welcome, but contributors should not submit secrets, private analytics data, customer exports, or real OAuth tokens.",
                ],
            },
            {
                "heading": "Availability And Changes",
                "items": [
                    "The app is provided as-is without uptime, accuracy, or fitness guarantees.",
                    "Features, scoring models, exports, and setup flows may change as the project improves.",
                    "Public deployments should add encrypted token storage, durable user accounts, platform rate limiting, and abuse monitoring before serving real customers.",
                ],
            },
        ],
    },
}


def create_app() -> Flask:
    settings = load_settings(ROOT)
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.secret_key = settings.secret_key
    token_store = FileTokenStore(settings.token_store_dir, settings.token_encryption_key)
    audit_limiter = InMemoryRateLimiter()
    public_pages = [
        {
            "path": "/",
            "priority": "1.0",
            "changefreq": "weekly",
        },
        {
            "path": "/robots.txt",
            "priority": "0.3",
            "changefreq": "monthly",
        },
        {
            "path": "/sitemap.xml",
            "priority": "0.3",
            "changefreq": "monthly",
        },
        {
            "path": "/llms.txt",
            "priority": "0.4",
            "changefreq": "monthly",
        },
        {
            "path": "/privacy",
            "priority": "0.7",
            "changefreq": "monthly",
        },
        {
            "path": "/terms",
            "priority": "0.7",
            "changefreq": "monthly",
        },
    ]

    def public_url(path: str) -> str:
        return f"{settings.app_base_url.rstrip('/')}/{path.lstrip('/')}"

    def homepage_metadata() -> dict[str, object]:
        app_url = public_url("/")
        return {
            "app_name": APP_NAME,
            "description": APP_DESCRIPTION,
            "canonical_url": app_url,
            "logo_url": public_url("/static/assets/logo.svg"),
            "repository_url": APP_REPOSITORY,
            "json_ld": {
                "@context": "https://schema.org",
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "description": APP_DESCRIPTION,
                "url": app_url,
                "applicationCategory": "BusinessApplication",
                "operatingSystem": "Web",
                "isAccessibleForFree": True,
                "codeRepository": APP_REPOSITORY,
                "license": f"{APP_REPOSITORY}/blob/main/LICENSE",
                "image": public_url("/static/assets/logo.svg"),
                "offers": {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD",
                },
                "featureList": [
                    "Instant URL-only SEO audit",
                    "GEO readiness scoring",
                    "Google Search Console and GA4 OAuth setup",
                    "Search clicks, impressions, CTR, ranking, and session reports",
                    "Markdown, JSON, content brief, and action queue exports",
                ],
            },
        }

    def page_metadata(path: str, title: str, description: str) -> dict[str, object]:
        canonical_url = public_url(path)
        return {
            "app_name": APP_NAME,
            "title": f"{title} | {APP_NAME}",
            "description": description,
            "canonical_url": canonical_url,
            "logo_url": public_url("/static/assets/logo.svg"),
        }

    def client_identity() -> str:
        forwarded_for = (request.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
        return forwarded_for or request.remote_addr or "unknown"

    def rate_limit_response(result: dict[str, int | bool]):
        retry_after = int(result.get("retry_after_seconds") or 0)
        response = jsonify(
            {
                "ok": False,
                "error": "RateLimitExceeded",
                "message": f"Audit rate limit exceeded. Try again in {retry_after} seconds.",
                "retry_after_seconds": retry_after,
            }
        )
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        response.headers["X-RateLimit-Limit"] = str(result.get("limit") or 0)
        response.headers["X-RateLimit-Remaining"] = str(result.get("remaining") or 0)
        response.headers["X-RateLimit-Reset"] = str(result.get("reset_seconds") or 0)
        return response

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response

    @app.get("/")
    def index():
        return render_template("index.html", meta=homepage_metadata())

    @app.get("/privacy")
    def privacy():
        page = LEGAL_PAGES["privacy"]
        return render_template(
            "legal.html",
            meta=page_metadata("/privacy", page["title"], page["description"]),
            page=page,
        )

    @app.get("/terms")
    def terms():
        page = LEGAL_PAGES["terms"]
        return render_template(
            "legal.html",
            meta=page_metadata("/terms", page["title"], page["description"]),
            page=page,
        )

    @app.get("/robots.txt")
    def robots_txt():
        body = "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Disallow: /api/",
                "Disallow: /auth/",
                f"Sitemap: {public_url('/sitemap.xml')}",
                "",
            ]
        )
        return Response(body, content_type="text/plain; charset=utf-8")

    @app.get("/sitemap.xml")
    def sitemap_xml():
        urls = "\n".join(
            [
                "  <url>"
                f"<loc>{escape(public_url(page['path']))}</loc>"
                f"<changefreq>{page['changefreq']}</changefreq>"
                f"<priority>{page['priority']}</priority>"
                "</url>"
                for page in public_pages
            ]
        )
        body = "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
                urls,
                "</urlset>",
                "",
            ]
        )
        return Response(body, content_type="application/xml; charset=utf-8")

    @app.get("/llms.txt")
    def llms_txt():
        body = "\n".join(
            [
                "# Open SEO Growth",
                "",
                "Open SEO Growth is an open-source SEO and GEO workbench for instant URL audits, beginner Google setup, and GA4/Search Console growth analysis.",
                "",
                "## Primary Pages",
                f"- App: {public_url('/')}",
                f"- Privacy Policy: {public_url('/privacy')}",
                f"- Terms Of Service: {public_url('/terms')}",
                f"- Sitemap: {public_url('/sitemap.xml')}",
                "",
                "## Useful Capabilities",
                "- Run a URL-only SEO and GEO readiness audit without Google data.",
                "- Export Markdown, JSON, content briefs, growth reports, and action queues from browser state.",
                "- Connect Google Search Console and GA4 through OAuth when the deployment is configured.",
                "- Use sample audit and sample growth modes when no Google account or website data is available.",
                "",
                "## Limits",
                "- GEO scoring is a transparent heuristic, not a promise of AI citations, rankings, or traffic.",
                "- Public multi-user deployments should replace file-based OAuth token storage with encrypted database-backed storage.",
                "- Anonymous live URL audits are rate limited and should also be protected by platform-level abuse controls.",
                "",
            ]
        )
        return Response(body, content_type="text/plain; charset=utf-8")

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True, "service": "open-seo-growth"})

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
                "platform_readiness": build_platform_readiness(settings),
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
            raw_url = str(payload.get("url") or "")
            if not raw_url.strip():
                raise ValueError("Enter a website URL first.")
            limit = audit_limiter.check(
                f"audit:{client_identity()}",
                limit=settings.audit_rate_limit_per_hour,
                window_seconds=3600,
            )
            if not limit["allowed"]:
                return rate_limit_response(limit)
            return jsonify(instant_audit(raw_url))
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
