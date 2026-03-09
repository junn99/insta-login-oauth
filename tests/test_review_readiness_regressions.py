from importlib import import_module, reload
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from requests import HTTPError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVACY_PAGE = PROJECT_ROOT / "pages" / "4_🔒_Privacy.py"
DELETION_PAGE = PROJECT_ROOT / "pages" / "5_🗑️_Data-Deletion.py"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _reload_oauth_with_env(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_APP_ID", "test-app-id")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://example.com/oauth/callback")
    monkeypatch.setenv("CONTACT_EMAIL", "reviewer@example.com")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")

    config_module = import_module("src.config")
    oauth_module = import_module("src.oauth")
    reload(config_module)
    oauth_module = reload(oauth_module)
    return oauth_module, config_module.config


class _MockResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.text = str(self._data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}")


def test_contact_email_placeholders():
    privacy = _read_text(PRIVACY_PAGE)
    deletion = _read_text(DELETION_PAGE)

    assert "[CONTACT_EMAIL]" not in privacy
    assert "[CONTACT_EMAIL]" not in deletion


def test_privacy_no_encryption_overclaim():
    privacy = _read_text(PRIVACY_PAGE)

    assert "암호화 저장" not in privacy
    assert "stored encrypted" not in privacy.lower()


def test_oauth_state_signing_and_tamper(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    state = oauth_module.generate_state()
    assert oauth_module.validate_state(state)

    payload_part, signature_part = state.split(".", 1)
    replacement = "A" if payload_part[0] != "A" else "B"
    tampered_payload = replacement + payload_part[1:]
    tampered_state = f"{tampered_payload}.{signature_part}"

    assert not oauth_module.validate_state(tampered_state)


def test_oauth_state_ttl_expiry(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    base_time = 1_700_000_000
    monkeypatch.setattr(oauth_module.time, "time", lambda: base_time)

    state = oauth_module.generate_state()
    assert oauth_module.validate_state(state)

    monkeypatch.setattr(
        oauth_module.time,
        "time",
        lambda: base_time + oauth_module._STATE_TTL_SECONDS + 1,
    )
    assert not oauth_module.validate_state(state)


def test_oauth_url_contains_scopes_and_redirect_uri(monkeypatch):
    oauth_module, app_config = _reload_oauth_with_env(monkeypatch)

    oauth_url = oauth_module.get_oauth_url(state="fixed-state")
    query = parse_qs(urlparse(oauth_url).query)

    required_scopes = {
        "instagram_business_basic",
        "instagram_business_manage_insights",
    }
    actual_scopes = set(query["scope"][0].split(","))

    assert required_scopes.issubset(actual_scopes)
    assert query["redirect_uri"][0] == app_config.OAUTH_REDIRECT_URI
    assert query["redirect_uri"][0] == "https://example.com/oauth/callback"
    assert oauth_url.startswith("https://www.instagram.com/oauth/authorize")


def test_complete_oauth_flow_returns_user_id(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    # Mock exchange_code_for_token (POST to Instagram OAuth)
    # Business Login returns {"data": [...]} format per official docs
    def fake_post(url, data=None):
        return _MockResponse(200, {"data": [{"access_token": "short-token", "user_id": 12345, "permissions": "instagram_business_basic,instagram_business_manage_insights"}]})

    # Mock get requests (long-lived token exchange + account info)
    def fake_get(url, params=None):
        if "access_token" in url or "ig_exchange_token" in str(params):
            return _MockResponse(200, {
                "access_token": "long-lived-token",
                "token_type": "bearer",
                "expires_in": 5184000,
            })
        if "/me" in url:
            # /me may also return {"data": [...]} per Get Started guide
            return _MockResponse(200, {"data": [{
                "user_id": "12345",
                "username": "testuser",
                "name": "Test User",
                "profile_picture_url": "https://example.com/pic.jpg",
                "followers_count": 1000,
                "media_count": 50,
            }]})
        raise AssertionError(f"Unexpected GET URL: {url}")

    monkeypatch.setattr(oauth_module.requests, "post", fake_post)
    monkeypatch.setattr(oauth_module.requests, "get", fake_get)

    result = oauth_module.complete_oauth_flow("test-code")

    assert result["success"] is True
    assert result["user_token"] == "long-lived-token"
    assert result["instagram_account"].id == "12345"
    assert result["instagram_account"].username == "testuser"
    assert "page_id" not in result
    assert "page_token" not in result
