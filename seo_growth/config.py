from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()

DEFAULT_DAYS = 30
DEFAULT_LAG_DAYS = 2
DEFAULT_MIN_IMPRESSIONS = 20
DEFAULT_AUDIT_RATE_LIMIT_PER_HOUR = 30

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw not in {None, ""} else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def env_text(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass(frozen=True)
class Settings:
    secret_key: str
    app_base_url: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    token_store_dir: Path
    report_days: int
    lag_days: int
    min_impressions: int
    audit_rate_limit_per_hour: int
    allow_insecure_oauth: bool

    @property
    def oauth_ready(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.google_redirect_uri)


def is_local_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def build_platform_readiness(settings: Settings) -> dict[str, object]:
    base_is_local = is_local_url(settings.app_base_url)
    redirect_is_local = is_local_url(settings.google_redirect_uri)
    base_uses_https = settings.app_base_url.startswith("https://")
    redirect_uses_https = settings.google_redirect_uri.startswith("https://")
    local_demo_ok = base_is_local and redirect_is_local and settings.allow_insecure_oauth
    hosted_https_ok = base_uses_https and redirect_uses_https and not settings.allow_insecure_oauth
    secret_is_default = settings.secret_key in {"", "dev-only-change-me", "change-me"}
    audit_rate_limit_ok = settings.audit_rate_limit_per_hour > 0
    items = [
        {
            "id": "oauth_client",
            "label": "Google OAuth client",
            "ok": settings.oauth_ready,
            "status": "Ready" if settings.oauth_ready else "Missing",
            "action": "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI.",
            "scope": "google",
        },
        {
            "id": "redirect_uri",
            "label": "OAuth redirect URI",
            "ok": bool(settings.google_redirect_uri.endswith("/auth/google/callback")),
            "status": "Configured" if settings.google_redirect_uri.endswith("/auth/google/callback") else "Check",
            "action": "Use /auth/google/callback and add the exact URI to Google Cloud.",
            "scope": "google",
        },
        {
            "id": "local_demo",
            "label": "Local demo mode",
            "ok": local_demo_ok,
            "status": "Ready" if local_demo_ok else "Off",
            "action": "Use localhost plus ALLOW_INSECURE_OAUTH=1 only for local testing.",
            "scope": "local",
        },
        {
            "id": "hosted_https",
            "label": "Hosted HTTPS mode",
            "ok": hosted_https_ok,
            "status": "Ready" if hosted_https_ok else "Not ready",
            "action": "Set APP_BASE_URL and GOOGLE_REDIRECT_URI to HTTPS and remove ALLOW_INSECURE_OAUTH.",
            "scope": "production",
        },
        {
            "id": "secret_key",
            "label": "Flask secret key",
            "ok": not secret_is_default,
            "status": "Set" if not secret_is_default else "Default",
            "action": "Set a strong FLASK_SECRET_KEY before sharing a hosted deployment.",
            "scope": "production",
        },
        {
            "id": "audit_rate_limit",
            "label": "Public audit rate limit",
            "ok": audit_rate_limit_ok,
            "status": f"{settings.audit_rate_limit_per_hour}/hour" if audit_rate_limit_ok else "Off",
            "action": "Set AUDIT_RATE_LIMIT_PER_HOUR above zero before allowing anonymous URL scans.",
            "scope": "production",
        },
        {
            "id": "token_store",
            "label": "Token storage",
            "ok": False,
            "status": "File store",
            "action": "FileTokenStore is fine for local demos. Hosted multi-user deployments need encrypted database-backed token storage.",
            "scope": "production",
        },
    ]
    ready_for_google = settings.oauth_ready and (local_demo_ok or hosted_https_ok)
    ready_for_hosting = settings.oauth_ready and hosted_https_ok and not secret_is_default and audit_rate_limit_ok
    return {
        "mode": "local_demo" if local_demo_ok else "hosted_https" if hosted_https_ok else "setup_needed",
        "ready_for_google": ready_for_google,
        "ready_for_hosted_saas": False,
        "hosted_core_ready": ready_for_hosting,
        "token_store": "file",
        "app_base_url": settings.app_base_url,
        "redirect_uri": settings.google_redirect_uri,
        "allow_insecure_oauth": settings.allow_insecure_oauth,
        "audit_rate_limit_per_hour": settings.audit_rate_limit_per_hour,
        "items": items,
        "summary": (
            "Local demo OAuth is ready."
            if ready_for_google and local_demo_ok
            else "Hosted OAuth basics are ready, but token storage must be replaced before multi-user SaaS."
            if ready_for_hosting
            else "Google connection needs platform setup before users can authorize in one click."
        ),
    }


def load_settings(root: Path) -> Settings:
    app_base_url = env_text("APP_BASE_URL") or env_text("RENDER_EXTERNAL_URL") or "http://127.0.0.1:8792"
    app_base_url = app_base_url.rstrip("/")
    redirect_uri = env_text("GOOGLE_REDIRECT_URI") or f"{app_base_url}/auth/google/callback"
    token_dir = Path(os.getenv("TOKEN_STORE_DIR", "instance/oauth_tokens"))
    if not token_dir.is_absolute():
        token_dir = root / token_dir
    return Settings(
        secret_key=os.getenv("FLASK_SECRET_KEY", "dev-only-change-me"),
        app_base_url=app_base_url,
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        google_redirect_uri=redirect_uri,
        token_store_dir=token_dir,
        report_days=env_int("ANALYTICS_REPORT_DAYS", DEFAULT_DAYS, minimum=7, maximum=180),
        lag_days=env_int("ANALYTICS_DATA_LAG_DAYS", DEFAULT_LAG_DAYS, minimum=0, maximum=7),
        min_impressions=env_int("GSC_OPPORTUNITY_MIN_IMPRESSIONS", DEFAULT_MIN_IMPRESSIONS, minimum=1, maximum=10000),
        audit_rate_limit_per_hour=env_int(
            "AUDIT_RATE_LIMIT_PER_HOUR",
            DEFAULT_AUDIT_RATE_LIMIT_PER_HOUR,
            minimum=0,
            maximum=10000,
        ),
        allow_insecure_oauth=os.getenv("ALLOW_INSECURE_OAUTH", "").lower() in {"1", "true", "yes"},
    )
