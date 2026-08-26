from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = PROJECT_ROOT / "pages" / "2_🔐_Login.py"
MIGRATION = PROJECT_ROOT / "migrations" / "002_add_consent_onboarding_transaction.sql"
SCHEMA = PROJECT_ROOT / "supabase_schema.sql"
BINDING_ID = "browser-binding-id-1234567890"


def test_terms_copy_uses_full_influencer_v12_terms():
    from src.consent import CONSENT_COPY, TERMS_VERSION

    terms = next(item for item in CONSENT_COPY if item.key == "terms_accepted")
    body = terms.body

    assert TERMS_VERSION == "influencer-v1.2-2026-08-26"
    assert body.startswith("셀럽라이프 인플루언서 서비스 이용약관 | v1.2")
    assert "Influencer Service Terms of Use" in body
    assert "운영 사업자: ㈜꿈선생 / 713-81-03266" in body
    assert "작성 기준일: 2026. 8. 26." in body
    assert "중요 조항 요약" in body
    assert "우회 거래 손해배상" in body
    assert "※ 위 요약은 이해를 돕기 위한 안내" in body
    assert "제1조 (목적)" in body
    assert "제25조 (개별 캠페인 조건의 우선)" in body
    assert "별표 1 | 소싱 제품 보호 예외 판단 기준" in body
    assert "별표 2 | 노쇼·취소 운영 원칙" in body
    assert "이 약관은 서비스에서 별도로 공지한 시행일부터 적용합니다." in body
    assert "[Preview 임시 약관]" not in body
    assert "정식 배포 전 법률 검토" not in body
    assert "셀럽라이프  ·  인플루언서용" not in body

    for article_number in range(1, 26):
        assert f"제{article_number}조" in body


def test_streamlit_login_callback_uses_shared_completion_service():
    source = LOGIN_PAGE.read_text(encoding="utf-8")

    assert "complete_instagram_login" in source
    assert "complete_oauth_flow(code)" not in source
    assert "create_or_update_user(" not in source
    assert "save_token(" not in source


def test_database_exposes_atomic_onboarding_rpc(monkeypatch):
    import src.database as database_module
    from src.consent import ConsentAcceptance
    from src.oauth import generate_state, parse_state

    calls = []

    class FakeRpcResult:
        data = 42

    class FakeClient:
        def rpc(self, name, params):
            calls.append((name, params))
            return self

        def execute(self):
            return FakeRpcResult()

    monkeypatch.setattr(database_module, "get_client", lambda: FakeClient())
    monkeypatch.setattr(database_module.config, "INSTAGRAM_APP_SECRET", "s" * 32)
    consent = parse_state(
        generate_state(ConsentAcceptance.accepted_now(), binding_id=BINDING_ID),
        expected_binding_id=BINDING_ID,
    )

    user_id = database_module.complete_instagram_onboarding(
        instagram_id="ig-123",
        instagram_username="celeb_user",
        access_token="token-value",
        expires_at=consent.accepted_at,
        consent=consent,
    )

    assert user_id == 42
    assert calls == [
        (
            "complete_instagram_onboarding",
            calls[0][1],
        )
    ]
    params = calls[0][1]
    assert params["p_instagram_id"] == "ig-123"
    assert params["p_state_nonce"] == consent.nonce
    assert params["p_bundle_hash"] == consent.bundle_hash
    assert params["p_consent_age"] is True
    assert params["p_consent_instagram"] is True


def test_database_rejects_missing_or_false_consent(monkeypatch):
    import src.database as database_module
    from src.consent import (
        CONSENT_SCHEMA_VERSION,
        INSTAGRAM_PERMISSIONS_VERSION,
        PRIVACY_VERSION,
        TERMS_VERSION,
        ConsentAcceptance,
    )

    class FakeClient:
        def rpc(self, *_args, **_kwargs):
            raise AssertionError("RPC must not run when consent is invalid")

    monkeypatch.setattr(database_module, "get_client", lambda: FakeClient())

    accepted_at = ConsentAcceptance.accepted_now().accepted_at
    consent = SimpleNamespace(
        nonce="nonce-1",
        accepted_at=accepted_at,
        bundle_hash="a" * 64,
        consent_schema_version=CONSENT_SCHEMA_VERSION,
        terms_version=TERMS_VERSION,
        privacy_version=PRIVACY_VERSION,
        instagram_permissions_version=INSTAGRAM_PERMISSIONS_VERSION,
        age_confirmed=True,
        terms_accepted=True,
        privacy_accepted=True,
        instagram_permissions_accepted=False,
    )

    try:
        database_module.complete_instagram_onboarding(
            instagram_id="ig-123",
            instagram_username="celeb_user",
            access_token="token-value",
            expires_at=consent.accepted_at,
            consent=consent,
        )
    except ValueError as exc:
        assert "instagram_permissions_accepted=true" in str(exc)
    else:
        raise AssertionError("expected false consent to fail before RPC")


def test_callback_service_short_circuits_missing_code(monkeypatch):
    import src.oauth_callback_service as service

    monkeypatch.setattr(
        service.config,
        "validate_runtime",
        lambda: (_ for _ in ()).throw(AssertionError("runtime should not run")),
    )
    monkeypatch.setattr(
        service,
        "parse_state",
        lambda *_args: (_ for _ in ()).throw(AssertionError("state should not parse")),
    )

    try:
        service.complete_instagram_login("", "signed-state")
    except ValueError as exc:
        assert str(exc) == "missing_code"
    else:
        raise AssertionError("expected missing code")


def test_callback_service_validates_runtime_before_state_exchange_or_rpc(monkeypatch):
    import src.oauth_callback_service as service

    monkeypatch.setattr(service.config, "validate_runtime", lambda: ["SUPABASE_URL"])
    monkeypatch.setattr(
        service,
        "parse_state",
        lambda *_args: (_ for _ in ()).throw(AssertionError("state should not parse")),
    )
    monkeypatch.setattr(
        service,
        "complete_oauth_flow",
        lambda *_args: (_ for _ in ()).throw(AssertionError("token exchange should not run")),
    )

    try:
        service.complete_instagram_login("auth-code", "signed-state")
    except ValueError as exc:
        assert str(exc) == "configuration_error"
    else:
        raise AssertionError("expected configuration error")


def test_callback_service_wraps_atomic_persistence_failure(monkeypatch):
    import src.database as database_module
    import src.oauth_callback_service as service

    account = SimpleNamespace(id="ig-123", username="celeb_user")
    parsed_state = SimpleNamespace(nonce="nonce-1")
    monkeypatch.setattr(service.config, "validate_runtime", lambda: [])
    monkeypatch.setattr(
        service,
        "parse_state",
        lambda _state, *, expected_binding_id=None: parsed_state,
    )
    monkeypatch.setattr(
        service,
        "complete_oauth_flow",
        lambda _code: {
            "success": True,
            "instagram_account": account,
            "user_token": "token-value",
            "user_token_expires": None,
        },
    )
    monkeypatch.setattr(
        database_module,
        "complete_instagram_onboarding",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("database detail")),
    )

    try:
        service.complete_instagram_login("auth-code", "signed-state")
    except service.OnboardingPersistenceError as exc:
        assert str(exc) == "consent persistence failed"
        assert isinstance(exc.__cause__, RuntimeError)
    else:
        raise AssertionError("expected persistence error")


def test_database_rejects_blank_identity_fields_before_rpc(monkeypatch):
    import src.database as database_module

    monkeypatch.setattr(
        database_module,
        "get_client",
        lambda: (_ for _ in ()).throw(AssertionError("RPC must not run")),
    )

    for field in ("instagram_id", "instagram_username", "access_token"):
        kwargs = {
            "instagram_id": "ig-123",
            "instagram_username": "celeb_user",
            "access_token": "token-value",
            "consent": SimpleNamespace(),
        }
        kwargs[field] = "   "
        try:
            database_module.complete_instagram_onboarding(**kwargs)
        except ValueError as exc:
            assert field in str(exc)
        else:
            raise AssertionError(f"expected blank {field} to fail")


def test_migration_creates_user_consents_and_atomic_rpc():
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.user_consents" in sql
    assert "state_nonce text not null unique" in sql
    assert "bundle_hash text not null" in sql
    assert "tokens_user_type_unique unique (user_id, token_type)" in sql
    assert "create or replace function public.complete_instagram_onboarding" in sql
    assert "security definer" in sql
    assert "grant execute on function public.complete_instagram_onboarding" in sql
    assert "to service_role" in sql
    assert "revoke all on function public.complete_instagram_onboarding" in sql
    assert "on conflict (state_nonce) do nothing" in sql
    assert "unsupported consent schema version" in sql
    assert "unsupported consent policy version" in sql
    assert "influencer-v1.2-2026-08-26" in sql


def test_base_schema_contains_consent_snapshot_contract():
    sql = SCHEMA.read_text(encoding="utf-8").lower()

    assert "create table user_consents" in sql
    assert "state_nonce text not null unique" in sql
    assert "terms_version text not null" in sql
    assert "privacy_version text not null" in sql
    assert "instagram_permissions_version text not null" in sql
    assert "bundle_hash text not null" in sql
    assert "complete_instagram_onboarding" in sql
    assert "influencer-v1.2-2026-08-26" in sql
