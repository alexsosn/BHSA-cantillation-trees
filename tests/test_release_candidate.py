"""RED contract for a truthful, reproducible first researcher release (#27)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "docs" / "RELEASE_NOTES_0.1.0.md"


def release_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_release_notes_exist_and_match_package_and_citation_metadata():
    version = release_version()
    assert version == "0.1.0"
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"version: {version}" in citation
    assert "cantillation graph" in citation.lower()
    assert "syntax" in citation.lower()
    assert NOTES.is_file()
    notes = NOTES.read_text(encoding="utf-8")
    assert f"v{version}" in notes
    assert "candidate" in notes.lower()
    assert "23,213" in notes
    assert "142,534" in notes
    assert "Gen.1.7#p3-6" in notes
    assert "651638" in notes


def test_release_notes_state_supported_workflows_and_known_limits():
    notes = NOTES.read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/RELEASE_NOTES_0.1.0.md" in readme
    for command in (
        "build-graph", "boundaries", "compare-halves",
        "compare-syntax", "syntax-relations",
    ):
        assert command in notes
    for phrase in (
        "fuzzy", "inconclusive", "original BHSA", "MorphHB",
        "de Hoop", "Park", "not implemented",
    ):
        assert phrase in notes
    # No promise that the derived full graph ships inside the lightweight module.
    assert "generated locally" in notes.lower()


def test_ci_checks_noneditable_install_and_public_cli_help():
    workflow = (ROOT / ".github/workflows/test.yml").read_text(encoding="utf-8")
    assert "python -m venv" in workflow
    assert " -m pip install ." in workflow
    assert "bhsa-cantillation --help" in workflow
    for command in (
        "build-graph", "boundaries", "compare-halves",
        "compare-syntax", "syntax-relations",
    ):
        assert f"bhsa-cantillation {command} --help" in workflow
