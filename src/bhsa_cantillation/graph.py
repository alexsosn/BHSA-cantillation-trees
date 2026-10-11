"""Lossless source-derived word, unit and phrase graph for one cantillation verse.

This projection is independent of Text-Fabric warp materialization; the caller's
BHSA slot IDs are retained and may overlap between orthographic words or units.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import AccentUnit, WordAlignment


@dataclass(frozen=True)
class CantWord:
    id: str
    ordinal: int
    slots: tuple[int, ...]
    text: str


@dataclass(frozen=True)
class CantUnit:
    id: str
    ordinal: int
    path: str
    slots: tuple[int, ...]
    text: str
    accent: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class CantPhrase:
    id: str
    first_unit: int
    last_unit: int
    cut_after_unit: int
    slots: tuple[int, ...]
    accent: str
    depth: int


@dataclass
class CantGraph:
    osis_id: str
    words: dict[str, CantWord]
    units: dict[str, CantUnit]
    phrases: dict[str, CantPhrase]
    # Child ID -> (parent phrase ID, 1/2 in textual order).
    parents: dict[str, tuple[str, int]]
    # Phrase ID -> closing unit of the first child.
    cuts: dict[str, str]
    # Unit ID -> its disjunctive terminal source word.
    terminals: dict[str, str]
    root: str


def _union_slots(*groups: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(slot for group in groups for slot in group))


def project_graph(
    osis_id: str,
    alignments: list[WordAlignment],
    units: list[AccentUnit],
    tree: dict,
) -> CantGraph:
    """Project existing canonical JSON into a source-identical, ordered graph."""
    if not osis_id or not units or not alignments:
        raise ValueError("Graph requires verse ID, source alignments and units")

    words: dict[str, CantWord] = {}
    for ordinal, alignment in enumerate(alignments, start=1):
        source_id = alignment.source.source_id
        if not source_id:
            raise ValueError("Missing MorphHB source word identifier")
        if source_id in words:
            raise ValueError(f"Duplicate MorphHB source word identifier: {source_id}")
        if not alignment.slots:
            raise ValueError(f"Missing BHSA slots for source word: {source_id}")
        words[source_id] = CantWord(
            source_id, ordinal, alignment.slots, alignment.source.text
        )

    graph_units: dict[str, CantUnit] = {}
    unit_ids: list[str] = []
    unit_source_ids: list[str] = []
    for ordinal, unit in enumerate(units, start=1):
        if unit.ordinal != ordinal:
            raise ValueError("Accentual unit ordinals are not in textual order")
        ids = tuple(word.source_id for word in unit.source_words)
        if not ids or any(not source_id for source_id in ids):
            raise ValueError("Each unit requires source word identifiers")
        if any(source_id not in words for source_id in ids):
            raise ValueError("Unit references an unknown source word")
        expected_slots = _union_slots(*(words[source_id].slots for source_id in ids))
        if expected_slots != unit.slots:
            raise ValueError("Unit slots differ from source word slots")
        unit_id = f"{osis_id}#u{ordinal}"
        unit_ids.append(unit_id)
        unit_source_ids.extend(ids)
        graph_units[unit_id] = CantUnit(
            unit_id, ordinal, unit.path, unit.slots, unit.text, unit.accent_name, ids
        )

    if unit_source_ids != list(words):
        raise ValueError("Unit source words do not match source alignment order")

    graph = CantGraph(
        osis_id=osis_id,
        words=words,
        units=graph_units,
        phrases={},
        parents={},
        cuts={},
        terminals={
            unit_id: graph_units[unit_id].source_ids[-1] for unit_id in unit_ids
        },
        root="",
    )

    def walk(node: dict, first_index: int, depth: int) -> tuple[str, int, tuple[int, ...]]:
        if not isinstance(node, dict):
            raise ValueError("Expected a binary tree node or leaf dictionary")
        children = node.get("children")
        if children is None:
            if first_index >= len(units):
                raise ValueError("Tree has more leaves than accentual units")
            unit = units[first_index]
            expected_leaf = {
                "path": unit.path,
                "slots": [unit.slots[0], unit.slots[-1]],
                "text": unit.text,
                "accent": unit.accent_name,
            }
            if node != expected_leaf:
                raise ValueError("Canonical JSON leaf differs from corresponding unit")
            return unit_ids[first_index], first_index + 1, unit.slots

        if not isinstance(children, list) or len(children) != 2:
            raise ValueError("Each internal cantillation node must have two binary children")
        first_child, split, first_slots = walk(children[0], first_index, depth + 1)
        second_child, end, second_slots = walk(children[1], split, depth + 1)
        if split >= end or split == first_index:
            raise ValueError("Empty split in canonical cantillation tree")
        closing_unit = units[split - 1]
        if node.get("accent") != closing_unit.accent_name:
            raise ValueError("Tree cut accent differs from terminal source unit")
        phrase_id = f"{osis_id}#p{first_index + 1}-{end}"
        if phrase_id in graph.phrases:
            raise ValueError(f"Duplicate phrase span: {phrase_id}")
        graph.phrases[phrase_id] = CantPhrase(
            phrase_id,
            first_index + 1,
            end,
            split,
            _union_slots(first_slots, second_slots),
            closing_unit.accent_name,
            depth,
        )
        graph.parents[first_child] = (phrase_id, 1)
        graph.parents[second_child] = (phrase_id, 2)
        graph.cuts[phrase_id] = unit_ids[split - 1]
        return phrase_id, end, graph.phrases[phrase_id].slots

    root, consumed, _ = walk(tree, 0, 0)
    if consumed != len(units):
        raise ValueError("Tree leaf count differs from unit count")
    graph.root = root
    if len(graph.phrases) != len(units) - 1:
        raise ValueError("Graph is not a full binary cantillation tree")
    return graph


def reconstruct_tree(graph: CantGraph) -> dict:
    """Reconstruct the canonical JSON tree using only the graph representation."""
    children: dict[str, dict[int, str]] = {}
    for child_id, (parent_id, position) in graph.parents.items():
        children.setdefault(parent_id, {})[position] = child_id

    def walk(node_id: str) -> dict:
        if node_id in graph.units:
            unit = graph.units[node_id]
            return {
                "path": unit.path,
                "slots": [unit.slots[0], unit.slots[-1]],
                "text": unit.text,
                "accent": unit.accent,
            }
        phrase = graph.phrases[node_id]
        ordered = children[node_id]
        if set(ordered) != {1, 2}:
            raise ValueError("Graph phrase lacks two ordered binary children")
        return {
            "accent": phrase.accent,
            "children": [walk(ordered[1]), walk(ordered[2])],
        }

    return walk(graph.root)
