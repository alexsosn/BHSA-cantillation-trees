"""RED researcher book/chapter selector acceptance for existing graph exports (#30)."""

import json

import pytest
from test_half_verse import save_halves
from test_syntax_boundary import save_syntax_graph

from bhsa_cantillation.cli import main, parser


def _export(command, graph, output, *selection):
    assert main([
        command, "--graph", str(graph), *selection, "--output", str(output),
    ]) == 0
    return [
        json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()
    ]


@pytest.mark.parametrize("command", ("boundaries", "compare-syntax", "syntax-relations"))
def test_book_chapter_equals_explicit_osis_verse_for_saved_graph(tmp_path, command):
    graph = save_syntax_graph(tmp_path)
    book = _export(
        command, graph, tmp_path / "book.jsonl", "--book", "Gen", "--chapter", "1"
    )
    exact = _export(
        command, graph, tmp_path / "exact.jsonl", "--verse", "Gen.1.1"
    )
    assert book == exact
    assert book and {r["osis_id"] for r in book} == {"Gen.1.1"}
    assert (tmp_path / "book.jsonl").read_bytes() == (tmp_path / "exact.jsonl").read_bytes()


def test_book_chapter_selects_original_half_verse_comparison(tmp_path):
    graph = save_halves(tmp_path)
    book = _export(
        "compare-halves", graph, tmp_path / "book.jsonl",
        "--book", "Gen", "--chapter", "1",
    )
    explicit = _export(
        "compare-halves", graph, tmp_path / "explicit.jsonl",
        "--verse", "Gen.1.1",
    )
    assert book == explicit
    assert len(book) == 1 and book[0]["status"] == "match"


@pytest.mark.parametrize("command", ("boundaries", "compare-syntax", "syntax-relations"))
def test_book_without_chapter_and_singleton_selection(tmp_path, command):
    graph = save_syntax_graph(tmp_path)
    genesis = _export(command, graph, tmp_path / "gen.jsonl", "--book", "Gen")
    psalm = _export(
        command, graph, tmp_path / "ps.jsonl", "--book", "Ps", "--chapter", "117"
    )
    assert genesis and {r["osis_id"] for r in genesis} == {"Gen.1.1"}
    assert psalm == []  # known singleton: no cant_phrase, successful empty selection


def test_book_selector_has_no_cross_book_prefix_matches(tmp_path):
    graph = save_syntax_graph(tmp_path, psalm_split=True)
    genesis = _export(
        "boundaries", graph, tmp_path / "gen.jsonl",
        "--book", "Gen", "--chapter", "1",
    )
    psalm = _export(
        "boundaries", graph, tmp_path / "ps.jsonl",
        "--book", "Ps", "--chapter", "117",
    )
    assert len(genesis) == 3
    assert len(psalm) == 1
    assert {r["osis_id"] for r in psalm} == {"Ps.117.1"}


@pytest.mark.parametrize(
    "invalid",
    (
        ("--book", "gen"),
        ("--book", "Gen", "--verse", "Gen.1.1"),
        ("--chapter", "1"),
        ("--book", "Gen", "--chapter", "0"),
        ("--book", "Gen", "--chapter", "-1"),
    ),
)
def test_invalid_selector_fails_before_writing_file(tmp_path, invalid):
    graph = save_syntax_graph(tmp_path)
    target = tmp_path / "previous.jsonl"
    target.write_bytes(b"verified previous report\n")
    with pytest.raises(SystemExit) as error:
        main(["compare-syntax", "--graph", str(graph), *invalid, "--output", str(target)])
    assert error.value.code == 2
    assert target.read_bytes() == b"verified previous report\n"


@pytest.mark.parametrize("command", ("boundaries", "compare-syntax", "syntax-relations"))
def test_valid_book_with_absent_chapter_fails_closed(tmp_path, command):
    graph = save_syntax_graph(tmp_path)
    target = tmp_path / f"{command}.jsonl"
    target.write_bytes(b"previous verified\n")
    with pytest.raises(ValueError, match="No verses.*Gen.*2"):
        main([
            command, "--graph", str(graph), "--book", "Gen", "--chapter", "2",
            "--output", str(target),
        ])
    assert target.read_bytes() == b"previous verified\n"
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))


def test_default_unfiltered_behavior_preserved_and_relations_still_require_selection(
    tmp_path
):
    graph = save_syntax_graph(tmp_path)
    rows = _export("compare-syntax", graph, tmp_path / "all.jsonl")
    assert len(rows) == 3
    with pytest.raises(SystemExit) as error:
        main([
            "syntax-relations", "--graph", str(graph), "--output", str(tmp_path / "bad.jsonl")
        ])
    assert error.value.code == 2  # no unbounded pairwise relation export


def test_parser_book_choices_and_chapter_dependence():
    for command in ("boundaries", "compare-halves", "compare-syntax", "syntax-relations"):
        parsed = parser().parse_args([
            command, "--graph", "graph", "--book", "1Sam",
            "--chapter", "3", "--output", "out.tsv",
        ])
        assert parsed.book == "1Sam"
        assert parsed.chapter == 3
        assert parsed.verse == []
