"""Shared Instagram OAuth start handling for ASGI and Vercel API routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib.parse import parse_qsl, urlsplit

from . import oauth as oauth_module
from .config import config
from .consent import ConsentAcceptance
from .consent_binding import build_binding_cookie, create_binding_token

LOGIN_PATH = "/Login"
MAX_FORM_BODY_BYTES = 2048
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
REQUIRED_CONSENT_FIELDS = frozenset(
    {
        "age_confirmed",
        "terms_accepted",
        "privacy_accepted",
        "instagram_permissions_accepted",
    }
)


@dataclass(frozen=True)
class OAuthStartResponse:
    status_code: int
    headers: tuple[tuple[str, str], ...]
    body: bytes = b""


def handle_instagram_start(
    *,
    method: str,
    headers: Mapping[str, str],
    body: bytes,
    scheme: str = "https",
) -> OAuthStartResponse:
    """Validate the static consent POST and redirect to Instagram OAuth."""
    normalized_headers = _normalize_headers(headers)
    if method.upper() != "POST":
        return OAuthStartResponse(
            405,
            (
                ("allow", "POST"),
                ("content-type", "text/plain; charset=utf-8"),
            ),
            b"Method Not Allowed",
        )

    if not _has_form_content_type(normalized_headers.get("content-type", "")):
        return _login_error("invalid_request")
    if not _same_origin_request(normalized_headers, scheme=scheme):
        return _login_error("invalid_request")
    if len(body) > MAX_FORM_BODY_BYTES:
        return _login_error("invalid_request")
    if not _valid_consent_form(body):
        return _login_error("invalid_request")

    if config.validate_runtime():
        return _login_error("configuration_error")

    try:
        binding = create_binding_token(config.SESSION_COOKIE_SECRET)
        oauth_url = oauth_module.get_oauth_url(
            consent=ConsentAcceptance.accepted_now(),
            binding_id=binding.binding_id,
        )
    except (TypeError, ValueError):
        return _login_error("configuration_error")

    return _redirect(oauth_url, ("set-cookie", build_binding_cookie(binding.token)))


def _redirect(
    location: str,
    *extra_headers: tuple[str, str],
) -> OAuthStartResponse:
    return OAuthStartResponse(
        303,
        (
            ("location", location),
            ("cache-control", "no-store"),
            ("referrer-policy", "no-referrer"),
            *extra_headers,
        ),
    )


def _login_error(code: str) -> OAuthStartResponse:
    return _redirect(f"{LOGIN_PATH}?step=consent&auth_error={code}")


def _normalize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _has_form_content_type(content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == FORM_CONTENT_TYPE


def _same_origin_request(headers: Mapping[str, str], *, scheme: str) -> bool:
    host = headers.get("host", "")
    if not host:
        return False

    expected_origin = f"{scheme}://{host}"
    sec_fetch_site = headers.get("sec-fetch-site", "")
    if sec_fetch_site == "cross-site":
        return False

    origin = headers.get("origin", "")
    if origin:
        return origin == expected_origin

    referer = headers.get("referer", "")
    return _url_origin(referer) == expected_origin


def _url_origin(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _valid_consent_form(body: bytes) -> bool:
    try:
        form_pairs = parse_qsl(
            body.decode("ascii"),
            keep_blank_values=True,
            strict_parsing=True,
        )
    except (UnicodeDecodeError, ValueError):
        return False

    if len(form_pairs) != len(REQUIRED_CONSENT_FIELDS):
        return False

    seen: set[str] = set()
    for key, value in form_pairs:
        if key in seen or key not in REQUIRED_CONSENT_FIELDS or value != "true":
            return False
        seen.add(key)
    return seen == REQUIRED_CONSENT_FIELDS
