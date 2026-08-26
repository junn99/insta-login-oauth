"""Main Streamlit application entry point."""

import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler

from src.auth import hydrate_session_from_cookie, initialize_session_state
from src.config import config
from src.database import init_db
from src.ui.celeblife_login import render_login_page

# Page configuration
st.set_page_config(
    page_title="Instagram Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Check configuration before touching database/session-backed runtime state.
missing = config.validate_runtime()
preview_ui_only = config.is_vercel_preview() and bool(missing)

if preview_ui_only:
    render_login_page(
        oauth_url=None,
        back_url="/",
        privacy_url="/Privacy",
        oauth_disabled=False,
        continue_url="/Login?step=consent",
    )
    st.stop()

# Initialize database on app start
init_db()

# Initialize and restore browser session state
initialize_session_state()
hydrate_session_from_cookie()
if "scheduler_started" not in st.session_state:
    st.session_state.scheduler_started = False


def start_background_scheduler():
    """Start APScheduler for background jobs."""
    if st.session_state.scheduler_started:
        return

    from jobs.collect_insights import run_collection
    from jobs.refresh_tokens import run_token_refresh

    scheduler = BackgroundScheduler()

    # Collect insights every 6 hours
    scheduler.add_job(run_collection, "interval", hours=6, id="collect_insights")

    # Refresh tokens daily
    scheduler.add_job(run_token_refresh, "interval", days=1, id="refresh_tokens")

    scheduler.start()
    st.session_state.scheduler_started = True


# Start scheduler only on the existing non-Vercel runtime.
if not missing and config.SUPABASE_URL and config.scheduler_allowed():
    start_background_scheduler()


# Main page content
st.title("📊 인스타그램 인사이트 대시보드")

if missing:
    st.error(f"⚠️ 설정 누락: {', '.join(missing)}")
    st.info("필수 환경 변수를 설정해주세요.")
    st.stop()

# Show login status
if st.session_state.user_id:
    st.success(f"✅ @{st.session_state.instagram_username} 로그인됨")
    st.info("**대시보드**에서 인사이트를 확인하세요.")
    if config.IS_VERCEL:
        st.link_button("로그아웃", "/auth/logout")
    elif st.button("로그아웃"):
        st.session_state.user_id = None
        st.session_state.instagram_username = None
        st.rerun()
else:
    st.warning("시작하려면 인스타그램 비즈니스 계정으로 로그인해주세요.")
    st.info("사이드바의 **로그인** 페이지에서 계정을 연결하세요.")

# Quick stats section
st.markdown("---")
st.subheader("사용 가이드")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 1️⃣ 로그인")
    st.write("Instagram으로 비즈니스 계정을 연결하세요.")

with col2:
    st.markdown("### 2️⃣ 대시보드")
    st.write("참여도, 도달, 팔로워 추이를 확인하세요.")

with col3:
    st.markdown("### 3️⃣ 자동 수집")
    if config.IS_VERCEL:
        st.write("Preview에서는 자동 수집이 비활성화되어 있습니다.")
    else:
        st.write("인사이트는 6시간마다 자동으로 수집됩니다.")
