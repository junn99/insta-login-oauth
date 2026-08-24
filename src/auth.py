"""Streamlit-side restoration of the signed browser session."""

import logging

import streamlit as st
from streamlit.errors import StreamlitAPIException

from .config import config
from .database import get_user_by_id
from .session import COOKIE_NAME, verify_session_token

logger = logging.getLogger(__name__)


def initialize_session_state() -> None:
    """Create the authentication keys expected by every page."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "instagram_username" not in st.session_state:
        st.session_state.instagram_username = None


def hydrate_session_from_cookie() -> bool:
    """Restore Streamlit session state from a valid host-only signed cookie."""
    initialize_session_state()
    if st.session_state.user_id:
        return True
    if not config.SESSION_COOKIE_SECRET:
        return False

    try:
        token = st.context.cookies.get(COOKIE_NAME)
    except (AttributeError, StreamlitAPIException):
        logger.warning("Browser cookies are unavailable in this Streamlit runtime")
        return False

    if not token:
        return False

    payload = verify_session_token(token, config.SESSION_COOKIE_SECRET)
    if payload is None:
        return False

    try:
        user = get_user_by_id(payload.user_id)
    except Exception as exc:  # noqa: BLE001 - Supabase SDK exception hierarchy varies.
        logger.warning(
            "Signed session could not be resolved to a database user (%s)",
            type(exc).__name__,
        )
        return False

    if not user or user.id is None:
        return False

    st.session_state.user_id = user.id
    st.session_state.instagram_username = user.instagram_username
    return True
