"""RED exact-slot-set relation contract for original BHSA syntax (#21)."""

from bhsa_cantillation.syntax_relations import classify_slot_relation


def test_exact_set_relation_partition():
    base = frozenset({1, 2, 4})
    assert classify_slot_relation(base, frozenset({1, 2, 4})) == "exact"
    assert classify_slot_relation(base, frozenset({1, 2, 3, 4})) == "inside"
    assert classify_slot_relation(base, frozenset({2, 4})) == "contains"
    assert classify_slot_relation(base, frozenset({2, 3, 5})) == "crossing"
    assert classify_slot_relation(base, frozenset({3})) == "disjoint"


def test_disjoint_interleaved_envelopes_are_not_crossing():
    # Real pinned BHSA Gen.1.7 clauses 427578/427579 demonstrate this.
    left = frozenset({101, 102, 103, 104, 105, 112, 113, 114, 115})
    right = frozenset({106, 107, 108, 109, 110, 111})
    assert min(left) < min(right) < max(right) < max(left)
    assert classify_slot_relation(left, right) == "disjoint"
    assert classify_slot_relation(right, left) == "disjoint"


def test_gapped_subset_must_not_be_classified_by_envelope():
    # An envelope-only classifier would call these 'inside'.
    assert classify_slot_relation(
        frozenset({1, 3}), frozenset({1, 2})
    ) == "crossing"
    assert classify_slot_relation(
        frozenset({2}), frozenset({1, 3})
    ) == "disjoint"


def test_empty_slotsets_are_inconclusive():
    assert classify_slot_relation(frozenset(), frozenset({1})) == "inconclusive"
    assert classify_slot_relation(frozenset({1}), frozenset()) == "inconclusive"
