"""Contract tests for raw MorphHB catalogue metadata and endpoint projection."""

from xml.etree import ElementTree as ET

from bhsa_cantillation import build
from bhsa_cantillation.model import SourceWord
from bhsa_cantillation.morphhb import NS, parse_verse


CATALOG = {
    "prose": {
        "conjunctive": {},
        "disjunctive": {
            "\u0591": {"name": "Atnach", "rank": "0"},
            "\u0596": {"name": "Tipcha", "rank": "1", "final": "true"},
            "\u0597": {"name": "Revia", "rank": "2", "final": "false"},
        },
    },
    "poetic": {
        "conjunctive": {},
        "disjunctive": {"\u0591": {"name": "Atnach", "rank": "1", "final": "true"}},
    },
}


def parse_word(osis: str, text: str) -> SourceWord:
    xml = f'<verse xmlns="{NS[1:-1]}" osisID="{osis}"><w id="w1" n="0">{text}</w></verse>'
    return parse_verse(ET.fromstring(xml), CATALOG)[0]


def test_real_catalogue_rank_differs_between_prose_and_poetic_atnach():
    prose = parse_word("Gen.1.1", "אֱלֹהִ֑ים")
    poetic = parse_word("Ps.1.1", "אֱלֹהִ֑ים")
    assert (prose.accent_name, prose.accent_rank, prose.accent_final) == (
        "Atnach", 0, None
    )
    assert (poetic.accent_name, poetic.accent_rank, poetic.accent_final) == (
        "Atnach", 1, True
    )


def test_explicit_false_differs_from_missing_final():
    explicit_false = parse_word("Gen.1.1", "דָּבָ֗ר")
    explicit_true = parse_word("Gen.1.1", "דָּבָ֖ר")
    assert (explicit_false.accent_rank, explicit_false.accent_final) == (2, False)
    assert (explicit_true.accent_rank, explicit_true.accent_final) == (1, True)


def test_fallback_does_not_fabricate_catalogue_values():
    unknown = parse_word("Gen.1.1", "דָּבָ֞ר")
    assert unknown.accent_catalogued is False
    assert unknown.accent_rank is None
    assert unknown.accent_final is None


def test_meteg_lookup_inherits_only_source_catalogue_fields():
    # _accent_entry strips meteg only for catalogue lookup.
    word = parse_word("Gen.1.1", "דָּֽבָ֖ר")
    assert word.accent_catalogued is True
    assert word.accent_name == "Tipcha"
    assert (word.accent_rank, word.accent_final) == (1, True)


def test_endpoint_projection_preserves_multiple_source_words_without_mixing_missing():
    features = {"cantillation_catalog_rank": {}, "cantillation_catalog_final": {}}
    first = SourceWord(
        "w1", "x", "x", 1, accent_catalogued=True, accent_rank=0, accent_final=None
    )
    second = SourceWord(
        "w2", "y", "y", 1, accent_catalogued=True, accent_rank=1, accent_final=True
    )
    third = SourceWord(
        "w3", "z", "z", 1, accent_catalogued=True, accent_rank=2, accent_final=False
    )
    build._append_catalogue_features(features, 42, (first, second, third))
    assert features["cantillation_catalog_rank"][42] == "0 | 1 | 2"
    assert features["cantillation_catalog_final"][42] == "? | 1 | 0"


def test_catalogue_endpoint_features_are_raw_source_strings():
    for feature in ("cantillation_catalog_rank", "cantillation_catalog_final"):
        assert build.FEATURE_META[feature]["valueType"] == "str"
        meta = build._metadata("2021", "pinned-source")[feature]
        assert "MorphHB" in meta["description"]
        assert meta["source"].endswith("/pinned-source")


def test_uncatalogued_manual_word_never_projects_inventedbuild._metadata():
    features = {"cantillation_catalog_rank": {}, "cantillation_catalog_final": {}}
    bad = SourceWord("fallback", "x", "x", 1, accent_rank=9, accent_final=True)
    build._append_catalogue_features(features, 42, (bad,))
    assert features == {"cantillation_catalog_rank": {}, "cantillation_catalog_final": {}}


def test_projection_keeps_source_position_through_fallbacks():
    features = {"cantillation_catalog_rank": {}, "cantillation_catalog_final": {}}
    fallback = SourceWord("fb", "x", "x", 1)
    known = SourceWord("known", "y", "y", 1, accent_catalogued=True, accent_rank=3)
    build._append_catalogue_features(features, 7, (fallback, known))
    assert features["cantillation_catalog_rank"][7] == "? | 3"
    assert 7 not in features["cantillation_catalog_final"]


def test_malformed_catalogue_values_fail_closed():
    from pytest import raises

    original = CATALOG["prose"]["disjunctive"]["\u0596"]
    CATALOG["prose"]["disjunctive"]["\u0596"] = {
        "name": "Tipcha", "rank": True, "final": 1
    }
    try:
        with raises(ValueError, match="rank"):
            parse_word("Gen.1.1", "דָּבָ֖ר")
        CATALOG["prose"]["disjunctive"]["\u0596"] = {
            "name": "Tipcha", "rank": "1", "final": 1
        }
        with raises(ValueError, match="final"):
            parse_word("Gen.1.1", "דָּבָ֖ר")
    finally:
        CATALOG["prose"]["disjunctive"]["\u0596"] = original
