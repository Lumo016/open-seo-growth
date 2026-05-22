from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

DEFAULT_DAYS = 30
DEFAULT_LAG_DAYS = 2
DEFAULT_MIN_IMPRESSIONS = 20

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
    allow_insecure_oauth: bool

    @property
    def oauth_ready(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.google_redirect_uri)


def load_settings(root: Path) -> Settings:
    app_base_url = os.getenv("APP_BASE_URL", "http://127.0.0.1:8792").rstrip("/")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", f"{app_base_url}/auth/google/callback")
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
        allow_insecure_oauth=os.getenv("ALLOW_INSECURE_OAUTH", "").lower() in {"1", "true", "yes"},
    )

