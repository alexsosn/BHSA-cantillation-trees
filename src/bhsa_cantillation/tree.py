"""Create accentual units and MorphHB-compatible binary trees."""

from __future__ import annotations

from .model import AccentUnit, WordAlignment


def make_units(alignments: list[WordAlignment]) -> list[AccentUnit]:
    """Group words through each disjunctive accent."""
    units: list[AccentUnit] = []
    pending: list[WordAlignment] = []
    for alignment in alignments:
        pending.append(alignment)
        if alignment.source.path is None:
            continue
        source_words = tuple(item.source for item in pending)
        slots = tuple(dict.fromkeys(slot for item in pending for slot in item.slots))
        text = " ".join(word.text.replace("/", "") + word.trailing for word in source_words).strip()
        units.append(
            AccentUnit(
                ordinal=len(units) + 1,
                path=alignment.source.path,
                slots=slots,
                text=text,
                accent_name=alignment.source.accent_name,
                source_words=source_words,
            )
        )
        pending = []
    if pending:
        raise ValueError("Verse ends with words not closed by a structural path")
    return units


def _leaf(unit: AccentUnit) -> dict:
    return {
        "path": unit.path,
        "slots": [unit.slots[0], unit.slots[-1]],
        "text": unit.text,
        "accent": unit.accent_name,
    }


def build_tree(units: list[AccentUnit], level: int = 0) -> dict:
    """Port MorphHB's binary-tree grouping algorithm to a JSON structure."""
    if not units:
        raise ValueError("Cannot build a tree without accentual units")
    if len(units) == 1:
        return _leaf(units[0])

    first_parts = units[0].path.split(".")
    code = first_parts[level] if level < len(first_parts) else None
    split = len(units)
    for index, unit in enumerate(units):
        parts = unit.path.split(".")
        candidate = parts[level] if level < len(parts) else None
        if candidate != code:
            split = index
            break

    if split == len(units):
        return build_tree(units, level + 1)
    if split == 0:
        raise ValueError("Invalid structural path ordering")

    left = build_tree(units[:split], level + 1)
    right = build_tree(units[split:], level)
    return {
        "accent": units[split - 1].accent_name,
        "children": [left, right],
    }
