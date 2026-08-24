import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from src.asgi_middleware import OAuthQuerySanitizerMiddleware
from src.models import InstagramAccount, User
from src.session import COOKIE_NAME, SESSION_MAX_AGE_SECONDS, verify_session_token

SECRET = "s" * 32


def test_oauth_query_middleware_removes_code_from_downstream_scope():
    observed = {}

    async def downstream(scope, receive, send):
        observed["query_string"] = scope["query_string"]
        observed["captured"] = scope["state"]["oauth_query_string"]

    scope = {
        "type": "http",
        "path": "/auth/callback",
        "query_string": b"code=one-time-secret&state=signed-state",
    }
    middleware = OAuthQuerySanitizerMiddleware(downstream)

    asyncio.run(middleware(scope, None, None))

    assert observed["query_string"] == b""
    assert observed["captured"] == b"code=one-time-secret&state=signed-state"


def test_asgi_entrypoint_exposes_preview_routes():
    import asgi

    paths = {route.path for route in asgi.app._user_routes}

    assert paths == {"/auth/callback", "/auth/logout", "/healthz"}


def _request(path: str, query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "query_string": query_string.encode("ascii"),
            "headers": [],
            "server": ("testserver", 443),
            "scheme": "https",
        }
    )


def test_oauth_callback_sets_signed_session_cookie_and_redirects(monkeypatch):
    import src.asgi_routes as routes

    calls = {"users": [], "tokens": []}
    expires_at = datetime(2026, 8, 24, tzinfo=timezone.utc)

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(routes, "validate_state", lambda state: state == "valid-state")
    monkeypatch.setattr(
        routes,
        "complete_oauth_flow",
        lambda code: {
            "success": True,
            "user_token": "instagram-access-token",
            "user_token_expires": expires_at,
            "instagram_account": InstagramAccount(id="ig-123", username="celeb_user"),
        },
    )

    def fake_create_or_update_user(instagram_id, instagram_username):
        calls["users"].append((instagram_id, instagram_username))
        return User(id=42, instagram_id=instagram_id, instagram_username=instagram_username)

    def fake_save_token(user_id, token_type, access_token, expires_at=None):
        calls["tokens"].append((user_id, token_type, access_token, expires_at))

    monkeypatch.setattr(routes, "create_or_update_user", fake_create_or_update_user)
    monkeypatch.setattr(routes, "save_token", fake_save_token)

    response = routes.oauth_callback(
        _request("/auth/callback", "code=auth-code&state=valid-state")
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Dashboard"
    assert response.headers["cache-control"] == "no-store"
    assert calls["users"] == [("ig-123", "celeb_user")]
    assert calls["tokens"] == [
        (42, "user", "instagram-access-token", expires_at),
    ]
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE_NAME}=")
    assert f"Max-Age={SESSION_MAX_AGE_SECONDS}" in cookie
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "instagram-access-token" not in cookie

    token = cookie.split("=", 1)[1].split(";", 1)[0]
    payload = verify_session_token(token, SECRET)
    assert payload.user_id == 42


def test_oauth_callback_rejects_invalid_state_without_token_exchange(monkeypatch):
    import src.asgi_routes as routes

    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(routes, "validate_state", lambda state: False)

    def fail_exchange(code):
        raise AssertionError(f"token exchange should not run: {code}")

    monkeypatch.setattr(routes, "complete_oauth_flow", fail_exchange)

    response = routes.oauth_callback(
        _request("/auth/callback", "code=auth-code&state=bad-state")
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?auth_error=invalid_state"
    assert "set-cookie" not in response.headers


def test_oauth_callback_sanitizes_callback_failure(monkeypatch, caplog):
    import src.asgi_routes as routes

    secret_error = RuntimeError("leaked-code auth-code leaked-token")

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(routes, "validate_state", lambda state: True)
    monkeypatch.setattr(
        routes,
        "complete_oauth_flow",
        lambda code: (_ for _ in ()).throw(secret_error),
    )

    with caplog.at_level("ERROR", logger="src.asgi_routes"):
        response = routes.oauth_callback(
            _request("/auth/callback", "code=auth-code&state=valid-state")
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?auth_error=callback_failed"
    log_text = caplog.text
    assert "RuntimeError" in log_text
    assert "auth-code" not in log_text
    assert "leaked-token" not in log_text


def test_oauth_callback_reports_configuration_error_before_exchange(monkeypatch):
    import src.asgi_routes as routes

    monkeypatch.setattr(routes.config, "validate_runtime", lambda: ["SESSION_COOKIE_SECRET"])
    monkeypatch.setattr(routes, "validate_state", lambda state: True)

    def fail_exchange(code):
        raise AssertionError(f"token exchange should not run: {code}")

    monkeypatch.setattr(routes, "complete_oauth_flow", fail_exchange)

    response = routes.oauth_callback(
        _request("/auth/callback", "code=auth-code&state=valid-state")
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?auth_error=configuration_error"


def test_logout_clears_session_cookie():
    import src.asgi_routes as routes

    response = routes.logout(SimpleNamespace())

    assert response.status_code == 303
    assert response.headers["location"] == "/Login"
    assert response.headers["set-cookie"] == (
        f"{COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax; Secure; HttpOnly"
    )


def test_healthz_is_liveness_only():
    import src.asgi_routes as routes

    response = routes.healthz(SimpleNamespace())

    assert response.status_code == 200
    assert response.body == b'{"status":"ok"}'
    assert response.headers["cache-control"] == "no-store"
