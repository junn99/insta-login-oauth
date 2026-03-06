"""Live Insights - Real-time API demonstration for Meta App Review."""

import streamlit as st
import pandas as pd

from src.database import init_db, get_user_by_id, get_user_token
from src.instagram_api import InstagramAPI, InstagramAPIError
from src.permission_badge import show_permission_badge

st.set_page_config(page_title="Live Insights", page_icon="🔍", layout="wide")
init_db()

st.title("🔍 실시간 인사이트 / Live Insights")
st.info(
    "This page demonstrates live Instagram Graph API calls using the granted permissions."
)

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

user_token = get_user_token(selected_user_id, "user")
if not user_token:
    st.error("유효한 토큰이 없습니다. 다시 로그인해주세요.")
    st.stop()

api = InstagramAPI(user_token.access_token, selected_user.instagram_id)

st.markdown("---")

# Section 1: Profile Information (instagram_business_basic)
st.subheader("1. 프로필 정보 / Profile Information")
show_permission_badge("instagram_business_basic")
try:
    info = api.get_account_info()
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**사용자명 / Username:** @{info.get('username', 'N/A')}")
        st.write(f"**이름 / Name:** {info.get('name', 'N/A')}")
        st.write(f"**소개 / Biography:** {info.get('biography', 'N/A')}")
    with col2:
        st.metric("팔로워 / Followers", f"{info.get('followers_count', 0):,}")
        st.metric("팔로잉 / Following", f"{info.get('follows_count', 0):,}")
        st.metric("게시물 / Posts", f"{info.get('media_count', 0):,}")
    with st.expander("API Details"):
        st.code(
            f"GET /{selected_user.instagram_id}?fields=id,username,name,profile_picture_url,followers_count,follows_count,media_count,biography"
        )
except InstagramAPIError as e:
    st.error(f"API Error: {e}")

st.markdown("---")

# Section 2: Business Insights (instagram_business_manage_insights)
st.subheader("2. 비즈니스 인사이트 / Business Insights")
show_permission_badge("instagram_business_manage_insights")
try:
    insights = api.get_insights(period="day")
    if insights:
        df = pd.DataFrame(insights)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("현재 사용 가능한 인사이트 데이터가 없습니다.")
    with st.expander("API Details"):
        st.code(
            f"GET /{selected_user.instagram_id}/insights?metric=impressions,reach,profile_views,follower_count&period=day&metric_type=total_value"
        )
except InstagramAPIError as e:
    st.error(f"API Error: {e}")

st.markdown("---")

# Section 3: Audience Demographics (instagram_business_manage_insights)
st.subheader("3. 오디언스 인구통계 / Audience Demographics")
show_permission_badge("instagram_business_manage_insights")
try:
    audience = api.get_audience_data()
    if audience:
        for key, data in audience.items():
            st.write(f"**{key}:**")
            if data:
                df = pd.DataFrame(list(data.items()), columns=["Category", "Count"])
                df = df.nlargest(10, "Count")
                st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("오디언스 인구통계 데이터는 팔로워 100명 이상일 때 제공됩니다. / Audience demographics require 100+ followers.")
    with st.expander("API Details"):
        st.code(
            f"GET /{selected_user.instagram_id}/insights?metric=follower_demographics&period=lifetime&metric_type=total_value"
        )
except InstagramAPIError as e:
    st.error(f"API Error: {e}")
