"""Contract tests for Phase 3 Text-Fabric graph node/edge materialization."""

from pathlib import Path

import pytest

from bhsa_cantillation.graph import project_graph
from bhsa_cantillation.graph_tf import GraphTFCollector, materialize_graph_types
from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.tree import build_tree, make_units


def source(name, slot, path, accent):
    return WordAlignment(
        SourceWord(
            source_id=name,
            text=name,
            consonants="א",
            morph_count=1,
            path=path,
            accent_name=accent,
            accent_type="disjunctive" if path is not None else "conjunctive",
            accent_catalogued=True,
            accent_rank=0,
            accent_final=None,
        ),
        (slot,),
    )


def sample(osis="Gen.1.1", slots=(1, 2, 3, 4)):
    alignments = [
        source("w1", slots[0], "1.0", "Tipcha"),
        source("w2", slots[1], "1", "Atnach"),
        source("w3", slots[2], "0.0", "Tipcha"),
        source("w4", slots[3], "0", "Sof Pasuq"),
    ]
    units = make_units(alignments)
    tree = build_tree(units)
    return alignments, project_graph(osis, alignments, units, tree)


def test_add_types_are_deterministic_appended_and_preserve_word_slot_overlaps():
    alignments, graph = sample()
    collector = GraphTFCollector(base_max_node=100, max_slot=10)
    collector.append(80, graph, alignments)
    batch = collector.finalize()

    assert batch.ranges == {
        "cant_phrase": (101, 103),
        "cant_unit": (104, 107),
        "cant_word": (108, 111),
    }
    assert batch.counts == {"cant_phrase": 3, "cant_unit": 4, "cant_word": 4}
    for node_type, spec in batch.add_types.items():
        assert spec["nodeFrom"] == 1
        assert spec["nodeTo"] == batch.counts[node_type]
        assert len(spec["nodeSlots"]) == batch.counts[node_type]
        assert all(slots and all(1 <= slot <= 10 for slot in slots) for slots in spec["nodeSlots"].values())
    assert batch.add_types["cant_word"]["nodeSlots"] == {
        1: {1}, 2: {2}, 3: {3}, 4: {4}
    }
    assert batch.add_types["cant_word"]["nodeFeatures"]["cant_word_id"][1] == "w1"
    assert "cant_word_catalog_final" not in batch.add_types["cant_word"]["nodeFeatures"]
    assert batch.edges["cant_root"] == {80: {102}}

    overlaps, shared = sample("Gen.99.1", (1, 1, 2, 2))
    second = GraphTFCollector(base_max_node=100, max_slot=10)
    second.append(80, shared, overlaps)
    other = second.finalize()
    assert other.add_types["cant_word"]["nodeSlots"] == {
        1: {1}, 2: {1}, 3: {2}, 4: {2}
    }
    assert other.add_types["cant_unit"]["nodeSlots"] == {
        1: {1}, 2: {1}, 3: {2}, 4: {2}
    }


def test_ordered_parents_cuts_terminals_members_and_root_edges():
    alignments, graph = sample()
    collector = GraphTFCollector(base_max_node=100, max_slot=10)
    collector.append(80, graph, alignments)
    batch = collector.finalize()
    assert batch.edges["cant_parent"] == {
        104: {101: 1},
        105: {102: 1},
        106: {103: 1},
        107: {103: 2},
        101: {102: 1},
        103: {102: 2},
    }
    assert batch.edges["cant_cut_after"] == {
        101: {104}, 102: {105}, 103: {106}
    }
    assert batch.edges["cant_terminal"] == {
        104: {108}, 105: {109}, 106: {110}, 107: {111}
    }
    assert batch.edges["cant_member"] == {
        108: {104}, 109: {105}, 110: {106}, 111: {107}
    }


def test_singleton_root_is_unit_and_root_cuts_absent():
    alignments = [source("a", 1, None, "Munnach"), source("b", 2, "0", "Sof Pasuq")]
    units = make_units(alignments)
    graph = project_graph("Ps.117.1", alignments, units, build_tree(units))
    collector = GraphTFCollector(base_max_node=100, max_slot=10)
    collector.append(80, graph, alignments)
    batch = collector.finalize()
    assert batch.counts == {"cant_unit": 1, "cant_word": 2}
    assert batch.edges["cant_root"] == {80: {101}}
    assert batch.edges["cant_parent"] == {}
    assert batch.edges["cant_cut_after"] == {}
    assert batch.edges["cant_terminal"] == {101: {103}}
    assert batch.edges["cant_member"] == {102: {101}, 103: {101}}


def test_verse_identity_duplicate_and_non_slot_ranges_are_rejected():
    alignments, graph = sample()
    collector = GraphTFCollector(base_max_node=100, max_slot=10)
    collector.append(80, graph, alignments)
    with pytest.raises(ValueError, match="duplicate verse"):
        collector.append(80, graph, alignments)
    with pytest.raises(ValueError, match="outside"):
        GraphTFCollector(base_max_node=100, max_slot=3).append(80, graph, alignments)
    with pytest.raises(ValueError, match="BHSA verse"):
        GraphTFCollector(base_max_node=100, max_slot=10).append(4, graph, alignments)


def test_rejects_mutated_source_identity_and_graph_shape():
    alignments, graph = sample()
    alignments[0].source.source_id = "forged"
    with pytest.raises(ValueError, match="source"):
        GraphTFCollector(base_max_node=100, max_slot=10).append(80, graph, alignments)
    alignments[0].source.source_id = "w1"
    graph.cuts[graph.root] = "forged"
    with pytest.raises(ValueError, match="cut"):
        GraphTFCollector(base_max_node=100, max_slot=10).append(80, graph, alignments)


def test_toy_text_fabric_modify_append_and_reloaded_cross_type_edges(tmp_path):
    tf = pytest.importorskip("tf.fabric")
    core = tmp_path / "core"
    target = tmp_path / "derived"
    core.mkdir()
    saved = tf.Fabric(locations=str(core), silent="deep").save(
        nodeFeatures={
            "otype": {1: "word", 2: "word", 3: "word", 4: "word", 5: "verse"},
        },
        edgeFeatures={"oslots": {5: {1, 2, 3, 4}}},
        metaData={"otype": {"valueType": "str"}, "oslots": {"valueType": "str"}},
        silent="deep",
    )
    assert saved
    alignments, graph = sample()
    collector = GraphTFCollector(base_max_node=5, max_slot=4)
    collector.append(5, graph, alignments)
    batch = collector.finalize()
    materialize_graph_types(core, target, batch)
    api = tf.Fabric(locations=str(target), silent="deep").load(
        "cant_word_id cant_unit_id cant_phrase_id cant_parent cant_terminal cant_cut_after "
        "cant_root cant_member",
        silent="deep",
    )
    assert api is not None
    assert api.F.otype.v(5) == "verse"
    assert api.F.otype.maxSlot == 4
    assert api.F.otype.maxNode == 16
    assert api.F.otype.s("cant_phrase") == (6, 7, 8)
    assert api.F.cant_word_id.v(13) == "w1"
    assert api.E.cant_parent.f(9) == ((6, 1),)
    assert api.E.cant_cut_after.f(7) == (10,)
    assert api.E.cant_terminal.f(12) == (16,)
    assert api.E.cant_member.f(16) == (12,)
    assert api.E.cant_root.f(5) == (7,)
