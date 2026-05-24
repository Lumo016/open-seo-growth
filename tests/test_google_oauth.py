from google.oauth2.credentials import Credentials

from seo_growth.google_oauth import FileTokenStore


TOKEN_KEY = "unit-test-token-encryption-secret"


def make_credentials() -> Credentials:
    return Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )


def test_file_token_store_can_encrypt_google_credentials(tmp_path):
    store = FileTokenStore(tmp_path, TOKEN_KEY)

    store.save("session-1", make_credentials())

    raw = (tmp_path / "session-1.json").read_bytes()
    assert b"access-token" not in raw
    assert b"refresh-token" not in raw
    assert b"client-secret" not in raw

    loaded = store.load("session-1")
    assert loaded is not None
    assert loaded.token == "access-token"
    assert loaded.refresh_token == "refresh-token"


def test_file_token_store_keeps_plaintext_when_no_encryption_key(tmp_path):
    store = FileTokenStore(tmp_path)

    store.save("session-1", make_credentials())

    raw = (tmp_path / "session-1.json").read_text(encoding="utf-8")
    assert "access-token" in raw
    assert "refresh-token" in raw


def test_file_token_store_migrates_plain_token_when_encryption_is_enabled(tmp_path):
    FileTokenStore(tmp_path).save("session-1", make_credentials())
    encrypted_store = FileTokenStore(tmp_path, TOKEN_KEY)

    loaded = encrypted_store.load("session-1")

    assert loaded is not None
    assert loaded.token == "access-token"
    raw = (tmp_path / "session-1.json").read_bytes()
    assert b"access-token" not in raw
