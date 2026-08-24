import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_uses_streamlit_asgi_entrypoint_and_hobby_duration():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    vercel = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert 'streamlit>=1.61,<1.62' in pyproject
    assert 'entrypoint = "asgi:app"' in pyproject
    assert (PROJECT_ROOT / ".python-version").read_text().strip() == "3.12"
    assert vercel["functions"]["asgi.py"]["maxDuration"] == 300
    assert "pages/**" in vercel["functions"]["asgi.py"]["includeFiles"]
    assert "assets/**" in vercel["functions"]["asgi.py"]["includeFiles"]


def test_vercel_preview_config_has_no_cron_or_production_redirects():
    vercel = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert "crons" not in vercel
    assert "redirects" not in vercel
    assert "builds" not in vercel
