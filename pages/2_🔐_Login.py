"""Login page for Instagram OAuth."""

import logging
import time

import streamlit as st
from streamlit.errors import StreamlitAPIException

import src.oauth as oauth_module
from src.auth import hydrate_session_from_cookie
from src.config import config
from src.consent import CONSENT_ITEMS, ConsentAcceptance, all_required_accepted
from src.consent_binding import (
    CONSENT_BINDING_COOKIE_NAME,
    CONSENT_BINDING_MAX_AGE_SECONDS,
    CONSENT_BINDING_SESSION_EXP_KEY,
    CONSENT_BINDING_SESSION_KEY,
    create_binding_id,
    verify_binding_token,
)
from src.database import init_db
from src.oauth_callback_service import OnboardingPersistenceError, complete_instagram_login
from src.permission_badge import show_permission_badge
from src.ui.celeblife_login import (
    render_consent_page,
    render_instagram_preview_page,
    render_login_page,
)

logger = logging.getLogger(__name__)


def _login_error_code(exc: Exception) -> str:
    exc_code = getattr(exc, "code", None)
    if exc_code == "expired_state":
        return "expired_state"
    if exc_code == "invalid_state":
        return "invalid_state"
    if isinstance(exc, OnboardingPersistenceError):
        return "consent_persistence_failed"
    if isinstance(exc, ValueError) and str(exc) in {
        "missing_code",
        "configuration_error",
    }:
        return str(exc)
    return "callback_failed"


def _build_oauth_url(binding_id: str) -> str:
    return oauth_module.get_oauth_url(
        consent=ConsentAcceptance.accepted_now(),
        binding_id=binding_id,
    )


def _clear_consent_handoff() -> None:
    st.session_state.pop("cl_oauth_handoff_url", None)
    st.session_state.pop(CONSENT_BINDING_SESSION_KEY, None)
    st.session_state.pop(CONSENT_BINDING_SESSION_EXP_KEY, None)


def _cookie_binding_id() -> str | None:
    if not config.SESSION_COOKIE_SECRET:
        return None
    try:
        token = st.context.cookies.get(CONSENT_BINDING_COOKIE_NAME)
    except (AttributeError, StreamlitAPIException):
        logger.warning("Consent binding cookie is unavailable in this Streamlit runtime")
        return None
    return verify_binding_token(token, config.SESSION_COOKIE_SECRET)


def _session_binding_id() -> str:
    now = int(time.time())
    binding_id = st.session_state.get(CONSENT_BINDING_SESSION_KEY)
    expires_at = st.session_state.get(CONSENT_BINDING_SESSION_EXP_KEY)
    if (
        not isinstance(binding_id, str)
        or not isinstance(expires_at, int)
        or expires_at <= now
    ):
        binding_id = create_binding_id()
        st.session_state[CONSENT_BINDING_SESSION_KEY] = binding_id
        st.session_state[CONSENT_BINDING_SESSION_EXP_KEY] = (
            now + CONSENT_BINDING_MAX_AGE_SECONDS
        )
    return binding_id


def _current_binding_id() -> str | None:
    if config.IS_VERCEL:
        return _cookie_binding_id()
    return _session_binding_id()

st.set_page_config(
    page_title="Login",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

missing = config.validate_runtime()
preview_ui_only = config.is_vercel_preview() and bool(missing)

if preview_ui_only:
    if st.query_params.get("step") == "consent":
        render_consent_page(
            oauth_url=None,
            privacy_url="/Privacy",
            oauth_disabled=True,
            preview_next_url="/Login?step=instagram-preview",
        )
    elif st.query_params.get("step") == "instagram-preview":
        render_instagram_preview_page(back_url="/Login?step=consent")
    else:
        if (
            "code" in st.query_params
            or "error" in st.query_params
            or "auth_error" in st.query_params
        ):
            _clear_consent_handoff()
            st.query_params.clear()
        render_login_page(
            oauth_url=None,
            back_url="/",
            privacy_url="/Privacy",
            oauth_disabled=False,
            continue_url="/Login?step=consent",
        )
    st.stop()

if missing:
    st.title("🔐 인스타그램 로그인")
    st.error("앱 로그인 설정이 완료되지 않았습니다. 관리자에게 문의하세요.")
    st.query_params.clear()
    st.stop()

init_db()
hydrate_session_from_cookie()

# Check for OAuth callback
params = st.query_params

if config.IS_VERCEL and ("code" in params or "error" in params):
    _clear_consent_handoff()
    st.title("🔐 인스타그램 로그인")
    st.error("로그인을 완료하지 못했습니다. Instagram으로 다시 로그인해 주세요.")
    st.link_button(
        "다시 동의하고 연결하기",
        "/Login?step=consent",
        type="primary",
        use_container_width=True,
    )
    st.query_params.clear()
    st.stop()

if "auth_error" in params:
    _clear_consent_handoff()
    st.title("🔐 인스타그램 로그인")
    error_messages = {
        "access_denied": "권한 요청이 취소되었습니다.",
        "missing_code": "인증 코드가 없습니다. 다시 시도해 주세요.",
        "invalid_state": "로그인 세션이 유효하지 않거나 만료되었습니다.",
        "expired_state": "로그인 동의 시간이 만료되었습니다. 다시 진행해 주세요.",
        "configuration_error": "Preview 로그인 설정이 완료되지 않았습니다.",
        "consent_persistence_failed": "동의 내역을 저장하지 못했습니다. 다시 시도해 주세요.",
        "callback_failed": "로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    }
    error_code = params.get("auth_error", "")
    st.error(error_messages.get(error_code, "로그인을 완료하지 못했습니다."))
    st.link_button("다시 동의하고 연결하기", "/Login?step=consent", use_container_width=True)

elif "code" in params:
    st.title("🔐 인스타그램 로그인")

    code = params.get("code") or ""
    state = params.get("state") or ""

    with st.spinner("로그인 처리 중..."):
        try:
            login = complete_instagram_login(
                code,
                state,
                expected_binding_id=_current_binding_id(),
            )
            st.session_state.user_id = login.user_id
            st.session_state.instagram_username = login.instagram_username
            _clear_consent_handoff()

            st.success(f"✅ @{login.instagram_username} 로그인 성공!")
            show_permission_badge("instagram_business_basic")
            show_permission_badge("instagram_business_manage_insights")
            st.info("**대시보드**에서 인사이트를 확인하세요!")

        except Exception as exc:
            # OAuth exceptions can include request URLs with credentials. Keep
            # both the browser and server log sanitized.
            logger.error(
                "Legacy Streamlit OAuth callback failed (%s)", type(exc).__name__
            )
            error_code = _login_error_code(exc)
            if error_code == "expired_state":
                st.error("로그인 동의 시간이 만료되었습니다. 다시 진행해 주세요.")
            elif error_code == "invalid_state":
                st.error("세션이 유효하지 않습니다. 다시 진행해 주세요.")
            elif error_code == "configuration_error":
                st.error("Preview 로그인 설정이 완료되지 않았습니다.")
            elif error_code == "consent_persistence_failed":
                st.error("동의 내역을 저장하지 못했습니다. 다시 시도해 주세요.")
            else:
                st.error("로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
            _clear_consent_handoff()
            st.link_button("다시 동의하고 연결하기", "/Login?step=consent")

    # Clear query params
    st.query_params.clear()

elif "error" in params:
    _clear_consent_handoff()
    st.title("🔐 인스타그램 로그인")

    error = params.get("error")
    error_reason = params.get("error_reason", "")

    if error_reason == "user_denied":
        st.warning("권한 요청이 거부되었습니다.")
        st.markdown("""
        이 앱을 사용하려면 다음 권한이 필요합니다:
        - **instagram_business_basic** - 계정 기본 정보
        - **instagram_business_manage_insights** - 인사이트 데이터

        아래 버튼을 클릭하여 다시 시도하세요.
        """)
        st.link_button("다시 동의하고 연결하기", "/Login?step=consent", type="primary")
    else:
        st.error("로그인 실패: Instagram에서 로그인 요청을 완료하지 못했습니다.")
        st.info("문제가 계속되면 관리자에게 문의하세요.")
        st.link_button("다시 동의하고 연결하기", "/Login?step=consent", type="primary")

    st.query_params.clear()

else:
    if st.session_state.get("user_id"):
        st.success(f"@{st.session_state.instagram_username} 로그인됨")
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("대시보드로 이동", "/Dashboard", use_container_width=True)
        with col2:
            if config.IS_VERCEL:
                st.link_button("로그아웃", "/auth/logout", use_container_width=True)
            elif st.button("로그아웃", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.instagram_username = None
                st.rerun()
    else:
        if params.get("step") == "consent":
            consent_values = {
                item.key: bool(st.session_state.get(f"cl_consent_{item.key}"))
                for item in CONSENT_ITEMS
            }
            oauth_url = None
            if all_required_accepted(consent_values):
                oauth_url = st.session_state.get("cl_oauth_handoff_url")
                if not oauth_url:
                    binding_id = _current_binding_id()
                    if binding_id:
                        oauth_url = _build_oauth_url(binding_id)
                        st.session_state["cl_oauth_handoff_url"] = oauth_url
            render_consent_page(
                oauth_url=oauth_url,
                privacy_url="/Privacy",
                preview_next_url=None,
            )
        else:
            render_login_page(
                oauth_url=None,
                back_url="/",
                privacy_url="/Privacy",
                continue_url=(
                    "/auth/instagram/start"
                    if config.IS_VERCEL
                    else "/Login?step=consent"
                ),
            )
