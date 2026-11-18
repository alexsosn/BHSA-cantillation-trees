"""RED exact-slot-set relation contract for original BHSA syntax (#21)."""

import csv
import json

import pytest

from bhsa_cantillation.boundaries import load_boundary_api
from bhsa_cantillation.cli import main
from bhsa_cantillation.syntax_relations import (
    classify_slot_relation,
    iter_syntax_relation_rows,
)
from test_syntax_boundary import save_syntax_graph


def test_exact_set_relation_partition():
    base = frozenset({1, 2, 4})
    assert classify_slot_relation(base, frozenset({1, 2, 4})) == "exact"
    assert classify_slot_relation(base, frozenset({1, 2, 3, 4})) == "inside"
    assert classify_slot_relation(base, frozenset({2, 4})) == "contains"
    assert classify_slot_relation(base, frozenset({2, 3, 5})) == "crossing"
    assert classify_slot_relation(base, frozenset({3})) == "disjoint"


def test_disjoint_interleaved_envelopes_are_not_crossing():
    # Real pinned BHSA Gen.1.7 clauses 427578/427579 demonstrate this.
    left = frozenset({101, 102, 103, 104, 105, 112, 113, 114, 115})
    right = frozenset({106, 107, 108, 109, 110, 111})
    assert min(left) < min(right) < max(right) < max(left)
    assert classify_slot_relation(left, right) == "disjoint"
    assert classify_slot_relation(right, left) == "disjoint"


def test_gapped_subset_must_not_be_classified_by_envelope():
    # An envelope-only classifier would call these 'inside'.
    assert classify_slot_relation(
        frozenset({1, 3}), frozenset({1, 2})
    ) == "crossing"
    assert classify_slot_relation(
        frozenset({2}), frozenset({1, 3})
    ) == "disjoint"


def test_empty_slotsets_are_inconclusive():
    assert classify_slot_relation(frozenset(), frozenset({1})) == "inconclusive"
    assert classify_slot_relation(frozenset({1}), frozenset()) == "inconclusive"


# Integration acceptance contract: the classifier must be usable on the saved
# BHSA + cantillation Text-Fabric graph, not just hand-picked slot sets.

def test_saved_tf_exact_relation_report_uses_original_ids_and_slot_sets(tmp_path):
    graph = save_syntax_graph(tmp_path)
    rows = list(iter_syntax_relation_rows(
        load_boundary_api(graph), verse_ids=["Gen.1.1"]
    ))
    assert len(rows) == 21  # three persisted phrases × seven eligible original nodes
    assert {row["osis_id"] for row in rows} == {"Gen.1.1"}
    assert {row["syntax_node"] for row in rows} == {8, 10, 11, 12, 13, 15, 16}
    assert not {9, 14} & {row["syntax_node"] for row in rows}

    relations = {(row["phrase_id"], row["syntax_node"]): row for row in rows}
    left = "Gen.1.1#p1-2"
    right = "Gen.1.1#p3-4"
    assert relations[left, 11]["relation"] == "exact"
    assert relations[left, 12]["relation"] == "contains"
    assert relations[left, 13]["relation"] == "crossing"
    assert relations[left, 13]["syntax_bhsa_slots"] == "1,4"  # gapped original
    assert relations[left, 16]["relation"] == "disjoint"
    assert relations[right, 13]["relation"] == "crossing"
    assert relations[right, 16]["relation"] == "exact"
    assert relations["Gen.1.1#p1-4", 8]["relation"] == "contains"
    assert relations[left, 11]["cantillation_bhsa_slots"] == "1-3"
    assert relations[left, 11]["slot_status"] == "comparable"
    assert all(row["cut_after_word_index"] >= 1 for row in rows)


def test_relation_cli_roundtrip_denominators_selection_and_atomic_output(tmp_path, capsys):
    graph = save_syntax_graph(tmp_path)
    output = tmp_path / "relations.jsonl"
    args = [
        "syntax-relations", "--graph", str(graph), "--verse", "Gen.1.1",
        "--verse", "Gen.1.1", "--output", str(output),
    ]
    assert main(args) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["cuts"] == 3
    assert stats["comparable"] == 3
    assert stats["comparisons"] == 21
    assert stats["status_counts"] == {"comparable": 3}
    assert stats["relation_counts"] == {
        "contains": 9, "crossing": 2, "disjoint": 6, "exact": 4
    }
    assert stats["candidates_selected_by_type"] == {
        "phrase": 3, "phrase_atom": 2, "clause_atom": 1, "clause": 1
    }
    assert stats["syntax_node_exclusions_global"]["phrase"]["cross_verse"] == 1
    assert stats["syntax_node_exclusions_global"]["clause"]["cross_verse"] == 1
    original = output.read_bytes()
    assert main(args) == 0
    capsys.readouterr()
    assert output.read_bytes() == original

    tsv = tmp_path / "relations.tsv"
    assert main([
        "syntax-relations", "--graph", str(graph), "--format", "tsv",
        "--verse", "Ps.117.1", "--verse", "Gen.1.1", "--output", str(tsv),
    ]) == 0
    capsys.readouterr()
    with tsv.open(encoding="utf-8", newline="") as handle:
        parsed = list(csv.DictReader(handle, delimiter="\t"))
    records = [json.loads(line) for line in original.decode().splitlines()]
    assert parsed == [
        {key: "" if value is None else str(value) for key, value in r.items()}
        for r in records
    ]


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({"alignment": "fuzzy"}, "fuzzy_alignment"),
        ({"source_slots": ((1, 2), (3,), (3,), (5,))}, "ambiguous_slots"),
        ({"source_slots": ((1, 2), (4,), (3,), (5,))}, "ambiguous_slots"),
    ],
)
def test_noncomparable_phrase_has_null_relation_not_false_disagreement(
    tmp_path, kwargs, status
):
    rows = list(iter_syntax_relation_rows(
        load_boundary_api(save_syntax_graph(tmp_path, **kwargs)),
        verse_ids=["Gen.1.1"],
    ))
    root = [r for r in rows if r["phrase_id"] == "Gen.1.1#p1-4"]
    assert len(root) == 1
    assert root[0]["slot_status"] == status
    assert root[0]["relation"] is None
    assert root[0]["syntax_node"] is None


@pytest.mark.parametrize("fmt", ["jsonl", "tsv"])
def test_known_singleton_and_unknown_selection_preserve_output(tmp_path, capsys, fmt):
    graph = save_syntax_graph(tmp_path)
    path = tmp_path / f"output.{fmt}"
    assert main([
        "syntax-relations", "--graph", str(graph), "--verse", "Ps.117.1",
        "--format", fmt, "--output", str(path),
    ]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["cuts"] == 0
    assert stats["comparisons"] == 0
    if fmt == "jsonl":
        assert path.read_bytes() == b""
    else:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            assert reader.fieldnames is not None
            assert list(reader) == []

    path.write_bytes(b"previous verified output\n")
    with pytest.raises(ValueError, match="Unknown OSIS"):
        main([
            "syntax-relations", "--graph", str(graph), "--verse", "Gen.1.999",
            "--format", fmt, "--output", str(path),
        ])
    assert path.read_bytes() == b"previous verified output\n"
    assert not list(tmp_path.glob(f".{path.name}.*.tmp"))


def test_incomplete_original_syntax_layer_must_fail_closed_atomically(tmp_path):
    graph = save_syntax_graph(tmp_path, missing_clause_layer=True)
    out = tmp_path / "existing.jsonl"
    out.write_bytes(b"verified\n")
    with pytest.raises(ValueError, match="Missing original BHSA syntax layer.*clause"):
        main([
            "syntax-relations", "--graph", str(graph),
            "--verse", "Gen.1.1", "--output", str(out),
        ])
    assert out.read_bytes() == b"verified\n"


def test_syntax_relations_requires_bounded_verse_selection(tmp_path):
    graph = save_syntax_graph(tmp_path)
    with pytest.raises(SystemExit) as error:
        main(["syntax-relations", "--graph", str(graph),
              "--output", str(tmp_path / "all.jsonl")])
    assert error.value.code == 2


def test_saved_tf_inside_is_strict_and_directional(tmp_path):
    # The same original clause contains both child cantillation phrases,
    # and equals their root; all other original nodes remain unchanged.
    api = load_boundary_api(save_syntax_graph(tmp_path, containing_clause=True))
    matches = {
        r["phrase_id"]: r["relation"]
        for r in iter_syntax_relation_rows(api, verse_ids=["Gen.1.1"])
        if r["syntax_node"] == 8
    }
    assert matches == {
        "Gen.1.1#p1-2": "inside",
        "Gen.1.1#p1-4": "exact",
        "Gen.1.1#p3-4": "inside",
    }


def test_corrupted_nonselected_saved_graph_rejects_atomic_relation_export(tmp_path):
    tf = pytest.importorskip("tf.fabric")
    graph = save_syntax_graph(tmp_path, psalm_split=True)
    api = load_boundary_api(graph)
    psalm_root = api.E.cant_root.f(18)[0]
    genesis_root = api.E.cant_root.f(17)[0]
    output = tmp_path / "prior.jsonl"
    output.write_bytes(b"prior validated report\n")
    # Corrupt the *unselected* Psalm's cut target, leaving selected Genesis
    # untouched. A consumer that validates only selected verses would accept.
    assert tf.Fabric(locations=str(graph), silent="deep").save(
        edgeFeatures={"cant_cut_after": {psalm_root: {genesis_root}}},
        metaData={"cant_cut_after": {"valueType": "str"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="cut|phrase"):
        main([
            "syntax-relations", "--graph", str(graph), "--verse", "Gen.1.1",
            "--output", str(output),
        ])
    assert output.read_bytes() == b"prior validated report\n"
    assert not list(tmp_path.glob(".prior.jsonl.*.tmp"))
