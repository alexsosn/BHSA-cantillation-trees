"""Read-only comparison of saved cantillation root cuts to BHSA half-verse slots.

This report compares *sets of BHSA word slots*, never a MorphHB source-word
index to a BHSA slot number. Ambiguous source alignment is inconclusive.
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

HALF_VERSE_FIELDS = (
    "verse_node",
    "osis_id",
    "system",
    "alignment",
    "status",
    "root_phrase_node",
    "root_cut_after_word_index",
    "half_verse_count",
    "half_verse_nodes",
    "half_verse_spans",
    "first_half_bhsa_slots",
    "root_left_bhsa_slots",
    "root_right_bhsa_slots",
    "root_left_bhsa_slot_count",
    "root_right_bhsa_slot_count",
    "root_overlap_slot_count",
)


def _slot_span(slots: Collection[int]) -> str:
    """Render exact sets as comma-separated inclusive ranges, not just min/max."""
    order = sorted(slots)
    if not order:
        return ""
    ranges = []
    first = last = order[0]
    for slot in order[1:]:
        if slot == last + 1:
            last = slot
        else:
            ranges.append(str(first) if first == last else f"{first}-{last}")
            first = last = slot
    ranges.append(str(first) if first == last else f"{first}-{last}")
    return ",".join(ranges)


def _half_verses_by_verse(api, verses: list[int]) -> dict[int, list[tuple[int, frozenset[int]]]]:
    """Map original BHSA half_verse nodes to their source verse without rebuilding them."""
    E, F = api.E, api.F
    slot_owner = {}
    for verse in verses:
        slots = E.oslots.s(verse)
        if not slots:
            raise ValueError(f"Missing BHSA verse slots at {verse}")
        for slot in slots:
            if slot in slot_owner:
                raise ValueError(f"BHSA slot {slot} belongs to multiple verses")
            slot_owner[slot] = verse

    result: dict[int, list[tuple[int, frozenset[int]]]] = {v: [] for v in verses}
    for node in F.otype.s("half_verse"):
        slots = frozenset(E.oslots.s(node))
        owners = {slot_owner.get(slot) for slot in slots}
        if not slots or None in owners or len(owners) != 1:
            raise ValueError(f"BHSA half_verse {node} crosses verses or lacks source slots")
        verse = next(iter(owners))
        result[verse].append((node, slots))
    for parts in result.values():
        parts.sort(key=lambda pair: (min(pair[1]), pair[0]))
    return result


def _valid_binary_partition(
    half_verses: list[tuple[int, frozenset[int]]], verse_slots: frozenset[int]
) -> bool:
    if len(half_verses) != 2:
        return False
    left, right = half_verses[0][1], half_verses[1][1]
    return (
        bool(left) and bool(right)
        and not left & right
        and left | right == verse_slots
        and len(left) == max(left) - min(left) + 1
        and len(right) == max(right) - min(right) + 1
        and max(left) + 1 == min(right)
    )


def iter_half_verse_rows(
    api, *, verse_ids: Collection[str] | None = None
) -> Iterator[dict]:
    """Yield one per-verse comparison, validating the entire saved graph first.

    Agreement is only assessed for a non-singleton root, two complete disjoint
    BHSA half-verses, exact MorphHB alignment, and a disjoint complete source
    root slot partition. Every other status is explicitly inconclusive.
    """
    F, E = api.F, api.E
    selected = set(verse_ids) if verse_ids is not None else None
    verses = sorted(F.otype.s("verse"))
    half_by_verse = _half_verses_by_verse(api, verses)

    # A fully exhausted boundary iterator validates the persisted TF graph,
    # including unselected verses, orphan nodes, and singleton identities.
    root_rows = {}
    for record in iter_boundary_rows(api):
        if record["depth"] == 0:
            verse = record["verse_node"]
            if verse in root_rows:
                raise ValueError(f"Duplicate persisted root split at verse {verse}")
            root_rows[verse] = record

    root_phrases = {row["phrase_node"] for row in root_rows.values()}
    root_children: dict[int, dict[int, int]] = {}
    for child, targets in E.cant_parent.data.items():
        for parent, position in targets.items():
            if parent in root_phrases:
                root_children.setdefault(parent, {})[position] = child

    seen_ids = set()
    for verse in verses:
        root_node = E.cant_root.f(verse)[0]
        root_row = root_rows.get(verse)
        if root_row is None:
            unit_id = F.cant_unit_id.v(root_node)
            if not isinstance(unit_id, str) or not unit_id.endswith("#u1"):
                raise ValueError(f"Missing singleton OSIS identity at verse {verse}")
            osis_id = unit_id.rsplit("#u", 1)[0]
        else:
            osis_id = root_row["osis_id"]
            if root_node != root_row["phrase_node"]:
                raise ValueError(f"Persisted root phrase disagrees with boundary at {verse}")
        if not osis_id or osis_id in seen_ids:
            raise ValueError(f"Missing or duplicate OSIS identity at verse {verse}")
        seen_ids.add(osis_id)

        parts = half_by_verse[verse]
        verse_slots = frozenset(E.oslots.s(verse))
        first_half = parts[0][1] if parts else frozenset()
        left = right = frozenset()
        if root_row is not None:
            children = root_children.get(root_node)
            if children is None or set(children) != {1, 2}:
                raise ValueError(f"Missing ordered root children at verse {verse}")
            left = frozenset(E.oslots.s(children[1]))
            right = frozenset(E.oslots.s(children[2]))
        overlap = len(left & right)

        alignment = F.cantillation_alignment.v(verse)
        if root_row is None:
            status = "no_root_split"
        elif not parts:
            status = "missing_half_verse"
        elif len(parts) != 2:
            status = "nonbinary_half_verse"
        elif not _valid_binary_partition(parts, verse_slots):
            status = "ambiguous_half_verse"
        elif alignment != "exact":
            status = "fuzzy_alignment"
        elif overlap or left | right != verse_slots:
            status = "ambiguous_root_slots"
        else:
            status = "match" if left == first_half else "mismatch"

        if selected is None or osis_id in selected:
            yield {
                "verse_node": verse,
                "osis_id": osis_id,
                "system": F.cantillation_system.v(verse),
                "alignment": alignment,
                "status": status,
                "root_phrase_node": root_node if root_row is not None else None,
                "root_cut_after_word_index": (
                    root_row["cut_after_word_index"] if root_row is not None else None
                ),
                "half_verse_count": len(parts),
                "half_verse_nodes": ";".join(str(node) for node, _ in parts),
                "half_verse_spans": ";".join(_slot_span(slots) for _, slots in parts),
                "first_half_bhsa_slots": _slot_span(first_half),
                "root_left_bhsa_slots": _slot_span(left),
                "root_right_bhsa_slots": _slot_span(right),
                "root_left_bhsa_slot_count": len(left),
                "root_right_bhsa_slot_count": len(right),
                "root_overlap_slot_count": overlap,
            }

    missing = selected - seen_ids if selected is not None else set()
    if missing:
        raise ValueError(f"Unknown OSIS verse ID(s): {', '.join(sorted(missing))}")


def write_half_verse_rows(
    api, output: Path, *, fmt: str = "jsonl", verse_ids: Collection[str] | None = None
) -> dict:
    """Atomically export the fixed schema and return a truthful comparison denominator."""
    if fmt not in ("jsonl", "tsv"):
        raise ValueError(f"Unsupported half-verse output format: {fmt}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    counts: Counter[str] = Counter()
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            if fmt == "tsv":
                writer = csv.DictWriter(handle, fieldnames=HALF_VERSE_FIELDS, delimiter="\t")
                writer.writeheader()
            for record in iter_half_verse_rows(api, verse_ids=verse_ids):
                counts[record["status"]] += 1
                if fmt == "jsonl":
                    handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                else:
                    writer.writerow(record)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "verses": counts.total(),
        "comparable": counts["match"] + counts["mismatch"],
        "status_counts": dict(sorted(counts.items())),
    }
