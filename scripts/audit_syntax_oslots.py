"""Audit exact BHSA syntax oslots topology before comparing cantillation cuts.

One-off research probe for issue #21. Use the pinned 2021 BHSA Text-Fabric
dataset; never infer slot membership from interval envelopes or source-word
indices. Counts refer to original BHSA syntax nodes, not derived graph nodes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from itertools import combinations
from pathlib import Path

from bhsa_cantillation.books import BOOKS

SYNTAX_TYPES = ("phrase", "phrase_atom", "clause_atom", "clause")
RELATION_KINDS = (
    "identical",
    "strict_containment",
    "crossing",
    "interleaved_disjoint",
    "shared_end_slot",
)


def _sample(target: list[dict], example: dict, limit: int) -> None:
    if len(target) < limit:
        target.append(example)


def _slot_ranges(slots: frozenset[int]) -> str:
    """Losslessly render exact source slot sets as inclusive consecutive runs."""
    ordered = sorted(slots)
    if not ordered:
        return ""
    runs = []
    first = last = ordered[0]
    for slot in ordered[1:]:
        if slot == last + 1:
            last = slot
        else:
            runs.append(str(first) if first == last else f"{first}-{last}")
            first = last = slot
    runs.append(str(first) if first == last else f"{first}-{last}")
    return ",".join(runs)


def _describe(node: int, kind: str, slots: frozenset[int], osis: str) -> dict:
    order = sorted(slots)
    return {
        "node": node,
        "type": kind,
        "osis_id": osis,
        "first_slot": order[0],
        "last_slot": order[-1],
        "slot_count": len(slots),
        "slot_ranges": _slot_ranges(slots),
        "slot_sample": order[:12],
    }


def audit_syntax_oslots(
    api, *, verse_labels: Mapping[int, str] | None = None, max_examples: int = 4
) -> dict:
    """Return deterministic, bounded evidence about the *original* BHSA sets.

    Pairwise counts exclude nodes without a unique owning verse. Strict
    containment and crossing use exact slot-set inclusion/intersection.
    Shared end slots are an independent count, not a mutually exclusive class.
    """
    if max_examples < 0:
        raise ValueError("max_examples must be nonnegative")
    E, F = api.E, api.F
    verses = sorted(F.otype.s("verse"))
    if not verses:
        raise ValueError("No original BHSA verses")
    labels = verse_labels or {}
    slot_owner: dict[int, int] = {}
    for verse in verses:
        slots = frozenset(E.oslots.s(verse))
        if not slots:
            raise ValueError(f"Missing original BHSA verse slots: {verse}")
        for slot in slots:
            if slot in slot_owner:
                raise ValueError(f"BHSA slot {slot} belongs to multiple verses")
            slot_owner[slot] = verse

    by_verse: dict[int, list[tuple[int, str, frozenset[int]]]] = {
        verse: [] for verse in verses
    }
    types: dict[str, dict] = {}
    examples: dict[str, list[dict]] = {
        key: [] for key in (*RELATION_KINDS, "gapped", "cross_verse", "missing_slots",
                             "unassigned_slots")
    }
    for kind in SYNTAX_TYPES:
        stats = {
            "nodes": 0,
            "assigned_to_verse": 0,
            "missing_slots": 0,
            "unassigned_slots": 0,
            "cross_verse": 0,
            "gapped": 0,
            "total_gap_slots": 0,
            "gapped_examples": [],
            "cross_verse_examples": [],
        }
        types[kind] = stats
        for node in F.otype.s(kind):
            stats["nodes"] += 1
            slots = frozenset(E.oslots.s(node))
            if not slots:
                stats["missing_slots"] += 1
                _sample(examples["missing_slots"], {"node": node, "type": kind},
                        max_examples)
                continue
            gaps = max(slots) - min(slots) + 1 - len(slots)
            owners = {slot_owner.get(slot) for slot in slots}
            osis = ""
            if len(owners) == 1 and None not in owners:
                owner = next(iter(owners))
                osis = labels.get(owner, str(owner))
            sample = _describe(node, kind, slots, osis)
            if gaps:
                stats["gapped"] += 1
                stats["total_gap_slots"] += gaps
                _sample(stats["gapped_examples"], sample, max_examples)
                _sample(examples["gapped"], sample, max_examples)
            if None in owners:
                stats["unassigned_slots"] += 1
                _sample(examples["unassigned_slots"], sample, max_examples)
                continue
            if len(owners) != 1:
                ordered_owners = sorted(owners)
                sample["verse_nodes"] = ordered_owners
                sample["osis_ids"] = [
                    labels.get(verse, str(verse)) for verse in ordered_owners
                ]
                stats["cross_verse"] += 1
                _sample(stats["cross_verse_examples"], sample, max_examples)
                _sample(examples["cross_verse"], sample, max_examples)
                continue
            verse = next(iter(owners))
            stats["assigned_to_verse"] += 1
            by_verse[verse].append((node, kind, slots))

    counts: Counter[str] = Counter({key: 0 for key in RELATION_KINDS})
    pair_count = 0
    for verse in verses:
        items = sorted(by_verse[verse])
        osis = labels.get(verse, str(verse))
        for (a, kind_a, slots_a), (b, kind_b, slots_b) in combinations(items, 2):
            pair_count += 1
            intersection = slots_a & slots_b
            if slots_a == slots_b:
                relation = "identical"
            elif slots_a < slots_b or slots_b < slots_a:
                relation = "strict_containment"
            elif intersection:
                relation = "crossing"
            elif (min(slots_a) <= max(slots_b) and min(slots_b) <= max(slots_a)):
                relation = "interleaved_disjoint"
            else:
                relation = None
            if relation is not None:
                counts[relation] += 1
                if len(examples[relation]) < max_examples:
                    _sample(examples[relation], {
                        "osis_id": osis,
                        "nodes": [a, b],
                        "types": [kind_a, kind_b],
                        "slots": [sorted(slots_a)[:12], sorted(slots_b)[:12]],
                        "slot_ranges": [_slot_ranges(slots_a), _slot_ranges(slots_b)],
                    }, max_examples)
            if max(slots_a) == max(slots_b):
                counts["shared_end_slot"] += 1
                _sample(examples["shared_end_slot"], {
                    "osis_id": osis,
                    "nodes": [a, b],
                    "types": [kind_a, kind_b],
                    "last_slot": max(slots_a),
                }, max_examples)

    return {
        "verse_count": len(verses),
        "original_syntax_nodes": sum(stats["nodes"] for stats in types.values()),
        "pair_denominator": pair_count,
        "types": types,
        "relations": {key: counts[key] for key in RELATION_KINDS},
        "examples": examples,
    }


def _verse_osis_labels(api) -> dict[int, str]:
    """Use original Latin BHSA book feature, not localized section display names."""
    bhsa_to_osis = {bhsa: osis for osis, bhsa in BOOKS}
    labels: dict[int, str] = {}
    for node in api.F.otype.s("verse"):
        section = api.T.sectionFromNode(node)
        if not section or len(section) != 3:
            raise ValueError(f"No BHSA section identity for verse {node}")
        _display_book, chapter, verse = section
        book_nodes = api.L.u(node, otype="book")
        if len(book_nodes) != 1:
            raise ValueError(f"Expected one original BHSA book node above verse {node}")
        book = api.F.book.v(book_nodes[0])
        if book not in bhsa_to_osis:
            raise ValueError(f"Unknown original BHSA book code at verse {node}: {book}")
        labels[node] = f"{bhsa_to_osis[book]}.{chapter}.{verse}"
    return labels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bhsa", required=True, type=Path, help="pinned BHSA tf/2021")
    parser.add_argument("--output", required=True, type=Path, help="research JSON report")
    parser.add_argument("--bhsa-commit", required=True, help="checked-out BHSA source commit")
    parser.add_argument("--max-examples", type=int, default=4)
    args = parser.parse_args(argv)

    from tf.fabric import Fabric

    api = Fabric(locations=str(args.bhsa), silent="deep").load(
        "book chapter verse", silent="deep"
    )
    if api is None:
        raise RuntimeError("Unable to load original BHSA syntax warp")
    labels = _verse_osis_labels(api)
    result = audit_syntax_oslots(api, verse_labels=labels, max_examples=args.max_examples)
    result["bhsa_commit"] = args.bhsa_commit
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "verses": result["verse_count"],
        "nodes": result["original_syntax_nodes"],
        "types": result["types"],
        "relations": result["relations"],
        "pair_denominator": result["pair_denominator"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
