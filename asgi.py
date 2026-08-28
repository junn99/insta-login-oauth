"""Vercel Python entrypoint for the Streamlit ASGI application."""

from pathlib import Path

import streamlit as st
from starlette.middleware import Middleware
from starlette.routing import Route

from src.asgi_middleware import OAuthQuerySanitizerMiddleware
from src.asgi_routes import healthz, instagram_start, logout, oauth_callback

APP_SCRIPT = Path(__file__).with_name("app.py")

app = st.App(
    APP_SCRIPT,
    routes=[
        Route("/auth/callback", oauth_callback, methods=["GET"]),
        Route("/auth/instagram/start", instagram_start, methods=["GET", "POST"]),
        Route("/auth/logout", logout, methods=["GET"]),
        Route("/healthz", healthz, methods=["GET"]),
    ],
    middleware=[Middleware(OAuthQuerySanitizerMiddleware)],
)
