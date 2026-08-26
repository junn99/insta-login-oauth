"""Short-lived browser binding for the consent-to-OAuth handoff."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

CONSENT_BINDING_COOKIE_NAME = "cl_consent_binding"
CONSENT_BINDING_SESSION_KEY = "cl_consent_binding_id"
CONSENT_BINDING_SESSION_EXP_KEY = "cl_consent_binding_exp"
CONSENT_BINDING_MAX_AGE_SECONDS = 10 * 60
CONSENT_BINDING_VERSION = 1
MIN_SECRET_BYTES = 32
_BINDING_ID_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


@dataclass(frozen=True)
class ConsentBinding:
    binding_id: str
    token: str
    issued_at: int
    expires_at: int


def create_binding_token(
    secret: str | bytes,
    *,
    binding_id: str | None = None,
    now: int | None = None,
) -> ConsentBinding:
    """Create a signed cookie token containing a random browser binding id."""
    issued_at = _current_time(now)
    resolved_binding_id = binding_id or create_binding_id()
    _require_binding_id(resolved_binding_id)
    payload = {
        "v": CONSENT_BINDING_VERSION,
        "bid": resolved_binding_id,
        "iat": issued_at,
        "exp": issued_at + CONSENT_BINDING_MAX_AGE_SECONDS,
    }
    payload_part = _base64url_encode(_json_bytes(payload))
    signature_part = _base64url_encode(_sign(payload_part.encode("ascii"), secret))
    return ConsentBinding(
        binding_id=resolved_binding_id,
        token=f"{payload_part}.{signature_part}",
        issued_at=issued_at,
        expires_at=payload["exp"],
    )


def verify_binding_token(
    token: str | None,
    secret: str | bytes,
    *,
    now: int | None = None,
) -> str | None:
    """Return the binding id from a valid cookie token, otherwise None."""
    if not isinstance(token, str) or not token:
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
    except (ValueError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
        return None

    return _parse_payload(payload, now=_current_time(now))


def create_binding_id() -> str:
    """Create the opaque id embedded in both the browser binding and OAuth state."""
    return secrets.token_urlsafe(24)


def is_valid_binding_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 24 <= len(value) <= 128
        and all(character in _BINDING_ID_ALPHABET for character in value)
    )


def require_matching_binding(actual: str | None, expected: str | None) -> str:
    """Fail closed unless both binding ids are present and equal."""
    if not is_valid_binding_id(actual) or not is_valid_binding_id(expected):
        raise ValueError("invalid_browser_binding")
    if not hmac.compare_digest(actual, expected):
        raise ValueError("invalid_browser_binding")
    return actual


def build_binding_cookie(token: str) -> str:
    if not token:
        raise ValueError("token must be non-empty")
    return (
        f"{CONSENT_BINDING_COOKIE_NAME}={token}; "
        f"Max-Age={CONSENT_BINDING_MAX_AGE_SECONDS}; Path=/; "
        "SameSite=Lax; Secure; HttpOnly"
    )


def build_clear_binding_cookie() -> str:
    return (
        f"{CONSENT_BINDING_COOKIE_NAME}=; Max-Age=0; Path=/; "
        "SameSite=Lax; Secure; HttpOnly"
    )


def _parse_payload(payload: Any, *, now: int) -> str | None:
    if not isinstance(payload, dict):
        return None
    if set(payload) != {"v", "bid", "iat", "exp"}:
        return None
    if type(payload["v"]) is not int or payload["v"] != CONSENT_BINDING_VERSION:
        return None

    binding_id = payload["bid"]
    issued_at = payload["iat"]
    expires_at = payload["exp"]
    if not is_valid_binding_id(binding_id):
        return None
    if isinstance(issued_at, bool) or not isinstance(issued_at, int):
        return None
    if isinstance(expires_at, bool) or not isinstance(expires_at, int):
        return None
    if issued_at > now or expires_at <= issued_at or expires_at <= now:
        return None
    return binding_id


def _require_binding_id(value: str) -> None:
    if not is_valid_binding_id(value):
        raise ValueError("binding_id must be a non-empty opaque string")


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


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))
