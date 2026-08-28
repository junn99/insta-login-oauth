import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from src.consent_binding import CONSENT_BINDING_COOKIE_NAME
from src.oauth_start_service import MAX_FORM_BODY_BYTES, handle_instagram_start

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRET = "s" * 32
VALID_FORM = (
    b"age_confirmed=true&terms_accepted=true&privacy_accepted=true&"
    b"instagram_permissions_accepted=true"
)
VALID_HEADERS = {
    "host": "preview.example",
    "origin": "https://preview.example",
    "sec-fetch-site": "same-origin",
    "content-type": "application/x-www-form-urlencoded",
}


def _patch_runtime(monkeypatch, service, *, oauth_url: str | None = None):
    monkeypatch.setattr(service.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(service.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        service.oauth_module,
        "get_oauth_url",
        lambda *, consent, binding_id: oauth_url
        or (
            "https://www.instagram.com/oauth/authorize?"
            f"client_id=app-id&state=signed-state-for-{binding_id}"
        ),
    )


def test_vercel_oauth_start_uses_node_function_not_python_streamlit():
    assert not (PROJECT_ROOT / "api" / "instagram_start.py").exists()

    result = subprocess.run(
        [
            "node",
            "-e",
            "require('./api/instagram_start.js'); process.stdout.write('ok');",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout == "ok"


def test_canonical_post_mints_binding_cookie_and_redirects(monkeypatch):
    import src.oauth_start_service as service

    _patch_runtime(monkeypatch, service)

    response = handle_instagram_start(
        method="POST",
        headers=VALID_HEADERS,
        body=VALID_FORM,
    )

    assert response.status_code == 303
    headers = dict(response.headers)
    parsed = urlparse(headers["location"])
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://www.instagram.com/oauth/authorize"
    )
    assert parse_qs(parsed.query)["client_id"] == ["app-id"]
    assert headers["cache-control"] == "no-store"
    assert headers["referrer-policy"] == "no-referrer"
    cookie = headers["set-cookie"]
    assert cookie.startswith(f"{CONSENT_BINDING_COOKIE_NAME}=")
    assert "Max-Age=600" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" in cookie
    assert "HttpOnly" in cookie


@pytest.mark.parametrize(
    "body",
    [
        b"age_confirmed=true&terms_accepted=true&privacy_accepted=true",
        b"age_confirmed=true&terms_accepted=true&privacy_accepted=true&"
        b"instagram_permissions_accepted=false",
        b"age_confirmed=true&terms_accepted=true&privacy_accepted=true&"
        b"instagram_permissions_accepted=true&age_confirmed=true",
        b"age_confirmed=true&terms_accepted=true&privacy_accepted=true&"
        b"instagram_permissions_accepted=true&csrf_token=secret",
        b"age_confirmed=True&terms_accepted=true&privacy_accepted=true&"
        b"instagram_permissions_accepted=true",
        b"age_confirmed&terms_accepted=true&privacy_accepted=true&"
        b"instagram_permissions_accepted=true",
    ],
)
def test_invalid_forms_redirect_without_cookie(monkeypatch, body):
    import src.oauth_start_service as service

    _patch_runtime(monkeypatch, service)

    response = handle_instagram_start(
        method="POST",
        headers=VALID_HEADERS,
        body=body,
    )

    assert response.status_code == 303
    headers = dict(response.headers)
    assert headers["location"] == "/Login?step=consent&auth_error=invalid_request"
    assert "set-cookie" not in headers


@pytest.mark.parametrize(
    ("headers", "expected_location"),
    [
        (
            {
                **VALID_HEADERS,
                "origin": "https://evil.example",
                "referer": "https://preview.example/Login",
            },
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            {
                **VALID_HEADERS,
                "sec-fetch-site": "cross-site",
            },
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            {
                key: value
                for key, value in VALID_HEADERS.items()
                if key not in {"origin"}
            }
            | {"referer": "https://preview.example/Login?step=consent"},
            "https://www.instagram.com/oauth/authorize",
        ),
    ],
)
def test_origin_fetch_site_and_referer_rules(monkeypatch, headers, expected_location):
    import src.oauth_start_service as service

    _patch_runtime(monkeypatch, service)

    response = handle_instagram_start(
        method="POST",
        headers=headers,
        body=VALID_FORM,
    )

    location = dict(response.headers)["location"]
    assert location.startswith(expected_location)


@pytest.mark.parametrize(
    ("method", "headers", "body", "expected_status", "expected_location"),
    [
        ("GET", VALID_HEADERS, b"", 405, None),
        (
            "POST",
            {**VALID_HEADERS, "content-type": "multipart/form-data"},
            VALID_FORM,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            VALID_HEADERS,
            b"a" * (MAX_FORM_BODY_BYTES + 1),
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
    ],
)
def test_method_content_type_and_body_size_are_bounded(
    monkeypatch,
    method,
    headers,
    body,
    expected_status,
    expected_location,
):
    import src.oauth_start_service as service

    _patch_runtime(monkeypatch, service)

    response = handle_instagram_start(method=method, headers=headers, body=body)

    assert response.status_code == expected_status
    response_headers = dict(response.headers)
    assert "set-cookie" not in response_headers
    if expected_location is None:
        assert response.body == b"Method Not Allowed"
    else:
        assert response_headers["location"] == expected_location


def test_valid_request_reports_configuration_error_without_cookie(monkeypatch):
    import src.oauth_start_service as service

    monkeypatch.setattr(service.config, "validate_runtime", lambda: ["SUPABASE_URL"])

    response = handle_instagram_start(
        method="POST",
        headers=VALID_HEADERS,
        body=VALID_FORM,
    )

    headers = dict(response.headers)
    assert response.status_code == 303
    assert headers["location"] == "/Login?step=consent&auth_error=configuration_error"
    assert "set-cookie" not in headers
