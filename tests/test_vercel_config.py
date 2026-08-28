import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_preview_login_avoids_streamlit_asgi_function_bundle():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    vercel = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert 'streamlit>=1.61,<1.62' in pyproject
    assert "[tool.vercel]" not in pyproject
    assert 'entrypoint = "asgi:app"' not in pyproject
    assert (PROJECT_ROOT / ".python-version").read_text().strip() == "3.12"
    assert "$schema" in vercel


def test_vercel_preview_config_has_no_cron_or_production_redirects():
    vercel = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert "framework" not in vercel
    assert "functions" not in vercel
    assert "crons" not in vercel
    assert "redirects" not in vercel
    assert "builds" not in vercel


def test_vercel_rewrites_instagram_start_to_node_api():
    vercel = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert {
        "source": "/auth/instagram/start",
        "destination": "/api/instagram_start",
    } in vercel.get("rewrites", [])


def test_hidden_login_static_canary_is_public_static_asset_only():
    vercel = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))
    canary = PROJECT_ROOT / "public" / "__canary" / "login-static" / "index.html"
    source_paths = [
        item.get("source")
        for item in vercel.get("headers", [])
        if isinstance(item, dict)
    ]

    assert canary.exists()
    assert 'data-celeblife-static-canary="login-static"' in canary.read_text(
        encoding="utf-8"
    )
    assert "/__canary/login-static" in source_paths
    assert all(path not in {"/Login", "/auth/instagram/start"} for path in source_paths)


def test_login_static_asset_exists_with_same_document_consent_and_post_handoff():
    page = PROJECT_ROOT / "public" / "Login" / "index.html"
    html = page.read_text(encoding="utf-8")

    assert page.exists()
    assert 'data-celeblife-static-login="true"' in html
    assert 'href="/Login?step=consent"' in html
    assert 'action="/auth/instagram/start"' in html
    assert 'method="post"' in html
    assert 'name="age_confirmed"' in html
    assert 'name="terms_accepted"' in html
    assert 'name="privacy_accepted"' in html
    assert 'name="instagram_permissions_accepted"' in html
    assert "history[replace ? 'replaceState' : 'pushState']" in html
