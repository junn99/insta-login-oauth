"""CelebLife Privacy Policy page."""

from __future__ import annotations

import streamlit as st

from src.consent import PRIVACY_POLICY_BODY


st.set_page_config(page_title="Privacy Policy", page_icon="🔒", layout="centered")

st.markdown(PRIVACY_POLICY_BODY.replace("\n", "  \n"))
