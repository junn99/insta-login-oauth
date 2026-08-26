"""Shared Instagram OAuth callback completion service."""

from __future__ import annotations

from dataclasses import dataclass

from . import oauth as oauth_module
from .config import config


@dataclass(frozen=True)
class OnboardingResult:
    """Result needed after DB persistence completes."""

    user_id: int
    instagram_id: str
    instagram_username: str
    state_nonce: str


class OnboardingPersistenceError(RuntimeError):
    """The atomic user/consent/token write did not complete."""


def parse_state(state: str, *, expected_binding_id: str | None = None):
    """Parse OAuth state through the current oauth module binding."""
    return oauth_module.parse_state(state, expected_binding_id=expected_binding_id)


def complete_oauth_flow(code: str):
    """Exchange the OAuth code through the current oauth module binding."""
    return oauth_module.complete_oauth_flow(code)


def complete_instagram_login(
    code: str,
    state: str,
    *,
    expected_binding_id: str | None = None,
) -> OnboardingResult:
    """Validate state, exchange OAuth code, and persist onboarding atomically."""
    if not code:
        raise ValueError("missing_code")

    if config.validate_runtime():
        raise ValueError("configuration_error")

    parsed_state = parse_state(state, expected_binding_id=expected_binding_id)
    result = complete_oauth_flow(code)
    if not result.get("success"):
        raise ValueError("OAuth flow did not report success")

    account = result["instagram_account"]

    # Imported lazily so this module stays importable while the database RPC
    # wrapper is wired in a separate slice.
    from .database import complete_instagram_onboarding

    try:
        user_id = complete_instagram_onboarding(
            instagram_id=account.id,
            instagram_username=account.username,
            access_token=result["user_token"],
            expires_at=result["user_token_expires"],
            consent=parsed_state,
        )
    except Exception as exc:
        raise OnboardingPersistenceError("consent persistence failed") from exc
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise OnboardingPersistenceError("consent persistence returned invalid user id")

    return OnboardingResult(
        user_id=user_id,
        instagram_id=account.id,
        instagram_username=account.username,
        state_nonce=parsed_state.nonce,
    )


__all__ = [
    "ExpiredStateError",
    "OnboardingPersistenceError",
    "OnboardingResult",
    "complete_oauth_flow",
    "StateError",
    "parse_state",
    "complete_instagram_login",
]

ExpiredStateError = oauth_module.ExpiredStateError
StateError = oauth_module.StateError
