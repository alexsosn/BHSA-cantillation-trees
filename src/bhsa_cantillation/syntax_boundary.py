"""Compare persisted cantillation cuts with ends of original BHSA syntactic nodes.

A MorphHB word index is *never* treated as a BHSA slot index. Comparable
internal cuts require an exact verse alignment and two ordered, adjacent,
non-overlapping consecutive BHSA child slot sets. Other cuts are inconclusive.
Gapped BHSA syntax objects may still have a well-defined final occupied slot.
"""

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

SYNTAX_TYPES = ("phrase", "phrase_atom", "clause_atom", "clause")
SYNTAX_BOUNDARY_FIELDS = (
    "verse_node",
    "osis_id",
    "system",
    "alignment",
    "phrase_node",
    "phrase_id",
    "depth",
    "cut_accent",
    "cut_after_word_index",
    "slot_status",
    "bhsa_cut_after_slot",
    "first_child_bhsa_slots",
    "second_child_bhsa_slots",
    "ends_phrase",
    "phrase_nodes",
    "ends_phrase_atom",
    "phrase_atom_nodes",
    "ends_clause_atom",
    "clause_atom_nodes",
    "ends_clause",
    "clause_nodes",
)


def _ordered_adjacent_child_slots(left: frozenset[int], right: frozenset[int]) -> bool:
    """Only a single strictly ordered BHSA slot boundary is comparable."""
    return (
        bool(left) and bool(right)
        and not left & right
        and len(left) == max(left) - min(left) + 1
        and len(right) == max(right) - min(right) + 1
        and max(left) + 1 == min(right)
    )


def _original_syntax_endpoint_index(api):
    """Index original BHSA object ends by verse/type/slot, excluding cross-verse nodes.

    A functional phrase or clause may have gaps. Its final *occupied* slot
    is still defined; gaps must never be filled to infer set containment.
    """
    E, F = api.E, api.F
    syntax_nodes = {kind: F.otype.s(kind) for kind in SYNTAX_TYPES}
    for kind, nodes in syntax_nodes.items():
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

    endpoints: dict[tuple[int, str, int], list[int]] = {}
    exclusions: dict[str, Counter[str]] = {
        kind: Counter({"missing_slots": 0, "unassigned_slots": 0, "cross_verse": 0})
        for kind in SYNTAX_TYPES
    }
    for kind, nodes in syntax_nodes.items():
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
            owner = next(iter(owners))
            endpoints.setdefault((owner, kind, max(slots)), []).append(node)
    # Sort node identities independently of Text-Fabric iteration semantics.
    for nodes in endpoints.values():
        nodes.sort()
    return endpoints, {
        kind: {reason: exclusions[kind][reason]
               for reason in ("missing_slots", "unassigned_slots", "cross_verse")}
        for kind in SYNTAX_TYPES
    }


def _children_by_phrase(api) -> dict[int, dict[int, int]]:
    children: dict[int, dict[int, int]] = {}
    for child, targets in api.E.cant_parent.data.items():
        for parent, position in targets.items():
            branch = children.setdefault(parent, {})
            if position in branch:
                raise ValueError(f"Duplicate saved graph child position at {parent}")
            branch[position] = child
    return children


def iter_syntax_boundary_rows(
    api, *, verse_ids: Collection[str] | None = None, _end_index=None
) -> Iterator[dict]:
    """Yield one diagnostic per saved cant_phrase, after graph validation.

    Nonselected verses and their graph structure are still validated by the
    underlying persisted-boundary iterator. Syntax exclusions are *global*.
    """
    if _end_index is None:
        _end_index, _ = _original_syntax_endpoint_index(api)
    children = _children_by_phrase(api)
    E = api.E

    for row in iter_boundary_rows(api, verse_ids=verse_ids):
        phrase = row["phrase_node"]
        branch = children.get(phrase)
        if branch is None or set(branch) != {1, 2}:
            raise ValueError(f"Missing two ordered saved children at {phrase}")
        first = frozenset(E.oslots.s(branch[1]))
        second = frozenset(E.oslots.s(branch[2]))
        if row["alignment"] != "exact":
            status, cut_slot = "fuzzy_alignment", None
        elif not _ordered_adjacent_child_slots(first, second):
            status, cut_slot = "ambiguous_slots", None
        else:
            status, cut_slot = "comparable", max(first)

        record = {
            key: row[key] for key in (
                "verse_node", "osis_id", "system", "alignment", "phrase_node", "phrase_id",
                "depth", "cut_accent", "cut_after_word_index",
            )
        }
        record.update({
            "slot_status": status,
            "bhsa_cut_after_slot": cut_slot,
            "first_child_bhsa_slots": _slot_span(first),
            "second_child_bhsa_slots": _slot_span(second),
        })
        for kind in SYNTAX_TYPES:
            nodes = (
                _end_index.get((row["verse_node"], kind, cut_slot), [])
                if cut_slot is not None else []
            )
            record[f"ends_{kind}"] = bool(nodes) if cut_slot is not None else None
            record[f"{kind}_nodes"] = ";".join(str(node) for node in nodes)
        yield record


def write_syntax_boundary_rows(
    api, output: Path, *, fmt: str = "jsonl", verse_ids: Collection[str] | None = None
) -> dict:
    """Atomically export fixed-schema JSONL/TSV with truthful cut denominators."""
    if fmt not in ("jsonl", "tsv"):
        raise ValueError(f"Unsupported syntax boundary output format: {fmt}")
    endpoints, exclusions = _original_syntax_endpoint_index(api)
    output.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    matches: Counter[str] = Counter({kind: 0 for kind in SYNTAX_TYPES})
    grouped: dict[tuple[str, str | None], dict[str, Counter[str]]] = {}
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            if fmt == "tsv":
                writer = csv.DictWriter(
                    handle, fieldnames=SYNTAX_BOUNDARY_FIELDS, delimiter="\t"
                )
                writer.writeheader()
            for record in iter_syntax_boundary_rows(
                api, verse_ids=verse_ids, _end_index=endpoints
            ):
                status = record["slot_status"]
                counts[status] += 1
                # A key includes the accentuation system: identical labels
                # in poetic and prose passages never share a denominator.
                key = (record["system"], record["cut_accent"])
                if key not in grouped:
                    grouped[key] = {
                        "statuses": Counter(),
                        "matches": Counter({kind: 0 for kind in SYNTAX_TYPES}),
                    }
                stratum = grouped[key]
                stratum["statuses"][status] += 1
                for kind in SYNTAX_TYPES:
                    if record[f"ends_{kind}"] is True:
                        matches[kind] += 1
                        stratum["matches"][kind] += 1
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
    by_system_accent = []
    # Text-Fabric can represent an absent cut-accent label as None. Keep
    # the unknown-label stratum rather than crashing when sorting mixed
    # (string, None) keys after the output file has already been replaced.
    for (system, accent), stratum in sorted(
        grouped.items(),
        key=lambda item: (
            item[0][0], item[0][1] is None, item[0][1] or "",
        ),
    ):
        statuses = stratum["statuses"]
        hits = stratum["matches"]
        comparable = statuses["comparable"]
        by_system_accent.append({
            "system": system,
            "accent": accent,
            "cuts": statuses.total(),
            "comparable": comparable,
            "status_counts": dict(sorted(statuses.items())),
            "matches_by_type": {kind: hits[kind] for kind in SYNTAX_TYPES},
            "match_fraction_by_type": {
                kind: round(hits[kind] / comparable, 6) if comparable else None
                for kind in SYNTAX_TYPES
            },
        })
    return {
        "cuts": counts.total(),
        "comparable": counts["comparable"],
        "status_counts": dict(sorted(counts.items())),
        "matches_by_type": {kind: matches[kind] for kind in SYNTAX_TYPES},
        "syntax_node_exclusions_global": exclusions,
        "by_system_accent": by_system_accent,
    }
