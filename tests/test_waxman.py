from pathlib import Path

from bhsa_cantillation.waxman import read_waxman, waxman_spans


def test_read_waxman_and_extract_spans(tmp_path: Path):
    source = tmp_path / "prodosic_trees.txt"
    source.write_text(
        "Genesis 1 1: {'name': 'PASUK', 'children': "
        "[{'name': 'TIPCHA', 'children': [{'name': 'בְּרֵאשִׁית'}]}]}\n",
        encoding="utf-8",
    )
    trees = read_waxman(source)
    text, spans = waxman_spans(trees["Gen.1.1"])
    assert text == "בראשית"
    assert {(node["start"], node["end"]) for node in spans} == {(0, 6)}


def test_read_waxman_rejects_code(tmp_path: Path):
    source = tmp_path / "prodosic_trees.txt"
    source.write_text("Genesis 1 1: __import__('os').system('false')\n", encoding="utf-8")
    try:
        read_waxman(source)
    except (ValueError, SyntaxError):
        pass
    else:
        raise AssertionError("non-literal input should be rejected")
