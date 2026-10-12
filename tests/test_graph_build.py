"""TDD contracts for a separate full BHSA+cantillation graph dataset."""

from pathlib import Path

import pytest

from bhsa_cantillation.cli import parser
from bhsa_cantillation.graph import project_graph
from bhsa_cantillation.build import FEATURE_META
from bhsa_cantillation.graph_build import (
    build_graph_dataset,
    check_graph_stats,
    required_graph_features,
)
from bhsa_cantillation.graph_tf import GraphTFCollector
from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.tree import build_tree, make_units


def test_cli_requires_separate_input_module_and_explicit_output():
    args = parser().parse_args(
        ["build-graph", "--bhsa", "/bhsa", "--module", "/module",
         "--morphhb", "/morphhb", "--output", "/derived"]
    )
    assert args.command == "build-graph"
    assert args.bhsa == Path("/bhsa")
    assert args.module == Path("/module")
    assert args.morphhb == Path("/morphhb")
    assert args.output == Path("/derived")


def test_graph_counts_derive_from_full_binary_shape():
    alignments = [
        WordAlignment(SourceWord(f"w{i}", str(i), "א", 1, path=str(i), accent_name="a"),
                      (i,))
        for i in range(1, 4)
    ]
    units = make_units(alignments)
    graph = project_graph("Gen.1.1", alignments, units, build_tree(units))
    collector = GraphTFCollector(base_max_node=100, max_slot=10)
    collector.append(80, graph, alignments)
    batch = collector.finalize()
    assert check_graph_stats(batch, verses=1, source_words=3, units=3) is None
    with pytest.raises(ValueError, match="count"):
        check_graph_stats(batch, verses=1, source_words=4, units=3)


def test_graph_build_never_overwrites_existing_dataset(tmp_path):
    bhsa = tmp_path / "bhsa"
    module = tmp_path / "module"
    morphhb = tmp_path / "morphhb"
    output = tmp_path / "derived"
    output.mkdir()
    (output / "otype.tf").write_text("existing", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        build_graph_dataset(bhsa, module, morphhb, output)


def test_build_graph_preloads_every_published_cantillation_feature_before_copy():
    loaded = set(required_graph_features())
    assert set(FEATURE_META).issubset(loaded)
    assert {"book", "chapter", "verse", "g_cons_utf8"} <= loaded
