"""Acceptance tests for Hitin-Mashiah's objective main-division tables."""

import pytest

from bhsa_cantillation.hitin_mashiah import classify_root, summarize


def candidate(osis="Gen.1.1", *, marks=None, cut=4, accent="Atnach",
              final="Sof Pasuq", alignment="exact", system="prose"):
    if marks is None:
        marks = ["", "", "", "", "", "׃"]
    return classify_root(osis, system, alignment, cut, marks, accent, final)


def test_printed_examples_maqqef_changes_length_and_right_side():
    # 1 Kgs 8:45: two links before the cut; Josh 10:43: one on each side.
    kings = candidate("1Kgs.8.45", marks=["", "", "־", "", "־", "", "", "׃"],
                      cut=6)
    josh = candidate("Josh.10.43", marks=["", "", "־", "", "", "־", "", "׃"],
                     cut=5, accent="Zaqef Qatan")
    assert (kings["source_words"], kings["words"], kings["right_words"]) == (8, 6, 2)
    assert (josh["source_right_words"], josh["words"], josh["right_words"]) == (3, 6, 2)
    assert kings["category"] == "Atnah"
    assert josh["category"] == "Tipha/Zaqef"
    assert kings["status"] == josh["status"] == "included"


def test_chain_on_right_counts_one_and_preserves_original_count():
    # Exod 12:45, printed p. 206 example 19.
    row = candidate("Exod.12.45", marks=["", "", "־", "־", "׃"],
                    cut=2, accent="Tipcha")
    assert (row["words"], row["right_words"], row["source_right_words"]) == (3, 1, 3)
    assert row["category"] == "Tipha"


def test_footnote_nine_excluded_not_moved_to_other_table():
    row = candidate(cut=5, marks=["", "", "", "", "", "֖׃"],
                    final="Mëayla with Sof Pasuq")
    assert row["status"] == "maayla_exclusion"
    result = summarize([row])
    assert result["status_counts"] == {"maayla_exclusion": 1}
    assert all(cell["observed"] == 0 for table in result["tables"].values()
               for cell in table)


@pytest.mark.parametrize("kwargs,status", [
    ({"osis": "Job.1.1"}, "outside_21_books"),
    ({"osis": "Ps.1.1", "system": "poetic"}, "outside_21_books"),
    ({"alignment": "fuzzy"}, "fuzzy_alignment"),
    ({"accent": "unknown"}, "unmapped_cut_accent"),
    ({"final": "unknown"}, "unmapped_final_accent"),
    ({"marks": ["", "", "", "־", "", "׃"]}, "split_maqqef"),
    ({"marks": ["", "", "", "", "", "־"]}, "terminal_maqqef"),
    ({"cut": 2}, "other_right_length"),
    ({"cut": 5, "accent": "Zaqef Gadol"}, "not_in_published_category"),
])
def test_explicit_exclusion_reasons(kwargs, status):
    assert candidate(**kwargs)["status"] == status


def test_explicit_catalogue_aliases_and_delta_inventory():
    rows = [
        candidate("Gen.1.1", accent="Munnach with Atnach"),
        candidate("Gen.1.2", accent="Merkha with Tipcha"),
        candidate("Gen.1.3", accent="Qadma with Zaqef Qatan"),
        candidate("Gen.1.4", cut=5, accent="Mëayla with Atnach"),
    ]
    report = summarize(rows)
    assert report["status_counts"] == {"included": 4}
    one = report["tables"]["one_word"]
    two = report["tables"]["two_words"]
    assert sum(c["published"] for c in one) == 408
    assert sum(c["published"] for c in two) == 1832
    assert sum(c["observed"] for c in one) == 1
    assert sum(c["observed"] for c in two) == 3
    assert all(c["delta"] == c["observed"] - c["published"]
               for c in one + two)
    assert sorted(v for c in one + two for v in c["verses"]) == [
        "Gen.1.1", "Gen.1.2", "Gen.1.3", "Gen.1.4",
    ]
    assert report == summarize(list(reversed(rows)))


def test_invalid_source_cut_rejected():
    with pytest.raises(ValueError, match="cut"):
        candidate(cut=0)
