import base64
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.models import Token, User

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PAGE = PROJECT_ROOT / "pages" / "1_📊_Dashboard.py"
SETTINGS_PAGE = PROJECT_ROOT / "pages" / "3_⚙️_Settings.py"
LIVE_INSIGHTS_PAGE = PROJECT_ROOT / "pages" / "6_🔍_Live_Insights.py"
APP_PAGE = PROJECT_ROOT / "app.py"


def _link_button_urls(app) -> list[str]:
    return [
        getattr(element.proto, "url", "")
        for element in app.main
        if type(element).__name__ == "UnknownElement"
        and getattr(element.proto, "url", "")
    ]


def _all_markdown(app) -> str:
    return "\n".join(element.value for element in app.markdown)


def _disabled_instagram_cta(html: str) -> str:
    match = re.search(
        r"<button[^>]*class=\"cl-instagram-button\"[^>]*>.*?</button>",
        html,
        re.DOTALL,
    )
    assert match, html
    return match.group(0)


def _jwt_with_role(role: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode("ascii")
    payload = base64.urlsafe_b64encode(
        json.dumps({"role": role}).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    return f"{header}.{payload}.signature"


def test_preview_safe_mode_is_forced_by_vercel_preview(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(Config, "PREVIEW_SAFE_MODE", False, raising=False)

    assert Config.preview_safe_mode() is True


def test_scheduler_is_forbidden_inside_vercel(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)

    assert Config.scheduler_allowed() is False


def test_supabase_runtime_validation_requires_server_key_on_vercel(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(
        Config, "OAUTH_REDIRECT_URI", "https://preview.example/auth/callback", raising=False
    )
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://example.supabase.co", raising=False)

    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_publishable_public", raising=False)
    assert "SUPABASE_KEY (secret/service_role required)" in Config.validate_runtime()

    monkeypatch.setattr(Config, "SUPABASE_KEY", _jwt_with_role("anon"), raising=False)
    assert "SUPABASE_KEY (secret/service_role required)" in Config.validate_runtime()

    monkeypatch.setattr(Config, "SUPABASE_KEY", _jwt_with_role("service_role"), raising=False)
    assert "SUPABASE_KEY (secret/service_role required)" not in Config.validate_runtime()

    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_secret_server", raising=False)
    assert "SUPABASE_KEY (secret/service_role required)" not in Config.validate_runtime()


def test_vercel_runtime_requires_https_auth_callback_redirect(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://example.supabase.co", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_secret_server", raising=False)

    error = "OAUTH_REDIRECT_URI (Vercel must be https://<host>/auth/callback)"

    for invalid_uri in (
        "https://preview.example/Login",
        "http://preview.example/auth/callback",
        "https:///auth/callback",
        "https://preview.example/auth/callback?next=/Dashboard",
        "https://preview.example/auth/callback#fragment",
        "not a url",
    ):
        monkeypatch.setattr(Config, "OAUTH_REDIRECT_URI", invalid_uri, raising=False)
        assert error in Config.validate_runtime()

    monkeypatch.setattr(
        Config, "OAUTH_REDIRECT_URI", "https://preview.example/auth/callback", raising=False
    )
    assert error not in Config.validate_runtime()


def test_vercel_preview_supabase_isolation_fails_closed_by_default(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(
        Config, "ALLOW_SHARED_SUPABASE_IN_PREVIEW", False, raising=False
    )
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(
        Config, "OAUTH_REDIRECT_URI", "https://preview.example/auth/callback", raising=False
    )
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://prodref.supabase.co", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_secret_server", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PREVIEW_PROJECT_REF", "", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PRODUCTION_PROJECT_REF", "", raising=False)

    errors = Config.validate_runtime()

    assert "SUPABASE_PREVIEW_PROJECT_REF" in errors
    assert "SUPABASE_PRODUCTION_PROJECT_REF" in errors


def test_vercel_preview_allows_shared_supabase_with_explicit_opt_in(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(
        Config, "ALLOW_SHARED_SUPABASE_IN_PREVIEW", True, raising=False
    )
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(
        Config, "OAUTH_REDIRECT_URI", "https://preview.example/auth/callback", raising=False
    )
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://prodref.supabase.co", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_secret_server", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PREVIEW_PROJECT_REF", "", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PRODUCTION_PROJECT_REF", "", raising=False)

    errors = Config.validate_runtime()

    assert errors == []
    assert Config.preview_safe_mode() is True


def test_vercel_preview_shared_supabase_rejects_non_project_urls(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(
        Config, "ALLOW_SHARED_SUPABASE_IN_PREVIEW", True, raising=False
    )
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(
        Config, "OAUTH_REDIRECT_URI", "https://preview.example/auth/callback", raising=False
    )
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_secret_server", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PREVIEW_PROJECT_REF", "", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PRODUCTION_PROJECT_REF", "", raising=False)

    error = "SUPABASE_URL (must be https://<project-ref>.supabase.co)"
    for invalid_url in (
        "https://example.com",
        "http://prodref.supabase.co",
        "https://api.supabase.com",
        "https://prodref.supabase.co/rest/v1",
        "https://prodref.supabase.co:443",
        "https://prodref.supabase.co:bad",
        "https://user@prodref.supabase.co",
        "https://user:pass@prodref.supabase.co",
        "not a url",
    ):
        monkeypatch.setattr(Config, "SUPABASE_URL", invalid_url, raising=False)
        assert error in Config.validate_runtime()

    monkeypatch.setattr(Config, "SUPABASE_URL", "https://prodref.supabase.co", raising=False)
    assert error not in Config.validate_runtime()


def test_vercel_preview_shared_supabase_still_requires_base_security(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(
        Config, "ALLOW_SHARED_SUPABASE_IN_PREVIEW", True, raising=False
    )
    monkeypatch.setattr(Config, "SESSION_COOKIE_SECRET", "short", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(
        Config, "OAUTH_REDIRECT_URI", "http://preview.example/auth/callback", raising=False
    )
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://prodref.supabase.co", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_KEY", "sb_publishable_public", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PREVIEW_PROJECT_REF", "", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_PRODUCTION_PROJECT_REF", "", raising=False)

    errors = Config.validate_runtime()

    assert "SESSION_COOKIE_SECRET (minimum 32 bytes)" in errors
    assert (
        "OAUTH_REDIRECT_URI (Vercel must be https://<host>/auth/callback)"
        in errors
    )
    assert "SUPABASE_KEY (secret/service_role required)" in errors
    assert "SUPABASE_PREVIEW_PROJECT_REF" not in errors
    assert "SUPABASE_PRODUCTION_PROJECT_REF" not in errors


def test_non_vercel_allows_existing_login_redirect_compatibility(monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "IS_VERCEL", False, raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_ID", "app-id", raising=False)
    monkeypatch.setattr(Config, "INSTAGRAM_APP_SECRET", "app-secret", raising=False)
    monkeypatch.setattr(Config, "OAUTH_REDIRECT_URI", "https://example.com/Login", raising=False)
    monkeypatch.setattr(Config, "CONTACT_EMAIL", "reviewer@example.com", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_URL", "https://example.supabase.co", raising=False)
    monkeypatch.setattr(Config, "SUPABASE_KEY", "test-key", raising=False)

    assert "OAUTH_REDIRECT_URI (Vercel must be https://<host>/auth/callback)" not in (
        Config.validate_runtime()
    )


def test_init_db_missing_supabase_config_does_not_create_client(monkeypatch):
    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_KEY", "", raising=False)
    monkeypatch.setattr(database_module, "_client", None)
    monkeypatch.setattr(
        database_module,
        "create_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("init_db must not construct Supabase client without config")
        ),
    )

    database_module.init_db()


def test_app_does_not_start_scheduler_on_vercel(monkeypatch):
    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(database_module, "init_db", lambda: None)
    monkeypatch.setattr(config_module.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(config_module.config, "scheduler_allowed", lambda: False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "")

    import apscheduler.schedulers.background as background_module

    class FailingScheduler:
        def __init__(self, *args, **kwargs):
            raise AssertionError("scheduler must not be constructed on Vercel")

    monkeypatch.setattr(background_module, "BackgroundScheduler", FailingScheduler)

    app = AppTest.from_file(APP_PAGE, default_timeout=5)
    app.run(timeout=5)

    assert not app.exception


def test_root_preview_missing_config_renders_login_visual_without_db_or_oauth(
    monkeypatch,
):
    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(config_module.Config, "INSTAGRAM_APP_ID", "", raising=False)
    monkeypatch.setattr(config_module.Config, "INSTAGRAM_APP_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.Config, "OAUTH_REDIRECT_URI", "", raising=False)
    monkeypatch.setattr(config_module.Config, "CONTACT_EMAIL", "", raising=False)
    monkeypatch.setattr(config_module.Config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.Config, "SUPABASE_KEY", "", raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(config_module.config, "INSTAGRAM_APP_ID", "", raising=False)
    monkeypatch.setattr(config_module.config, "INSTAGRAM_APP_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.config, "OAUTH_REDIRECT_URI", "", raising=False)
    monkeypatch.setattr(config_module.config, "CONTACT_EMAIL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_KEY", "", raising=False)
    monkeypatch.setattr(
        database_module,
        "init_db",
        lambda: (_ for _ in ()).throw(
            AssertionError("credentialless preview root must not initialize DB")
        ),
    )
    monkeypatch.setattr(
        database_module,
        "create_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("credentialless preview root must not create Supabase client")
        ),
    )

    app = AppTest.from_file(APP_PAGE, default_timeout=5)
    app.run(timeout=5)
    html = _all_markdown(app)

    assert not app.exception
    assert "cl-login-page" in html
    assert "Instagram으로 계속하기" in html
    assert app.error == []
    assert 'href="/Login?step=consent"' in html
    assert "javascript:" not in html
    assert 'href="#"' not in html


def test_vercel_production_safe_mode_missing_config_does_not_render_ui_only(
    monkeypatch,
):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "production", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", True, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.Config, "INSTAGRAM_APP_ID", "", raising=False)
    monkeypatch.setattr(config_module.Config, "INSTAGRAM_APP_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.Config, "OAUTH_REDIRECT_URI", "", raising=False)
    monkeypatch.setattr(config_module.Config, "CONTACT_EMAIL", "", raising=False)
    monkeypatch.setattr(config_module.Config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.Config, "SUPABASE_KEY", "", raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "production", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", True, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.config, "INSTAGRAM_APP_ID", "", raising=False)
    monkeypatch.setattr(config_module.config, "INSTAGRAM_APP_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.config, "OAUTH_REDIRECT_URI", "", raising=False)
    monkeypatch.setattr(config_module.config, "CONTACT_EMAIL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_KEY", "", raising=False)

    app = AppTest.from_file(APP_PAGE, default_timeout=5)
    app.run(timeout=5)
    html = _all_markdown(app)

    assert not app.exception
    assert app.error
    assert "설정 누락" in app.error[0].value
    assert "cl-login-page" not in html


def test_non_vercel_safe_mode_missing_config_keeps_config_error(monkeypatch):
    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", False, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", True, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.Config, "INSTAGRAM_APP_ID", "", raising=False)
    monkeypatch.setattr(config_module.Config, "INSTAGRAM_APP_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.Config, "OAUTH_REDIRECT_URI", "", raising=False)
    monkeypatch.setattr(config_module.Config, "CONTACT_EMAIL", "", raising=False)
    monkeypatch.setattr(config_module.Config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.Config, "SUPABASE_KEY", "", raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", False, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", True, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.config, "INSTAGRAM_APP_ID", "", raising=False)
    monkeypatch.setattr(config_module.config, "INSTAGRAM_APP_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.config, "OAUTH_REDIRECT_URI", "", raising=False)
    monkeypatch.setattr(config_module.config, "CONTACT_EMAIL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(config_module.config, "SUPABASE_KEY", "", raising=False)
    monkeypatch.setattr(database_module, "create_client", lambda *args, **kwargs: None)

    app = AppTest.from_file(APP_PAGE, default_timeout=5)
    app.run(timeout=5)
    html = _all_markdown(app)

    assert not app.exception
    assert app.error
    assert "설정 누락" in app.error[0].value
    assert "cl-login-page" not in html


def test_logged_in_non_vercel_app_uses_streamlit_logout_button(monkeypatch):
    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(database_module, "init_db", lambda: None)
    monkeypatch.setattr(config_module.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(config_module.config, "scheduler_allowed", lambda: False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", False)

    app = AppTest.from_file(APP_PAGE, default_timeout=5)
    app.session_state["user_id"] = 42
    app.session_state["instagram_username"] = "celeb_user"
    app.run(timeout=5)

    assert not app.exception
    assert "/auth/logout" not in _link_button_urls(app)
    assert any(button.label == "로그아웃" for button in app.button)


def test_logged_in_vercel_app_links_asgi_logout(monkeypatch):
    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(database_module, "init_db", lambda: None)
    monkeypatch.setattr(config_module.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(config_module.config, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(config_module.config, "scheduler_allowed", lambda: False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True)

    app = AppTest.from_file(APP_PAGE, default_timeout=5)
    app.session_state["user_id"] = 42
    app.session_state["instagram_username"] = "celeb_user"
    app.run(timeout=5)

    assert not app.exception
    assert "/auth/logout" in _link_button_urls(app)


def test_dashboard_preview_renders_existing_data_without_collection(monkeypatch):
    import src.config as config_module
    import src.database as database_module
    import src.insights_collector as collector_module

    user = User(id=42, instagram_id="ig-123", instagram_username="celeb_user")

    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview")
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False)
    monkeypatch.setattr(database_module, "init_db", lambda: None)
    monkeypatch.setattr(database_module, "get_user_by_id", lambda user_id: user)
    monkeypatch.setattr(database_module, "get_insights", lambda *args, **kwargs: [])
    monkeypatch.setattr(database_module, "get_latest_insights", lambda user_id: {})
    monkeypatch.setattr(database_module, "get_latest_audience_data", lambda user_id: None)
    monkeypatch.setattr(
        database_module,
        "get_user_token",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview dashboard must not read token for collection")
        ),
    )
    monkeypatch.setattr(
        collector_module,
        "collect_insights_for_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview dashboard must not collect insights")
        ),
    )
    monkeypatch.setattr(
        collector_module,
        "collect_audience_for_user",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview dashboard must not collect audience")
        ),
    )

    app = AppTest.from_file(DASHBOARD_PAGE, default_timeout=5)
    app.session_state["user_id"] = 42
    app.run(timeout=5)

    assert not app.exception
    assert any("Preview 안전모드" in item.value for item in app.info)


def test_settings_preview_does_not_refresh_tokens(monkeypatch):
    import src.config as config_module
    import src.database as database_module
    import src.oauth as oauth_module

    user = User(
        id=42,
        instagram_id="ig-123",
        instagram_username="celeb_user",
        created_at=datetime(2026, 8, 24, tzinfo=timezone.utc),
    )
    token = Token(
        user_id=42,
        token_type="user",
        access_token="stored-token",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview")
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False)
    monkeypatch.setattr(database_module, "init_db", lambda: None)
    monkeypatch.setattr(database_module, "get_user_by_id", lambda user_id: user)
    monkeypatch.setattr(database_module, "get_user_token", lambda *args, **kwargs: token)
    monkeypatch.setattr(
        database_module,
        "save_token",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview settings must not save refreshed token")
        ),
    )
    monkeypatch.setattr(
        oauth_module,
        "refresh_long_lived_token",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview settings must not refresh token")
        ),
    )

    app = AppTest.from_file(SETTINGS_PAGE, default_timeout=5)
    app.session_state["user_id"] = 42
    app.run(timeout=5)

    assert not app.exception
    assert any("토큰 수동 갱신이 비활성화" in item.value for item in app.info)


def test_live_insights_preview_stops_before_instagram_api(monkeypatch):
    import src.config as config_module
    import src.database as database_module
    import src.instagram_api as instagram_api_module

    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview")
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False)
    monkeypatch.setattr(database_module, "init_db", lambda: None)
    monkeypatch.setattr(
        database_module,
        "get_user_by_id",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview live insights must stop before user lookup")
        ),
    )
    monkeypatch.setattr(
        instagram_api_module,
        "InstagramAPI",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("preview live insights must stop before live API client")
        ),
    )

    app = AppTest.from_file(LIVE_INSIGHTS_PAGE, default_timeout=5)
    app.session_state["user_id"] = 42
    app.run(timeout=5)

    assert not app.exception
    assert any("실시간 호출이 비활성화" in item.value for item in app.info)
