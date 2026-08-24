import time
from types import SimpleNamespace

from src.models import User
from src.session import COOKIE_NAME, create_session_token

SECRET = "s" * 32


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_hydrate_session_from_cookie_restores_streamlit_session(monkeypatch):
    import src.auth as auth_module

    session_state = FakeSessionState()
    token = create_session_token(42, SECRET, now=int(time.time()) - 60)

    monkeypatch.setattr(auth_module.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(
        auth_module,
        "get_user_by_id",
        lambda user_id: User(
            id=user_id,
            instagram_id="ig-123",
            instagram_username="celeb_user",
        ),
    )
    monkeypatch.setattr(
        auth_module,
        "st",
        SimpleNamespace(
            session_state=session_state,
            context=SimpleNamespace(cookies={COOKIE_NAME: token}),
        ),
    )

    assert auth_module.hydrate_session_from_cookie() is True
    assert session_state["user_id"] == 42
    assert session_state["instagram_username"] == "celeb_user"


def test_hydrate_session_from_cookie_rejects_invalid_cookie(monkeypatch):
    import src.auth as auth_module

    session_state = FakeSessionState()

    monkeypatch.setattr(auth_module.config, "SESSION_COOKIE_SECRET", SECRET, raising=False)
    monkeypatch.setattr(
        auth_module,
        "get_user_by_id",
        lambda user_id: (_ for _ in ()).throw(
            AssertionError("invalid cookie must not touch database")
        ),
    )
    monkeypatch.setattr(
        auth_module,
        "st",
        SimpleNamespace(
            session_state=session_state,
            context=SimpleNamespace(cookies={COOKIE_NAME: "invalid.cookie"}),
        ),
    )

    assert auth_module.hydrate_session_from_cookie() is False
    assert session_state["user_id"] is None
    assert session_state["instagram_username"] is None
