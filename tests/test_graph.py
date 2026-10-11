"""TDD contracts for canonical MorphHB cantillation graph projection."""

import pytest

from bhsa_cantillation.graph import project_graph, reconstruct_tree
from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.tree import build_tree, make_units


def aligned(identifier: str, slot: int, path: str | None, accent: str) -> WordAlignment:
    word = SourceWord(
        source_id=identifier,
        text=identifier,
        consonants="א",
        morph_count=1,
        path=path,
        accent_name=accent,
        accent_type="disjunctive" if path is not None else "conjunctive",
    )
    return WordAlignment(word, (slot,))


def genesis_fixture():
    alignments = [
        aligned("g1", 1, "1.0", "Tipcha"),
        aligned("g2", 2, None, "Munnach"),
        aligned("g3", 3, "1", "Atnach"),
        aligned("g4", 4, None, "Merkha"),
        aligned("g5", 5, "0.0", "Tipcha"),
        aligned("g6", 6, None, "Merkha"),
        aligned("g7", 7, "0", "Sof Pasuq"),
    ]
    units = make_units(alignments)
    return alignments, units, build_tree(units)


def test_genesis_graph_is_binary_valued_ordered_and_roundtrips():
    alignments, units, tree = genesis_fixture()
    graph = project_graph("Gen.1.1", alignments, units, tree)
    assert len(graph.words) == 7
    assert len(graph.units) == 4
    assert len(graph.phrases) == 3
    assert len(graph.parents) == 6
    assert len(graph.cuts) == 3
    assert len(graph.terminals) == 4
    assert graph.root == "Gen.1.1#p1-4"
    assert graph.phrases[graph.root].slots == (1, 2, 3, 4, 5, 6, 7)
    assert graph.phrases[graph.root].accent == "Atnach"
    assert graph.parents["Gen.1.1#p1-2"] == (graph.root, 1)
    assert graph.parents["Gen.1.1#p3-4"] == (graph.root, 2)
    assert graph.cuts[graph.root] == "Gen.1.1#u2"
    assert graph.terminals["Gen.1.1#u2"] == "g3"
    assert graph.units["Gen.1.1#u2"].source_ids == ("g2", "g3")
    assert reconstruct_tree(graph) == tree


def test_one_unit_verse_root_is_its_unit_with_no_phrase():
    alignments = [aligned("w1", 5, None, "Munnach"), aligned("w2", 6, "0", "Sof Pasuq")]
    units = make_units(alignments)
    tree = build_tree(units)
    graph = project_graph("Ps.117.1", alignments, units, tree)
    assert graph.root == "Ps.117.1#u1"
    assert not graph.phrases
    assert not graph.parents
    assert not graph.cuts
    assert graph.terminals == {"Ps.117.1#u1": "w2"}
    assert reconstruct_tree(graph) == tree


def test_shared_slot_keeps_distinct_words_and_units_with_overlapping_oslots():
    alignments = [aligned("w1", 42, "1", "Atnach"), aligned("w2", 42, "0", "Sof Pasuq")]
    units = make_units(alignments)
    tree = build_tree(units)
    graph = project_graph("Gen.99.1", alignments, units, tree)
    assert graph.words["w1"].slots == (42,)
    assert graph.words["w2"].slots == (42,)
    assert graph.units["Gen.99.1#u1"].slots == (42,)
    assert graph.units["Gen.99.1#u2"].slots == (42,)
    assert graph.phrases[graph.root].slots == (42,)
    assert graph.parents["Gen.99.1#u1"] == (graph.root, 1)
    assert graph.parents["Gen.99.1#u2"] == (graph.root, 2)
    assert reconstruct_tree(graph) == tree


def test_duplicate_or_missing_source_word_identity_is_rejected():
    alignments, units, tree = genesis_fixture()
    alignments[0].source.source_id = "g2"
    with pytest.raises(ValueError, match="duplicate"):
        project_graph("Gen.1.1", alignments, units, tree)
    alignments[0].source.source_id = ""
    with pytest.raises(ValueError, match="source"):
        project_graph("Gen.1.1", alignments, units, tree)


def test_tree_leaf_mismatch_and_unit_order_mismatch_are_rejected():
    alignments, units, tree = genesis_fixture()
    malformed = {"path": "BAD", "slots": [1, 1], "text": "g1", "accent": "Tipcha"}
    with pytest.raises(ValueError, match="leaf"):
        project_graph("Gen.1.1", alignments, units, malformed)
    with pytest.raises(ValueError, match="unit"):
        project_graph("Gen.1.1", alignments, list(reversed(units)), tree)


def test_split_accent_mismatch_cannot_silently_enter_graph():
    alignments, units, tree = genesis_fixture()
    tree["accent"] = "NOT_ATNACH"
    with pytest.raises(ValueError, match="cut"):
        project_graph("Gen.1.1", alignments, units, tree)


def test_nonbinary_internal_node_is_rejected():
    alignments, units, tree = genesis_fixture()
    tree["children"] = [tree["children"][0]]
    with pytest.raises(ValueError, match="binary"):
        project_graph("Gen.1.1", alignments, units, tree)
