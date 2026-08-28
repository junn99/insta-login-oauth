import asyncio
import base64
import json
from datetime import datetime, timezone
from types import SimpleNamespace

from starlette.requests import Request

from src.asgi_middleware import OAuthQuerySanitizerMiddleware
from src.consent_binding import (
    CONSENT_BINDING_COOKIE_NAME,
    build_clear_binding_cookie,
    create_binding_token,
    verify_binding_token,
)
from src.oauth_callback_service import OnboardingPersistenceError, OnboardingResult
from src.session import COOKIE_NAME, SESSION_MAX_AGE_SECONDS, verify_session_token

SECRET = "s" * 32
BINDING_ID = "browser-binding-id-1234567890"


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

    assert paths == {
        "/auth/callback",
        "/auth/instagram/start",
        "/auth/logout",
        "/healthz",
    }


def _request(
    path: str,
    query_string: str = "",
    *,
    cookie_header: str | None = None,
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    form: bytes | None = None,
) -> Request:
    resolved_headers = list(headers or [])
    if cookie_header:
        resolved_headers.append((b"cookie", cookie_header.encode("ascii")))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string.encode("ascii"),
        "headers": resolved_headers,
        "server": ("testserver", 443),
        "scheme": "https",
    }

    async def receive():
        return {"type": "http.request", "body": form or b"", "more_body": False}

    return Request(
        scope,
        receive=receive,
    )


def _binding_cookie_header() -> str:
    binding = create_binding_token(
        SECRET,
        binding_id=BINDING_ID,
    )
    return f"{CONSENT_BINDING_COOKIE_NAME}={binding.token}"


def _set_cookies(response) -> list[str]:
    return [
        value.decode("latin1")
        for name, value in response.raw_headers
        if name == b"set-cookie"
    ]


def test_consent_binding_token_is_signed_and_short_lived():
    binding = create_binding_token(
        SECRET,
        binding_id=BINDING_ID,
        now=1_700_000_000,
    )

    assert verify_binding_token(binding.token, SECRET, now=1_700_000_001) == BINDING_ID
    assert verify_binding_token(
        binding.token,
        SECRET,
        now=1_700_000_000 + 601,
    ) is None

    payload, signature = binding.token.split(".", 1)
    replacement = "A" if payload[0] != "A" else "B"
    tampered = f"{replacement}{payload[1:]}.{signature}"
    assert verify_binding_token(tampered, SECRET, now=1_700_000_001) is None


def test_consent_binding_rejects_malformed_base64_and_boolean_version():
    import src.consent_binding as consent_binding

    assert verify_binding_token("%%%.$$$", SECRET, now=1_700_000_001) is None

    binding = create_binding_token(
        SECRET,
        binding_id=BINDING_ID,
        now=1_700_000_000,
    )
    payload_part, _signature = binding.token.split(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding))
    payload["v"] = True
    assert consent_binding._parse_payload(payload, now=1_700_000_001) is None


def test_oauth_callback_uses_shared_completion_service(monkeypatch):
    import src.asgi_routes as routes

    calls = []

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])

    def fake_complete_instagram_login(code, state, *, expected_binding_id=None):
        calls.append((code, state, expected_binding_id))
        return OnboardingResult(
            user_id=42,
            instagram_id="ig-123",
            instagram_username="celeb_user",
            state_nonce="nonce-1",
        )

    monkeypatch.setattr(routes, "complete_instagram_login", fake_complete_instagram_login)

    response = routes.oauth_callback(
        _request(
            "/auth/callback",
            "code=auth-code&state=signed-consent-state",
            cookie_header=_binding_cookie_header(),
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Dashboard"
    assert calls == [("auth-code", "signed-consent-state", BINDING_ID)]


def test_oauth_callback_sets_signed_session_cookie_and_redirects(monkeypatch):
    import src.asgi_routes as routes

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        routes,
        "complete_instagram_login",
        lambda code, state, *, expected_binding_id=None: OnboardingResult(
            user_id=42,
            instagram_id="ig-123",
            instagram_username="celeb_user",
            state_nonce="nonce-1",
        ),
    )

    response = routes.oauth_callback(
        _request(
            "/auth/callback",
            "code=auth-code&state=valid-state",
            cookie_header=_binding_cookie_header(),
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Dashboard"
    assert response.headers["cache-control"] == "no-store"
    cookies = _set_cookies(response)
    cookie = next(item for item in cookies if item.startswith(f"{COOKIE_NAME}="))
    assert cookie.startswith(f"{COOKIE_NAME}=")
    assert f"Max-Age={SESSION_MAX_AGE_SECONDS}" in cookie
    assert "Secure" in cookie
    assert "HttpOnly" in cookie

    token = cookie.split("=", 1)[1].split(";", 1)[0]
    payload = verify_session_token(token, SECRET)
    assert payload.user_id == 42
    assert build_clear_binding_cookie() in cookies


def test_oauth_callback_maps_invalid_state_from_shared_service(monkeypatch):
    import src.asgi_routes as routes
    from src.oauth import StateValidationError

    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        routes,
        "complete_instagram_login",
        lambda code, state, *, expected_binding_id=None: (_ for _ in ()).throw(
            StateValidationError("invalid_state")
        ),
    )

    response = routes.oauth_callback(
        _request(
            "/auth/callback",
            "code=auth-code&state=bad-state",
            cookie_header=_binding_cookie_header(),
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?step=consent&auth_error=invalid_state"
    assert build_clear_binding_cookie() in _set_cookies(response)


def test_oauth_callback_sanitizes_callback_failure(monkeypatch, caplog):
    import src.asgi_routes as routes

    secret_error = RuntimeError("leaked-code auth-code leaked-token")

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        routes,
        "complete_instagram_login",
        lambda code, state, *, expected_binding_id=None: (
            _ for _ in ()
        ).throw(secret_error),
    )

    with caplog.at_level("ERROR", logger="src.asgi_routes"):
        response = routes.oauth_callback(
            _request(
                "/auth/callback",
                "code=auth-code&state=valid-state",
                cookie_header=_binding_cookie_header(),
            )
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?step=consent&auth_error=callback_failed"
    log_text = caplog.text
    assert "RuntimeError" in log_text
    assert "auth-code" not in log_text
    assert "leaked-token" not in log_text


def test_oauth_callback_reports_configuration_error_before_exchange(monkeypatch):
    import src.asgi_routes as routes

    calls = []
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: ["SUPABASE_URL"])
    monkeypatch.setattr(
        routes,
        "complete_instagram_login",
        lambda code, state, *, expected_binding_id=None: calls.append(
            (code, state, expected_binding_id)
        ),
    )

    response = routes.oauth_callback(
        _request("/auth/callback", "code=auth-code&state=valid-state")
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?step=consent&auth_error=configuration_error"
    assert calls == []


def test_oauth_callback_reports_missing_code_before_runtime_validation(monkeypatch):
    import src.asgi_routes as routes

    calls = []
    monkeypatch.setattr(
        routes.config,
        "validate_runtime",
        lambda: (_ for _ in ()).throw(AssertionError("runtime should not run")),
    )
    monkeypatch.setattr(routes, "complete_instagram_login", lambda *args: calls.append(args))

    response = routes.oauth_callback(_request("/auth/callback", "state=valid-state"))

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?step=consent&auth_error=missing_code"
    assert calls == []


def test_oauth_callback_maps_atomic_persistence_failure(monkeypatch):
    import src.asgi_routes as routes

    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        routes,
        "complete_instagram_login",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OnboardingPersistenceError("secret database detail")
        ),
    )

    response = routes.oauth_callback(
        _request(
            "/auth/callback",
            "code=auth-code&state=valid-state",
            cookie_header=_binding_cookie_header(),
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/Login?step=consent&auth_error=consent_persistence_failed"
    )
    assert build_clear_binding_cookie() in _set_cookies(response)


def test_oauth_callback_fails_closed_without_browser_binding(monkeypatch):
    import src.asgi_routes as routes

    calls = []
    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        routes,
        "complete_instagram_login",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    response = routes.oauth_callback(
        _request("/auth/callback", "code=auth-code&state=valid-state")
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?step=consent&auth_error=callback_failed"
    assert calls == [(("auth-code", "valid-state"), {"expected_binding_id": None})]
    assert build_clear_binding_cookie() in _set_cookies(response)


def test_instagram_start_rejects_get_without_binding(monkeypatch):
    import src.asgi_routes as routes

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])

    response = asyncio.run(routes.instagram_start(_request("/auth/instagram/start")))

    assert response.status_code == 405
    assert CONSENT_BINDING_COOKIE_NAME not in response.headers.get("set-cookie", "")


def test_instagram_start_requires_static_consent_post(monkeypatch):
    import src.asgi_routes as routes

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])

    response = asyncio.run(
        routes.instagram_start(
            _request(
                "/auth/instagram/start",
                method="POST",
                headers=[
                    (b"host", b"testserver"),
                    (b"origin", b"https://testserver"),
                    (b"sec-fetch-site", b"same-origin"),
                    (b"content-type", b"application/x-www-form-urlencoded"),
                ],
                form=b"age_confirmed=true&terms_accepted=true",
            )
        )
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/Login?step=consent&auth_error=invalid_request"
    assert CONSENT_BINDING_COOKIE_NAME not in response.headers.get("set-cookie", "")


def test_instagram_start_sets_binding_cookie_and_redirects_to_oauth(monkeypatch):
    import src.asgi_routes as routes
    import src.oauth_start_service as oauth_start_service

    monkeypatch.setattr(routes.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(routes.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        oauth_start_service.oauth_module,
        "get_oauth_url",
        lambda *, consent, binding_id: (
            f"https://www.instagram.com/oauth/authorize?client_id=app-id"
            f"&redirect_uri=https%3A%2F%2Fpreview.example%2Fauth%2Fcallback"
            f"&state=signed-state-for-{binding_id}"
        ),
    )

    response = asyncio.run(
        routes.instagram_start(
            _request(
                "/auth/instagram/start",
                method="POST",
                headers=[
                    (b"host", b"testserver"),
                    (b"origin", b"https://testserver"),
                    (b"sec-fetch-site", b"same-origin"),
                    (b"content-type", b"application/x-www-form-urlencoded"),
                ],
                form=(
                    b"age_confirmed=true&terms_accepted=true&privacy_accepted=true&"
                    b"instagram_permissions_accepted=true"
                ),
            )
        )
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith(
        "https://www.instagram.com/oauth/authorize?"
    )
    assert "client_id=app-id" in response.headers["location"]
    assert "redirect_uri=https%3A%2F%2Fpreview.example%2Fauth%2Fcallback" in response.headers["location"]
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{CONSENT_BINDING_COOKIE_NAME}=")
    assert "Max-Age=600" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" in cookie
    assert "HttpOnly" in cookie


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
