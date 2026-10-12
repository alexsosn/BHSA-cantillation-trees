"""Consumer-facing boundary-export contract tests (issue #14).

Tests consume a saved Text-Fabric graph, never the in-memory graph projection.
"""

import csv
import json

import pytest

from bhsa_cantillation.boundaries import iter_boundary_rows, load_boundary_api
from bhsa_cantillation.cli import main
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


def four_units(slots=(1, 2, 3, 4), skew=None):
    alignments = [
        source("w1", slots[0], "1.0", "Tipcha"),
        source("w2", slots[1], "1", "Atnach"),
        source("w3", slots[2], "0.0", "Tipcha"),
        source("w4", slots[3], "0", "Sof Pasuq"),
    ]
    units = make_units(alignments)
    tree = build_tree(units)
    if skew is not None:
        leaves = [
            {
                "path": unit.path,
                "slots": [unit.slots[0], unit.slots[-1]],
                "text": unit.text,
                "accent": unit.accent_name,
            }
            for unit in units
        ]
        if skew == "left":
            tree = {
                "accent": units[2].accent_name,
                "children": [
                    {"accent": units[1].accent_name, "children": [
                        {"accent": units[0].accent_name, "children": leaves[:2]},
                        leaves[2],
                    ]},
                    leaves[3],
                ],
            }
        elif skew == "right":
            tree = {
                "accent": units[0].accent_name,
                "children": [
                    leaves[0],
                    {"accent": units[1].accent_name, "children": [
                        leaves[1],
                        {"accent": units[2].accent_name, "children": leaves[2:]},
                    ]},
                ],
            }
        else:
            raise ValueError(f"Unexpected skew: {skew}")
    return alignments, project_graph("Gen.1.1", alignments, units, tree)


@pytest.fixture
def graph_path(tmp_path):
    return save_graph(tmp_path)


def save_graph(tmp_path, *, slots=(1, 2, 3, 4), singleton=False, skew=None):
    tf = pytest.importorskip("tf.fabric")
    core = tmp_path / "core"
    target = tmp_path / "derived"
    core.mkdir()
    # In the singleton test, the additional verse still shares the same derived graph.
    max_slot = 6 if singleton else 4
    base_max = max_slot + (2 if singleton else 1)
    types = {slot: "word" for slot in range(1, max_slot + 1)}
    types[max_slot + 1] = "verse"
    oslots = {max_slot + 1: set(range(1, 5))}
    if singleton:
        types[base_max] = "verse"
        oslots[base_max] = {5, 6}
    assert tf.Fabric(locations=str(core), silent="deep").save(
        nodeFeatures={"otype": types},
        edgeFeatures={"oslots": oslots},
        metaData={
            "otype": {"valueType": "str"},
            "oslots": {"valueType": "str"},
            "otext": {"description": "boundary export test BHSA warp"},
        },
        silent="deep",
    )
    collector = GraphTFCollector(base_max_node=base_max, max_slot=max_slot)
    alignments, graph = four_units(slots, skew=skew)
    collector.append(max_slot + 1, graph, alignments)
    if singleton:
        pair = [source("a", 5, None, "Munnach"), source("b", 6, "0", "Sof Pasuq")]
        units = make_units(pair)
        collector.append(base_max, project_graph("Ps.117.1", pair, units, build_tree(units)), pair)
    features = {
        "cantillation_system": {max_slot + 1: "prose"},
        "cantillation_alignment": {max_slot + 1: "exact"},
    }
    if singleton:
        features["cantillation_system"][base_max] = "poetic"
        features["cantillation_alignment"][base_max] = "fuzzy"
    materialize_graph_types(
        core, target, collector.finalize(),
        extra_node_features=features,
        extra_feature_meta={
            "cantillation_system": {"valueType": "str"},
            "cantillation_alignment": {"valueType": "str"},
        },
    )
    return target


def test_export_canonical_textual_order_and_absolute_source_word_coordinates(graph_path):
    rows = list(iter_boundary_rows(load_boundary_api(graph_path)))
    assert len(rows) == 3
    assert [(r["first_unit"], r["last_unit"], r["cut_after_unit"]) for r in rows] == [
        (1, 2, 1), (1, 4, 2), (3, 4, 3)
    ]
    assert [r["cut_after_word_index"] for r in rows] == [1, 2, 3]
    assert [r["phrase_first_word_index"] for r in rows] == [1, 1, 3]
    assert [r["phrase_last_word_index"] for r in rows] == [2, 4, 4]
    assert [(r["first_child_word_count"], r["second_child_word_count"]) for r in rows] == [
        (1, 1), (2, 2), (1, 1)
    ]
    assert all(r["signed_split"] == 0 for r in rows)
    assert rows[1]["osis_id"] == "Gen.1.1"
    assert rows[1]["verse_node"] == 5
    assert rows[1]["system"] == "prose"
    assert rows[1]["alignment"] == "exact"
    assert rows[1]["cut_unit_id"] == "Gen.1.1#u2"
    assert rows[1]["cut_terminal_word_id"] == "w2"



@pytest.mark.parametrize(
    ("skew", "expected_split", "expected_first_words"),
    [("left", -0.5, 3), ("right", 0.5, 1)],
)
def test_asymmetric_split_sign_and_root_cut_source_coordinates(
    tmp_path, skew, expected_split, expected_first_words
):
    rows = list(iter_boundary_rows(load_boundary_api(save_graph(tmp_path, skew=skew))))
    assert len(rows) == 3
    root = next(row for row in rows if row["depth"] == 0)
    assert root["signed_split"] == expected_split
    assert root["first_child_word_count"] == expected_first_words
    assert root["cut_after_word_index"] == expected_first_words
    assert root["first_child_fraction"] == expected_first_words / 4


def test_shared_bhsa_slots_do_not_reduce_source_word_counts(tmp_path):
    rows = list(iter_boundary_rows(load_boundary_api(save_graph(tmp_path, slots=(1, 1, 2, 2)))))
    assert [r["cut_after_word_index"] for r in rows] == [1, 2, 3]
    root = next(row for row in rows if row["first_unit"] == 1 and row["last_unit"] == 4)
    assert root["phrase_word_count"] == 4
    assert root["bhsa_slot_count"] == 2
    assert (root["first_bhsa_slot"], root["last_bhsa_slot"]) == (1, 2)


def test_single_unit_verse_has_no_boundary(tmp_path):
    rows = list(iter_boundary_rows(load_boundary_api(save_graph(tmp_path, singleton=True))))
    assert len(rows) == 3
    assert {row["verse_node"] for row in rows} == {7}


def test_missing_cut_edge_is_rejected(graph_path):
    tf = pytest.importorskip("tf.fabric")
    assert tf.Fabric(locations=str(graph_path), silent="deep").save(
        edgeFeatures={"cant_cut_after": {7: {10}}},
        metaData={"cant_cut_after": {"valueType": "str"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="cut"):
        list(iter_boundary_rows(load_boundary_api(graph_path)))


def test_duplicate_parent_or_missing_child_is_rejected(graph_path):
    tf = pytest.importorskip("tf.fabric")
    # Overwrite saved edges with a malformed child assignment rather than forging a Python tree.
    assert tf.Fabric(locations=str(graph_path), silent="deep").save(
        edgeFeatures={"cant_parent": {9: {6: 1}, 10: {6: 1}, 11: {8: 1}, 12: {8: 2}}},
        metaData={"cant_parent": {"edgeValues": True, "valueType": "int"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="child|parent|branch"):
        list(iter_boundary_rows(load_boundary_api(graph_path)))



def test_forged_membership_cannot_change_source_word_provenance(graph_path):
    tf = pytest.importorskip("tf.fabric")
    # A source word moved to another unit while stored unit/phrase counts remain intact.
    assert tf.Fabric(locations=str(graph_path), silent="deep").save(
        edgeFeatures={"cant_member": {
            13: {9}, 14: {9}, 15: {11}, 16: {12},
        }},
        metaData={"cant_member": {"valueType": "str"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="member"):
        list(iter_boundary_rows(load_boundary_api(graph_path)))


def test_invalid_graph_keeps_prior_export_untouched(graph_path, tmp_path):
    tf = pytest.importorskip("tf.fabric")
    output = tmp_path / "prior.jsonl"
    output.write_bytes(b"prior valid export\\n")
    assert tf.Fabric(locations=str(graph_path), silent="deep").save(
        edgeFeatures={"cant_cut_after": {7: {10}}},
        metaData={"cant_cut_after": {"valueType": "str"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="cut"):
        main(["boundaries", "--graph", str(graph_path), "--output", str(output)])
    assert output.read_bytes() == b"prior valid export\\n"
    assert not list(tmp_path.glob(".prior.jsonl.*.tmp"))


def test_cross_verse_source_slot_forgery_is_rejected(tmp_path):
    tf = pytest.importorskip("tf.fabric")
    target = save_graph(tmp_path, singleton=True)
    saved = tf.Fabric(locations=str(target), silent="deep").load("cant_root", silent="deep")
    singleton_root = saved.E.cant_root.f(8)[0]
    slots = {node: set(group) for node, group in saved.E.oslots.items()}
    slots[singleton_root] = {1}  # BHSA slot 1 belongs to verse 7, not verse 8.
    types = {
        node: saved.F.otype.v(node)
        for node in range(1, saved.F.otype.maxNode + 1)
    }
    assert tf.Fabric(locations=str(target), silent="deep").save(
        nodeFeatures={"otype": types},
        edgeFeatures={"oslots": slots},
        metaData={"otype": {"valueType": "str"}, "oslots": {"valueType": "str"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="slot|member"):
        list(iter_boundary_rows(load_boundary_api(target)))


def test_cli_jsonl_tsv_are_deterministic_and_share_schema(graph_path, tmp_path):
    json_path = tmp_path / "boundaries.jsonl"
    tsv_path = tmp_path / "boundaries.tsv"
    args = [
        "boundaries", "--graph", str(graph_path), "--format", "jsonl",
        "--output", str(json_path),
    ]
    assert main(args) == 0
    original = json_path.read_bytes()
    args = [
        "boundaries", "--graph", str(graph_path), "--format", "jsonl",
        "--output", str(json_path),
    ]
    assert main(args) == 0
    assert json_path.read_bytes() == original
    parsed = [json.loads(line) for line in original.decode("utf-8").splitlines()]
    assert len(parsed) == 3
    args = [
        "boundaries", "--graph", str(graph_path), "--format", "tsv",
        "--output", str(tsv_path),
    ]
    assert main(args) == 0
    with tsv_path.open(encoding="utf-8", newline="") as f:
        tsv_rows = list(csv.DictReader(f, delimiter="\t"))
    assert len(tsv_rows) == 3
    assert list(tsv_rows[0]) == list(parsed[0])
    assert [int(row["cut_after_word_index"]) for row in tsv_rows] == [1, 2, 3]
