import json
import os
import subprocess
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from src.consent_binding import CONSENT_BINDING_COOKIE_NAME, verify_binding_token
from src.oauth import parse_state


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRET = "s" * 32
VALID_FORM = (
    "age_confirmed=true&terms_accepted=true&privacy_accepted=true&"
    "instagram_permissions_accepted=true"
)


def _node_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "INSTAGRAM_APP_ID": "app-id",
            "INSTAGRAM_APP_SECRET": SECRET,
            "OAUTH_REDIRECT_URI": "https://preview.example/auth/callback",
            "CONTACT_EMAIL": "contact@example.com",
            "SESSION_COOKIE_SECRET": SECRET,
            "SUPABASE_URL": "https://previewref.supabase.co",
            "SUPABASE_KEY": "sb_secret_test",
            "VERCEL": "1",
            "VERCEL_ENV": "preview",
            "ALLOW_SHARED_SUPABASE_IN_PREVIEW": "1",
        }
    )
    if extra:
        env.update(extra)
    return env


def _invoke_node(
    *,
    method: str = "POST",
    body: str | dict = VALID_FORM,
    headers: dict[str, str] | None = None,
    raw_headers: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    script = """
const {Readable} = require('stream');
const handler = require('./api/instagram_start.js');
const payload = JSON.parse(process.argv[1]);
const chunks = typeof payload.body === 'string'
  ? [Buffer.from(payload.body || '', 'utf8')]
  : [];
const req = Readable.from(chunks);
req.method = payload.method;
req.headers = payload.headers;
req.rawHeaders = payload.rawHeaders;
if (payload.parsedBody) req.body = payload.parsedBody;
const out = {headers: {}};
const res = {
  setHeader(key, value) { out.headers[String(key).toLowerCase()] = value; },
  end(body) {
    out.statusCode = this.statusCode;
    out.body = body ? String(body) : '';
    process.stdout.write(JSON.stringify(out));
  },
};
handler(req, res);
"""
    request_headers = headers or {
        "host": "preview.example",
        "origin": "https://preview.example",
        "sec-fetch-site": "same-origin",
        "content-type": "application/x-www-form-urlencoded",
        "content-length": str(
            len((body if isinstance(body, str) else VALID_FORM).encode("utf-8"))
        ),
    }
    completed = subprocess.run(
        [
            "node",
            "-e",
            script,
            json.dumps(
                {
                    "method": method,
                    "body": body if isinstance(body, str) else "",
                    "parsedBody": body if isinstance(body, dict) else None,
                    "headers": request_headers,
                    "rawHeaders": raw_headers
                    or [item for pair in request_headers.items() for item in pair],
                }
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env or _node_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_node_function_import_does_not_load_python_or_streamlit():
    completed = subprocess.run(
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

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "ok"


def test_node_oauth_start_state_and_cookie_validate_in_python(monkeypatch):
    monkeypatch.setattr("src.oauth.config.INSTAGRAM_APP_SECRET", SECRET, raising=False)

    result = _invoke_node()

    assert result["statusCode"] == 303
    headers = result["headers"]
    assert headers["cache-control"] == "no-store"
    assert headers["referrer-policy"] == "no-referrer"

    cookie = SimpleCookie()
    cookie.load(headers["set-cookie"])
    binding_token = cookie[CONSENT_BINDING_COOKIE_NAME].value
    binding_id = verify_binding_token(binding_token, SECRET)
    assert binding_id

    parsed_location = urlparse(headers["location"])
    assert (
        f"{parsed_location.scheme}://{parsed_location.netloc}{parsed_location.path}"
        == "https://www.instagram.com/oauth/authorize"
    )
    params = parse_qs(parsed_location.query)
    assert params["client_id"] == ["app-id"]
    assert params["redirect_uri"] == ["https://preview.example/auth/callback"]
    assert params["scope"] == [
        "instagram_business_basic,instagram_business_manage_insights"
    ]
    assert params["response_type"] == ["code"]

    parsed_state = parse_state(params["state"][0], expected_binding_id=binding_id)
    assert parsed_state.age_confirmed is True
    assert parsed_state.terms_accepted is True
    assert parsed_state.privacy_accepted is True
    assert parsed_state.instagram_permissions_accepted is True
    assert parsed_state.terms_version == "influencer-v1.2-2026-08-26"
    assert parsed_state.privacy_version == "privacy-2026-08-26-v3"
    assert (
        parsed_state.instagram_permissions_version
        == "instagram-permissions-2026-08-26"
    )


def test_node_oauth_start_accepts_vercel_parsed_form_body(monkeypatch):
    monkeypatch.setattr("src.oauth.config.INSTAGRAM_APP_SECRET", SECRET, raising=False)

    result = _invoke_node(
        body={
            "age_confirmed": "true",
            "terms_accepted": "true",
            "privacy_accepted": "true",
            "instagram_permissions_accepted": "true",
        }
    )

    assert result["statusCode"] == 303
    assert result["headers"]["location"].startswith(
        "https://www.instagram.com/oauth/authorize?"
    )
    assert "set-cookie" in result["headers"]


@pytest.mark.parametrize(
    ("method", "body", "headers", "raw_headers", "expected_status", "expected_location"),
    [
        ("GET", "", {}, [], 405, None),
        (
            "POST",
            VALID_FORM,
            {
                "host": "preview.example",
                "origin": "https://evil.example",
                "sec-fetch-site": "same-origin",
                "content-type": "application/x-www-form-urlencoded",
            },
            None,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            VALID_FORM,
            {
                "host": "preview.example",
                "origin": "https://preview.example",
                "sec-fetch-site": "same-origin",
                "content-type": "multipart/form-data",
            },
            None,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            VALID_FORM + "&age_confirmed=true",
            {
                "host": "preview.example",
                "origin": "https://preview.example",
                "sec-fetch-site": "same-origin",
                "content-type": "application/x-www-form-urlencoded",
            },
            None,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            "age_confirmed=%E0%A4%A&terms_accepted=true&privacy_accepted=true&"
            "instagram_permissions_accepted=true",
            {
                "host": "preview.example",
                "origin": "https://preview.example",
                "sec-fetch-site": "same-origin",
                "content-type": "application/x-www-form-urlencoded",
            },
            None,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            VALID_FORM,
            {
                "host": "preview.example",
                "sec-fetch-site": "same-origin",
                "content-type": "application/x-www-form-urlencoded",
            },
            None,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            "a" * 2049,
            {
                "host": "preview.example",
                "origin": "https://preview.example",
                "sec-fetch-site": "same-origin",
                "content-type": "application/x-www-form-urlencoded",
                "content-length": "2049",
            },
            None,
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
        (
            "POST",
            VALID_FORM,
            {
                "host": "preview.example",
                "origin": "https://preview.example",
                "sec-fetch-site": "same-origin",
                "content-type": "application/x-www-form-urlencoded",
                "content-length": "12",
            },
            [
                "host",
                "preview.example",
                "content-length",
                "12",
                "content-length",
                "12",
            ],
            303,
            "/Login?step=consent&auth_error=invalid_request",
        ),
    ],
)
def test_node_oauth_start_rejects_invalid_requests(
    method,
    body,
    headers,
    raw_headers,
    expected_status,
    expected_location,
):
    if method == "POST" and "content-length" not in headers:
        headers = {**headers, "content-length": str(len(body.encode("utf-8")))}

    result = _invoke_node(
        method=method,
        body=body,
        headers=headers,
        raw_headers=raw_headers,
    )

    assert result["statusCode"] == expected_status
    response_headers = result["headers"]
    assert "set-cookie" not in response_headers
    if expected_location is None:
        assert result["body"] == "Method Not Allowed"
    else:
        assert response_headers["location"] == expected_location


def test_node_oauth_start_configuration_error_mints_no_cookie():
    result = _invoke_node(env=_node_env({"INSTAGRAM_APP_SECRET": ""}))

    assert result["statusCode"] == 303
    assert result["headers"]["location"] == (
        "/Login?step=consent&auth_error=configuration_error"
    )
    assert "set-cookie" not in result["headers"]
