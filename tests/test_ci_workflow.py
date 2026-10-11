"""Protect CI trigger coverage and superseded-run cancellation."""

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"


def load_workflow():
    from yaml import BaseLoader, load

    # BaseLoader keeps the GitHub Actions "on" key as a string.
    return load(WORKFLOW.read_text(encoding="utf-8"), Loader=BaseLoader)


def test_pull_requests_run_once_and_main_pushes_are_covered():
    workflow = load_workflow()
    # BaseLoader deliberately keeps the GitHub Actions "on" key as a string.
    events = workflow["on"]
    assert events["push"]["branches"] == ["main"]
    assert "pull_request" in events
    # No PR branch filter: stacked PRs and forks also need tests.
    assert events["pull_request"] in ("", None)


def test_superseded_pr_runs_do_not_cancel_other_pull_requests():
    workflow = load_workflow()
    concurrency = workflow["concurrency"]
    assert (
        concurrency["group"]
        == "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}"
    )
    assert concurrency["cancel-in-progress"] == "true"


def test_ci_keeps_lint_and_tests_as_required_job_steps():
    workflow = load_workflow()
    steps = workflow["jobs"]["test"]["steps"]
    commands = [step["run"] for step in steps if "run" in step]
    assert "python -m ruff check ." in commands
    assert "python -m pytest" in commands
