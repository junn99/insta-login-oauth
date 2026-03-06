"""Instagram Login OAuth flow for Instagram Business API."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import requests

from .config import config
from .models import InstagramAccount


_STATE_TTL_SECONDS = 600
_STATE_FUTURE_SKEW_SECONDS = 60


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_state_payload(payload_bytes: bytes) -> bytes:
    secret = config.INSTAGRAM_APP_SECRET.encode("utf-8")
    return hmac.new(secret, payload_bytes, hashlib.sha256).digest()


def generate_state() -> str:
    """Generate a signed stateless CSRF state token."""
    payload = {
        "iat": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = _sign_state_payload(payload_bytes)
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def validate_state(state: str) -> bool:
    """Validate a signed stateless CSRF state token."""
    try:
        if not state or "." not in state:
            return False

        payload_part, signature_part = state.split(".", 1)
        payload_bytes = _b64url_decode(payload_part)
        received_signature = _b64url_decode(signature_part)
        expected_signature = _sign_state_payload(payload_bytes)

        if not hmac.compare_digest(received_signature, expected_signature):
            return False

        payload = json.loads(payload_bytes.decode("utf-8"))
        iat = payload.get("iat")
        if not isinstance(iat, int):
            return False

        now = int(time.time())
        if now - iat > _STATE_TTL_SECONDS:
            return False
        if iat - now > _STATE_FUTURE_SKEW_SECONDS:
            return False

        return True
    except Exception:
        return False


def get_oauth_url(state: Optional[str] = None) -> str:
    """Generate Instagram OAuth authorization URL."""
    if state is None:
        state = generate_state()

    params = {
        "client_id": config.INSTAGRAM_APP_ID,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "state": state,
        "scope": "instagram_business_basic,instagram_business_manage_insights",
        "response_type": "code",
    }
    return f"{config.INSTAGRAM_OAUTH_URL}/oauth/authorize?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for short-lived access token."""
    url = f"{config.INSTAGRAM_OAUTH_URL}/oauth/access_token"
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
    data["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

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
    data["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

    return data


def complete_oauth_flow(code: str) -> dict:
    """Complete the full OAuth flow and return all necessary data."""
    # Step 1: Exchange code for short-lived token + user_id
    token_data = exchange_code_for_token(code)
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
    info = response.json()

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
