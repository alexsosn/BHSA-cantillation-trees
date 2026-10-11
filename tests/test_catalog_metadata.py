"""Contract tests for raw MorphHB catalogue metadata and endpoint projection."""

from xml.etree import ElementTree as ET

from bhsa_cantillation.build import FEATURE_META, _append_catalogue_features, _metadata
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
    for word in (first, second, third):
        _append_catalogue_features(features, 42, word)
    assert features["cantillation_catalog_rank"][42] == "0 | 1 | 2"
    assert features["cantillation_catalog_final"][42] == "1 | 0"


def test_catalogue_endpoint_features_are_raw_source_strings():
    for feature in ("cantillation_catalog_rank", "cantillation_catalog_final"):
        assert FEATURE_META[feature]["valueType"] == "str"
        meta = _metadata("2021", "pinned-source")[feature]
        assert "MorphHB" in meta["description"]
        assert meta["source"].endswith("/pinned-source")


def test_uncatalogued_manual_word_never_projects_invented_metadata():
    features = {"cantillation_catalog_rank": {}, "cantillation_catalog_final": {}}
    bad = SourceWord("fallback", "x", "x", 1, accent_rank=9, accent_final=True)
    _append_catalogue_features(features, 42, bad)
    assert features == {"cantillation_catalog_rank": {}, "cantillation_catalog_final": {}}
