"""Exact original BHSA slot-set relations for cantillation/syntax comparisons.

Numeric span envelopes are not used: discontinuous original BHSA phrase
and clause nodes can interleave without sharing any occupied word slots.
"""


def classify_slot_relation(
    cantillation_slots: frozenset[int], syntax_slots: frozenset[int]
) -> str:
    """Classify one cantillation span against one original syntax object.

    'inside' means the cantillation span is strictly inside syntax.
    'contains' means the cantillation span strictly contains syntax.
    'crossing' requires occupied-slot overlap without either containing
    the other. Empty sets are inconclusive rather than disjoint.
    """
    if not cantillation_slots or not syntax_slots:
        return "inconclusive"
    if cantillation_slots == syntax_slots:
        return "exact"
    if cantillation_slots < syntax_slots:
        return "inside"
    if syntax_slots < cantillation_slots:
        return "contains"
    if cantillation_slots & syntax_slots:
        return "crossing"
    return "disjoint"
