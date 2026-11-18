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


from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from collections.abc import Collection, Iterator
from pathlib import Path

from .boundaries import iter_boundary_rows
from .half_verse import _slot_span
from .syntax_boundary import (
    SYNTAX_TYPES,
    _children_by_phrase,
    _ordered_adjacent_child_slots,
)

RELATION_FIELDS = (
    "verse_node",
    "osis_id",
    "system",
    "alignment",
    "phrase_node",
    "phrase_id",
    "depth",
    "cut_accent",
    "cut_after_word_index",
    "cantillation_bhsa_slots",
    "slot_status",
    "syntax_type",
    "syntax_node",
    "syntax_bhsa_slots",
    "relation",
)


def _original_syntax_by_verse(api, selected_verses: set[int]):
    """Scan original BHSA objects once; retain exact sets only in selected verses.

    Original BHSA functional phrase/clause objects can be discontinuous or
    cross a verse boundary. Never infer ownership from their min/max envelopes.
    Global exclusions are counted before the selection filter.
    """
    F, E = api.F, api.E
    by_kind = {kind: tuple(F.otype.s(kind)) for kind in SYNTAX_TYPES}
    for kind, nodes in by_kind.items():
        if not nodes:
            raise ValueError(f"Missing original BHSA syntax layer: {kind}")

    slot_owner: dict[int, int] = {}
    for verse in F.otype.s("verse"):
        slots = E.oslots.s(verse)
        if not slots:
            raise ValueError(f"Missing original BHSA verse slots: {verse}")
        for slot in slots:
            if slot in slot_owner:
                raise ValueError(f"BHSA slot {slot} belongs to multiple verses")
            slot_owner[slot] = verse

    by_verse: dict[int, list[tuple[str, int, frozenset[int]]]] = {
        verse: [] for verse in selected_verses
    }
    selected_counts = {kind: 0 for kind in SYNTAX_TYPES}
    exclusions = {
        kind: {"missing_slots": 0, "unassigned_slots": 0, "cross_verse": 0}
        for kind in SYNTAX_TYPES
    }
    for kind, nodes in by_kind.items():
        for node in nodes:
            slots = frozenset(E.oslots.s(node))
            if not slots:
                exclusions[kind]["missing_slots"] += 1
                continue
            owners = {slot_owner.get(slot) for slot in slots}
            if None in owners:
                exclusions[kind]["unassigned_slots"] += 1
                continue
            if len(owners) != 1:
                exclusions[kind]["cross_verse"] += 1
                continue
            verse = next(iter(owners))
            if verse in selected_verses:
                by_verse[verse].append((kind, node, slots))
                selected_counts[kind] += 1
    # Type order is the documented fixed schema; numeric node order within type.
    for records in by_verse.values():
        records.sort(key=lambda item: (SYNTAX_TYPES.index(item[0]), item[1]))
    return by_verse, selected_counts, exclusions, {
        kind: len(nodes) for kind, nodes in by_kind.items()
    }


def _prepare(api, verse_ids: Collection[str] | None):
    """Validate the full saved graph, then prepare a bounded original-BHSA view."""
    if not verse_ids:
        raise ValueError("syntax-relations requires at least one --verse selection")
    selected = set(verse_ids)
    # Exhausting the iterator validates all verses, including unselected ones
    # and disconnected roots, before opening or replacing the export file.
    boundary_rows = list(iter_boundary_rows(api, verse_ids=selected))
    F, E = api.F, api.E
    selected_verses = set()
    for verse in F.otype.s("verse"):
        root = E.cant_root.f(verse)[0]
        if F.otype.v(root) == "cant_phrase":
            osis = F.cant_phrase_id.v(root).split("#p", 1)[0]
        else:
            osis = F.cant_unit_id.v(root).rsplit("#u", 1)[0]
        if osis in selected:
            selected_verses.add(verse)
    by_verse, candidates, exclusions, totals = _original_syntax_by_verse(
        api, selected_verses
    )
    return boundary_rows, by_verse, _children_by_phrase(api), candidates, exclusions, totals


def _iter_prepared_rows(api, boundary_rows, by_verse, children) -> Iterator[dict]:
    E = api.E
    for cut in boundary_rows:
        phrase = cut["phrase_node"]
        branch = children.get(phrase)
        if branch is None or set(branch) != {1, 2}:
            raise ValueError(f"Missing two ordered saved children at {phrase}")
        first = frozenset(E.oslots.s(branch[1]))
        second = frozenset(E.oslots.s(branch[2]))
        if cut["alignment"] != "exact":
            status = "fuzzy_alignment"
        elif not _ordered_adjacent_child_slots(first, second):
            status = "ambiguous_slots"
        else:
            status = "comparable"

        base = {
            key: cut[key] for key in (
                "verse_node", "osis_id", "system", "alignment", "phrase_node",
                "phrase_id", "depth", "cut_accent", "cut_after_word_index",
            )
        }
        base["cantillation_bhsa_slots"] = _slot_span(E.oslots.s(phrase))
        base["slot_status"] = status
        # A row with null syntax fields records an inconclusive phrase (or a
        # comparable phrase without any eligible original syntax candidates).
        if status != "comparable" or not by_verse[cut["verse_node"]]:
            yield {
                **base, "syntax_type": None, "syntax_node": None,
                "syntax_bhsa_slots": "", "relation": None,
            }
            continue
        cant_slots = frozenset(E.oslots.s(phrase))
        for kind, node, original_slots in by_verse[cut["verse_node"]]:
            yield {
                **base,
                "syntax_type": kind,
                "syntax_node": node,
                "syntax_bhsa_slots": _slot_span(original_slots),
                "relation": classify_slot_relation(cant_slots, original_slots),
            }


def iter_syntax_relation_rows(
    api, *, verse_ids: Collection[str] | None
) -> Iterator[dict]:
    """Yield exact per-pair BHSA slot-set relations for selected saved phrases.

    All rows are from the persisted cantillation tree and original BHSA nodes.
    Inconclusive projections have a null relation, not a false disagreement.
    """
    boundaries, by_verse, children, _, _, _ = _prepare(api, verse_ids)
    yield from _iter_prepared_rows(api, boundaries, by_verse, children)


def write_syntax_relation_rows(
    api, output: Path, *, fmt: str = "jsonl", verse_ids: Collection[str] | None
) -> dict:
    """Atomically export a bounded pairwise report and truthful denominators."""
    if fmt not in ("jsonl", "tsv"):
        raise ValueError(f"Unsupported syntax relation output format: {fmt}")
    boundaries, by_verse, children, candidates, exclusions, totals = _prepare(
        api, verse_ids
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    statuses: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    by_type: dict[str, Counter[str]] = {
        kind: Counter() for kind in SYNTAX_TYPES
    }
    seen_phrases: set[int] = set()
    comparisons = 0
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            if fmt == "tsv":
                writer = csv.DictWriter(
                    handle, fieldnames=RELATION_FIELDS, delimiter="\t"
                )
                writer.writeheader()
            for record in _iter_prepared_rows(api, boundaries, by_verse, children):
                phrase = record["phrase_node"]
                if phrase not in seen_phrases:
                    seen_phrases.add(phrase)
                    statuses[record["slot_status"]] += 1
                relation = record["relation"]
                if relation is not None:
                    comparisons += 1
                    relations[relation] += 1
                    by_type[record["syntax_type"]][relation] += 1
                if fmt == "jsonl":
                    handle.write(
                        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                    )
                else:
                    writer.writerow(record)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if len(seen_phrases) != len(boundaries):
        raise ValueError("Report omitted a saved phrase")
    return {
        "cuts": len(boundaries),
        "comparable": statuses["comparable"],
        "status_counts": dict(sorted(statuses.items())),
        "comparisons": comparisons,
        "relation_counts": dict(sorted(relations.items())),
        "relations_by_type": {
            kind: dict(sorted(by_type[kind].items())) for kind in SYNTAX_TYPES
        },
        "candidates_selected_by_type": candidates,
        "syntax_node_totals_global": totals,
        "syntax_node_exclusions_global": exclusions,
    }
