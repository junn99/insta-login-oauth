"""Login page for Instagram OAuth."""

import logging

import streamlit as st

from src.auth import hydrate_session_from_cookie
from src.config import config
from src.database import create_or_update_user, init_db, save_token
from src.oauth import complete_oauth_flow, get_oauth_url, validate_state
from src.permission_badge import show_permission_badge
from src.ui.celeblife_login import render_login_page

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Login",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

missing = config.validate_runtime()
preview_ui_only = config.is_vercel_preview() and bool(missing)

if preview_ui_only:
    render_login_page(
        oauth_url=None,
        back_url="/",
        privacy_url="/Privacy",
        oauth_disabled=True,
    )
    st.query_params.clear()
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
    st.title("🔐 인스타그램 로그인")
    st.error("로그인을 완료하지 못했습니다. Instagram으로 다시 로그인해 주세요.")
    st.link_button(
        "🔗 Instagram으로 다시 로그인",
        get_oauth_url(),
        type="primary",
        use_container_width=True,
    )
    st.query_params.clear()
    st.stop()

if "auth_error" in params:
    st.title("🔐 인스타그램 로그인")
    error_messages = {
        "access_denied": "권한 요청이 취소되었습니다.",
        "missing_code": "인증 코드가 없습니다. 다시 시도해 주세요.",
        "invalid_state": "로그인 세션이 유효하지 않거나 만료되었습니다.",
        "configuration_error": "Preview 로그인 설정이 완료되지 않았습니다.",
        "callback_failed": "로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    }
    error_code = params.get("auth_error", "")
    st.error(error_messages.get(error_code, "로그인을 완료하지 못했습니다."))
    st.link_button(
        "🔗 Instagram으로 다시 로그인",
        get_oauth_url(),
        type="primary",
        use_container_width=True,
    )

elif "code" in params:
    st.title("🔐 인스타그램 로그인")

    code = params.get("code") or ""
    state = params.get("state") or ""

    if not code:
        st.warning("인증 코드가 없습니다. 다시 시도해 주세요.")
        st.link_button(
            "🔗 Instagram으로 다시 로그인",
            get_oauth_url(),
            type="primary",
            use_container_width=True,
        )
        st.query_params.clear()
        st.stop()

    if not validate_state(state):
        st.error("세션이 유효하지 않거나 만료되었습니다. 다시 시도해 주세요. / Invalid or expired session.")
        st.link_button(
            "🔗 Instagram으로 다시 로그인",
            get_oauth_url(),
            type="primary",
            use_container_width=True,
        )
        st.query_params.clear()
        st.stop()

    with st.spinner("로그인 처리 중..."):
        try:
            result = complete_oauth_flow(code)

            if result["success"]:
                ig_account = result["instagram_account"]

                # Create or update user
                user = create_or_update_user(
                    instagram_id=ig_account.id,
                    instagram_username=ig_account.username,
                )
                if user.id is None:
                    raise ValueError("사용자 ID 생성에 실패했습니다.")

                # Save user token
                save_token(
                    user_id=user.id,
                    token_type="user",
                    access_token=result["user_token"],
                    expires_at=result["user_token_expires"],
                )

                # Update session state
                st.session_state.user_id = user.id
                st.session_state.instagram_username = user.instagram_username

                st.success(f"✅ @{ig_account.username} 로그인 성공!")
                show_permission_badge("instagram_business_basic")
                show_permission_badge("instagram_business_manage_insights")

                # Show account info
                st.markdown("### 계정 정보")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**사용자명:** @{ig_account.username}")
                    st.write(f"**이름:** {ig_account.name or '없음'}")
                with col2:
                    st.write(
                        f"**팔로워:** {ig_account.followers_count:,}"
                        if ig_account.followers_count
                        else "없음"
                    )
                    st.write(
                        f"**게시물:** {ig_account.media_count:,}"
                        if ig_account.media_count
                        else "없음"
                    )

                st.info("**대시보드**에서 인사이트를 확인하세요!")

        except Exception as exc:
            # OAuth exceptions can include request URLs with credentials. Keep
            # both the browser and server log sanitized.
            logger.error(
                "Legacy Streamlit OAuth callback failed (%s)", type(exc).__name__
            )
            st.error("로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    # Clear query params
    st.query_params.clear()

elif "error" in params:
    st.title("🔐 인스타그램 로그인")

    error = params.get("error")
    error_reason = params.get("error_reason", "")
    error_desc = params.get("error_description", "알 수 없는 오류")

    if error_reason == "user_denied":
        st.warning("권한 요청이 거부되었습니다.")
        st.markdown("""
        이 앱을 사용하려면 다음 권한이 필요합니다:
        - **instagram_business_basic** - 계정 기본 정보
        - **instagram_business_manage_insights** - 인사이트 데이터

        아래 버튼을 클릭하여 다시 시도하세요.
        """)
        retry_url = get_oauth_url()
        st.link_button("🔗 다시 시도", retry_url, type="primary")
    else:
        st.error(f"로그인 실패: {error_desc}")
        st.info("문제가 계속되면 관리자에게 문의하세요.")

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
        render_login_page(oauth_url=get_oauth_url(), back_url="/", privacy_url="/Privacy")
