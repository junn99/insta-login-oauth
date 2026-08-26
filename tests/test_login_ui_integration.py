import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGIN_PAGE = PROJECT_ROOT / "pages" / "2_🔐_Login.py"
ASSET_DIR = PROJECT_ROOT / "assets" / "login"


@pytest.fixture
def login_patches(monkeypatch):
    import requests

    import src.config as config_module
    import src.database as database_module
    import src.oauth as oauth_module

    required_config = {
        "INSTAGRAM_APP_ID": "test-app-id",
        "INSTAGRAM_APP_SECRET": "test-app-secret",
        "OAUTH_REDIRECT_URI": "https://example.com/Login",
        "CONTACT_EMAIL": "reviewer@example.com",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "test-supabase-key",
    }
    for key, value in required_config.items():
        monkeypatch.setattr(config_module.Config, key, value, raising=False)
        monkeypatch.setattr(config_module.config, key, value, raising=False)
    monkeypatch.setattr(config_module.Config, "IS_VERCEL", False, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", False, raising=False)

    calls = {
        "init_db": 0,
        "oauth_url": 0,
        "validate_state": [],
        "complete_oauth_flow": [],
        "users": [],
        "tokens": [],
    }

    def fail_network(*args, **kwargs):
        raise AssertionError(f"Unexpected external network call: {args!r} {kwargs!r}")

    monkeypatch.setattr(requests.sessions.Session, "request", fail_network)

    def fail_supabase(*args, **kwargs):
        raise AssertionError(f"Unexpected Supabase client creation: {args!r} {kwargs!r}")

    monkeypatch.setattr(database_module, "create_client", fail_supabase)
    monkeypatch.setattr(oauth_module.requests, "post", fail_network)
    monkeypatch.setattr(oauth_module.requests, "get", fail_network)

    def fake_init_db():
        calls["init_db"] += 1

    def fake_get_oauth_url(*, consent=None, binding_id=None):
        calls["oauth_url"] += 1
        assert consent is not None
        assert binding_id is not None
        return "https://instagram.example/oauth?next=/Login&state=a\"b&scope=x<y>"

    monkeypatch.setattr(database_module, "init_db", fake_init_db)
    monkeypatch.setattr(oauth_module, "get_oauth_url", fake_get_oauth_url)

    return {
        "calls": calls,
        "database": database_module,
        "oauth": oauth_module,
    }


def _run_app(query_params=None, timeout=5):
    app = AppTest.from_file(LOGIN_PAGE, default_timeout=timeout)
    if query_params:
        app.query_params.update(query_params)
    return app.run(timeout=timeout)


def _all_markdown(app):
    return "\n".join(element.value for element in app.markdown)


def _link_buttons(app):
    return [
        element.proto
        for element in app
        if type(element).__name__ == "UnknownElement"
        and getattr(element.proto, "url", "")
    ]


def _disabled_instagram_cta(html: str) -> str:
    match = re.search(
        r"<button[^>]*class=\"cl-instagram-button\"[^>]*>.*?</button>",
        html,
        re.DOTALL,
    )
    assert match, html
    return match.group(0)


def test_login_assets_exist_and_are_non_empty():
    expected_assets = [
        ASSET_DIR / "celeblife_logo_purple.png",
        ASSET_DIR / "celeblife_symbol_purple.png",
    ]

    for asset in expected_assets:
        assert asset.exists()
        assert asset.stat().st_size > 0


def test_initial_login_page_renders_celeblife_ui_and_escapes_urls(login_patches):
    app = _run_app()
    html = _all_markdown(app)

    assert login_patches["calls"]["init_db"] == 1
    assert login_patches["calls"]["oauth_url"] == 0
    assert not app.title
    assert not app.error
    assert app.markdown[0].value.startswith("<style>")
    assert "\n\n" not in app.markdown[0].value
    assert "\n        <main" not in app.markdown[0].value
    # Mobile-first cascade: the phone layout is the unconditional base and
    # desktop is layered on with min-width. Guard against a regression back to
    # the old desktop-first structure.
    assert "@media (min-width: 421px)" in html
    assert "@media (min-width: 961px)" in html
    assert "@media (max-height: 720px) and (max-width: 960.98px)" in html
    # Landscape phones are too short for the connect graphic + pinned footer;
    # without this rule the CTA falls ~100px below the fold at 844x390.
    assert "@media (max-height: 500px) and (max-width: 960.98px)" in html
    assert "@media (max-width: 1080px)" not in html
    assert "@media (max-width: 620px)" not in html
    # The desktop story panel must be off by default, not merely overridden.
    assert ".cl-visual-panel {\ndisplay: none;\n}" in html
    assert "env(safe-area-inset-bottom)" in html
    assert "@media (hover: hover)" in html
    assert "Pretendard" in html
    # Meta partner-status wording is not permitted; only the login-method claim.
    assert "Meta 공식 로그인 방식" in html
    assert "공식파트너" not in html
    assert "cl-login-page" in html
    assert "반응을 읽고," in html
    assert "선택의 기준을 만듭니다." in html
    assert "반응을 읽고,<br>" not in html
    assert "채널 데이터를 분석해 맞는 제품과 판매 방향을 제안합니다." in html
    assert "연결된 채널의 콘텐츠와 반응 데이터를 분석해" not in html
    assert "Instagram으로 계속하기" in html
    assert 'href="/Login?step=consent"' in html
    assert 'target="_self"' in html
    assert "https://instagram.example/oauth" not in html
    assert 'rel="noopener noreferrer"' not in html
    assert "이전으로" not in html
    assert "cl-back-link" not in html
    assert 'href="/"' not in html
    assert 'href="/Privacy"' not in html


def test_initial_login_page_primary_cta_routes_to_full_page_consent(login_patches):
    app = _run_app()
    html = _all_markdown(app)

    assert 'href="/Login?step=consent"' in html
    assert "https://instagram.example/oauth" not in html


def test_configured_vercel_intro_cta_sets_browser_binding_first(
    login_patches,
    monkeypatch,
):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "production", raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "production", raising=False)
    for key, value in {
        "SESSION_COOKIE_SECRET": "s" * 32,
        "OAUTH_REDIRECT_URI": "https://preview.example/auth/callback",
        "SUPABASE_KEY": "sb_secret_server",
    }.items():
        monkeypatch.setattr(config_module.Config, key, value, raising=False)
        monkeypatch.setattr(config_module.config, key, value, raising=False)

    app = _run_app()
    html = _all_markdown(app)

    assert 'href="/auth/instagram/start"' in html
    assert 'href="/Login?step=consent"' not in html


def test_consent_step_renders_full_page_terms_gate(login_patches):
    app = _run_app({"step": "consent"})
    html = _all_markdown(app)

    labels = [checkbox.label for checkbox in app.checkbox]
    detail_modal_ids = [
        "cl-consent-modal-terms-accepted",
        "cl-consent-modal-privacy-accepted",
    ]
    detail_trigger_ids = [
        "cl-consent-trigger-terms-accepted",
        "cl-consent-trigger-privacy-accepted",
    ]
    age_detail_modal_id = "cl-consent-modal-age-confirmed"
    age_detail_trigger_id = "cl-consent-trigger-age-confirmed"

    assert "cl-consent-title" in html
    assert "st-key-cl-consent-shell" in html
    assert '<div class="cl-brand-mark" role="img" aria-label="CelebLife">' in html
    assert "CELEBLIFE ONBOARDING" in html
    assert "max-width: 560px" in html
    assert "필수 동의를 확인한 뒤 Instagram 연결을 진행합니다." in html
    assert "동의 후 Instagram으로 계속하기" not in html
    assert "필수 항목에 모두 동의합니다." in labels
    assert "만 14세 이상입니다. (필수)" in labels
    assert "서비스 이용약관에 동의합니다. (필수)" in labels
    assert "개인정보 수집·이용에 동의합니다. (필수)" in labels
    assert "Instagram 데이터 접근·분석에 동의합니다. (필수)" not in labels
    assert len(labels) == 4
    assert app.expander == []
    assert all(f'href="#{modal_id}"' in html for modal_id in detail_modal_ids)
    assert all(f'id="{modal_id}"' in html for modal_id in detail_modal_ids)
    assert all(f'id="{trigger_id}"' in html for trigger_id in detail_trigger_ids)
    assert all(f'href="#{trigger_id}"' in html for trigger_id in detail_trigger_ids)
    assert html.count('aria-haspopup="dialog"') == 2
    assert f'href="#{age_detail_modal_id}"' not in html
    assert f'id="{age_detail_modal_id}"' not in html
    assert f'id="{age_detail_trigger_id}"' not in html
    assert f'href="#{age_detail_trigger_id}"' not in html
    assert all(
        f'aria-controls="{modal_id}"' in html for modal_id in detail_modal_ids
    )
    assert all(
        f'aria-labelledby="{modal_id}-title"' in html
        and f'id="{modal_id}-title"' in html
        for modal_id in detail_modal_ids
    )
    assert all(
        f'aria-describedby="{modal_id}-description"' in html
        and f'id="{modal_id}-description"' in html
        for modal_id in detail_modal_ids
    )
    assert html.count('class="cl-policy-modal__title"') == 2
    normalized_button_labels = [button.label.replace(" ", "") for button in app.button]
    assert normalized_button_labels.count("상세보기") == 0
    assert html.count('class="cl-consent-detail-link"') == 2
    assert "셀럽라이프는 만 14세 이상만 이용할 수 있습니다." not in html
    assert "주식회사 꿈선생(이하 &quot;회사&quot;)은" in html
    assert "Instagram 계정 연결 및 관리" in html
    assert "cl-consent-page" in html
    assert ".cl-login-page.cl-consent-page" in html
    assert "position: relative !important" in html
    assert "min-height: auto !important" in html
    assert "--cl-consent-gutter: 20px" in html
    assert "--cl-consent-gutter: 18px" in html
    assert "--cl-consent-block-gap: 16px" in html
    assert "--cl-consent-panel-bottom: 12px" in html
    assert "--cl-consent-shell-gap: 4px" in html
    assert "gap: var(--cl-consent-shell-gap) !important" in html
    assert "var(--cl-consent-gutter)" in html
    assert (
        "padding: max(20px, env(safe-area-inset-top)) 0 "
        "var(--cl-consent-panel-bottom) !important"
        in html
    )
    assert (
        "[data-testid=\"stMarkdownContainer\"]:has(.cl-consent-page)" in html
    )
    assert "margin-bottom: 0 !important" in html
    assert "max-width: none !important" in html
    assert (
        ".cl-login-page.cl-consent-page .cl-form-card .cl-brand-mark"
        in html
    )
    assert (
        ".cl-login-page.cl-consent-page .cl-form-card .cl-eyebrow"
        in html
    )
    assert html.count("display: block !important") >= 2
    assert ".st-key-cl_consent_submit_disabled .stButton > button" in html
    assert (
        ".st-key-cl_consent_submit_link [data-testid=\"stLinkButton\"] > a"
        in html
    )
    assert (
        ".st-key-cl-consent-shell [class*=\"st-key-cl_consent_item_\"] "
        ".stHorizontalBlock"
        in html
    )
    assert "align-items: flex-start" in html
    assert "flex-wrap: nowrap !important" in html
    assert (
        ".stHorizontalBlock > [data-testid=\"stColumn\"]:first-child"
        in html
    )
    assert "flex: 1 1 auto !important" in html
    assert "min-width: 0 !important" in html
    assert (
        ".stHorizontalBlock > [data-testid=\"stColumn\"]:last-child"
        in html
    )
    assert "flex: 0 0 auto !important" in html
    assert "min-width: auto !important" in html
    assert (
        ".st-key-cl-consent-shell .cl-consent-detail-link"
        in html
    )
    assert "vertical_alignment=\"center\"" not in html
    assert (
        ".st-key-cl-consent-shell [data-testid=\"stLinkButton\"] > a"
        not in html
    )
    assert "min-height: 44px" in html
    assert "margin: 0 !important" in html
    assert "line-height: 1.4 !important" in html
    assert "line-height: 1.8 !important" in html
    assert "line-height: 1.52" in html
    assert "line-height: 1.54" in html
    assert "margin-bottom: 0" in html
    assert "box-sizing: border-box" in html
    assert "padding: 0 !important" in html
    assert (
        "[class*=\"st-key-cl_consent_detail_\"] "
        "[data-testid=\"stMarkdownContainer\"]"
        in html
    )
    assert "[data-testid=\"stMarkdownContainer\"] p" in html
    assert "justify-content: flex-end" in html
    assert ".cl-policy-modal *" in html
    assert "font-family: __CONSENT_FONT_STACK__ !important" not in html
    assert "Material Symbols Rounded" in html
    assert ".cl-policy-modal:target" in html
    assert "width: min(100%, 640px)" in html
    assert "max-height: min(82dvh, 760px)" in html
    assert "max-height: 86dvh" in html
    assert "overflow: hidden" in html
    assert "overflow-y: auto" in html
    assert "position: sticky" in html
    assert "cl-policy-modal__footer" in html
    assert "cl-policy-modal__close-button" in html
    assert "확인했어요" in html
    assert "margin-top: 12px" in html
    assert "line-height: 1.86 !important" in html
    assert "line-height: 1.54" in html
    assert "line-height: 1.72" in html
    assert "line-height: 1.58" in html
    assert "cl-policy-modal__document-title" in html
    assert "cl-policy-modal__metadata" in html
    assert "cl-policy-modal__intro" in html
    assert "cl-policy-modal__section-heading" in html
    assert "cl-policy-modal__section-number" in html
    assert "cl-policy-modal__subheading" in html
    assert "cl-policy-modal__list-row" in html
    assert "cl-policy-modal__paragraph" in html
    assert '<span class="cl-policy-modal__section-number">1</span>' in html
    assert '<span class="cl-policy-modal__section-number">11</span>' in html
    assert '<span class="cl-policy-modal__section-number">부칙</span>' in html
    assert '<p class="cl-policy-modal__subheading">회원 정보</p>' in html
    assert '<li class="cl-policy-modal__list-row">이름</li>' in html
    assert (
        '<li class="cl-policy-modal__list-row">'
        "Supabase: 데이터베이스 및 서비스 데이터 저장·관리</li>"
        in html
    )
    assert "본 개인정보처리방침은 셀럽라이프 서비스 이용 과정에서" in html
    assert "Instagram Access Token 등 OAuth 인증에 필요한 정보" in html
    assert "Instagram 계정 연결 및 관리" in html
    assert "셀럽라이프 개인정보처리방침" in html
    assert "최종 업데이트: 2026년 8월 26일" in html
    assert "사업자등록번호: 713-81-03266" in html
    assert "이메일: dkssud374@gmail.com" in html
    assert "본 개인정보처리방침은 2026년 8월 26일부터 시행합니다." in html
    privacy_modal_html = html[
        html.index('id="cl-consent-modal-privacy-accepted"') :
    ]
    assert (
        privacy_modal_html.index("셀럽라이프 개인정보처리방침")
        < privacy_modal_html.index("최종 업데이트: 2026년 8월 26일")
        < privacy_modal_html.index("수집 및 처리하는 정보")
        < privacy_modal_html.index("개인정보처리방침의 변경")
        < privacy_modal_html.index("부칙")
    )
    assert "개인정보 처리방침 전체 보기" not in html
    assert 'href="/Privacy"' not in html


def test_terms_policy_renderer_supports_pdf_plaintext_contract():
    import src.ui.celeblife_login as login_ui

    body = """셀럽라이프 인플루언서 서비스 이용약관 | v1.2
셀럽라이프와 인플루언서의 서비스 이용 조건을 정합니다.
운영 서비스: 셀럽라이프
운영 사업자: 주식회사 꿈선생
작성 기준일: 2026년 8월 26일

중요 조항 요약
소싱 제품 보호
회사가 먼저 발굴한 제품은 90일 동안 원칙적으로 셀럽라이프를 통해 진행합니다.
기존 일정 예외
소싱 전에 이미 해당 월 진행이 확정된 건은 예외입니다.
선행 독점·전속 예외
유효한 독점·전속 계약이 이미 체결된 경우 제한 범위에 한해 예외가 적용됩니다.
단순 제안은 예외 아님
과거 제안이나 샘플 수령만 한 상태는 기존 확정으로 보지 않습니다.
노쇼·일방 취소
반복 노쇼는 서비스 이용 제한 사유가 될 수 있습니다.
우회 거래 손해배상
회사 밖에서 수수료를 회피한 경우 손해배상을 청구할 수 있습니다.
※ 위 요약은 이해를 돕기 위한 안내이며, 구체적인 권리·의무는 아래 약관 본문과 개별 캠페인 조건에 따릅니다.

제1조 (목적)
본 약관은 셀럽라이프 인플루언서 서비스의 이용 조건을 정합니다.
① 회원은 본 약관을 확인하고 동의합니다.

제2조 (서비스의 범위)
회사는 Instagram 데이터 분석 및 상품 추천 기능을 제공합니다.
1. 회원의 채널 데이터에 기초한 상품 탐색·추천

별표 1 | 콘텐츠 인정 기준
구분 | 처리 원칙 | 산정 기준
게시물|원본 링크와 계정 권한이 확인되는 경우|인정
릴스|성과 데이터 증빙이 있는 경우|증빙 시 인정
광고성 게시물|권한 또는 출처가 확인되지 않는 경우|불인정

별표 2 | 증빙 자료
상황 | 기존 확정 인정 | 처리
계정 캡처|본인 계정임을 확인할 수 있는 자료|인정

부칙
본 약관은 2026년 8월 26일부터 시행합니다."""

    html = login_ui._consent_detail_body_html("terms_accepted", body)

    assert "cl-policy-modal__document--terms" in html
    assert "cl-policy-modal__document-title" in html
    assert "cl-policy-modal__document-subtitle" in html
    assert html.count("cl-policy-modal__metadata-row") == 3
    assert "cl-policy-modal__summary-grid" in html
    assert html.count("cl-policy-modal__summary-card") == 6
    assert "cl-policy-modal__section--article" in html
    assert "cl-policy-modal__section--appendix" in html
    assert "cl-policy-modal__table-list" in html
    assert html.count("cl-policy-modal__table-row") == 4
    assert html.count("cl-policy-modal__table-cell") == 12
    assert html.count("cl-policy-modal__status-badge") == 4
    assert "cl-policy-modal__note" in html
    assert "<table" not in html
    assert "구분 | 처리 원칙 | 산정 기준" not in html
    assert "상황 | 기존 확정 인정 | 처리" not in html
    assert '<span class="cl-policy-modal__table-label">구분</span>' in html
    assert '<span class="cl-policy-modal__table-label">처리 원칙</span>' in html
    assert '<span class="cl-policy-modal__table-label">산정 기준</span>' in html
    assert '<span class="cl-policy-modal__table-label">상황</span>' in html
    assert '<span class="cl-policy-modal__table-label">기존 확정 인정</span>' in html
    assert '<span class="cl-policy-modal__table-label">처리</span>' in html
    assert '<p class="cl-policy-modal__paragraph">① 회원은 본 약관을 확인하고 동의합니다.</p>' in html
    assert '<li class="cl-policy-modal__list-row">1. 회원의 채널 데이터에 기초한 상품 탐색·추천</li>' in html
    assert "페이지 1" not in html
    assert "셀럽라이프 인플루언서 서비스 이용약관 | v1.2" in html
    assert "소싱 제품 보호" in html
    assert "제1조" in html
    assert "별표 1" in html
    assert "부칙" in html
    assert (
        html.index("셀럽라이프 인플루언서 서비스 이용약관 | v1.2")
        < html.index("운영 서비스")
        < html.index("중요 조항 요약")
        < html.index("제1조")
        < html.index("별표 1")
        < html.index("별표 2")
        < html.index("부칙")
    )


def test_terms_policy_renderer_escapes_pdf_plaintext_values():
    import src.ui.celeblife_login as login_ui

    body = """셀럽라이프 인플루언서 서비스 이용약관 | v1.2
<script>alert(1)</script>
운영 서비스: 셀럽라이프 <서비스>
운영 사업자: 주식회사 꿈선생
작성 기준일: 2026년 8월 26일
중요 조항 요약
위험: <img src=x onerror=alert(1)>
제1조 (목적)
본문 <b>태그</b>는 텍스트로 보입니다.
별표 1 | 기준
항목|<기준>|인정
부칙
끝"""

    html = login_ui._consent_detail_body_html("terms_accepted", body)

    assert "<script>" not in html
    assert "<img" not in html
    assert "<b>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "셀럽라이프 &lt;서비스&gt;" in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "&lt;기준&gt;" in html


def test_consent_step_does_not_start_oauth_before_required_agreements(
    login_patches,
):
    app = _run_app({"step": "consent"})
    html = _all_markdown(app)

    assert login_patches["calls"]["oauth_url"] == 0
    assert "https://instagram.example/oauth" not in html
    assert any(
        button.label == "동의하고 Instagram으로 계속하기" for button in app.button
    )


def test_consent_step_back_action_returns_to_intro_and_clears_state(login_patches):
    app = _run_app({"step": "consent"})
    html = _all_markdown(app)

    assert any(button.label == "이전으로" for button in app.button)
    assert 'href="/Login"' not in html
    assert "state=" not in html

    app.session_state["cl_consent_all"] = True
    app.session_state["cl_consent_age_confirmed"] = True
    app.session_state["cl_consent_terms_accepted"] = True
    app.session_state["cl_consent_privacy_accepted"] = True
    app.session_state["cl_consent_instagram_permissions_accepted"] = True
    app.session_state["cl_oauth_handoff_url"] = "https://instagram.example/oauth?state=cached"
    app.button(key="cl_consent_back").click().run()

    assert app.query_params == {}
    assert app.session_state["cl_consent_all"] is False
    assert app.session_state["cl_consent_age_confirmed"] is False
    assert app.session_state["cl_consent_terms_accepted"] is False
    assert app.session_state["cl_consent_privacy_accepted"] is False
    assert app.session_state["cl_consent_instagram_permissions_accepted"] is False
    assert "cl_oauth_handoff_url" not in app.session_state


def test_preview_missing_config_login_renders_disabled_ui_without_oauth_or_db(
    login_patches,
    monkeypatch,
):
    import src.config as config_module
    import src.database as database_module
    import src.oauth as oauth_module

    calls = login_patches["calls"]

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    for key in (
        "INSTAGRAM_APP_ID",
        "INSTAGRAM_APP_SECRET",
        "OAUTH_REDIRECT_URI",
        "CONTACT_EMAIL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ):
        monkeypatch.setattr(config_module.Config, key, "", raising=False)
        monkeypatch.setattr(config_module.config, key, "", raising=False)

    monkeypatch.setattr(
        database_module,
        "create_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("credentialless preview must not create Supabase client")
        ),
    )
    monkeypatch.setattr(
        oauth_module,
        "get_oauth_url",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("credentialless preview must not generate OAuth URL")
        ),
    )
    monkeypatch.setattr(
        oauth_module,
        "complete_oauth_flow",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("credentialless preview must not exchange token")
        ),
    )

    app = _run_app({"code": "auth-code", "state": "state-value"})
    html = _all_markdown(app)

    assert not app.exception
    assert calls["init_db"] == 0
    assert calls["oauth_url"] == 0
    assert calls["complete_oauth_flow"] == []
    assert "cl-login-page" in html
    assert app.error == []
    assert app.query_params == {}
    assert 'href="/Login?step=consent"' in html
    assert "javascript:" not in html
    assert 'href="#"' not in html


def test_preview_missing_config_consent_step_renders_without_oauth_or_db(
    login_patches,
    monkeypatch,
):
    import src.config as config_module
    import src.database as database_module
    import src.oauth as oauth_module

    calls = login_patches["calls"]

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    for key in (
        "INSTAGRAM_APP_ID",
        "INSTAGRAM_APP_SECRET",
        "OAUTH_REDIRECT_URI",
        "CONTACT_EMAIL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ):
        monkeypatch.setattr(config_module.Config, key, "", raising=False)
        monkeypatch.setattr(config_module.config, key, "", raising=False)

    monkeypatch.setattr(
        database_module,
        "create_client",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("credentialless preview consent must not create Supabase client")
        ),
    )
    monkeypatch.setattr(
        oauth_module,
        "get_oauth_url",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("credentialless preview consent must not generate OAuth URL")
        ),
    )

    app = _run_app({"step": "consent"})
    html = _all_markdown(app)

    assert not app.exception
    assert calls["init_db"] == 0
    assert calls["oauth_url"] == 0
    assert "cl-consent-title" in html
    assert any(
        button.label == "동의하고 Instagram으로 계속하기" for button in app.button
    )
    assert "https://instagram.example/oauth" not in html
    assert dict(app.query_params) == {"step": ["consent"]}


def test_preview_missing_config_consent_step_links_to_preview_handoff(
    login_patches,
    monkeypatch,
):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    for key in (
        "INSTAGRAM_APP_ID",
        "INSTAGRAM_APP_SECRET",
        "OAUTH_REDIRECT_URI",
        "CONTACT_EMAIL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ):
        monkeypatch.setattr(config_module.Config, key, "", raising=False)
        monkeypatch.setattr(config_module.config, key, "", raising=False)

    app = _run_app({"step": "consent"})
    for checkbox in app.checkbox:
        checkbox.check()
    app = app.run()

    assert any(
        button.url == "/Login?step=instagram-preview"
        for button in _link_buttons(app)
    )


def test_preview_missing_config_instagram_preview_step_renders_mock_handoff(
    login_patches,
    monkeypatch,
):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "preview", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", False, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "s" * 32, raising=False)
    for key in (
        "INSTAGRAM_APP_ID",
        "INSTAGRAM_APP_SECRET",
        "OAUTH_REDIRECT_URI",
        "CONTACT_EMAIL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ):
        monkeypatch.setattr(config_module.Config, key, "", raising=False)
        monkeypatch.setattr(config_module.config, key, "", raising=False)

    app = _run_app({"step": "instagram-preview"})
    html = _all_markdown(app)

    assert not app.exception
    assert "Instagram 로그인 화면 미리보기" in html
    assert "실제 인증과 권한 화면은 Meta가 호스팅합니다." in html
    assert "동의 화면으로 돌아가기" in html
    assert 'href="/Login?step=consent"' in html


def test_render_login_page_routes_to_consent_when_oauth_url_is_missing(monkeypatch):
    import src.ui.celeblife_login as login_ui

    rendered = []
    monkeypatch.setattr(
        login_ui.st,
        "markdown",
        lambda body, unsafe_allow_html=False: rendered.append(
            {"body": body, "unsafe": unsafe_allow_html}
        ),
    )

    login_ui.render_login_page(oauth_url=None)

    assert len(rendered) == 1
    assert rendered[0]["unsafe"] is True
    html = rendered[0]["body"]
    assert 'href="/Login?step=consent"' in html
    assert "https://instagram.example/oauth" not in html


def test_render_login_page_never_uses_supplied_oauth_url(monkeypatch):
    import src.ui.celeblife_login as login_ui

    rendered = []
    monkeypatch.setattr(
        login_ui.st,
        "markdown",
        lambda body, unsafe_allow_html=False: rendered.append(body),
    )

    login_ui.render_login_page(
        oauth_url="https://instagram.example/oauth?state=must-not-leak",
        continue_url="https://attacker.example/skip-consent",
    )

    html = rendered[0]
    assert 'href="/Login?step=consent"' in html
    assert "https://instagram.example/oauth" not in html
    assert "https://attacker.example" not in html


@pytest.mark.parametrize(
    "query_params",
    [
        {"code": "auth-code", "state": "state-value"},
        {
            "error": "access_denied",
            "error_reason": "user_denied",
            "error_description": "sensitive callback details",
        },
        {"auth_error": "callback_failed"},
    ],
)
def test_vercel_non_preview_missing_config_blocks_login_queries_before_side_effects(
    login_patches,
    monkeypatch,
    query_params,
):
    import src.config as config_module
    import src.oauth as oauth_module

    calls = login_patches["calls"]

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.Config, "VERCEL_ENV", "production", raising=False)
    monkeypatch.setattr(config_module.Config, "PREVIEW_SAFE_MODE", True, raising=False)
    monkeypatch.setattr(config_module.Config, "SESSION_COOKIE_SECRET", "", raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "VERCEL_ENV", "production", raising=False)
    monkeypatch.setattr(config_module.config, "PREVIEW_SAFE_MODE", True, raising=False)
    monkeypatch.setattr(config_module.config, "SESSION_COOKIE_SECRET", "", raising=False)
    for key in (
        "INSTAGRAM_APP_ID",
        "INSTAGRAM_APP_SECRET",
        "OAUTH_REDIRECT_URI",
        "CONTACT_EMAIL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ):
        monkeypatch.setattr(config_module.Config, key, "", raising=False)
        monkeypatch.setattr(config_module.config, key, "", raising=False)

    monkeypatch.setattr(
        oauth_module,
        "validate_state",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("missing config must stop before state validation")
        ),
    )
    monkeypatch.setattr(
        oauth_module,
        "complete_oauth_flow",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("missing config must stop before token exchange")
        ),
    )

    app = _run_app(query_params)
    html = _all_markdown(app)

    assert not app.exception
    assert calls["init_db"] == 0
    assert calls["oauth_url"] == 0
    assert calls["complete_oauth_flow"] == []
    assert app.query_params == {}
    assert app.error
    assert app.error[0].value == "앱 로그인 설정이 완료되지 않았습니다. 관리자에게 문의하세요."
    assert "sensitive callback details" not in html
    assert "cl-login-page" not in html


def test_breakpoint_blocks_are_in_cascade_order(login_patches):
    """The media queries have equal specificity, so source order is the ONLY
    thing making them resolve correctly. Substring assertions stay green if the
    blocks get reordered, which would silently break the viewports they fix.
    """

    app = _run_app()
    html = _all_markdown(app)

    base = html.index(".cl-login-page .cl-form-card {")
    bp421 = html.index("@media (min-width: 421px)")
    bp961 = html.index("@media (min-width: 961px)")
    short = html.index("@media (max-height: 720px) and (max-width: 960.98px)")
    landscape = html.index("@media (max-height: 500px) and (max-width: 960.98px)")
    hover = html.index("@media (hover: hover)")

    # Mobile base must precede every min-width block that widens it.
    assert base < bp421 < bp961, "mobile-first order broken"
    # 500px must come after 720px: both match a landscape phone and the tighter
    # one has to win, which it only does by being later.
    assert short < landscape, "landscape block must follow the short-viewport block"
    # Hover last so it can override the touch-safe defaults.
    assert bp961 < hover


def test_heading_elements_avoid_streamlit_custom_heading(login_patches):
    """Streamlit's CustomHeading overwrites the id on any real h1/h2, which kills
    the aria-labelledby on both sections and adds "Link to heading" tab stops.
    """

    app = _run_app()
    html = _all_markdown(app)

    assert "<h1" not in html and "<h2" not in html
    for element in (
        '<p class="cl-form-title" id="cl-form-title" role="heading" aria-level="1">',
        '<p class="cl-story-title" id="cl-story-title" role="heading" aria-level="2">',
    ):
        assert element in html, f"heading lost its role/id wiring: {element}"

    # Each section's aria-labelledby must point at an id that exists.
    for section_id in ("cl-form-title", "cl-story-title"):
        assert f'aria-labelledby="{section_id}"' in html
        assert f'id="{section_id}"' in html


def test_no_bare_element_selector_outranks_a_component_rule(login_patches):
    """A descendant selector like ".cl-story-copy p" is (0,2,1) and silently
    outranks the (0,2,0) .cl-story-title / .cl-eyebrow rules inside the same
    container -- which flattened the desktop story panel to body text. Every
    component rule must be class-only so specificity stays uniform.
    """

    app = _run_app()
    html = _all_markdown(app)

    offenders = re.findall(
        r"^\.cl-login-page(?: \.[a-z0-9-]+)* ([a-z]+[a-z0-9]*) \{", html, re.MULTILINE
    )
    # h1/h2/p/a appear once in the deliberate Streamlit reset, and svg/strong/span
    # rules are scoped to a single component; a bare element after a component
    # class is what breaks sibling class rules.
    assert set(offenders) <= {"h1", "h2", "p", "a", "svg", "strong", "span"}, offenders
    assert ".cl-story-copy p {" not in html
    assert ".cl-login-page .cl-story-lead {" in html


def test_login_styles_outrank_streamlit_theme(login_patches):
    """Streamlit themes markdown h1-h6/a via ".st-emotion-cache-xxxx h1", which
    beats a bare single-class selector -- including font-family "Source Sans",
    which has no Korean glyphs and renders the headline as tofu boxes. Component
    rules must stay scoped under .cl-login-page so they win on specificity.
    """

    app = _run_app()
    html = _all_markdown(app)

    # The brand font must be forced across the subtree, not merely inherited.
    assert 'font-family: "Pretendard Variable"' in html
    assert "sans-serif !important;" in html

    # Streamlit's heading padding and link underline must be neutralised.
    assert "text-decoration: none !important;" in html

    # Text rules that collide with Streamlit's element selectors must carry the
    # two-class scope. A bare ".cl-form-title {" would silently lose again.
    for scoped in (
        ".cl-login-page .cl-form-title {",
        ".cl-login-page .cl-lead {",
        ".cl-login-page .cl-instagram-button {",
        ".cl-login-page .cl-trust-copy {",
    ):
        assert scoped in html, f"unscoped selector regressed: {scoped}"

    assert "\n.cl-form-title {" not in html
    assert "\n.cl-instagram-button {" not in html


def test_success_callback_preserves_token_save_session_and_clears_query(login_patches, monkeypatch):
    import src.oauth_callback_service as callback_service

    calls = login_patches["calls"]

    def fake_complete_instagram_login(code, state, *, expected_binding_id=None):
        calls["complete_oauth_flow"].append((code, state))
        return callback_service.OnboardingResult(
            user_id=42,
            instagram_id="ig-123",
            instagram_username="celeb_user",
            state_nonce="nonce-123",
        )

    monkeypatch.setattr(
        callback_service,
        "complete_instagram_login",
        fake_complete_instagram_login,
    )

    app = _run_app({"code": "auth-code", "state": "valid-state"})

    assert calls["complete_oauth_flow"] == [("auth-code", "valid-state")]
    assert app.session_state["user_id"] == 42
    assert app.session_state["instagram_username"] == "celeb_user"
    assert app.query_params == {}
    # Streamlit 1.61 renders a leading emoji as the status icon instead of
    # keeping it in the message value returned by AppTest.
    assert app.success[0].value == "@celeb_user 로그인 성공!"


def test_vercel_login_query_callback_does_not_exchange_token(login_patches, monkeypatch):
    import src.config as config_module

    calls = login_patches["calls"]

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    for key, value in {
        "OAUTH_REDIRECT_URI": "https://preview.example/auth/callback",
        "SESSION_COOKIE_SECRET": "s" * 32,
        "SUPABASE_KEY": "sb_secret_server",
    }.items():
        monkeypatch.setattr(config_module.Config, key, value, raising=False)
        monkeypatch.setattr(config_module.config, key, value, raising=False)
    monkeypatch.setattr(
        config_module.Config,
        "SUPABASE_PREVIEW_PROJECT_REF",
        "previewref",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "SUPABASE_PRODUCTION_PROJECT_REF",
        "prodref",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "SUPABASE_URL",
        "https://previewref.supabase.co",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "SUPABASE_PREVIEW_PROJECT_REF",
        "previewref",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "SUPABASE_PRODUCTION_PROJECT_REF",
        "prodref",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "SUPABASE_URL",
        "https://previewref.supabase.co",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "CONTACT_EMAIL",
        "reviewer@example.com",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "INSTAGRAM_APP_ID",
        "app-id",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "INSTAGRAM_APP_SECRET",
        "app-secret",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "CONTACT_EMAIL",
        "reviewer@example.com",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "INSTAGRAM_APP_ID",
        "app-id",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "INSTAGRAM_APP_SECRET",
        "app-secret",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "VERCEL_ENV",
        "preview",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "VERCEL_ENV",
        "preview",
        raising=False,
    )
    monkeypatch.setattr(
        config_module.config,
        "validate_runtime",
        lambda: [],
        raising=False,
    )
    monkeypatch.setattr(
        config_module.Config,
        "validate_runtime",
        classmethod(lambda cls: []),
        raising=False,
    )
    import src.oauth_callback_service as callback_service

    monkeypatch.setattr(
        callback_service,
        "complete_instagram_login",
        lambda code, state, *, expected_binding_id=None: (_ for _ in ()).throw(
            AssertionError("shared callback should not run on Vercel /Login")
        ),
    )

    app = _run_app({"code": "auth-code", "state": "valid-state"})

    assert calls["complete_oauth_flow"] == []
    assert calls["oauth_url"] == 0
    assert app.query_params == {}
    assert "로그인을 완료하지 못했습니다" in app.error[0].value


def test_vercel_login_error_query_uses_sanitized_retry(login_patches, monkeypatch):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    for key, value in {
        "OAUTH_REDIRECT_URI": "https://preview.example/auth/callback",
        "SESSION_COOKIE_SECRET": "s" * 32,
        "SUPABASE_KEY": "sb_secret_server",
    }.items():
        monkeypatch.setattr(config_module.Config, key, value, raising=False)
        monkeypatch.setattr(config_module.config, key, value, raising=False)

    app = _run_app(
        {
            "error": "access_denied",
            "error_reason": "user_denied",
            "error_description": "sensitive callback details",
        }
    )

    assert app.query_params == {}
    assert "로그인을 완료하지 못했습니다" in app.error[0].value
    assert "sensitive callback details" not in _all_markdown(app)


def test_logged_in_non_vercel_login_page_does_not_link_asgi_logout(
    login_patches, monkeypatch
):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", False, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", False, raising=False)

    app = _run_app()
    app.session_state["user_id"] = 42
    app.session_state["instagram_username"] = "celeb_user"
    app.run()

    assert "/auth/logout" not in [button.url for button in _link_buttons(app)]
    assert any(button.label == "로그아웃" for button in app.button)


def test_logged_in_vercel_login_page_links_asgi_logout(login_patches, monkeypatch):
    import src.config as config_module

    monkeypatch.setattr(config_module.Config, "IS_VERCEL", True, raising=False)
    monkeypatch.setattr(config_module.config, "IS_VERCEL", True, raising=False)
    for key, value in {
        "OAUTH_REDIRECT_URI": "https://preview.example/auth/callback",
        "SESSION_COOKIE_SECRET": "s" * 32,
        "SUPABASE_KEY": "sb_secret_server",
    }.items():
        monkeypatch.setattr(config_module.Config, key, value, raising=False)
        monkeypatch.setattr(config_module.config, key, value, raising=False)

    app = _run_app()
    app.session_state["user_id"] = 42
    app.session_state["instagram_username"] = "celeb_user"
    app.run()

    assert "/auth/logout" in [button.url for button in _link_buttons(app)]


def test_invalid_state_does_not_exchange_token_and_clears_query(login_patches, monkeypatch):
    import src.oauth_callback_service as callback_service

    calls = login_patches["calls"]

    monkeypatch.setattr(
        callback_service,
        "complete_instagram_login",
        lambda code, state, *, expected_binding_id=None: (_ for _ in ()).throw(
            callback_service.StateError("invalid_state")
        ),
    )

    app = _run_app({"code": "auth-code", "state": "bad-state"})

    assert calls["complete_oauth_flow"] == []
    assert calls["oauth_url"] == 0
    assert app.query_params == {}
    assert "세션이 유효하지 않습니다" in app.error[0].value
    link_buttons = _link_buttons(app)
    assert len(link_buttons) == 1
    assert link_buttons[0].label == "다시 동의하고 연결하기"
    assert link_buttons[0].url == "/Login?step=consent"


def test_persistence_failure_uses_safe_retry_message(login_patches, monkeypatch):
    import src.oauth_callback_service as callback_service

    monkeypatch.setattr(
        callback_service,
        "complete_instagram_login",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            callback_service.OnboardingPersistenceError("sensitive database detail")
        ),
    )

    app = _run_app({"code": "auth-code", "state": "valid-state"})

    assert app.query_params == {}
    assert app.error[0].value == "동의 내역을 저장하지 못했습니다. 다시 시도해 주세요."
    assert "sensitive database detail" not in _all_markdown(app)
    link_buttons = _link_buttons(app)
    assert len(link_buttons) == 1
    assert link_buttons[0].url == "/Login?step=consent"


def test_user_denied_error_shows_retry_url_and_clears_query(login_patches):
    calls = login_patches["calls"]

    app = _run_app(
        {
            "error": "access_denied",
            "error_reason": "user_denied",
            "error_description": "User denied",
        }
    )

    assert calls["oauth_url"] == 0
    assert app.query_params == {}
    assert app.warning[0].value == "권한 요청이 거부되었습니다."
    assert "instagram_business_manage_insights" in _all_markdown(app)
    link_buttons = _link_buttons(app)
    assert len(link_buttons) == 1
    assert link_buttons[0].label == "다시 동의하고 연결하기"
    assert link_buttons[0].url == "/Login?step=consent"
