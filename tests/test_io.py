import io
import json

import pytest

from bhsa_cantillation.io import render_tree, select_records, write_json

TREE = {
    "accent": "Atnach",
    "children": [
        {"path": "1", "slots": [1, 2], "text": "בְּרֵאשִׁית", "accent": "Tipcha"},
        {"path": "0", "slots": [3, 4], "text": "בָּרָא", "accent": "Sof Pasuq"},
    ],
}
RECORD = {
    "osis_id": "Gen.1.1",
    "bhsa_section": ["Genesis", 1, 1],
    "system": "prose",
    "alignment": "exact",
    "tree": TREE,
}


def test_render_tree_ascii_with_details():
    assert render_tree(TREE, details=True) == (
        "Atnach\n"
        "|-- Tipcha: בְּרֵאשִׁית  [path=1; slots=1-2]\n"
        "`-- Sof Pasuq: בָּרָא  [path=0; slots=3-4]"
    )


def test_select_records_accepts_reference_spellings():
    assert list(select_records([RECORD], ["Gen 1:1"])) == [RECORD]
    with pytest.raises(ValueError, match="not found"):
        list(select_records([RECORD], ["Gen.1.2"]))


def test_write_json_and_json_lines():
    array = io.StringIO()
    assert write_json([RECORD], array, json_lines=False, pretty=False) == 1
    assert json.loads(array.getvalue()) == [RECORD]

    lines = io.StringIO()
    assert write_json([RECORD], lines, json_lines=True, pretty=False) == 1
    assert json.loads(lines.getvalue()) == RECORD
