"""RED saved-TF acceptance tests for BHSA syntax/end-cut comparison (#21)."""

import csv
import json

import pytest

from bhsa_cantillation.boundaries import load_boundary_api
from bhsa_cantillation.cli import main
from bhsa_cantillation.graph import project_graph
from bhsa_cantillation.graph_tf import GraphTFCollector, materialize_graph_types
from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.syntax_boundary import iter_syntax_boundary_rows
from bhsa_cantillation.tree import build_tree, make_units


def source(name, slots, path, accent):
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
        tuple(slots),
    )


def save_syntax_graph(
    tmp_path, *, alignment="exact", source_slots=((1, 2), (3,), (4,), (5,)),
    psalm_split=False, missing_clause_layer=False, containing_clause=False,
):
    tf = pytest.importorskip("tf.fabric")
    core, derived = tmp_path / "core", tmp_path / "derived"
    core.mkdir()
    # Original BHSA IDs remain fixed; nodes 9 and 14 intentionally span verses.
    types = {
        **{n: "word" for n in range(1, 8)},
        8: "clause", 9: "clause",
        10: "clause_atom",
        11: "phrase", 12: "phrase", 13: "phrase", 14: "phrase",
        15: "phrase_atom", 16: "phrase_atom",
        17: "verse", 18: "verse",
    }
    if missing_clause_layer:
        # Preserve original numeric IDs but remove the required 'clause' type
        # from the BHSA warp. Treating this as zero matches is unsound.
        types[8] = types[9] = "clause_atom"
    spans = {
        8: ({1, 2, 3, 4, 5} if containing_clause else {1, 2, 3}), 9: {5, 6},
        10: {1, 2, 3},
        11: {1, 2, 3}, 12: {3}, 13: {1, 4}, 14: {5, 6},
        15: {1, 2}, 16: {4, 5},
        17: {1, 2, 3, 4, 5}, 18: {6, 7},
    }
    assert tf.Fabric(locations=str(core), silent="deep").save(
        nodeFeatures={"otype": types},
        edgeFeatures={"oslots": spans},
        metaData={
            "otype": {"valueType": "str"},
            "oslots": {"valueType": "str"},
            "otext": {"description": "syntactic cut comparison test"},
        },
        silent="deep",
    )
    collector = GraphTFCollector(base_max_node=18, max_slot=7)
    alignments = [
        source("w1", source_slots[0], "1.0", "Tipcha"),
        source("w2", source_slots[1], "1", "Atnach"),
        source("w3", source_slots[2], "0.0", "Tipcha"),
        source("w4", source_slots[3], "0", "Sof Pasuq"),
    ]
    units = make_units(alignments)
    collector.append(
        17, project_graph("Gen.1.1", alignments, units, build_tree(units)), alignments
    )
    singleton_words = [
        source("a", (6,), "1" if psalm_split else None,
               "Atnach" if psalm_split else "Munnach"),
        source("b", (7,), "0", "Sof Pasuq"),
    ]
    singleton_units = make_units(singleton_words)
    collector.append(
        18,
        project_graph(
            "Ps.117.1", singleton_words, singleton_units, build_tree(singleton_units)
        ),
        singleton_words,
    )
    materialize_graph_types(
        core, derived, collector.finalize(),
        extra_node_features={
            "cantillation_system": {17: "prose", 18: "poetic"},
            "cantillation_alignment": {17: alignment, 18: "exact"},
        },
        extra_feature_meta={
            "cantillation_system": {"valueType": "str"},
            "cantillation_alignment": {"valueType": "str"},
        },
    )
    return derived


def get_rows(tmp_path, **kwargs):
    api = load_boundary_api(save_syntax_graph(tmp_path, **kwargs))
    return list(iter_syntax_boundary_rows(api))


def test_exact_cut_coincidence_uses_slot_not_source_word_index(tmp_path):
    rows = get_rows(tmp_path)
    assert len(rows) == 3
    root = next(row for row in rows if row["depth"] == 0)
    assert root["osis_id"] == "Gen.1.1"
    assert root["cut_after_word_index"] == 2
    assert root["bhsa_cut_after_slot"] == 3  # one source word spans slots 1-2
    assert root["slot_status"] == "comparable"
    assert root["ends_phrase"] is True
    assert root["phrase_nodes"] == "11;12"  # two syntax nodes share the same end slot
    assert root["ends_phrase_atom"] is False
    assert root["ends_clause_atom"] is True
    assert root["clause_atom_nodes"] == "10"
    assert root["ends_clause"] is True
    assert root["clause_nodes"] == "8"

    by_word_index = {row["cut_after_word_index"]: row for row in rows}
    assert by_word_index[1]["bhsa_cut_after_slot"] == 2
    assert by_word_index[1]["ends_phrase_atom"] is True
    assert by_word_index[1]["phrase_atom_nodes"] == "15"
    assert by_word_index[3]["bhsa_cut_after_slot"] == 4
    assert by_word_index[3]["ends_phrase"] is True
    assert by_word_index[3]["phrase_nodes"] == "13"  # gapped but last occupied slot = 4


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"alignment": "fuzzy"}, "fuzzy_alignment"),
        ({"source_slots": ((1, 2), (3,), (3,), (5,))}, "ambiguous_slots"),
        ({"source_slots": ((1, 2), (4,), (3,), (5,))}, "ambiguous_slots"),
    ],
)
def test_inconclusive_projection_is_never_negative_syntax_evidence(
    tmp_path, kwargs, expected
):
    rows = get_rows(tmp_path, **kwargs)
    root = next(row for row in rows if row["depth"] == 0)
    assert root["slot_status"] == expected
    assert root["bhsa_cut_after_slot"] is None
    for kind in ("phrase", "phrase_atom", "clause_atom", "clause"):
        assert root[f"ends_{kind}"] is None
        assert root[f"{kind}_nodes"] == ""


def test_cli_deterministic_jsonl_and_tsv_and_denominators(tmp_path, capsys):
    graph = save_syntax_graph(tmp_path)
    jsonl = tmp_path / "syntax.jsonl"
    args = ["compare-syntax", "--graph", str(graph), "--output", str(jsonl)]
    assert main(args) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["cuts"] == 3
    assert stats["comparable"] == 3
    assert stats["status_counts"] == {"comparable": 3}
    assert stats["matches_by_type"]["phrase"] == 2  # *cuts*, not nodes
    assert stats["syntax_node_exclusions_global"]["phrase"]["cross_verse"] == 1
    assert stats["syntax_node_exclusions_global"]["clause"]["cross_verse"] == 1
    original = jsonl.read_bytes()
    assert main(args) == 0
    capsys.readouterr()
    assert jsonl.read_bytes() == original

    rows = [json.loads(line) for line in original.decode().splitlines()]
    tsv = tmp_path / "syntax.tsv"
    assert main([
        "compare-syntax", "--graph", str(graph), "--format", "tsv",
        "--verse", "Ps.117.1", "--verse", "Gen.1.1",
        "--verse", "Gen.1.1", "--output", str(tsv),
    ]) == 0
    capsys.readouterr()
    with tsv.open(encoding="utf-8", newline="") as stream:
        parsed = list(csv.DictReader(stream, delimiter="\t"))
    assert len(parsed) == len(rows)
    assert list(parsed[0]) == list(rows[0])
    assert all(
        [("" if value is None else str(value)) for value in row.values()]
        == list(tsv_row.values())
        for row, tsv_row in zip(rows, parsed, strict=True)
    )


@pytest.mark.parametrize("fmt", ["jsonl", "tsv"])
def test_selected_singleton_exports_zero_cuts_but_known_verse(tmp_path, fmt, capsys):
    graph = save_syntax_graph(tmp_path)
    output = tmp_path / f"singleton.{fmt}"
    assert main([
        "compare-syntax", "--graph", str(graph),
        "--verse", "Ps.117.1", "--format", fmt, "--output", str(output),
    ]) == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["cuts"] == 0
    if fmt == "jsonl":
        assert output.read_bytes() == b""
    else:
        with output.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            assert list(reader) == []
            assert reader.fieldnames is not None


def test_unknown_verse_preserves_atomic_previous_output(tmp_path):
    graph = save_syntax_graph(tmp_path)
    output = tmp_path / "previous.jsonl"
    output.write_bytes(b"old verified export\n")
    with pytest.raises(ValueError, match="Unknown OSIS"):
        main([
            "compare-syntax", "--graph", str(graph),
            "--verse", "Gen.1.1", "--verse", "Gen.1.999",
            "--output", str(output),
        ])
    assert output.read_bytes() == b"old verified export\n"
    assert not list(tmp_path.glob(".previous.jsonl.*.tmp"))


def test_corrupt_nonselected_persisted_cut_fails_atomically(tmp_path):
    tf = pytest.importorskip("tf.fabric")
    graph = save_syntax_graph(tmp_path)
    api = load_boundary_api(graph)
    output = tmp_path / "previous.jsonl"
    output.write_bytes(b"prior verified export\n")
    root = api.E.cant_root.f(17)[0]
    assert tf.Fabric(locations=str(graph), silent="deep").save(
        edgeFeatures={"cant_cut_after": {root: {api.E.cant_root.f(18)[0]}}},
        metaData={"cant_cut_after": {"valueType": "str"}},
        silent="deep",
    )
    with pytest.raises(ValueError, match="cut|phrase"):
        main([
            "compare-syntax", "--graph", str(graph),
            "--verse", "Ps.117.1", "--output", str(output),
        ])
    assert output.read_bytes() == b"prior verified export\n"
    assert not list(tmp_path.glob(".previous.jsonl.*.tmp"))


def test_cross_verse_syntax_endpoint_is_not_falsely_counted_in_second_verse(tmp_path):
    # Both original syntax node 9 (clause) and 14 (phrase) occupy
    # {5, 6}, spanning Gen.1.1 and Ps.117.1. Psalm has a real cut after 6.
    graph = save_syntax_graph(tmp_path, psalm_split=True)
    rows = list(iter_syntax_boundary_rows(load_boundary_api(graph)))
    ps = next(row for row in rows if row["osis_id"] == "Ps.117.1")
    assert ps["slot_status"] == "comparable"
    assert ps["bhsa_cut_after_slot"] == 6
    assert ps["ends_phrase"] is False
    assert ps["phrase_nodes"] == ""
    assert ps["ends_clause"] is False
    assert ps["clause_nodes"] == ""


def test_missing_original_syntax_layer_fails_closed_and_preserves_output(tmp_path):
    graph = save_syntax_graph(tmp_path, missing_clause_layer=True)
    output = tmp_path / "previous.jsonl"
    output.write_bytes(b"prior verified export\n")
    with pytest.raises(ValueError, match="Missing original BHSA syntax layer.*clause"):
        main([
            "compare-syntax", "--graph", str(graph),
            "--output", str(output),
        ])
    assert output.read_bytes() == b"prior verified export\n"
    assert not list(tmp_path.glob(".previous.jsonl.*.tmp"))


def test_summary_by_system_and_accent_has_truthful_exact_denominators(tmp_path, capsys):
    # The source fixture has 3 Genesis cuts and 1 Psalm cut; the two
    # Atnach labels must remain separate because their systems differ.
    graph = save_syntax_graph(tmp_path, psalm_split=True)
    jsonl = tmp_path / "cuts.jsonl"
    assert main([
        "compare-syntax", "--graph", str(graph), "--output", str(jsonl),
    ]) == 0
    report = json.loads(capsys.readouterr().out)
    strata = report["by_system_accent"]
    assert [(s["system"], s["accent"], s["cuts"]) for s in strata] == [
        ("poetic", "Atnach", 1),
        ("prose", "Atnach", 1),
        ("prose", "Tipcha", 2),
    ]
    assert all(s["status_counts"] == {"comparable": s["cuts"]} for s in strata)
    assert all(s["comparable"] == s["cuts"] for s in strata)
    expected = {
        ("poetic", "Atnach"): (0, 0, 0, 0),
        ("prose", "Atnach"): (1, 0, 1, 1),
        ("prose", "Tipcha"): (1, 1, 0, 0),
    }
    types = ("phrase", "phrase_atom", "clause_atom", "clause")
    for s in strata:
        counts = dict(zip(types, expected[(s["system"], s["accent"])], strict=True))
        assert s["matches_by_type"] == counts
        assert s["match_fraction_by_type"] == {
            kind: round(value / s["comparable"], 6)
            for kind, value in counts.items()
        }
    assert sum(s["cuts"] for s in strata) == report["cuts"] == 4
    assert sum(s["comparable"] for s in strata) == report["comparable"]
    for kind in types:
        assert sum(s["matches_by_type"][kind] for s in strata) == (
            report["matches_by_type"][kind]
        )
    assert len(jsonl.read_text(encoding="utf-8").splitlines()) == 4


def test_noncomparable_group_has_null_fractions_not_false_zeroes(tmp_path, capsys):
    graph = save_syntax_graph(tmp_path, alignment="fuzzy", psalm_split=True)
    output = tmp_path / "fuzzy.jsonl"
    assert main([
        "compare-syntax", "--graph", str(graph), "--book", "Gen",
        "--output", str(output),
    ]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["cuts"] == 3
    assert report["comparable"] == 0
    strata = report["by_system_accent"]
    assert [(s["system"], s["accent"], s["cuts"]) for s in strata] == [
        ("prose", "Atnach", 1),
        ("prose", "Tipcha", 2),
    ]
    for s in strata:
        assert s["comparable"] == 0
        assert s["status_counts"] == {"fuzzy_alignment": s["cuts"]}
        assert all(value == 0 for value in s["matches_by_type"].values())
        assert all(value is None for value in s["match_fraction_by_type"].values())
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert all(r["ends_phrase"] is None for r in rows)


def test_singleton_grouped_summary_is_empty_and_fixed_jsonl_tsv_stays_unchanged(
    tmp_path, capsys
):
    graph = save_syntax_graph(tmp_path)
    jsonl = tmp_path / "singleton.jsonl"
    assert main([
        "compare-syntax", "--graph", str(graph), "--book", "Ps",
        "--chapter", "117", "--output", str(jsonl),
    ]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["cuts"] == 0
    assert report["by_system_accent"] == []
    assert jsonl.read_bytes() == b""

    tsv = tmp_path / "singleton.tsv"
    assert main([
        "compare-syntax", "--graph", str(graph), "--book", "Ps",
        "--chapter", "117", "--format", "tsv", "--output", str(tsv),
    ]) == 0
    assert json.loads(capsys.readouterr().out)["by_system_accent"] == []
    with tsv.open(encoding="utf-8", newline="") as stream:
        assert list(csv.DictReader(stream, delimiter="\\t")) == []


@pytest.mark.parametrize(
    "slots",
    (
        ((1, 2), (3,), (3,), (5,)),
        ((1, 2), (4,), (3,), (5,)),
    ),
)
def test_ambiguous_cuts_are_excluded_from_group_rate_denominator(
    tmp_path, capsys, slots
):
    graph = save_syntax_graph(tmp_path, source_slots=slots)
    output = tmp_path / "ambiguous.jsonl"
    assert main([
        "compare-syntax", "--graph", str(graph), "--book", "Gen",
        "--output", str(output),
    ]) == 0
    summary = json.loads(capsys.readouterr().out)
    strata = summary["by_system_accent"]
    assert strata
    assert sum(s["cuts"] for s in strata) == 3
    assert sum(s["comparable"] for s in strata) == summary["comparable"]
    for s in strata:
        assert s["cuts"] == sum(s["status_counts"].values())
        assert s["comparable"] == s["status_counts"].get("comparable", 0)
        for kind, hits in s["matches_by_type"].items():
            assert hits <= s["comparable"]
            expected = (
                round(hits / s["comparable"], 6) if s["comparable"] else None
            )
            assert s["match_fraction_by_type"][kind] == expected
    assert summary["status_counts"]["ambiguous_slots"] > 0
