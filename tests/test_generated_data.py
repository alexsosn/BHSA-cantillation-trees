import json
from pathlib import Path

import pytest

MODULE = Path(__file__).parents[1] / "tf" / "2021"
if not MODULE.exists():
    pytest.skip("generated TF module is not present", allow_module_level=True)

FEATURES = {
    "cantillation_accent",
    "cantillation_accent_status",
    "cantillation_accent_type",
    "cantillation_alignment",
    "cantillation_marks",
    "cantillation_path",
    "cantillation_source_id",
    "cantillation_system",
    "cantillation_tree",
    "cantillation_unit",
    "cantillation_unit_path",
    "cantillation_accent_signature",
    "cantillation_branch_signature",
    "cantillation_colless",
    "cantillation_colless_normalized",
    "cantillation_depth",
    "cantillation_depth_leaf_ratio",
    "cantillation_leaf_count",
    "cantillation_longest_accent_run",
    "cantillation_longest_ladder",
    "cantillation_mean_leaf_depth",
    "cantillation_sackin",
    "cantillation_shape",
}


def test_generated_feature_set_is_complete():
    assert {path.stem for path in MODULE.glob("*.tf") if path.is_file()} == FEATURES


def test_alignment_report_matches_pinned_build():
    report = json.loads((MODULE / "alignment-report.json").read_text(encoding="utf-8"))
    assert report["stats"] == {
        "verses": 23213,
        "source_words": 305507,
        "units": 165747,
        "exact_verses": 23203,
        "fuzzy_verses": 10,
        "max_distance": 1,
        "catalog_fallback_words": 308,
    }
    assert len(report["non_exact"]) == 10
    assert all(item["distance"] == 1 for item in report["non_exact"])
