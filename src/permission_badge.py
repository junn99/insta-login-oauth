"""Permission badge display helper for Meta App Review."""
import streamlit as st

PERMISSIONS = {
    "instagram_business_basic": {
        "label": "instagram_business_basic",
        "description": "Basic account info and profile data",
    },
    "instagram_business_manage_insights": {
        "label": "instagram_business_manage_insights",
        "description": "Account insights, analytics metrics, and audience demographics",
    },
}


def show_permission_badge(permission_key: str) -> None:
    """Display a permission badge caption."""
    perm = PERMISSIONS.get(permission_key)
    if perm:
        st.caption(f"🔑 Permission: `{perm['label']}` -- {perm['description']}")
