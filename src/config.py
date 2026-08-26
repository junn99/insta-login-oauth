"""Configuration management for urlinsta."""

import base64
import binascii
import json
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _supabase_key_kind(key: str) -> str:
    """Classify a Supabase server key without validating or logging it."""
    if key.startswith("sb_secret_"):
        return "secret"
    if key.startswith("sb_publishable_"):
        return "publishable"

    parts = key.split(".")
    if len(parts) != 3:
        return "unknown"

    try:
        payload_part = parts[1]
        padding = "=" * (-len(payload_part) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(payload_part + padding).decode("utf-8")
        )
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return "unknown"

    role = payload.get("role")
    return role if isinstance(role, str) else "unknown"


def _vercel_oauth_redirect_error(uri: str) -> str | None:
    """Return a Vercel-only redirect URI error label, or None when valid."""
    try:
        parsed = urlsplit(uri)
    except ValueError:
        return "OAUTH_REDIRECT_URI (Vercel must be https://<host>/auth/callback)"

    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path != "/auth/callback"
        or parsed.query
        or parsed.fragment
    ):
        return "OAUTH_REDIRECT_URI (Vercel must be https://<host>/auth/callback)"

    return None


class Config:
    """Application configuration from environment variables."""

    INSTAGRAM_APP_ID: str = os.getenv("INSTAGRAM_APP_ID", "")
    INSTAGRAM_APP_SECRET: str = os.getenv("INSTAGRAM_APP_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.getenv("OAUTH_REDIRECT_URI", "")
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "")
    SESSION_COOKIE_SECRET: str = os.getenv("SESSION_COOKIE_SECRET", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Deployment runtime
    IS_VERCEL: bool = _env_flag("VERCEL")
    VERCEL_ENV: str = os.getenv("VERCEL_ENV", "")
    PREVIEW_SAFE_MODE: bool = _env_flag("PREVIEW_SAFE_MODE")

    # Instagram API
    INSTAGRAM_API_BASE_URL: str = "https://graph.instagram.com/v22.0"
    INSTAGRAM_AUTH_URL: str = "https://www.instagram.com"       # authorize redirect
    INSTAGRAM_TOKEN_URL: str = "https://api.instagram.com"      # token exchange POST

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 180  # Conservative limit (Instagram allows 200/hour)
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour in seconds

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing keys."""
        required = [
            "INSTAGRAM_APP_ID",
            "INSTAGRAM_APP_SECRET",
            "OAUTH_REDIRECT_URI",
            "CONTACT_EMAIL",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]
        missing = [key for key in required if not getattr(cls, key)]
        return missing

    @classmethod
    def preview_safe_mode(cls) -> bool:
        """Return the fail-safe write policy for a Vercel Preview deployment."""
        return cls.VERCEL_ENV.lower() == "preview" or cls.PREVIEW_SAFE_MODE

    def is_vercel_preview(self) -> bool:
        """Return true only for an actual Vercel Preview runtime."""
        return self.IS_VERCEL and self.VERCEL_ENV.lower() == "preview"

    @classmethod
    def scheduler_allowed(cls) -> bool:
        """The in-process scheduler must never run inside a Vercel Function."""
        return not cls.IS_VERCEL

    @classmethod
    def validate_runtime(cls) -> list[str]:
        """Validate the base app plus Vercel-only security requirements."""
        errors = cls.validate()
        if not cls.IS_VERCEL:
            return errors

        if len(cls.SESSION_COOKIE_SECRET.encode("utf-8")) < 32:
            errors.append("SESSION_COOKIE_SECRET (minimum 32 bytes)")

        redirect_error = _vercel_oauth_redirect_error(cls.OAUTH_REDIRECT_URI)
        if redirect_error:
            errors.append(redirect_error)

        key_kind = _supabase_key_kind(cls.SUPABASE_KEY)
        if key_kind not in {"secret", "service_role"}:
            errors.append("SUPABASE_KEY (secret/service_role required)")

        return errors


config = Config()
