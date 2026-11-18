"""RED release publication contract: only publish after pinned corpus verification."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / ".github/workflows/publish-v0.1.0.yml"
GRAPH = ROOT / ".github/workflows/canonical-graph.yml"
NOTES = ROOT / "docs/RELEASE_NOTES_0.1.0.md"


def load_workflow(path):
    # PyYAML's default YAML 1.1 loader treats the literal 'on' as boolean.
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_publication_has_one_shot_main_trigger_and_manual_recovery():
    workflow = load_workflow(PUBLISH)
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["on"]["pull_request"]["paths"] == [
        ".github/workflows/publish-v0.1.0.yml",
    ]
    assert workflow["jobs"]["publish"]["if"] == "github.event_name != 'pull_request'"
    push = workflow["on"]["push"]
    assert push["branches"] == ["main"]
    assert push["paths"] == [".github/workflows/publish-v0.1.0.yml"]
    assert workflow["concurrency"]["cancel-in-progress"] == "false"


def test_publication_is_blocked_by_reused_full_pinned_graph_gate():
    workflow = load_workflow(PUBLISH)
    canonical = load_workflow(GRAPH)
    assert "workflow_call" in canonical["on"]
    # A called workflow sees its caller's github.workflow. Include that in
    # concurrency groups so the standalone PR run cannot cancel the caller.
    assert "github.workflow" in canonical["concurrency"]["group"]
    assert workflow["jobs"]["verify"]["uses"] == "./.github/workflows/canonical-graph.yml"
    publish = workflow["jobs"]["publish"]
    assert publish["needs"] == "verify"
    assert workflow["permissions"]["contents"] == "read"
    assert publish["permissions"]["contents"] == "write"


def test_release_is_version_pinned_fail_closed_and_has_package_assets():
    workflow = load_workflow(PUBLISH)
    steps = workflow["jobs"]["publish"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "python -m build" in commands
    assert "pip install ." in commands or "pip install dist/" in commands
    assert "gh release view v0.1.0" in commands
    assert "gh api" in commands and "git/ref/tags/v0.1.0" in commands
    assert "gh release create v0.1.0" in commands
    assert "--draft" in commands
    assert '--target "$GITHUB_SHA"' in commands
    assert "--notes-file docs/RELEASE_NOTES_0.1.0.md" in commands
    assert "dist/*.whl" in commands
    assert "dist/*.tar.gz" in commands
    assert "gh release edit v0.1.0 --draft=false" in commands
    assert "gh release view v0.1.0 --json" in commands
    assert "GH_TOKEN" in str(steps)


def test_published_notes_no_longer_claim_to_be_unpublished_candidate():
    notes = NOTES.read_text(encoding="utf-8")
    assert "# v0.1.0" in notes
    assert "23,213" in notes
    assert "Gen.1.7#p3-6" in notes
    assert "not yet a published" not in notes
    assert "release candidate, not" not in notes
    assert "not evidence that a GitHub tag" not in notes


def test_published_notes_link_to_versioned_readme_and_preserve_source_credit():
    notes = NOTES.read_text(encoding="utf-8")
    assert (
        "https://github.com/alexsosn/BHSA-cantillation-trees/"
        "blob/v0.1.0/README.md#researcher-quickstart-pinned-2021-corpus"
    ) in notes
    assert "CC BY 4.0" in notes
    assert "Open Scriptures Hebrew Bible" in notes
    assert "NOTICE" in notes
