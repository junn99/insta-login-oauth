import base64
import hashlib
import hmac
import json

import pytest

from src.session import (
    COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    SessionPayload,
    build_clear_cookie,
    build_clear_cookie_header,
    build_session_cookie,
    build_set_cookie_header,
    create_session_token,
    verify_session_token,
)

SECRET = "s" * 32
OTHER_SECRET = "o" * 32
NOW = 1_800_000_000


def _decode_payload(token: str) -> dict:
    payload_part = token.split(".", 1)[0]
    padding = "=" * (-len(payload_part) % 4)
    payload_bytes = base64.urlsafe_b64decode((payload_part + padding).encode("ascii"))
    return json.loads(payload_bytes)


def test_create_and_verify_session_token():
    token = create_session_token(123, SECRET, now=NOW)

    session = verify_session_token(token, SECRET, now=NOW + 10)

    assert session == SessionPayload(
        user_id=123,
        issued_at=NOW,
        expires_at=NOW + SESSION_MAX_AGE_SECONDS,
    )
    assert _decode_payload(token) == {
        "v": 1,
        "user_id": 123,
        "iat": NOW,
        "exp": NOW + SESSION_MAX_AGE_SECONDS,
    }


def test_token_uses_base64url_json_and_hmac_signature():
    token = create_session_token(1, SECRET, now=NOW)

    payload_part, signature_part = token.split(".")

    assert "=" not in payload_part
    assert "=" not in signature_part
    assert verify_session_token(token, OTHER_SECRET, now=NOW) is None


def test_tampered_payload_is_rejected():
    token = create_session_token(123, SECRET, now=NOW)
    payload_part, signature_part = token.split(".")
    replacement = "A" if payload_part[0] != "A" else "B"
    tampered = f"{replacement}{payload_part[1:]}.{signature_part}"

    assert verify_session_token(tampered, SECRET, now=NOW + 1) is None


def test_tampered_signature_is_rejected():
    token = create_session_token(123, SECRET, now=NOW)
    payload_part, signature_part = token.split(".")
    replacement = "A" if signature_part[-1] != "A" else "B"
    tampered = f"{payload_part}.{signature_part[:-1]}{replacement}"

    assert verify_session_token(tampered, SECRET, now=NOW + 1) is None


@pytest.mark.parametrize(
    "token",
    [
        "",
        "missing-signature",
        "too.many.parts",
        ".signature",
        "payload.",
        "!!!!.!!!!",
    ],
)
def test_malformed_tokens_are_rejected(token):
    assert verify_session_token(token, SECRET, now=NOW) is None


def test_expired_token_is_rejected():
    token = create_session_token(123, SECRET, now=NOW, max_age_seconds=60)

    assert verify_session_token(token, SECRET, now=NOW + 59).user_id == 123
    assert verify_session_token(token, SECRET, now=NOW + 60) is None


def test_future_issued_token_is_rejected():
    token = create_session_token(123, SECRET, now=NOW + 60)

    assert verify_session_token(token, SECRET, now=NOW) is None


@pytest.mark.parametrize("user_id", [0, -1, True, False, "123"])
def test_create_rejects_invalid_user_ids(user_id):
    with pytest.raises(ValueError):
        create_session_token(user_id, SECRET, now=NOW)


def test_verify_rejects_bool_user_id_payload():
    token = create_session_token(1, SECRET, now=NOW)
    payload = _decode_payload(token)
    payload["user_id"] = True
    forged_payload_part = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    signature = base64.urlsafe_b64encode(
        hmac.new(
            SECRET.encode("utf-8"),
            forged_payload_part.encode("ascii"),
            hashlib.sha256,
        ).digest()
    ).rstrip(b"=").decode("ascii")

    assert verify_session_token(f"{forged_payload_part}.{signature}", SECRET, now=NOW) is None


def test_secret_must_be_separate_and_strong():
    with pytest.raises(ValueError):
        create_session_token(1, "short", now=NOW)

    assert verify_session_token("bad.token", "short", now=NOW) is None


def test_set_cookie_header_has_secure_attributes():
    token = create_session_token(123, SECRET, now=NOW)

    header = build_set_cookie_header(token)

    assert header == (
        f"{COOKIE_NAME}={token}; Max-Age=604800; Path=/; "
        "SameSite=Lax; Secure; HttpOnly"
    )
    assert SECRET not in header
    assert build_session_cookie(token) == header


def test_clear_cookie_header_has_secure_attributes():
    assert build_clear_cookie_header() == (
        f"{COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax; Secure; HttpOnly"
    )
    assert build_clear_cookie() == build_clear_cookie_header()
