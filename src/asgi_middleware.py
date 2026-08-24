"""ASGI middleware used to keep one-time OAuth codes out of app access logs."""

from starlette.types import ASGIApp, Receive, Scope, Send


class OAuthQuerySanitizerMiddleware:
    """Capture callback query params, then clear them from the shared ASGI scope.

    Uvicorn formats its access line after the response from the same scope. This
    keeps the one-time authorization code out of application access logs while
    still making the original query available to the callback handler.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http" and scope.get("path") == "/auth/callback":
            state = scope.setdefault("state", {})
            state["oauth_query_string"] = scope.get("query_string", b"")
            scope["query_string"] = b""
        await self.app(scope, receive, send)
