import importlib.util
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

from src.consent import CONSENT_KEYS
from src.ui import celeblife_login as ui


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "tools" / "build_static_login.py"
STATIC_LOGIN_PATH = PROJECT_ROOT / "public" / "Login" / "index.html"
STATIC_ASSET_DIR = PROJECT_ROOT / "public" / "Login" / "assets"
SOURCE_ASSET_DIR = PROJECT_ROOT / "assets" / "login"


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[dict[str, str | None]] = []
        self.forms: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        data = dict(attrs)
        if tag == "input":
            self.inputs.append(data)
        elif tag == "form":
            self.forms.append(data)
        elif tag == "a":
            self.links.append(data)
        elif tag == "button":
            self.buttons.append(data)


def _load_generator():
    spec = importlib.util.spec_from_file_location("build_static_login", GENERATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generated_html() -> str:
    return STATIC_LOGIN_PATH.read_text(encoding="utf-8")


def _parse(html: str) -> _InputParser:
    parser = _InputParser()
    parser.feed(html)
    return parser


def _css_block(html: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\n\}}", html, re.S)
    assert match is not None, selector
    return match.group("body")


def test_generator_matches_checked_in_static_artifact():
    builder = _load_generator()

    assert builder.build() + "\n" == _generated_html()


def test_static_login_uses_source_copy_assets_and_responsive_styles():
    html = _generated_html()

    for copy in (
        "인스타그램을 연결해 주세요",
        "반응을 읽고,",
        "선택의 기준을 만듭니다.",
        "채널 데이터를 분석해 맞는 제품과 판매 방향을 제안합니다.",
        "Meta 공식 로그인 방식",
        "연결 전 동의가 필요해요",
        "필수 동의를 확인한 뒤 Instagram 연결을 진행합니다.",
        "동의하고 Instagram으로 계속하기",
    ):
        assert copy in html

    assert 'url("/Login/assets/celeblife_logo_purple.png")' in html
    assert 'url("/Login/assets/celeblife_symbol_purple.png")' in html
    assert "data:image/png;base64," not in html
    assert len(html.encode("utf-8")) < 220_000
    assert "@media (max-width: 420px)" in html
    assert "@media (min-width: 961px)" in html


def test_static_login_copies_exact_brand_asset_bytes():
    builder = _load_generator()
    assert tuple(builder.STATIC_BRAND_ASSETS) == (
        "celeblife_logo_purple.png",
        "celeblife_symbol_purple.png",
    )

    for filename in builder.STATIC_BRAND_ASSETS:
        source = SOURCE_ASSET_DIR / filename
        copied = STATIC_ASSET_DIR / filename
        assert copied.exists()
        assert copied.read_bytes() == source.read_bytes()
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == hashlib.sha256(
            source.read_bytes()
        ).hexdigest()


def test_static_consent_has_three_visible_required_checkboxes_and_two_modals():
    html = _generated_html()
    parser = _parse(html)

    visible_required = [
        item
        for item in parser.inputs
        if item.get("type") == "checkbox" and item.get("data-required") == "true"
    ]
    assert [item.get("name") for item in visible_required] == [
        item.key for item in ui.CONSENT_ITEMS
    ]
    assert len(visible_required) == 3

    assert 'id="cl-consent-trigger-age-confirmed"' not in html
    assert html.count('class="cl-consent-detail-link"') == 2
    detail_links = [
        link for link in parser.links if link.get("class") == "cl-consent-detail-link"
    ]
    assert [
        (link.get("href"), link.get("aria-controls")) for link in detail_links
    ] == [
        ("#cl-consent-modal-terms-accepted", "cl-consent-modal-terms-accepted"),
        ("#cl-consent-modal-privacy-accepted", "cl-consent-modal-privacy-accepted"),
    ]
    assert 'id="cl-consent-modal-terms-accepted"' in html
    assert 'id="cl-consent-modal-privacy-accepted"' in html
    assert 'id="cl-consent-modal-age-confirmed"' not in html
    assert "서비스 이용약관" in html
    assert "개인정보 수집·이용" in html


def test_static_consent_posts_exact_four_fields_to_instagram_start():
    html = _generated_html()
    parser = _parse(html)

    forms = [
        form
        for form in parser.forms
        if form.get("action") == "/auth/instagram/start"
        and form.get("method") == "post"
    ]
    assert len(forms) == 1

    named_inputs = [item for item in parser.inputs if item.get("name")]
    assert [item.get("name") for item in named_inputs] == list(CONSENT_KEYS)
    assert all(item.get("value") == "true" for item in named_inputs)
    assert len(named_inputs) == 4
    assert any(
        item.get("type") == "hidden"
        and item.get("name") == "instagram_permissions_accepted"
        for item in named_inputs
    )


def test_static_login_keeps_oauth_material_out_of_document():
    html = _generated_html()

    assert "client_secret" not in html
    assert "INSTAGRAM_APP_SECRET" not in html
    assert "oauth/authorize" not in html
    assert re.search(r"[?&]state=", html) is None
    assert "streamlit" not in html.lower()
    assert "stApp" not in html
    assert "data-testid" not in html
    assert "code=auth-code" not in html
    assert "state=state-value" not in html


def test_static_history_deep_link_error_and_submit_contracts():
    html = _generated_html()
    parser = _parse(html)

    assert 'href="/Login?step=consent"' in html
    assert "history[replace ? 'replaceState' : 'pushState']" in html
    assert "new URLSearchParams(location.search).get('step')" in html
    assert "params.has('auth_error') ? params.get('auth_error') : null" in html
    assert "로그인 동의 시간이 만료되었습니다. 다시 진행해 주세요." in html
    assert 'class="cl-form-error"' not in html

    back_buttons = [
        button for button in parser.buttons if button.get("class") == "cl-consent-back"
    ]
    assert len(back_buttons) == 1
    assert back_buttons[0].get("data-action") == "show-intro"
    assert '<span class="cl-consent-back-text">이전으로</span>' in html
    assert "gap: 8px;" in html

    submit_buttons = [
        button
        for button in parser.buttons
        if button.get("class") == "cl-consent-submit"
    ]
    assert len(submit_buttons) == 1
    assert submit_buttons[0].get("type") == "submit"
    assert "disabled" in submit_buttons[0]
    assert "submit.textContent" not in html
    assert "동의하고 Instagram으로 계속하기" in html


def test_static_mobile_consent_css_matches_frozen_measurement_contract():
    html = _generated_html()

    back = _css_block(html, ".cl-consent-back")
    assert "gap: 8px;" in back
    assert "min-height: 44px;" in back
    assert "margin: 0 0 4px;" in back
    assert "font-size: 16px;" in back
    assert "font-weight: 400;" in back
    assert "letter-spacing: 0;" in back
    assert "line-height: 1.6;" in back
    assert "border-radius: 8px;" in back

    back_icon = _css_block(html, ".cl-consent-back .cl-consent-back-icon")
    assert "width: 16px;" in back_icon
    assert "height: 16px;" in back_icon

    back_icon_svg = _css_block(html, ".cl-consent-back .cl-consent-back-icon svg")
    assert "width: 16px;" in back_icon_svg
    assert "height: 16px;" in back_icon_svg

    back_text = _css_block(html, ".cl-consent-back .cl-consent-back-text")
    assert "font-size: 14px;" in back_text
    assert "font-weight: 400;" in back_text
    assert "line-height: 1.6;" in back_text

    row = _css_block(html, ".cl-consent-row")
    assert "min-height: 48px;" in row

    form = _css_block(html, ".cl-consent-form")
    assert "margin-top: 4px;" in form

    copy = _css_block(html, ".cl-consent-page .cl-consent-copy")
    assert "margin-top: 22px;" in copy

    label = _css_block(html, ".cl-consent-label")
    assert "min-height: 48px;" in label
    assert "gap: 8px;" in label
    assert "font-size: 14px;" in label
    assert "font-weight: 400;" in label
    assert "letter-spacing: 0;" in label
    assert "line-height: 1.54;" in label

    checkbox = _css_block(html, ".cl-consent-label input")
    assert "position: absolute;" in checkbox
    assert "width: 1px;" in checkbox
    assert "height: 1px;" in checkbox
    assert "clip-path: inset(50%);" in checkbox

    checkmark = _css_block(html, ".cl-consent-checkmark")
    assert "width: 16px;" in checkmark
    assert "height: 16px;" in checkmark
    assert "margin-top: 2.5px;" in checkmark
    assert "border: 1px solid rgba(125, 79, 222, 0.42);" in checkmark
    assert "border-radius: 4px;" in checkmark

    checked = _css_block(html, ".cl-consent-label input:checked + .cl-consent-checkmark")
    assert "background: #7d4fde;" in checked
    assert "border-color: #7d4fde;" in checked

    detail = _css_block(html, ".cl-consent-detail-link")
    assert "min-height: 44px;" in detail
    assert "font-size: 16px;" in detail
    assert "line-height: 1.52;" in detail

    submit = _css_block(html, ".cl-consent-submit")
    assert "min-height: 60px;" in submit
    assert "margin-top: 16px;" in submit
    assert "padding: 4px 12px;" in submit
    assert "font-size: 15px;" in submit
    assert "font-weight: 680;" in submit
    assert "line-height: 1.6;" in submit

    submit_text = _css_block(html, ".cl-consent-submit-text")
    assert "font-size: 14px;" in submit_text
    assert "font-weight: 400;" in submit_text
    assert "line-height: 22.4px;" in submit_text

    assert "padding-top: max(28px, env(safe-area-inset-top));" in html
    assert "padding: max(18px, env(safe-area-inset-top)) 0 var(--cl-consent-panel-bottom);" in html
    assert "font-size: 25px;\nline-height: 1.42;" in html
    assert "font-size: 14.5px;\nline-height: 1.86;" in html
    assert "font-size: 13.5px;" in html
    assert ".cl-login-page .cl-card-footer {\nmargin-top: auto;\npadding-top: 16px;" in html
    assert ".cl-login-page .cl-security-note {\nline-height: 1.6;" in html


def test_static_navigation_waits_for_click_and_keeps_history_state_in_sync():
    html = _generated_html()

    assert "document.addEventListener('pointerdown'" not in html
    assert "window.__clConsentShownAt" not in html
    assert "document.addEventListener('click'" in html
    assert (
        "show(action === 'show-consent' ? 'consent' : 'intro', false, "
        "action === 'show-intro')"
    ) in html
    assert "const params = clearQuery ? new URLSearchParams() : new URLSearchParams(location.search);" in html
    assert "currentStep = isConsent ? 'consent' : 'intro';" in html


def test_static_auth_error_view_matches_streamlit_early_error_contract():
    html = _generated_html()
    parser = _parse(html)
    error_view = html.split('<main class="cl-static-error-page"', 1)[1].split(
        "</main>", 1
    )[0]

    for message in (
        "권한 요청이 취소되었습니다.",
        "인증 코드가 없습니다. 다시 시도해 주세요.",
        "로그인 세션이 유효하지 않거나 만료되었습니다.",
        "로그인 동의 시간이 만료되었습니다. 다시 진행해 주세요.",
        "Preview 로그인 설정이 완료되지 않았습니다.",
        "동의 내역을 저장하지 못했습니다. 다시 시도해 주세요.",
        "로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        "로그인을 완료하지 못했습니다.",
    ):
        assert message in html

    assert '<main class="cl-static-error-page" data-view="error" hidden>' in html
    assert 'aria-label="사이드바 펼치기"' in html
    assert 'aria-label="뒤로 가기"' not in html
    assert 'd="m7 6 5 6-5 6"' in error_view
    assert 'd="m12 6 5 6-5 6"' in error_view
    assert 'd="M15 6 9 12l6 6"' not in error_view
    assert 'data-error-message role="alert"' in html
    assert "if (errorCode !== null) {" in html
    assert "if (code !== null) {" in html
    assert "showError(errorCode);" in html
    assert "return;" in html
    assert "ERROR_MESSAGES[code] || DEFAULT_ERROR_MESSAGE" in html

    retry_links = [
        link
        for link in parser.links
        if link.get("class") == "cl-static-error-retry"
    ]
    assert len(retry_links) == 1
    assert retry_links[0].get("href") == "/Login?step=consent"
    assert "다시 동의하고 연결하기" in html


def test_static_auth_error_geometry_matches_frozen_streamlit_screen():
    html = _generated_html()

    page = _css_block(html, ".cl-static-error-page")
    assert "min-height: 100vh;" in page
    assert "padding: 96px 16px 160px;" in page
    assert "background: #ffffff;" in page
    assert "color: rgb(38, 39, 48);" in page

    chrome = _css_block(html, ".cl-static-chrome-button")
    assert "width: 28px;" in chrome
    assert "height: 28px;" in chrome
    assert "background: transparent;" in chrome

    chrome_left = _css_block(html, ".cl-static-chrome-button--left")
    assert "top: 16px;" in chrome_left
    assert "left: 18px;" in chrome_left

    chrome_right = _css_block(html, ".cl-static-chrome-button--right")
    assert "top: 15.5px;" in chrome_right
    assert "right: 18px;" in chrome_right

    title = _css_block(html, ".cl-static-error-title")
    assert "padding: 20px 0 16px;" in title
    assert "font-size: 44px;" in title
    assert "font-weight: 700;" in title
    assert "line-height: 1.2;" in title

    alert = _css_block(html, ".cl-static-error-alert")
    assert "min-height: 56px;" in alert
    assert "padding: 16px;" in alert
    assert "border-radius: 8px;" in alert
    assert "background: rgba(255, 43, 43, 0.1);" in alert
    assert "color: #bd4043;" in alert
    assert "font-size: 16px;" in alert
    assert "line-height: 1.5;" in alert

    retry = _css_block(html, ".cl-static-error-retry")
    assert "min-height: 40px;" in retry
    assert "margin-top: 16px;" in retry
    assert "padding: 4px 12px;" in retry
    assert "border: 1px solid rgba(38, 39, 48, 0.2);" in retry
    assert "border-radius: 8px;" in retry
    assert "font-size: 14px;" in retry
    assert "line-height: 1.6;" in retry

    assert "@media (min-width: 961px)" in html
    assert "padding-right: 80px;" in html
    assert "padding-left: 80px;" in html


def test_static_policy_typography_matches_frozen_streamlit_computed_styles():
    html = _generated_html()

    modal = _css_block(html, ".cl-policy-modal")
    assert "color: rgb(38, 39, 48);" in modal
    assert "line-height: 1.6;" in modal
    assert "overflow-wrap: break-word;" in modal

    eyebrow = _css_block(html, ".cl-policy-modal__eyebrow")
    assert "font-size: 16px;" in eyebrow
    assert "line-height: 1.35;" in eyebrow
    assert "word-break: break-word;" in eyebrow

    title = _css_block(html, ".cl-policy-modal__title")
    assert "font-size: 16px;" in title
    assert "line-height: 1.42;" in title

    metadata = _css_block(html, ".cl-policy-modal__metadata")
    assert "margin: 0;" in metadata
    assert "font-size: 14.5px;" in metadata

    metadata_row = _css_block(html, ".cl-policy-modal__metadata-row")
    assert "margin: 0;" in metadata_row
    assert "padding: 9px 11px !important;" in metadata_row
    specific_metadata_row = _css_block(
        html,
        ".cl-login-page .cl-policy-modal__metadata-row",
    )
    assert "padding: 9px 11px !important;" in specific_metadata_row

    list_row = _css_block(html, ".cl-policy-modal__list-row")
    assert "margin: 0.2em 0 0.2em 1.15em;" in list_row
    assert "font-size: 14.5px;" in list_row
    assert "overflow-wrap: anywhere;" in list_row

    table_list = _css_block(html, ".cl-login-page .cl-policy-modal__table-list")
    assert "gap: 10px;" in table_list
    assert "margin: 10px 0 0;" in table_list
    table_row = _css_block(html, ".cl-policy-modal__table-row")
    assert "margin: 0.2em 0 0.2em 1.15em;" in table_row
    assert "padding: 0 0 0 0.3em;" in table_row

    note = _css_block(html, ".cl-policy-modal__note")
    assert "margin: 0;" in note
    assert "padding: 11px 12px !important;" in note
    assert "font-size: 14.5px;" in note
    specific_note = _css_block(html, ".cl-login-page .cl-policy-modal__note")
    assert "padding: 11px 12px !important;" in specific_note

    paragraph = _css_block(html, ".cl-policy-modal__paragraph")
    assert "margin: 0;" in paragraph
    assert "word-break: break-word;" in paragraph

    body = _css_block(html, ".cl-policy-modal__body")
    assert "word-break: keep-all;" in body
    intro_paragraph = _css_block(html, ".cl-policy-modal__intro p")
    assert "word-break: break-word;" in intro_paragraph
    section_number = _css_block(html, ".cl-policy-modal__section-number")
    assert "word-break: break-word;" in section_number
    summary_label = _css_block(html, ".cl-policy-modal__summary-label")
    assert "word-break: break-word;" in summary_label
