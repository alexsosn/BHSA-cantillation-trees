"""Read-only saved-graph/BHSA half-verse comparison acceptance tests (#18)."""

import csv
import json

import pytest

from bhsa_cantillation.boundaries import load_boundary_api
from bhsa_cantillation.cli import main
from bhsa_cantillation.graph import project_graph
from bhsa_cantillation.graph_tf import GraphTFCollector, materialize_graph_types
from bhsa_cantillation.half_verse import iter_half_verse_rows
from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.tree import build_tree, make_units


def source(name, slot, path, accent):
    return WordAlignment(
        SourceWord(
            source_id=name, text=name, consonants="א", morph_count=1,
            path=path, accent_name=accent,
            accent_type="disjunctive" if path is not None else "conjunctive",
            accent_catalogued=True, accent_rank=0, accent_final=None,
        ),
        (slot,),
    )


def save_halves(
    tmp_path, *, first_halves=((1, 2), (3, 4)), slots=(1, 2, 3, 4),
    alignment="exact",
):
    tf = pytest.importorskip("tf.fabric")
    core, target = tmp_path / "core", tmp_path / "derived"
    core.mkdir()
    max_slot = 6
    halves = list(first_halves) + [(5, 6)]
    half_nodes = list(range(max_slot + 1, max_slot + 1 + len(halves)))
    genesis, psalm = half_nodes[-1] + 1, half_nodes[-1] + 2
    types = {slot: "word" for slot in range(1, max_slot + 1)}
    types.update({node: "half_verse" for node in half_nodes})
    types[genesis] = types[psalm] = "verse"
    oslots = {node: set(span) for node, span in zip(half_nodes, halves, strict=True)}
    oslots[genesis] = {1, 2, 3, 4}
    oslots[psalm] = {5, 6}
    assert tf.Fabric(locations=str(core), silent="deep").save(
        nodeFeatures={"otype": types},
        edgeFeatures={"oslots": oslots},
        metaData={
            "otype": {"valueType": "str"}, "oslots": {"valueType": "str"},
            "otext": {"description": "half-verse comparison test BHSA warp"},
        },
        silent="deep",
    )
    collector = GraphTFCollector(base_max_node=psalm, max_slot=max_slot)
    alignments = [
        source("w1", slots[0], "1.0", "Tipcha"),
        source("w2", slots[1], "1", "Atnach"),
        source("w3", slots[2], "0.0", "Tipcha"),
        source("w4", slots[3], "0", "Sof Pasuq"),
    ]
    units = make_units(alignments)
    collector.append(
        genesis, project_graph("Gen.1.1", alignments, units, build_tree(units)), alignments
    )
    pair = [source("a", 5, None, "Munnach"), source("b", 6, "0", "Sof Pasuq")]
    singleton = make_units(pair)
    collector.append(
        psalm, project_graph("Ps.117.1", pair, singleton, build_tree(singleton)), pair
    )
    features = {
        "cantillation_system": {genesis: "prose", psalm: "poetic"},
        "cantillation_alignment": {genesis: alignment, psalm: "exact"},
    }
    materialize_graph_types(
        core, target, collector.finalize(),
        extra_node_features=features,
        extra_feature_meta={
            "cantillation_system": {"valueType": "str"},
            "cantillation_alignment": {"valueType": "str"},
        },
    )
    return target


def get_rows(tmp_path, **kwargs):
    return list(iter_half_verse_rows(load_boundary_api(save_halves(tmp_path, **kwargs))))


def test_exact_root_cut_matches_bhsa_half_verse_slots_and_singleton_is_explicit(tmp_path):
    gen, ps = get_rows(tmp_path)
    assert (gen["osis_id"], ps["osis_id"]) == ("Gen.1.1", "Ps.117.1")
    assert gen["status"] == "match"
    assert gen["half_verse_count"] == 2
    assert gen["root_cut_after_word_index"] == 2
    assert gen["root_left_bhsa_slots"] == "1-2"
    assert gen["first_half_bhsa_slots"] == "1-2"
    assert gen["root_overlap_slot_count"] == 0
    assert ps["status"] == "no_root_split"
    assert ps["root_cut_after_word_index"] is None
    assert ps["half_verse_count"] == 1


def test_clean_nonmatching_slot_cut_is_a_mismatch(tmp_path):
    gen, _ = get_rows(tmp_path, first_halves=((1,), (2, 3, 4)))
    assert gen["status"] == "mismatch"
    assert gen["root_cut_after_word_index"] == 2
    assert gen["root_left_bhsa_slots"] == "1-2"


@pytest.mark.parametrize(
    ("halves", "expected"),
    [
        (((1, 2, 3, 4),), "nonbinary_half_verse"),
        (((1,), (2,), (3, 4)), "nonbinary_half_verse"),
        ((), "missing_half_verse"),
        (((1, 2), (2, 3, 4)), "ambiguous_half_verse"),
    ],
)
def test_nonbinary_missing_and_overlapping_bhsa_halves_are_not_false_mismatches(
    tmp_path, halves, expected
):
    gen, _ = get_rows(tmp_path, first_halves=halves)
    assert gen["status"] == expected


def test_shared_root_bhsa_slot_is_inconclusive(tmp_path):
    gen, _ = get_rows(tmp_path, slots=(1, 2, 2, 4))
    assert gen["root_overlap_slot_count"] == 1
    assert gen["status"] == "ambiguous_root_slots"


def test_fuzzy_alignment_is_not_treated_as_proven_agreement(tmp_path):
    gen, _ = get_rows(tmp_path, alignment="fuzzy")
    assert gen["status"] == "fuzzy_alignment"


def test_selected_cli_is_order_independent_and_fixed_schema_for_jsonl_tsv(tmp_path, capsys):
    target = save_halves(tmp_path)
    jsonl = tmp_path / "halves.jsonl"
    assert main([
        "compare-halves", "--graph", str(target), "--verse", "Ps.117.1",
        "--verse", "Gen.1.1", "--verse", "Gen.1.1", "--output", str(jsonl),
    ]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["verses"] == 2
    assert summary["comparable"] == 1
    assert summary["status_counts"] == {"match": 1, "no_root_split": 1}
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    assert [row["osis_id"] for row in rows] == ["Gen.1.1", "Ps.117.1"]
    tsv = tmp_path / "halves.tsv"
    assert main([
        "compare-halves", "--graph", str(target), "--format", "tsv",
        "--verse", "Gen.1.1", "--output", str(tsv),
    ]) == 0
    with tsv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        data = list(reader)
    assert len(data) == 1
    assert list(data[0]) == list(rows[0])


def test_unknown_verse_preserves_existing_comparison_and_removes_temporary(tmp_path):
    target = save_halves(tmp_path)
    output = tmp_path / "prior.jsonl"
    output.write_bytes(b"known good\n")
    with pytest.raises(ValueError, match="Unknown OSIS"):
        main([
            "compare-halves", "--graph", str(target), "--output", str(output),
            "--verse", "Gen.1.1", "--verse", "Gen.1.999",
        ])
    assert output.read_bytes() == b"known good\n"
    assert not list(tmp_path.glob(".prior.jsonl.*.tmp"))
