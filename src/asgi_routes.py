"""Small HTTP routes mounted next to the Streamlit ASGI application."""

import logging

from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from . import oauth as oauth_module
from .config import config
from .consent_binding import (
    CONSENT_BINDING_COOKIE_NAME,
    build_binding_cookie,
    build_clear_binding_cookie,
    create_binding_token,
    verify_binding_token,
)
from .oauth_callback_service import (
    OnboardingPersistenceError,
    complete_instagram_login,
)
from .session import build_clear_cookie, build_session_cookie, create_session_token

logger = logging.getLogger(__name__)

LOGIN_PATH = "/Login"
DASHBOARD_PATH = "/Dashboard"


def _redirect(location: str) -> RedirectResponse:
    response = RedirectResponse(location, status_code=303)
    response.headers["cache-control"] = "no-store"
    response.headers["referrer-policy"] = "no-referrer"
    return response


def _login_error(code: str) -> RedirectResponse:
    return _redirect(f"{LOGIN_PATH}?step=consent&auth_error={code}")


def _terminal_login_error(code: str) -> RedirectResponse:
    response = _login_error(code)
    response.headers.append("set-cookie", build_clear_binding_cookie())
    return response


def _login_error_code(exc: Exception) -> str:
    exc_code = getattr(exc, "code", None)
    if exc_code == "expired_state":
        return "expired_state"
    if exc_code == "invalid_state":
        return "invalid_state"
    if isinstance(exc, OnboardingPersistenceError):
        return "consent_persistence_failed"
    if isinstance(exc, ValueError) and str(exc) in {
        "missing_code",
        "configuration_error",
    }:
        return str(exc)
    return "callback_failed"


def oauth_callback(request: Request) -> RedirectResponse:
    """Complete OAuth, persist the existing user/token rows, and set a session."""
    captured_query = request.scope.get("state", {}).get("oauth_query_string")
    query_params = (
        QueryParams(captured_query)
        if captured_query is not None
        else request.query_params
    )

    if query_params.get("error"):
        return _terminal_login_error("access_denied")

    code = query_params.get("code", "")
    state = query_params.get("state", "")
    if not code:
        return _terminal_login_error("missing_code")

    if config.validate_runtime():
        return _terminal_login_error("configuration_error")

    try:
        expected_binding_id = verify_binding_token(
            request.cookies.get(CONSENT_BINDING_COOKIE_NAME),
            config.SESSION_COOKIE_SECRET,
        )
        login = complete_instagram_login(
            code,
            state,
            expected_binding_id=expected_binding_id,
        )
        session_token = create_session_token(login.user_id, config.SESSION_COOKIE_SECRET)
        response = _redirect(DASHBOARD_PATH)
        response.headers.append("set-cookie", build_session_cookie(session_token))
        response.headers.append("set-cookie", build_clear_binding_cookie())
        return response
    except Exception as exc:  # noqa: BLE001 - OAuth/HTTP/SDK errors converge here.
        # OAuth exceptions can embed codes or tokens in request URLs. Log only
        # the type so Preview logs remain useful without disclosing credentials.
        logger.error("OAuth callback failed (%s)", type(exc).__name__)
        return _terminal_login_error(_login_error_code(exc))


def instagram_start(_request: Request) -> RedirectResponse:
    """Set the short-lived consent binding cookie before showing consent UI."""
    if config.validate_runtime():
        return _login_error("configuration_error")
    try:
        binding = create_binding_token(config.SESSION_COOKIE_SECRET)
    except (TypeError, ValueError):
        return _login_error("configuration_error")

    response = _redirect(f"{LOGIN_PATH}?step=consent")
    response.headers.append("set-cookie", build_binding_cookie(binding.token))
    return response


def logout(_request: Request) -> RedirectResponse:
    """Clear the browser session without touching Instagram or Supabase."""
    response = _redirect(LOGIN_PATH)
    response.headers.append("set-cookie", build_clear_cookie())
    return response


def healthz(_request: Request) -> JSONResponse:
    """Host-level liveness only; no database or secret access."""
    return JSONResponse(
        {"status": "ok"},
        headers={"cache-control": "no-store"},
    )
