from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.tree import build_tree, make_units


def aligned(slot: int, text: str, path: str | None, accent: str) -> WordAlignment:
    source = SourceWord(
        source_id=str(slot),
        text=text,
        consonants=text,
        morph_count=1,
        path=path,
        accent_name=accent,
        accent_type="disjunctive" if path else "conjunctive",
    )
    return WordAlignment(source, (slot,))


def test_genesis_1_1_tree_shape():
    alignments = [
        aligned(1, "בראשית", "1.0", "Tipcha"),
        aligned(2, "ברא", None, "Munnach"),
        aligned(3, "אלהים", "1", "Atnach"),
        aligned(4, "את", None, "Merkha"),
        aligned(5, "השמים", "0.0", "Tipcha"),
        aligned(6, "ואת", None, "Merkha"),
        aligned(7, "הארץ", "0", "Sof Pasuq"),
    ]
    units = make_units(alignments)
    tree = build_tree(units)
    assert [unit.path for unit in units] == ["1.0", "1", "0.0", "0"]
    assert tree["accent"] == "Atnach"
    assert tree["children"][0]["accent"] == "Tipcha"
    assert tree["children"][1]["accent"] == "Tipcha"
    assert tree["children"][0]["children"][1]["slots"] == [2, 3]


def test_unit_path_is_required_at_verse_end():
    try:
        make_units([aligned(1, "ברא", None, "Munnach")])
    except ValueError as error:
        assert "not closed" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_shared_bhsa_slot_is_not_duplicated_inside_one_unit():
    units = make_units(
        [
            aligned(1, "תובל", None, "Munnach"),
            aligned(1, "קין", "0", "Sof Pasuq"),
        ]
    )
    assert units[0].slots == (1,)
