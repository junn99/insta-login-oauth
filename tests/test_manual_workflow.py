from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "manual-jobs.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_manual_workflow_has_no_schedule_trigger():
    workflow = _workflow_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "cron:" not in workflow


def test_manual_workflow_inputs_are_dormant_by_default():
    workflow = _workflow_text()

    assert "type: choice" in workflow
    assert "default: connectivity" in workflow
    for option in ("connectivity", "collect", "refresh"):
        assert f"- {option}" in workflow

    assert "type: boolean" in workflow
    assert "default: false" in workflow


def test_manual_workflow_db_jobs_require_execute_true():
    workflow = _workflow_text()

    assert "github.event.inputs.job == 'collect'" in workflow
    assert "github.event.inputs.job == 'refresh'" in workflow
    assert "github.event.inputs.execute == 'true'" in workflow
    assert "uv run collect-insights" in workflow
    assert "uv run refresh-tokens" in workflow


def test_manual_workflow_connectivity_runs_tests_and_db_jobs_are_serialized():
    workflow = _workflow_text()

    assert "permissions:\n  contents: read" in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
    assert "astral-sh/setup-uv@v10" in workflow
    assert 'python-version: "3.12"' in workflow
    assert "uv sync --locked" in workflow
    assert "uv run pytest -q" in workflow
    assert "environment: preview-db" in workflow
    assert "group: preview-db-manual-jobs" in workflow
    assert "cancel-in-progress: false" in workflow
