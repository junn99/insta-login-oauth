"""Instagram Login OAuth flow for Instagram Business API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import requests

from .consent import (
    CONSENT_STATE_KEYS,
    ConsentAcceptance,
    consent_bundle_hash,
    consent_payload,
)
from .config import config
from .consent_binding import is_valid_binding_id, require_matching_binding
from .models import InstagramAccount


_STATE_TTL_SECONDS = 600
_STATE_FUTURE_SKEW_SECONDS = 60
_STATE_VERSION = 1


class StateError(ValueError):
    """Base class for browser-safe OAuth state validation failures."""

    code = "invalid_state"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)


class InvalidStateError(StateError):
    """State is malformed, unsigned, tampered with, or missing consent."""


class ExpiredStateError(StateError):
    """State signature is valid but the timestamp is outside the TTL."""

    code = "expired_state"


class StateValidationError(InvalidStateError):
    """Backward-compatible state validation error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ParsedConsentState:
    version: int
    issued_at: int
    nonce: str
    binding_id: str
    consent: ConsentAcceptance
    bundle_hash: str
    raw_payload: dict[str, Any]

    @property
    def accepted_at(self) -> datetime:
        return self.consent.accepted_at

    @property
    def consent_schema_version(self) -> int:
        return self.consent.consent_schema_version

    @property
    def terms_version(self) -> str:
        return self.consent.terms_version

    @property
    def privacy_version(self) -> str:
        return self.consent.privacy_version

    @property
    def instagram_permissions_version(self) -> str:
        return self.consent.instagram_permissions_version

    @property
    def age_confirmed(self) -> bool:
        return self.consent.age_confirmed

    @property
    def terms_accepted(self) -> bool:
        return self.consent.terms_accepted

    @property
    def privacy_accepted(self) -> bool:
        return self.consent.privacy_accepted

    @property
    def consent_age(self) -> bool:
        return self.consent.age_confirmed

    @property
    def consent_terms(self) -> bool:
        return self.consent.terms_accepted

    @property
    def consent_privacy(self) -> bool:
        return self.consent.privacy_accepted

    @property
    def instagram_permissions_accepted(self) -> bool:
        return self.consent.instagram_permissions_accepted

    @property
    def consent_instagram(self) -> bool:
        return self.consent.instagram_permissions_accepted


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_state_payload(payload_bytes: bytes) -> bytes:
    secret = config.INSTAGRAM_APP_SECRET.encode("utf-8")
    return hmac.new(secret, payload_bytes, hashlib.sha256).digest()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def generate_state(
    consent: ConsentAcceptance | dict[str, Any] | None = None,
    *,
    binding_id: str | None = None,
) -> str:
    """Generate a signed consent handoff state token."""
    if not config.INSTAGRAM_APP_SECRET:
        raise ValueError("INSTAGRAM_APP_SECRET is required to sign OAuth state")
    if consent is None:
        raise ValueError("explicit consent is required to sign OAuth state")
    if not is_valid_binding_id(binding_id):
        raise ValueError("binding_id is required to sign OAuth state")

    now = int(time.time())
    payload = {
        "v": _STATE_VERSION,
        "iat": now,
        "nonce": secrets.token_urlsafe(16),
        "binding_id": binding_id,
    }
    payload.update(consent_payload(consent))
    payload["bundle_hash"] = consent_bundle_hash(payload)
    payload_bytes = _json_bytes(payload)
    signature = _sign_state_payload(payload_bytes)
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def _parse_state_or_raise(
    state: str,
    *,
    expected_binding_id: str | None,
) -> ParsedConsentState:
    """Validate and parse a signed consent handoff state token."""
    try:
        if not state or "." not in state:
            raise InvalidStateError("missing state")

        payload_part, signature_part = state.split(".", 1)
        payload_bytes = _b64url_decode(payload_part)
        received_signature = _b64url_decode(signature_part)
        expected_signature = _sign_state_payload(payload_bytes)

        if not hmac.compare_digest(received_signature, expected_signature):
            raise InvalidStateError("bad state signature")

        payload = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            raise InvalidStateError("state payload must be an object")
        if set(payload) != CONSENT_STATE_KEYS:
            raise InvalidStateError("state payload has unsupported fields")
        version = payload.get("v")
        if type(version) is not int or version != _STATE_VERSION:
            raise InvalidStateError("unsupported state version")

        iat = payload.get("iat")
        nonce = payload.get("nonce")
        binding_id = payload.get("binding_id")
        accepted_at = payload.get("accepted_at")
        bundle_hash = payload.get("bundle_hash")
        if type(iat) is not int:
            raise InvalidStateError("state iat is required")
        if not isinstance(nonce, str) or not nonce:
            raise InvalidStateError("state nonce is required")
        if not is_valid_binding_id(binding_id):
            raise InvalidStateError("state binding_id is required")
        try:
            require_matching_binding(binding_id, expected_binding_id)
        except ValueError as exc:
            raise InvalidStateError("state browser binding mismatch") from exc
        if not isinstance(accepted_at, str) or not accepted_at:
            raise InvalidStateError("accepted_at is required")
        if (
            not isinstance(bundle_hash, str)
            or len(bundle_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in bundle_hash)
        ):
            raise InvalidStateError("bundle_hash is required")

        now = int(time.time())
        if now - iat > _STATE_TTL_SECONDS:
            raise ExpiredStateError("state expired")
        if iat - now > _STATE_FUTURE_SKEW_SECONDS:
            raise InvalidStateError("state timestamp is in the future")

        try:
            accepted_dt = datetime.fromisoformat(accepted_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidStateError("accepted_at is invalid") from exc
        if accepted_dt.tzinfo is None:
            raise InvalidStateError("accepted_at timezone is required")
        now_dt = datetime.fromtimestamp(now, timezone.utc)
        if (accepted_dt - now_dt).total_seconds() > _STATE_FUTURE_SKEW_SECONDS:
            raise InvalidStateError("accepted_at is in the future")

        expected_hash = consent_bundle_hash(payload)
        if not hmac.compare_digest(expected_hash, bundle_hash):
            raise InvalidStateError("state consent hash mismatch")

        try:
            consent = ConsentAcceptance.from_mapping(payload)
        except ValueError as exc:
            raise InvalidStateError(str(exc)) from exc

        return ParsedConsentState(
            version=version,
            issued_at=iat,
            nonce=nonce,
            binding_id=binding_id,
            consent=consent,
            bundle_hash=bundle_hash,
            raw_payload=payload,
        )
    except StateError:
        raise
    except Exception as exc:
        raise InvalidStateError("invalid state") from exc


def parse_state(
    state: str,
    *,
    expected_binding_id: str | None = None,
) -> ParsedConsentState:
    """Validate and parse a signed consent handoff state token."""
    return _parse_state_or_raise(state, expected_binding_id=expected_binding_id)


def validate_state(
    state: str,
    *,
    expected_binding_id: str | None = None,
) -> bool:
    """Validate a signed consent handoff state token."""
    try:
        parse_state(state, expected_binding_id=expected_binding_id)
        return True
    except StateError:
        return False


def get_oauth_url(
    state: str | None = None,
    consent: ConsentAcceptance | None = None,
    binding_id: str | None = None,
) -> str:
    """Generate Instagram OAuth authorization URL."""
    if state is None:
        if consent is None:
            raise ValueError("explicit consent is required to build OAuth URL")
        state = generate_state(consent, binding_id=binding_id)

    params = {
        "client_id": config.INSTAGRAM_APP_ID,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "state": state,
        "scope": "instagram_business_basic,instagram_business_manage_insights",
        "response_type": "code",
    }
    return f"{config.INSTAGRAM_AUTH_URL}/oauth/authorize?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for short-lived access token."""
    url = f"{config.INSTAGRAM_TOKEN_URL}/oauth/access_token"
    data = {
        "client_id": config.INSTAGRAM_APP_ID,
        "client_secret": config.INSTAGRAM_APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "code": code,
    }

    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()


def get_long_lived_token(short_lived_token: str) -> dict:
    """Exchange short-lived token for long-lived user token (60 days)."""
    url = f"{config.INSTAGRAM_API_BASE_URL}/access_token"
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": config.INSTAGRAM_APP_SECRET,
        "access_token": short_lived_token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Calculate expiration (typically 60 days)
    expires_in = data.get("expires_in", 5184000)  # Default 60 days
    data["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return data


def refresh_long_lived_token(token: str) -> dict:
    """Refresh a long-lived token (extends expiration)."""
    url = f"{config.INSTAGRAM_API_BASE_URL}/refresh_access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    expires_in = data.get("expires_in", 5184000)
    data["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    return data


def _unwrap_data(response: dict) -> dict:
    """Unwrap Instagram API responses that use {"data": [...]} format."""
    if "data" in response and isinstance(response["data"], list) and response["data"]:
        return response["data"][0]
    return response


def complete_oauth_flow(code: str) -> dict:
    """Complete the full OAuth flow and return all necessary data."""
    # Step 1: Exchange code for short-lived token + user_id
    token_response = exchange_code_for_token(code)
    token_data = _unwrap_data(token_response)
    short_token = token_data["access_token"]
    user_id = str(token_data["user_id"])

    # Step 2: Short-lived → long-lived token
    long_token_data = get_long_lived_token(short_token)
    user_token = long_token_data["access_token"]
    user_token_expires = long_token_data["expires_at"]

    # Step 3: Fetch account info
    info_url = f"{config.INSTAGRAM_API_BASE_URL}/me"
    params = {
        "fields": "user_id,username,name,profile_picture_url,followers_count,media_count",
        "access_token": user_token,
    }
    response = requests.get(info_url, params=params)
    response.raise_for_status()
    info = _unwrap_data(response.json())

    ig_account = InstagramAccount(
        id=user_id,
        username=info.get("username", ""),
        name=info.get("name"),
        profile_picture_url=info.get("profile_picture_url"),
        followers_count=info.get("followers_count"),
        media_count=info.get("media_count"),
    )

    return {
        "success": True,
        "user_token": user_token,
        "user_token_expires": user_token_expires,
        "instagram_account": ig_account,
    }
