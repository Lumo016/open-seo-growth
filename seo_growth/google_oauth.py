from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from flask import session
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from .config import GOOGLE_SCOPES, Settings


def current_session_id() -> str:
    if "sid" not in session:
        session["sid"] = secrets.token_urlsafe(24)
    return str(session["sid"])


class FileTokenStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})
        return self.root / f"{safe}.json"

    def load(self, session_id: str) -> Credentials | None:
        path = self._path(session_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Credentials.from_authorized_user_info(data, scopes=GOOGLE_SCOPES)

    def save(self, session_id: str, credentials: Credentials) -> None:
        self._path(session_id).write_text(json.dumps(credentials_to_dict(credentials), indent=2), encoding="utf-8")

    def clear(self, session_id: str) -> None:
        path = self._path(session_id)
        if path.exists():
            path.unlink()


def credentials_to_dict(credentials: Credentials) -> dict[str, Any]:
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }


def oauth_client_config(settings: Settings) -> dict[str, Any]:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def make_flow(settings: Settings, *, state: str | None = None) -> Flow:
    if settings.allow_insecure_oauth:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    return Flow.from_client_config(
        oauth_client_config(settings),
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.google_redirect_uri,
        state=state,
    )


def ensure_credentials(settings: Settings, token_store: FileTokenStore) -> Credentials | None:
    credentials = token_store.load(current_session_id())
    if not credentials:
        return None
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_store.save(current_session_id(), credentials)
    return credentials


def authorized_session(credentials: Credentials) -> AuthorizedSession:
    return AuthorizedSession(credentials)

