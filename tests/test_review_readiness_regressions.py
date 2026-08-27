import base64
import json
from datetime import datetime, timedelta, timezone
from importlib import import_module, reload
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from requests import HTTPError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVACY_PAGE = PROJECT_ROOT / "pages" / "4_🔒_Privacy.py"
DELETION_PAGE = PROJECT_ROOT / "pages" / "5_🗑️_Data-Deletion.py"
APP_PAGE = PROJECT_ROOT / "app.py"
MIGRATION = PROJECT_ROOT / "migrations" / "002_add_consent_onboarding_transaction.sql"
SCHEMA = PROJECT_ROOT / "supabase_schema.sql"
BINDING_ID = "browser-binding-id-1234567890"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _reload_oauth_with_env(monkeypatch):
    monkeypatch.setenv("INSTAGRAM_APP_ID", "test-app-id")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://example.com/oauth/callback")
    monkeypatch.setenv("CONTACT_EMAIL", "reviewer@example.com")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-supabase-key")

    config_module = import_module("src.config")
    oauth_module = import_module("src.oauth")
    reload(config_module)
    oauth_module = reload(oauth_module)
    return oauth_module, config_module.config


class _MockResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.text = str(self._data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}")


def _accepted_consent_payload() -> dict:
    from src.consent import (
        INSTAGRAM_PERMISSIONS_VERSION,
        PRIVACY_VERSION,
        TERMS_VERSION,
    )

    return {
        "accepted_at": "2026-08-26T03:00:00+00:00",
        "age_confirmed": True,
        "terms_accepted": True,
        "privacy_accepted": True,
        "instagram_permissions_accepted": True,
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "instagram_permissions_version": INSTAGRAM_PERMISSIONS_VERSION,
    }


def _state_with_payload(oauth_module, payload: dict) -> str:
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = oauth_module._sign_state_payload(payload_bytes)
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_payload}.{encoded_signature}"


def test_contact_email_placeholders():
    privacy = _read_text(PRIVACY_PAGE)
    deletion = _read_text(DELETION_PAGE)

    assert "[CONTACT_EMAIL]" not in privacy
    assert "[CONTACT_EMAIL]" not in deletion


def test_privacy_no_encryption_overclaim():
    privacy = _read_text(PRIVACY_PAGE)

    assert "암호화 저장" not in privacy
    assert "stored encrypted" not in privacy.lower()


def test_consent_versions_are_production_neutral():
    from src.consent import (
        INSTAGRAM_PERMISSIONS_VERSION,
        PRIVACY_VERSION,
        TERMS_VERSION,
    )

    assert TERMS_VERSION == "influencer-v1.2-2026-08-26"
    assert PRIVACY_VERSION == "privacy-2026-08-26-v3"
    assert INSTAGRAM_PERMISSIONS_VERSION == "instagram-permissions-2026-08-26"


def test_consent_versions_have_no_preview_prefix():
    from src.consent import INSTAGRAM_PERMISSIONS_VERSION, PRIVACY_VERSION

    assert not PRIVACY_VERSION.startswith("preview-")
    assert not INSTAGRAM_PERMISSIONS_VERSION.startswith("preview-")


def test_schema_uses_same_consent_versions_as_python_contract():
    from src.consent import (
        INSTAGRAM_PERMISSIONS_VERSION,
        PRIVACY_VERSION,
        TERMS_VERSION,
    )

    sql = _read_text(SCHEMA)

    assert f"p_terms_version <> '{TERMS_VERSION}'" in sql
    assert f"p_privacy_version <> '{PRIVACY_VERSION}'" in sql
    assert (
        f"p_instagram_permissions_version <> '{INSTAGRAM_PERMISSIONS_VERSION}'"
        in sql
    )


def test_migration_uses_same_consent_versions_as_python_contract():
    from src.consent import (
        INSTAGRAM_PERMISSIONS_VERSION,
        PRIVACY_VERSION,
        TERMS_VERSION,
    )

    sql = _read_text(MIGRATION)

    assert f"p_terms_version <> '{TERMS_VERSION}'" in sql
    assert f"p_privacy_version <> '{PRIVACY_VERSION}'" in sql
    assert (
        f"p_instagram_permissions_version <> '{INSTAGRAM_PERMISSIONS_VERSION}'"
        in sql
    )


def test_privacy_page_renders_canonical_final_privacy_policy():
    privacy = _read_text(PRIVACY_PAGE)

    assert "from src.consent import PRIVACY_POLICY_BODY" in privacy
    assert "PRIVACY_POLICY_BODY" in privacy
    assert "Preview 버전" not in privacy
    assert "Preview 검증용" not in privacy
    assert "정식 배포 전 법률 검토" not in privacy


def test_data_deletion_page_uses_celeblife_identity():
    deletion = _read_text(DELETION_PAGE)

    assert "셀럽라이프" in deletion
    assert "CelebLife" in deletion
    assert "urlinsta" not in deletion


def test_data_deletion_page_includes_final_contact_and_30_day_timeline():
    deletion = _read_text(DELETION_PAGE)

    assert "{config.CONTACT_EMAIL}" in deletion
    assert "30일 이내" in deletion
    assert "within **30 days**" in deletion


def test_vercel_production_copy_is_distinct_from_preview_copy():
    app_source = _read_text(APP_PAGE)

    assert "if config.is_vercel_preview():" in app_source
    assert "elif config.IS_VERCEL:" in app_source
    assert (
        app_source.index("if config.is_vercel_preview():")
        < app_source.index("Preview에서는 자동 수집이 비활성화되어 있습니다.")
        < app_source.index("elif config.IS_VERCEL:")
        < app_source.index("Vercel 배포에서는 자동 수집이 비활성화되어 있습니다.")
    )


def test_oauth_state_signing_and_tamper(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )
    assert oauth_module.validate_state(state, expected_binding_id=BINDING_ID)

    payload_part, signature_part = state.split(".", 1)
    replacement = "A" if payload_part[0] != "A" else "B"
    tampered_payload = replacement + payload_part[1:]
    tampered_state = f"{tampered_payload}.{signature_part}"

    assert not oauth_module.validate_state(tampered_state)


def test_oauth_state_requires_explicit_consent(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    with pytest.raises(ValueError, match="explicit consent"):
        oauth_module.generate_state()

    with pytest.raises(ValueError, match="explicit consent"):
        oauth_module.get_oauth_url()


def test_oauth_state_ttl_expiry(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    base_time = 1_700_000_000
    monkeypatch.setattr(oauth_module.time, "time", lambda: base_time)

    payload = _accepted_consent_payload()
    payload["accepted_at"] = datetime.fromtimestamp(
        base_time,
        timezone.utc,
    ).isoformat()
    state = oauth_module.generate_state(consent=payload, binding_id=BINDING_ID)
    assert oauth_module.validate_state(state, expected_binding_id=BINDING_ID)

    monkeypatch.setattr(
        oauth_module.time,
        "time",
        lambda: base_time + oauth_module._STATE_TTL_SECONDS + 1,
    )
    assert not oauth_module.validate_state(state, expected_binding_id=BINDING_ID)


def test_parse_state_returns_typed_consent_acceptance(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    payload = _accepted_consent_payload()

    state = oauth_module.generate_state(consent=payload, binding_id=BINDING_ID)
    parsed = oauth_module.parse_state(state, expected_binding_id=BINDING_ID)

    assert parsed.nonce
    assert parsed.binding_id == BINDING_ID
    assert parsed.accepted_at == datetime(2026, 8, 26, 3, 0, tzinfo=timezone.utc)
    assert parsed.age_confirmed is True
    assert parsed.terms_accepted is True
    assert parsed.privacy_accepted is True
    assert parsed.instagram_permissions_accepted is True
    assert parsed.terms_version == "influencer-v1.2-2026-08-26"
    assert parsed.privacy_version == "privacy-2026-08-26-v3"
    assert parsed.instagram_permissions_version == "instagram-permissions-2026-08-26"


def test_parse_state_rejects_missing_required_consent(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )
    payload_part, _signature_part = state.split(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding))
    payload["instagram_permissions_accepted"] = False
    payload["bundle_hash"] = oauth_module.consent_bundle_hash(payload)
    state = _state_with_payload(oauth_module, payload)

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(state, expected_binding_id=BINDING_ID)
    assert oauth_module.validate_state(state, expected_binding_id=BINDING_ID) is False


def test_parse_state_rejects_wrong_consent_version(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )
    payload_part, _signature_part = state.split(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding))
    payload["instagram_permissions_version"] = "preview-2026-08-25"
    payload["bundle_hash"] = oauth_module.consent_bundle_hash(payload)
    state = _state_with_payload(oauth_module, payload)

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(state, expected_binding_id=BINDING_ID)
    assert oauth_module.validate_state(state, expected_binding_id=BINDING_ID) is False


def test_parse_state_rejects_future_accepted_at(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    base_time = datetime(2026, 8, 26, 3, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(oauth_module.time, "time", lambda: int(base_time.timestamp()))
    payload = _accepted_consent_payload()
    payload["accepted_at"] = (base_time + timedelta(seconds=61)).isoformat()

    state = oauth_module.generate_state(consent=payload, binding_id=BINDING_ID)

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(state, expected_binding_id=BINDING_ID)
    assert oauth_module.validate_state(state, expected_binding_id=BINDING_ID) is False


def test_parse_state_rejects_tampered_bundle_hash(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )
    payload_part, signature_part = state.split(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding))
    payload["bundle_hash"] = "0" * 64
    tampered_state = _state_with_payload(oauth_module, payload)

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(tampered_state, expected_binding_id=BINDING_ID)
    assert (
        oauth_module.validate_state(tampered_state, expected_binding_id=BINDING_ID)
        is False
    )


def test_parse_state_rejects_extra_or_legacy_consent_fields(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )
    payload_part, _signature_part = state.split(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding))
    payload["permissions_accepted"] = True
    payload["bundle_hash"] = oauth_module.consent_bundle_hash(payload)
    legacy_state = _state_with_payload(oauth_module, payload)

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(legacy_state, expected_binding_id=BINDING_ID)
    assert (
        oauth_module.validate_state(legacy_state, expected_binding_id=BINDING_ID)
        is False
    )


def test_generate_state_ignores_caller_transport_fields(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    payload = _accepted_consent_payload()
    payload.update(
        {
            "v": True,
            "iat": 1,
            "nonce": "caller-controlled",
            "binding_id": "caller-controlled-binding-id",
        }
    )

    state = oauth_module.generate_state(consent=payload, binding_id=BINDING_ID)
    parsed = oauth_module.parse_state(state, expected_binding_id=BINDING_ID)

    assert parsed.version == 1
    assert parsed.issued_at != 1
    assert parsed.nonce != "caller-controlled"
    assert parsed.binding_id == BINDING_ID
    assert parsed.binding_id != "caller-controlled-binding-id"


@pytest.mark.parametrize(("field", "value"), [("v", True), ("iat", True)])
def test_parse_state_rejects_boolean_integer_fields(monkeypatch, field, value):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )
    payload_part, _signature_part = state.split(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding))
    payload[field] = value
    payload["bundle_hash"] = oauth_module.consent_bundle_hash(payload)
    invalid_state = _state_with_payload(oauth_module, payload)

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(invalid_state, expected_binding_id=BINDING_ID)
    assert (
        oauth_module.validate_state(invalid_state, expected_binding_id=BINDING_ID)
        is False
    )


def test_oauth_url_contains_scopes_and_redirect_uri(monkeypatch):
    oauth_module, app_config = _reload_oauth_with_env(monkeypatch)

    oauth_url = oauth_module.get_oauth_url(
        consent=oauth_module.ConsentAcceptance.accepted_now(),
        binding_id=BINDING_ID,
    )
    query = parse_qs(urlparse(oauth_url).query)

    required_scopes = {
        "instagram_business_basic",
        "instagram_business_manage_insights",
    }
    actual_scopes = set(query["scope"][0].split(","))

    assert required_scopes.issubset(actual_scopes)
    assert query["redirect_uri"][0] == app_config.OAUTH_REDIRECT_URI
    assert query["redirect_uri"][0] == "https://example.com/oauth/callback"
    assert oauth_url.startswith("https://www.instagram.com/oauth/authorize")


def test_parse_state_rejects_missing_or_mismatched_browser_binding(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)
    state = oauth_module.generate_state(
        consent=_accepted_consent_payload(),
        binding_id=BINDING_ID,
    )

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(state)
    assert oauth_module.validate_state(state) is False

    with pytest.raises(oauth_module.StateError):
        oauth_module.parse_state(
            state,
            expected_binding_id="different-browser-binding-id-123",
        )
    assert (
        oauth_module.validate_state(
            state,
            expected_binding_id="different-browser-binding-id-123",
        )
        is False
    )


def test_complete_oauth_flow_returns_user_id(monkeypatch):
    oauth_module, _ = _reload_oauth_with_env(monkeypatch)

    # Mock exchange_code_for_token (POST to Instagram OAuth)
    # Business Login returns {"data": [...]} format per official docs
    def fake_post(url, data=None):
        return _MockResponse(200, {"data": [{"access_token": "short-token", "user_id": 12345, "permissions": "instagram_business_basic,instagram_business_manage_insights"}]})

    # Mock get requests (long-lived token exchange + account info)
    def fake_get(url, params=None):
        if "access_token" in url or "ig_exchange_token" in str(params):
            return _MockResponse(200, {
                "access_token": "long-lived-token",
                "token_type": "bearer",
                "expires_in": 5184000,
            })
        if "/me" in url:
            # /me may also return {"data": [...]} per Get Started guide
            return _MockResponse(200, {"data": [{
                "user_id": "12345",
                "username": "testuser",
                "name": "Test User",
                "profile_picture_url": "https://example.com/pic.jpg",
                "followers_count": 1000,
                "media_count": 50,
            }]})
        raise AssertionError(f"Unexpected GET URL: {url}")

    monkeypatch.setattr(oauth_module.requests, "post", fake_post)
    monkeypatch.setattr(oauth_module.requests, "get", fake_get)

    result = oauth_module.complete_oauth_flow("test-code")

    assert result["success"] is True
    assert result["user_token"] == "long-lived-token"
    assert result["instagram_account"].id == "12345"
    assert result["instagram_account"].username == "testuser"
    assert "page_id" not in result
    assert "page_token" not in result
