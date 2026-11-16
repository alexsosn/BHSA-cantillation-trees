"""RED contract tests for the pinned BHSA syntax oslots research gate (#21).

These synthetic sets deliberately include gapped objects and overlapping spans.
The audit must compare original slot *sets*, never min/max envelopes alone.
"""

from types import SimpleNamespace

import pytest

from scripts.audit_syntax_oslots import audit_syntax_oslots


def fixture_api():
    types = {
        **{slot: "word" for slot in range(1, 9)},
        9: "phrase",
        10: "phrase",
        11: "phrase",
        12: "phrase",
        13: "phrase",
        14: "phrase_atom",
        15: "clause",
        16: "clause_atom",
        20: "verse",
        21: "verse",
    }
    spans = {
        9: {1, 2, 4},       # gapped
        10: {2, 3},        # crosses 9 by exact set intersection
        11: {1, 2, 4},     # identical slotset to 9
        12: {6, 7},        # crosses the verse boundary
        13: {2},           # nested inside 9
        14: {4, 5},
        15: {1, 2, 3, 4, 5},
        16: {3, 4, 5},
        20: set(range(1, 7)),
        21: {7, 8},
    }
    return SimpleNamespace(
        F=SimpleNamespace(
            otype=SimpleNamespace(s=lambda kind: tuple(
                node for node, value in sorted(types.items()) if value == kind
            ))
        ),
        E=SimpleNamespace(
            oslots=SimpleNamespace(s=lambda node: sorted(spans[node]))
        ),
    )


def test_audit_exact_sets_and_verse_ownership():
    result = audit_syntax_oslots(
        fixture_api(), verse_labels={20: "Gen.1.1", 21: "Gen.1.2"}, max_examples=4
    )
    phrase = result["types"]["phrase"]
    assert phrase["nodes"] == 5
    assert phrase["gapped"] == 2  # the duplicate gapped node is a distinct BHSA node
    assert phrase["cross_verse"] == 1
    assert phrase["assigned_to_verse"] == 4
    assert result["relations"]["identical"] >= 1
    assert result["relations"]["strict_containment"] >= 1
    assert result["relations"]["crossing"] >= 1
    assert result["relations"]["shared_end_slot"] >= 1
    assert any(
        item["nodes"] == [9, 10] and item["osis_id"] == "Gen.1.1"
        for item in result["examples"]["crossing"]
    )
    assert any(
        item["node"] == 12 for item in result["examples"]["cross_verse"]
    )


def test_audit_deterministic_and_bounded_examples():
    result = audit_syntax_oslots(
        fixture_api(), verse_labels={20: "Gen.1.1", 21: "Gen.1.2"}, max_examples=1
    )
    assert all(len(items) <= 1 for items in result["examples"].values())
    assert all(len(items) <= 1 for v in result["types"].values()
               for key, items in v.items() if key.endswith("_examples"))
    assert audit_syntax_oslots(
        fixture_api(), verse_labels={20: "Gen.1.1", 21: "Gen.1.2"}, max_examples=1
    ) == result


def test_duplicate_word_slot_owner_is_rejected():
    api = fixture_api()
    old = api.E.oslots.s
    api.E.oslots.s = lambda node: [6, 7, 8] if node == 21 else old(node)
    with pytest.raises(ValueError, match="multiple verses"):
        audit_syntax_oslots(api)


def test_section_display_name_does_not_replace_original_bhsa_book_code():
    """T.sectionFromNode may display 'Numbers', but F.book uses 'Numeri'."""
    from scripts.audit_syntax_oslots import _verse_osis_labels

    api = fixture_api()
    api.F.book = SimpleNamespace(v=lambda node: "Numeri")
    api.L = SimpleNamespace(u=lambda node, otype: (100,) if otype == "book" else ())
    api.T = SimpleNamespace(sectionFromNode=lambda node: ("Numbers", 1, 1))
    assert _verse_osis_labels(api)[20] == "Num.1.1"


def test_cross_verse_example_names_both_source_verses():
    result = audit_syntax_oslots(
        fixture_api(), verse_labels={20: "Gen.1.1", 21: "Gen.1.2"}
    )
    sample = next(item for item in result["examples"]["cross_verse"] if item["node"] == 12)
    assert sample["verse_nodes"] == [20, 21]
    assert sample["osis_ids"] == ["Gen.1.1", "Gen.1.2"]


def test_gapped_sample_exposes_complete_exact_slot_runs():
    result = audit_syntax_oslots(
        fixture_api(), verse_labels={20: "Gen.1.1", 21: "Gen.1.2"}
    )
    sample = next(item for item in result["examples"]["gapped"] if item["node"] == 9)
    assert sample["slot_ranges"] == "1-2,4"
    assert sample["slot_count"] == 3


def test_pairwise_crossing_example_preserves_both_complete_slot_sets():
    result = audit_syntax_oslots(
        fixture_api(), verse_labels={20: "Gen.1.1", 21: "Gen.1.2"}
    )
    sample = next(item for item in result["examples"]["crossing"] if item["nodes"] == [9, 10])
    assert sample["slot_ranges"] == ["1-2,4", "2-3"]


def test_exhausted_pair_example_budget_avoids_eager_slot_rendering(monkeypatch):
    import scripts.audit_syntax_oslots as audit

    original = audit._slot_ranges
    calls = 0

    def counted(slots):
        nonlocal calls
        calls += 1
        return original(slots)

    monkeypatch.setattr(audit, "_slot_ranges", counted)
    result = audit.audit_syntax_oslots(fixture_api(), max_examples=0)
    # At zero examples only the per-node descriptions may render slots.
    # Pairwise comparisons must never format slot runs just to discard them.
    assert calls == result["original_syntax_nodes"]
    assert all(not examples for examples in result["examples"].values())
