"""Signed cookie session helpers for Vercel/ASGI auth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

COOKIE_NAME = "cl_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
DEFAULT_MAX_AGE_SECONDS = SESSION_MAX_AGE_SECONDS
SESSION_VERSION = 1
MIN_SECRET_BYTES = 32


@dataclass(frozen=True)
class SessionPayload:
    user_id: int
    issued_at: int
    expires_at: int


def create_session_token(
    user_id: int,
    secret: str | bytes,
    *,
    now: int | None = None,
    max_age_seconds: int = SESSION_MAX_AGE_SECONDS,
) -> str:
    """Create a signed, base64url-encoded JSON session token."""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")

    issued_at = _current_time(now)
    payload = {
        "v": SESSION_VERSION,
        "user_id": user_id,
        "iat": issued_at,
        "exp": issued_at + max_age_seconds,
    }
    payload_part = _base64url_encode(_json_bytes(payload))
    signature_part = _base64url_encode(_sign(payload_part.encode("ascii"), secret))
    return f"{payload_part}.{signature_part}"


def verify_session_token(
    token: str,
    secret: str | bytes,
    *,
    now: int | None = None,
) -> SessionPayload | None:
    """Return a typed session payload when the token is valid, otherwise None."""
    if not isinstance(token, str):
        return None

    parts = token.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None

    payload_part, signature_part = parts
    try:
        expected_signature = _base64url_encode(
            _sign(payload_part.encode("ascii"), secret)
        )
    except (TypeError, ValueError):
        return None

    if not hmac.compare_digest(signature_part, expected_signature):
        return None

    try:
        payload = json.loads(_base64url_decode(payload_part))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    session_payload = _parse_payload(payload)
    if session_payload is None:
        return None

    current_time = _current_time(now)
    if session_payload.issued_at > current_time:
        return None
    if session_payload.expires_at <= current_time:
        return None

    return session_payload


def build_set_cookie_header(
    token: str,
    *,
    cookie_name: str = COOKIE_NAME,
    max_age_seconds: int = SESSION_MAX_AGE_SECONDS,
) -> str:
    """Build the Set-Cookie value for a valid signed session token."""
    if not token:
        raise ValueError("token must be non-empty")
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    return (
        f"{cookie_name}={token}; Max-Age={max_age_seconds}; Path=/; "
        "SameSite=Lax; Secure; HttpOnly"
    )


def build_clear_cookie_header(*, cookie_name: str = COOKIE_NAME) -> str:
    """Build the Set-Cookie value that clears the session cookie."""
    return (
        f"{cookie_name}=; Max-Age=0; Path=/; SameSite=Lax; "
        "Secure; HttpOnly"
    )


def build_session_cookie(
    token: str,
    *,
    max_age_seconds: int = SESSION_MAX_AGE_SECONDS,
) -> str:
    return build_set_cookie_header(token, max_age_seconds=max_age_seconds)


def build_clear_cookie() -> str:
    return build_clear_cookie_header()


def _parse_payload(payload: Any) -> SessionPayload | None:
    if not isinstance(payload, dict):
        return None
    if set(payload) != {"v", "user_id", "iat", "exp"}:
        return None
    if payload["v"] != SESSION_VERSION:
        return None

    user_id = payload["user_id"]
    issued_at = payload["iat"]
    expires_at = payload["exp"]

    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        return None
    if isinstance(issued_at, bool) or not isinstance(issued_at, int):
        return None
    if isinstance(expires_at, bool) or not isinstance(expires_at, int):
        return None
    if expires_at <= issued_at:
        return None

    return SessionPayload(
        user_id=user_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _current_time(now: int | None) -> int:
    if now is None:
        return int(time.time())
    if isinstance(now, bool) or not isinstance(now, int):
        raise ValueError("now must be an integer timestamp")
    return now


def _secret_bytes(secret: str | bytes) -> bytes:
    if isinstance(secret, str):
        secret_bytes = secret.encode("utf-8")
    elif isinstance(secret, bytes):
        secret_bytes = secret
    else:
        raise TypeError("secret must be str or bytes")

    if len(secret_bytes) < MIN_SECRET_BYTES:
        raise ValueError("secret must be at least 32 bytes")
    return secret_bytes


def _sign(message: bytes, secret: str | bytes) -> bytes:
    return hmac.new(_secret_bytes(secret), message, hashlib.sha256).digest()


def _json_bytes(payload: dict[str, int]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
