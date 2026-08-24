"""Small HTTP routes mounted next to the Streamlit ASGI application."""

import logging

from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from .config import config
from .database import create_or_update_user, save_token
from .oauth import complete_oauth_flow, validate_state
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
    return _redirect(f"{LOGIN_PATH}?auth_error={code}")


def oauth_callback(request: Request) -> RedirectResponse:
    """Complete OAuth, persist the existing user/token rows, and set a session."""
    captured_query = request.scope.get("state", {}).get("oauth_query_string")
    query_params = (
        QueryParams(captured_query)
        if captured_query is not None
        else request.query_params
    )

    if query_params.get("error"):
        return _login_error("access_denied")

    code = query_params.get("code", "")
    state = query_params.get("state", "")
    if not code:
        return _login_error("missing_code")
    if not validate_state(state):
        return _login_error("invalid_state")
    if config.validate_runtime():
        return _login_error("configuration_error")

    try:
        result = complete_oauth_flow(code)
        if not result.get("success"):
            raise ValueError("OAuth flow did not report success")

        account = result["instagram_account"]
        user = create_or_update_user(
            instagram_id=account.id,
            instagram_username=account.username,
        )
        if not user or user.id is None:
            raise ValueError("User record did not return an id")

        save_token(
            user_id=user.id,
            token_type="user",
            access_token=result["user_token"],
            expires_at=result["user_token_expires"],
        )

        session_token = create_session_token(user.id, config.SESSION_COOKIE_SECRET)
        response = _redirect(DASHBOARD_PATH)
        response.headers.append("set-cookie", build_session_cookie(session_token))
        return response
    except Exception as exc:  # noqa: BLE001 - OAuth/HTTP/SDK errors converge here.
        # OAuth exceptions can embed codes or tokens in request URLs. Log only
        # the type so Preview logs remain useful without disclosing credentials.
        logger.error("OAuth callback failed (%s)", type(exc).__name__)
        return _login_error("callback_failed")


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
