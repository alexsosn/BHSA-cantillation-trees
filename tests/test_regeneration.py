"""RED acceptance contracts for regenerating the pinned BHSA 2021 TF module."""

from pathlib import Path

import pytest

from bhsa_cantillation.build import FEATURE_META
from bhsa_cantillation.regeneration import verify_module_files, verify_verse_features

PINNED_MORPHHB = "3d15126fb1ef74867fc1434be1942e837932691f"


def feature(value: str, *, source: str = PINNED_MORPHHB) -> str:
    return (
        "@node\n@dataset=BHSA cantillation trees\n"
        f"@source=https://github.com/openscriptures/morphhb/tree/{source}\n"
        "@valueType=str\n\n"
        f"1414389\t{value}\n"
    )


def prepare(reference: Path, candidate: Path):
    reference.mkdir()
    candidate.mkdir()
    for name in FEATURE_META:
        if name.startswith(("cantillation_catalog_", "cantillation_main_")) or (
            name == "cantillation_word_count"
        ):
            (candidate / f"{name}.tf").write_text(feature("7"), encoding="utf-8")
        else:
            (reference / f"{name}.tf").write_text(feature("same"), encoding="utf-8")
            (candidate / f"{name}.tf").write_text(feature("same"), encoding="utf-8")
    report = '{"stats":{"verses":2,"source_words":7},"non_exact":[],"uncatalogued_patterns":[]}'
    (reference / "alignment-report.json").write_text(report, encoding="utf-8")
    (candidate / "alignment-report.json").write_text(report, encoding="utf-8")


def test_accepts_unchanged_old_feature_payloads_and_pinned_new_features(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    prepare(old, new)
    # Volatile metadata may vary without changing the underlying TF features.
    path = new / "cantillation_accent.tf"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "@valueType=str", "@dateWritten=2026-10-12T14:00:00Z\n@valueType=str"
        ),
        encoding="utf-8",
    )
    verify_module_files(old, new, PINNED_MORPHHB)


def test_rejects_changed_original_data_even_when_metadata_is_identical(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    prepare(old, new)
    (new / "cantillation_accent.tf").write_text(feature("changed"), encoding="utf-8")
    with pytest.raises(ValueError, match="cantillation_accent"):
        verify_module_files(old, new, PINNED_MORPHHB)


def test_rejects_missing_added_features(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    prepare(old, new)
    (new / "cantillation_catalog_rank.tf").unlink()
    with pytest.raises(ValueError, match="cantillation_catalog_rank"):
        verify_module_files(old, new, PINNED_MORPHHB)


def test_rejects_wrong_pinned_source_or_alignment_report_drift(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    prepare(old, new)
    (new / "cantillation_catalog_rank.tf").write_text(
        feature("7", source="unverified"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="source"):
        verify_module_files(old, new, PINNED_MORPHHB)
    (new / "cantillation_catalog_rank.tf").write_text(feature("7"), encoding="utf-8")
    (new / "alignment-report.json").write_text('{"stats":{}}', encoding="utf-8")
    with pytest.raises(ValueError, match="report"):
        verify_module_files(old, new, PINNED_MORPHHB)


class FakeFeature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)

    def s(self, otype):
        assert otype == "verse"
        return tuple(self.values)


class FakeF:
    def __init__(self, data):
        for name, values in data.items():
            setattr(self, name, FakeFeature(values))


class FakeL:
    def d(self, verse, otype):
        assert otype == "word"
        return {101: (1, 2), 102: (3, 4)}[verse]


class FakeAPI:
    L = FakeL()

    def __init__(self, first_count=3):
        self.F = FakeF(
            {
                "otype": {101: "verse", 102: "verse"},
                "cantillation_leaf_count": {101: 2, 102: 1},
                "cantillation_word_count": {101: first_count, 102: 1},
                "cantillation_main_cut_word_index": {101: 1},
                "cantillation_main_first_word_count": {101: 1},
                "cantillation_main_second_word_count": {101: 2},
                "cantillation_main_cut_fraction": {101: "0.333333"},
                "cantillation_main_signed_split": {101: "0.333333"},
                "cantillation_source_id": {1: "a", 2: "b | c", 3: "d"},
            }
        )


def test_verse_measurements_match_source_ids_root_cut_and_singletons():
    verify_verse_features(FakeAPI(), {"verses": 2, "source_words": 4, "units": 3})


def test_verse_measurements_fail_on_source_word_count_drift():
    with pytest.raises(ValueError, match="source"):
        verify_verse_features(FakeAPI(first_count=2), {"verses": 2, "source_words": 4, "units": 3})
