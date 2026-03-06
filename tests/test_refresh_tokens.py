from datetime import datetime, timedelta, timezone
from importlib import import_module, reload

from src.models import Token, User


def _load_refresh_module():
    module = import_module("jobs.refresh_tokens")
    return reload(module)


def test_run_token_refresh_refreshes_user_token(monkeypatch):
    refresh_module = _load_refresh_module()
    now = datetime.now(timezone.utc)
    user = User(
        id=1,
        instagram_id="ig-1",
        instagram_username="influencer",
        facebook_page_id=None,
    )
    token = Token(
        id=1,
        user_id=1,
        token_type="user",
        access_token="old-user-token",
        expires_at=now + timedelta(days=1),
    )
    saved_tokens = []

    monkeypatch.setattr(refresh_module, "init_db", lambda: None)
    monkeypatch.setattr(refresh_module, "get_expiring_tokens", lambda days: [(user, token)])
    monkeypatch.setattr(
        refresh_module,
        "refresh_long_lived_token",
        lambda access_token: {
            "access_token": "new-user-token",
            "expires_at": now + timedelta(days=60),
        },
    )

    def fake_save_token(user_id, token_type, access_token, expires_at=None):
        saved_tokens.append(
            {
                "user_id": user_id,
                "token_type": token_type,
                "access_token": access_token,
                "expires_at": expires_at,
            }
        )

    monkeypatch.setattr(refresh_module, "save_token", fake_save_token)

    result = refresh_module.run_token_refresh(days_before_expiry=7)

    assert result["refreshed"] == 1
    assert result["failed"] == 0
    assert len(saved_tokens) == 1
    assert saved_tokens[0]["token_type"] == "user"
    assert saved_tokens[0]["access_token"] == "new-user-token"


def test_run_token_refresh_handles_failure(monkeypatch):
    refresh_module = _load_refresh_module()
    now = datetime.now(timezone.utc)
    user = User(
        id=1,
        instagram_id="ig-1",
        instagram_username="influencer",
        facebook_page_id=None,
    )
    token = Token(
        id=1,
        user_id=1,
        token_type="user",
        access_token="old-user-token",
        expires_at=now + timedelta(days=1),
    )

    monkeypatch.setattr(refresh_module, "init_db", lambda: None)
    monkeypatch.setattr(refresh_module, "get_expiring_tokens", lambda days: [(user, token)])
    monkeypatch.setattr(
        refresh_module,
        "refresh_long_lived_token",
        lambda access_token: (_ for _ in ()).throw(Exception("API error")),
    )
    monkeypatch.setattr(refresh_module, "save_token", lambda **kwargs: None)

    result = refresh_module.run_token_refresh(days_before_expiry=7)

    assert result["refreshed"] == 0
    assert result["failed"] == 1
    assert len(result["errors"]) == 1
