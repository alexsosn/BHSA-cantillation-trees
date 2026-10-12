"""Orthographic-word measurements at the existing cantillation-tree root."""

from copy import deepcopy

import pytest

from bhsa_cantillation.descriptors import main_cut_features
from bhsa_cantillation.model import SourceWord, WordAlignment
from bhsa_cantillation.tree import build_tree, make_units


def source(slot: int, ordinal: int, path: str | None = None) -> WordAlignment:
    word = SourceWord(
        source_id=f"w{ordinal}",
        text=f"w{ordinal}",
        consonants="א",
        morph_count=1,
        path=path,
        accent_name=f"a{ordinal}",
    )
    return WordAlignment(word, (slot,))


def make_example_units():
    # 7 MorphHB source words, 4 accent units, 5 distinct BHSA slots.
    alignments = [
        source(101, 1),
        source(101, 2, "1.0"),
        source(102, 3, "1"),
        source(103, 4),
        source(103, 5),
        source(104, 6, "0.0"),
        source(105, 7, "0"),
    ]
    return make_units(alignments)


def test_root_cut_counts_morphhb_source_words_not_slots_or_units():
    units = make_example_units()
    tree = build_tree(units)
    before = deepcopy(tree)
    assert [len(u.source_words) for u in units] == [2, 1, 3, 1]
    assert len({slot for u in units for slot in u.slots}) == 5
    assert main_cut_features(units, tree) == {
        "cantillation_word_count": 7,
        "cantillation_main_cut_word_index": 3,
        "cantillation_main_first_word_count": 3,
        "cantillation_main_second_word_count": 4,
        "cantillation_main_cut_fraction": "0.428571",
        "cantillation_main_signed_split": "0.142857",
    }
    assert tree == before


def test_directional_sign_uses_word_counts_not_unit_counts():
    alignments = [
        source(1, 1),
        source(2, 2),
        source(3, 3),
        source(4, 4),
        source(5, 5, "1"),
        source(6, 6, "0.0"),
        source(7, 7, "0"),
    ]
    units = make_units(alignments)
    assert main_cut_features(units, build_tree(units)) == {
        "cantillation_word_count": 7,
        "cantillation_main_cut_word_index": 5,
        "cantillation_main_first_word_count": 5,
        "cantillation_main_second_word_count": 2,
        "cantillation_main_cut_fraction": "0.714286",
        "cantillation_main_signed_split": "-0.428571",
    }


def test_one_unit_verse_has_no_defined_main_cut():
    units = make_units([source(1, 1), source(1, 2, "0")])
    assert main_cut_features(units, build_tree(units)) == {
        "cantillation_word_count": 2
    }


def test_malformed_tree_and_unit_cardinality_fail_closed():
    units = make_example_units()
    tree = build_tree(units)
    with pytest.raises(ValueError, match="leaf"):
        main_cut_features(units[:-1], tree)
    with pytest.raises(ValueError, match="binary"):
        main_cut_features(units, {"accent": "x", "children": [tree]})
    with pytest.raises(ValueError, match="unit"):
        main_cut_features([], tree)


def test_empty_source_unit_is_rejected():
    units = make_example_units()
    units[0] = type(units[0])(
        ordinal=units[0].ordinal,
        path=units[0].path,
        slots=units[0].slots,
        text=units[0].text,
        accent_name=units[0].accent_name,
        source_words=(),
    )
    with pytest.raises(ValueError, match="source"):
        main_cut_features(units, build_tree(units))


def test_multiword_qere_is_one_existing_morphhb_source_record():
    # MorphHB parse_verse stores multiword qere text on one ketiv SourceWord.
    qere = WordAlignment(
        SourceWord(
            source_id="ketiv",
            text="חֵ֣יל כָּאִֽים",
            consonants="חלכאים",
            morph_count=1,
            path="1",
            accent_name="Atnach",
        ),
        (1,),
    )
    units = make_units([qere, source(2, 2, "0")])
    values = main_cut_features(units, build_tree(units))
    assert values["cantillation_word_count"] == 2
    assert values["cantillation_main_first_word_count"] == 1
    assert values["cantillation_main_cut_fraction"] == "0.5"
