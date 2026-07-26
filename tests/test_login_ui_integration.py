from datetime import datetime, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.models import InstagramAccount, User


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = PROJECT_ROOT / "pages" / "2_🔐_Login.py"
ASSET_DIR = PROJECT_ROOT / "assets" / "login"


@pytest.fixture
def login_patches(monkeypatch):
    import requests

    import src.config as config_module
    import src.database as database_module
    import src.oauth as oauth_module

    required_config = {
        "INSTAGRAM_APP_ID": "test-app-id",
        "INSTAGRAM_APP_SECRET": "test-app-secret",
        "OAUTH_REDIRECT_URI": "https://example.com/Login",
        "CONTACT_EMAIL": "reviewer@example.com",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
    }
    for key, value in required_config.items():
        monkeypatch.setattr(config_module.Config, key, value, raising=False)

    calls = {
        "init_db": 0,
        "oauth_url": 0,
        "validate_state": [],
        "complete_oauth_flow": [],
        "users": [],
        "tokens": [],
    }

    def fail_network(*args, **kwargs):
        raise AssertionError(f"Unexpected external network call: {args!r} {kwargs!r}")

    monkeypatch.setattr(requests.sessions.Session, "request", fail_network)

    def fail_supabase(*args, **kwargs):
        raise AssertionError(f"Unexpected Supabase client creation: {args!r} {kwargs!r}")

    monkeypatch.setattr(database_module, "create_client", fail_supabase)
    monkeypatch.setattr(oauth_module.requests, "post", fail_network)
    monkeypatch.setattr(oauth_module.requests, "get", fail_network)

    def fake_init_db():
        calls["init_db"] += 1

    def fake_get_oauth_url():
        calls["oauth_url"] += 1
        return "https://instagram.example/oauth?next=/Login&state=a\"b&scope=x<y>"

    monkeypatch.setattr(database_module, "init_db", fake_init_db)
    monkeypatch.setattr(oauth_module, "get_oauth_url", fake_get_oauth_url)

    return {
        "calls": calls,
        "database": database_module,
        "oauth": oauth_module,
    }


def _run_app(query_params=None, timeout=5):
    app = AppTest.from_file(LOGIN_PAGE, default_timeout=timeout)
    if query_params:
        app.query_params.update(query_params)
    return app.run(timeout=timeout)


def _all_markdown(app):
    return "\n".join(element.value for element in app.markdown)


def _link_buttons(app):
    return [
        element.proto
        for element in app.main
        if type(element).__name__ == "UnknownElement"
        and getattr(element.proto, "url", "")
    ]


def test_login_assets_exist_and_are_non_empty():
    expected_assets = [
        ASSET_DIR / "celeblife_logo_purple.png",
        ASSET_DIR / "celeblife_instagram_illustration.png",
    ]

    for asset in expected_assets:
        assert asset.exists()
        assert asset.stat().st_size > 0


def test_initial_login_page_renders_celeblife_ui_and_escapes_urls(login_patches):
    app = _run_app()
    html = _all_markdown(app)

    assert login_patches["calls"]["init_db"] == 1
    assert login_patches["calls"]["oauth_url"] == 1
    assert not app.title
    assert not app.error
    assert app.markdown[0].value.startswith("<style>")
    assert "\n\n" not in app.markdown[0].value
    assert "\n        <main" not in app.markdown[0].value
    assert "@media (max-width: 1080px)" in html
    assert ".cl-visual-panel {\nmin-height: 780px;\n}" in html
    assert "@media (max-width: 620px)" in html
    assert ".cl-visual-panel {\nmin-height: 570px;\n}" in html
    assert "cl-login-page" in html
    assert "인스타그램으로 계속하기" in html
    assert "href=\"https://instagram.example/oauth?next=/Login&amp;state=a&quot;b&amp;scope=x&lt;y&gt;\"" in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html
    assert 'href="/"' in html
    assert 'href="/Privacy"' in html


def test_success_callback_preserves_token_save_session_and_clears_query(login_patches, monkeypatch):
    oauth_module = login_patches["oauth"]
    database_module = login_patches["database"]
    calls = login_patches["calls"]

    monkeypatch.setattr(
        oauth_module,
        "validate_state",
        lambda state: calls["validate_state"].append(state) or True,
    )

    expires_at = datetime(2026, 7, 24, tzinfo=timezone.utc)

    def fake_complete_oauth_flow(code):
        calls["complete_oauth_flow"].append(code)
        return {
            "success": True,
            "user_token": "stored-user-token",
            "user_token_expires": expires_at,
            "instagram_account": InstagramAccount(
                id="ig-123",
                username="celeb_user",
                name="Celeb User",
                followers_count=1234,
                media_count=56,
            ),
        }

    def fake_create_or_update_user(instagram_id, instagram_username):
        calls["users"].append(
            {
                "instagram_id": instagram_id,
                "instagram_username": instagram_username,
            }
        )
        return User(id=42, instagram_id=instagram_id, instagram_username=instagram_username)

    def fake_save_token(user_id, token_type, access_token, expires_at=None):
        calls["tokens"].append(
            {
                "user_id": user_id,
                "token_type": token_type,
                "access_token": access_token,
                "expires_at": expires_at,
            }
        )

    monkeypatch.setattr(oauth_module, "complete_oauth_flow", fake_complete_oauth_flow)
    monkeypatch.setattr(database_module, "create_or_update_user", fake_create_or_update_user)
    monkeypatch.setattr(database_module, "save_token", fake_save_token)

    app = _run_app({"code": "auth-code", "state": "valid-state"})

    assert calls["validate_state"] == ["valid-state"]
    assert calls["complete_oauth_flow"] == ["auth-code"]
    assert calls["users"] == [
        {"instagram_id": "ig-123", "instagram_username": "celeb_user"}
    ]
    assert calls["tokens"] == [
        {
            "user_id": 42,
            "token_type": "user",
            "access_token": "stored-user-token",
            "expires_at": expires_at,
        }
    ]
    assert app.session_state["user_id"] == 42
    assert app.session_state["instagram_username"] == "celeb_user"
    assert app.query_params == {}
    assert app.success[0].value == "✅ @celeb_user 로그인 성공!"


def test_invalid_state_does_not_exchange_token_and_clears_query(login_patches, monkeypatch):
    oauth_module = login_patches["oauth"]
    calls = login_patches["calls"]

    monkeypatch.setattr(
        oauth_module,
        "validate_state",
        lambda state: calls["validate_state"].append(state) or False,
    )

    def fail_complete(code):
        raise AssertionError(f"Token exchange should not run for invalid state: {code}")

    monkeypatch.setattr(oauth_module, "complete_oauth_flow", fail_complete)

    app = _run_app({"code": "auth-code", "state": "bad-state"})

    assert calls["validate_state"] == ["bad-state"]
    assert calls["complete_oauth_flow"] == []
    assert calls["oauth_url"] == 1
    assert app.query_params == {}
    assert "세션이 유효하지 않거나 만료되었습니다" in app.error[0].value
    link_buttons = _link_buttons(app)
    assert len(link_buttons) == 1
    assert link_buttons[0].label == "🔗 Instagram으로 다시 로그인"
    assert (
        link_buttons[0].url
        == "https://instagram.example/oauth?next=/Login&state=a\"b&scope=x<y>"
    )


def test_user_denied_error_shows_retry_url_and_clears_query(login_patches):
    calls = login_patches["calls"]

    app = _run_app(
        {
            "error": "access_denied",
            "error_reason": "user_denied",
            "error_description": "User denied",
        }
    )

    assert calls["oauth_url"] == 1
    assert app.query_params == {}
    assert app.warning[0].value == "권한 요청이 거부되었습니다."
    assert "instagram_business_manage_insights" in _all_markdown(app)
    link_buttons = _link_buttons(app)
    assert len(link_buttons) == 1
    assert link_buttons[0].label == "🔗 다시 시도"
    assert (
        link_buttons[0].url
        == "https://instagram.example/oauth?next=/Login&state=a\"b&scope=x<y>"
    )
