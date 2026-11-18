"""RED acceptance gates for a clean-workspace researcher quickstart (#25)."""

import re
import shlex
from pathlib import Path

from bhsa_cantillation.cli import parser

BHSA_COMMIT = "4db00e2157915495e1a4d3d57e41223df24775da"
MORPHHB_COMMIT = "3d15126fb1ef74867fc1434be1942e837932691f"


def quickstart() -> str:
    readme = Path(__file__).resolve().parents[1] / "README.md"
    text = readme.read_text(encoding="utf-8")
    return text.split("## Researcher quickstart (pinned 2021 corpus)\n", 1)[1].split(
        "\n## Features", 1
    )[0]


def documented_command(command: str) -> list[str]:
    text = re.sub(r"\\\n[ \t]*", " ", quickstart())
    matches = re.findall(
        rf"^bhsa-cantillation {re.escape(command)}(?: [^\\n]*)?$",
        text,
        flags=re.MULTILINE,
    )
    assert len(matches) == 1, (command, matches)
    return shlex.split(matches[0])


def test_quickstart_pins_complete_source_inputs():
    text = quickstart()
    assert (
        "git clone --filter=blob:none --sparse "
        "https://github.com/ETCBC/bhsa.git inputs/bhsa"
    ) in text
    assert "git -C inputs/bhsa sparse-checkout set tf/2021" in text
    assert f"git -C inputs/bhsa checkout {BHSA_COMMIT}" in text
    assert (
        "git clone --filter=blob:none --sparse "
        "https://github.com/openscriptures/morphhb.git inputs/morphhb"
    ) in text
    assert (
        "git -C inputs/morphhb sparse-checkout set "
        "wlc structure/OshbVerse/Script"
    ) in text
    assert f"git -C inputs/morphhb checkout {MORPHHB_COMMIT}" in text
    assert "python -m pip install -e ." in text
    assert "Do not reuse a nonempty" in text


def test_quickstart_commands_match_live_parser_and_pinned_graph_paths():
    build = parser().parse_args(documented_command("build-graph")[1:])
    assert build.command == "build-graph"
    assert build.bhsa == Path("inputs/bhsa/tf/2021")
    assert build.module == Path("tf/2021")
    assert build.morphhb == Path("inputs/morphhb")
    assert build.output == Path("build/canonical-graph/2021")
    assert build.source_commit == MORPHHB_COMMIT

    syntax = parser().parse_args(documented_command("compare-syntax")[1:])
    assert syntax.command == "compare-syntax"
    assert syntax.graph == build.output
    assert syntax.verse == ["Gen.1.1"]
    assert syntax.format == "tsv"
    assert syntax.output == Path("build/genesis-1-1-syntax.tsv")

    halves = parser().parse_args(documented_command("compare-halves")[1:])
    assert halves.command == "compare-halves"
    assert halves.graph == build.output
    assert halves.verse == ["Gen.1.1"]
    assert halves.output == Path("build/genesis-1-1-halves.jsonl")


def test_quickstart_explains_researcher_decision_boundaries():
    text = quickstart()
    for key in (
        "bhsa_cut_after_slot", "cut_after_word_index", "slot_status",
        "ends_phrase", "phrase_nodes", "fuzzy_alignment",
    ):
        assert key in text
    assert "MorphHB" in text and "BHSA" in text
    assert "OSIS" in text


def test_documented_input_revisions_match_pinned_integration_workflow():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/canonical-graph.yml"
    ).read_text(encoding="utf-8")
    assert f"ref: {BHSA_COMMIT}" in workflow
    assert f"ref: {MORPHHB_COMMIT}" in workflow
    assert "path: inputs/bhsa" in workflow
    assert "path: inputs/morphhb" in workflow
    assert "sparse-checkout: tf/2021" in workflow
    assert "structure/OshbVerse/Script" in workflow
