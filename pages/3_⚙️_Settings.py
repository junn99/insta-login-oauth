"""Settings page for account management."""

import streamlit as st
from datetime import datetime

from src.database import (
    init_db,
    get_user_by_id,
    get_user_token,
)
from src.oauth import refresh_long_lived_token
from src.database import save_token
from src.permission_badge import show_permission_badge

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
init_db()

st.title("⚙️ 설정")

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning(
        "로그인이 필요합니다. 로그인 페이지에서 인스타그램 계정을 먼저 연결해주세요."
    )
    st.stop()

selected_user = get_user_by_id(user_id)
if not selected_user:
    st.error("로그인된 사용자를 찾을 수 없습니다. 다시 로그인해주세요.")
    st.stop()
if selected_user.id is None:
    st.error("사용자 정보가 올바르지 않습니다. 다시 로그인해주세요.")
    st.stop()
selected_user_id = selected_user.id

# Account management
st.subheader("📱 연결된 계정")

with st.expander(f"@{selected_user.instagram_username}", expanded=True):
    show_permission_badge("instagram_business_basic")
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Instagram ID:** {selected_user.instagram_id}")
        st.write(
            f"**연결일:** {selected_user.created_at.strftime('%Y-%m-%d') if selected_user.created_at else 'N/A'}"
        )

    with col2:
        user_token = get_user_token(selected_user_id, "user")

        if user_token and user_token.expires_at:
            days_left = (user_token.expires_at - datetime.utcnow()).days
            if days_left > 14:
                st.success(f"✅ 토큰 유효: {days_left}일 남음")
            elif days_left > 0:
                st.warning(f"⚠️ 토큰 만료 예정: {days_left}일 남음")
            else:
                st.error("❌ 토큰 만료됨")
        else:
            st.info("토큰 상태 알 수 없음")

    if st.button("🔄 토큰 갱신", key=f"refresh_{selected_user_id}"):
        if user_token:
            try:
                with st.spinner("토큰 갱신 중..."):
                    new_token = refresh_long_lived_token(user_token.access_token)
                    save_token(
                        user_id=selected_user_id,
                        token_type="user",
                        access_token=new_token["access_token"],
                        expires_at=new_token["expires_at"],
                    )
                st.success(
                    f"토큰 갱신 완료! 새 만료일: {new_token['expires_at'].strftime('%Y-%m-%d')}"
                )
                st.rerun()
            except Exception as e:
                st.error(f"갱신 실패: {str(e)}")
        else:
            st.error("갱신할 토큰이 없습니다. 다시 로그인해주세요.")

st.markdown("---")

# Token expiration warnings
st.subheader("⏰ 토큰 상태")

user_token = get_user_token(selected_user_id, "user")
if user_token and user_token.expires_at:
    days_left = (user_token.expires_at - datetime.utcnow()).days
    if days_left <= 14:
        st.warning(f"⚠️ 토큰 만료 예정: {days_left}일 남음")
    else:
        st.success("✅ 토큰이 유효합니다")
else:
    st.warning("⚠️ 사용자 토큰 상태를 확인할 수 없습니다")

st.markdown("---")

# App info
st.subheader("ℹ️ 정보")
st.markdown("""
**인스타그램 인사이트 대시보드**

이 앱은 인스타그램 비즈니스 계정의 인사이트를 수집하고 표시합니다:
- 참여 지표 (노출, 도달, 프로필 조회)
- 팔로워 추이
- 오디언스 인구통계

**데이터 수집:**
- 인사이트는 6시간마다 자동으로 수집됩니다
- 토큰은 만료 전 자동으로 갱신됩니다

**개인정보:**
- 데이터는 비공개 데이터베이스에 안전하게 저장됩니다
- 비즈니스 인사이트만 접근하며, 개인 데이터에는 접근하지 않습니다
""")
