"""Deterministic read-only export of internal cuts from a saved TF graph.

All splits come from persisted cant_parent/cant_cut_after edges and node
features. Source-word coordinates count MorphHB orthographic words, not BHSA
word slots (which may overlap).
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

BOUNDARY_FIELDS = (
    "verse_node",
    "osis_id",
    "system",
    "alignment",
    "phrase_node",
    "phrase_id",
    "depth",
    "first_unit",
    "last_unit",
    "cut_after_unit",
    "cut_accent",
    "phrase_word_count",
    "first_child_word_count",
    "second_child_word_count",
    "first_child_unit_count",
    "second_child_unit_count",
    "cut_after_word_index",
    "phrase_first_word_index",
    "phrase_last_word_index",
    "first_child_fraction",
    "signed_split",
    "first_bhsa_slot",
    "last_bhsa_slot",
    "bhsa_slot_count",
    "cut_unit_id",
    "cut_terminal_word_id",
    "source_uri",
)

REQUIRED_FEATURES = (
    "cant_parent",
    "cant_cut_after",
    "cant_terminal",
    "cant_member",
    "cant_root",
    "cant_phrase_id",
    "cant_phrase_depth",
    "cant_phrase_word_count",
    "cant_phrase_unit_count",
    "cant_first_unit",
    "cant_last_unit",
    "cant_cut_after_unit",
    "cant_cut_accent",
    "cant_unit_id",
    "cant_unit_ordinal",
    "cant_unit_word_count",
    "cant_terminal_accent",
    "cant_word_id",
    "cant_word_ordinal",
    "cantillation_system",
    "cantillation_alignment",
)


@dataclass(frozen=True)
class _Span:
    first: int
    last: int
    first_leaf: int
    last_leaf: int
    units: int
    words: int
    slots: frozenset[int]


def load_boundary_api(graph_path: Path):
    """Load only graph features needed by a boundary consumer, never rebuild trees."""
    from tf.fabric import Fabric

    if not graph_path.is_dir() or not (graph_path / "otype.tf").is_file():
        raise FileNotFoundError(f"Not a saved Text-Fabric graph directory: {graph_path}")
    api = Fabric(locations=str(graph_path), silent="deep").load(
        " ".join(REQUIRED_FEATURES), silent="deep"
    )
    if api is None:
        raise RuntimeError(f"Could not load boundary graph features from {graph_path}")
    return api


def iter_boundary_rows(api) -> Iterator[dict]:
    """Yield one boundary per saved cant_phrase, sorted by verse and textual span.

    The entire persisted parent/root/cut graph is validated as it is traversed.
    A corrupt graph fails closed rather than silently deriving a replacement cut.
    The consumer must exhaust the iterator to check for orphan nodes.
    """
    F, E = api.F, api.E
    verses = set(F.otype.s("verse"))
    phrases = set(F.otype.s("cant_phrase"))
    units = set(F.otype.s("cant_unit"))
    words = set(F.otype.s("cant_word"))
    graph_nodes = phrases | units
    if not verses or not units:
        raise ValueError("No verses or cantillation units in saved graph")
    if set(E.cant_root.data) != verses:
        raise ValueError("Graph root edge sources differ from BHSA verses")
    if set(E.cant_cut_after.data) != phrases:
        raise ValueError("Graph cut edge sources differ from cantillation phrases")
    if set(E.cant_terminal.data) != units:
        raise ValueError("Graph terminal edge sources differ from cantillation units")
    if set(E.cant_member.data) != words or any(
        len(targets) != 1 or next(iter(targets)) not in units
        for targets in E.cant_member.data.values()
    ):
        raise ValueError("Graph source word membership is incomplete or duplicated")

    children: dict[int, dict[int, int]] = {}
    parents: dict[int, int] = {}
    for child, targets in E.cant_parent.data.items():
        if child not in graph_nodes or len(targets) != 1:
            raise ValueError(f"Invalid or multiparent graph child: {child}")
        parent, position = next(iter(targets.items()))
        if parent not in phrases or position not in (1, 2):
            raise ValueError(f"Invalid graph parent or child position: {child}")
        branch = children.setdefault(parent, {})
        if position in branch:
            raise ValueError(f"Duplicate graph child position for phrase {parent}")
        branch[position] = child
        parents[child] = parent
    if any(set(children.get(node, {})) != {1, 2} for node in phrases):
        raise ValueError("Saved graph contains a phrase without two ordered children")

    source_uri = (
        api.TF.features["cant_word_id"].metaData.get("source")
        or "https://github.com/openscriptures/morphhb"
    )
    visited: set[int] = set()
    seen_words: set[int] = set()
    roots: set[int] = set()

    def per_verse(verse: int, root: int) -> Iterator[dict]:
        system = F.cantillation_system.v(verse)
        alignment = F.cantillation_alignment.v(verse)
        if system not in ("prose", "poetic") or alignment not in ("exact", "fuzzy"):
            raise ValueError(f"Missing or invalid verse source metadata at {verse}")

        sizes: dict[int, int] = {}
        word_orders: dict[int, tuple[int, ...]] = {}
        records: list[dict] = []
        verse_id: str | None = None

        def visit(node: int, depth: int) -> _Span:
            nonlocal verse_id
            if node in visited:
                raise ValueError(f"Cycle or shared child in saved graph at node {node}")
            visited.add(node)
            slots = frozenset(E.oslots.s(node))
            if not slots or min(slots) < 1 or max(slots) > F.otype.maxSlot:
                raise ValueError(f"Invalid BHSA slot bounds at node {node}")
            if node in units:
                ordinal = F.cant_unit_ordinal.v(node)
                count = F.cant_unit_word_count.v(node)
                unit_id = F.cant_unit_id.v(node)
                if (
                    type(ordinal) is not int or ordinal < 1
                    or type(count) is not int or count < 1
                    or not isinstance(unit_id, str) or not unit_id.endswith(f"#u{ordinal}")
                    or ordinal in sizes
                ):
                    raise ValueError(f"Invalid source unit ordinal/word count at {node}")
                identity = unit_id.rsplit("#u", 1)[0]
                if verse_id is None:
                    verse_id = identity
                elif verse_id != identity:
                    raise ValueError(f"Cross-verse unit in persisted graph at {node}")
                terminal = E.cant_terminal.f(node)
                if (
                    len(terminal) != 1 or terminal[0] not in words
                    or not F.cant_word_id.v(terminal[0])
                ):
                    raise ValueError(f"Missing source terminal at unit {node}")
                members = E.cant_member.t(node)
                if (
                    len(members) != count
                    or len(set(members)) != count
                    or any(member not in words or member in seen_words for member in members)
                ):
                    raise ValueError(f"Forged or missing source word membership at unit {node}")
                member_slots = frozenset(
                    slot for member in members for slot in E.oslots.s(member)
                )
                if member_slots != slots:
                    raise ValueError(f"Source word member slots differ from unit slots: {node}")
                positions = [(F.cant_word_ordinal.v(member), member) for member in members]
                if any(type(position) is not int or position < 1 for position, _ in positions):
                    raise ValueError(f"Invalid source word ordinal in unit {node}")
                positions.sort()
                first_word = positions[0][0]
                if (
                    [position for position, _ in positions]
                    != list(range(first_word, first_word + count))
                    or terminal[0] != positions[-1][1]
                ):
                    raise ValueError(f"Noncontiguous source member order at unit {node}")
                sizes[ordinal] = count
                word_orders[ordinal] = tuple(position for position, _ in positions)
                seen_words.update(members)
                return _Span(ordinal, ordinal, node, node, 1, count, slots)

            if node not in phrases:
                raise ValueError(f"Unknown cantillation graph node {node}")
            first = children[node][1]
            second = children[node][2]
            if parents.get(first) != node or parents.get(second) != node:
                raise ValueError(f"Inconsistent graph child/parent at phrase {node}")
            left = visit(first, depth + 1)
            right = visit(second, depth + 1)
            total = left.words + right.words
            if (
                left.last + 1 != right.first
                or F.cant_first_unit.v(node) != left.first
                or F.cant_last_unit.v(node) != right.last
                or F.cant_cut_after_unit.v(node) != left.last
                or F.cant_phrase_unit_count.v(node) != left.units + right.units
                or F.cant_phrase_word_count.v(node) != total
                or F.cant_phrase_depth.v(node) != depth
                or slots != left.slots | right.slots
            ):
                raise ValueError(f"Stored phrase span/count/slots disagree with children: {node}")
            cuts = E.cant_cut_after.f(node)
            if len(cuts) != 1 or cuts[0] != left.last_leaf:
                raise ValueError(f"Missing, extraneous or shifted cut edge at phrase {node}")
            accent = F.cant_cut_accent.v(node)
            if accent != F.cant_terminal_accent.v(cuts[0]):
                raise ValueError(f"Cut accent differs from terminal unit at phrase {node}")
            phrase_id = F.cant_phrase_id.v(node)
            expected = f"{verse_id}#p{left.first}-{right.last}"
            if phrase_id != expected:
                raise ValueError(f"Saved phrase ID does not match span: {node}")
            terminal = E.cant_terminal.f(cuts[0])
            if len(terminal) != 1 or terminal[0] not in words:
                raise ValueError(f"Missing cut terminal source word at phrase {node}")
            records.append({
                "verse_node": verse,
                "osis_id": verse_id,
                "system": system,
                "alignment": alignment,
                "phrase_node": node,
                "phrase_id": phrase_id,
                "depth": depth,
                "first_unit": left.first,
                "last_unit": right.last,
                "cut_after_unit": left.last,
                "cut_accent": accent,
                "phrase_word_count": total,
                "first_child_word_count": left.words,
                "second_child_word_count": right.words,
                "first_child_unit_count": left.units,
                "second_child_unit_count": right.units,
                "cut_after_word_index": None,
                "phrase_first_word_index": None,
                "phrase_last_word_index": None,
                "first_child_fraction": round(left.words / total, 6),
                "signed_split": round((right.words - left.words) / total, 6),
                "first_bhsa_slot": min(slots),
                "last_bhsa_slot": max(slots),
                "bhsa_slot_count": len(slots),
                "cut_unit_id": F.cant_unit_id.v(cuts[0]),
                "cut_terminal_word_id": F.cant_word_id.v(terminal[0]),
                "source_uri": source_uri,
            })
            return _Span(
                left.first, right.last, left.first_leaf, right.last_leaf,
                left.units + right.units, total, slots,
            )

        span = visit(root, 0)
        if not span.slots <= frozenset(E.oslots.s(verse)):
            raise ValueError(f"Cantillation source slots outside BHSA verse {verse}")
        if span.first != 1 or span.units != span.last or len(sizes) != span.units:
            raise ValueError(f"Noncontiguous source unit order at verse {verse}")
        prefix = [0]
        for ordinal in range(1, span.units + 1):
            end = prefix[-1] + sizes[ordinal]
            if word_orders[ordinal] != tuple(range(prefix[-1] + 1, end + 1)):
                raise ValueError(f"Source words are out of verse order at verse {verse}")
            prefix.append(end)
        if prefix[-1] != span.words:
            raise ValueError(f"Source word count drift at verse {verse}")
        for row in sorted(
            records, key=lambda r: (r["first_unit"], r["last_unit"], r["phrase_node"])
        ):
            row["cut_after_word_index"] = prefix[row["cut_after_unit"]]
            row["phrase_first_word_index"] = prefix[row["first_unit"] - 1] + 1
            row["phrase_last_word_index"] = prefix[row["last_unit"]]
            yield row


    for verse in sorted(verses):
        edges = E.cant_root.f(verse)
        if len(edges) != 1 or edges[0] not in graph_nodes:
            raise ValueError(f"Missing or invalid root for verse {verse}")
        root = edges[0]
        if root in roots or root in parents:
            raise ValueError(f"Duplicate, parented or shared root for verse {verse}")
        roots.add(root)

        yield from per_verse(verse, root)

    if visited != graph_nodes or seen_words != words or set(parents) != graph_nodes - roots:
        raise ValueError("Orphan or disconnected cantillation nodes in saved graph")


def write_boundary_rows(api, output: Path, *, fmt: str = "jsonl") -> int:
    """Atomically write deterministic JSONL/TSV; preserve old file on validation error."""
    if fmt not in ("jsonl", "tsv"):
        raise ValueError(f"Unsupported boundary output format: {fmt}")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            if fmt == "tsv":
                writer = csv.DictWriter(handle, fieldnames=BOUNDARY_FIELDS, delimiter="\t")
                writer.writeheader()
            for record in iter_boundary_rows(api):
                if fmt == "jsonl":
                    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                    handle.write(line + "\n")
                else:
                    writer.writerow(record)
                count += 1
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return count
