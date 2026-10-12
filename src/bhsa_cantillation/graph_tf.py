"""Project canonical cantillation graphs onto appended Text-Fabric node types.

Text-Fabric's modify(addTypes=...) renumbers new nodes *in sorted type order*
and restricts references to other newly-added types. We therefore materialize
the full derived warp first, then save cross-type edges using its final node IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .graph import CantGraph, reconstruct_tree
from .model import WordAlignment

TYPES = ("cant_phrase", "cant_unit", "cant_word")
EDGES = ("cant_parent", "cant_cut_after", "cant_terminal", "cant_member", "cant_root")


@dataclass
class GraphTFBatch:
    add_types: dict[str, dict]
    edges: dict[str, dict[int, dict[int, int] | set[int]]]
    ranges: dict[str, tuple[int, int]]
    counts: dict[str, int]

    @property
    def max_node(self) -> int:
        return max((last for _, last in self.ranges.values()), default=0)


def _dedup_slots(slots, max_slot: int) -> set[int]:
    if not slots or any(type(slot) is not int or not 1 <= slot <= max_slot for slot in slots):
        raise ValueError("Cantillation node has slots outside the BHSA word slot range")
    return set(slots)


class GraphTFCollector:
    """Accumulate one or more validated verse graphs in stable textual order."""

    def __init__(self, base_max_node: int, max_slot: int):
        if not 0 < max_slot < base_max_node:
            raise ValueError("BHSA original max node must exceed the word-slot range")
        self.base_max_node = base_max_node
        self.max_slot = max_slot
        self._records: dict[str, list[tuple[set[int], dict]]] = {t: [] for t in TYPES}
        self._links: dict[str, list[tuple[tuple[str, int] | int, tuple[str, int], int]]] = {
            name: [] for name in EDGES
        }
        self._verses: set[int] = set()
        self._osis_ids: set[str] = set()

    def append(self, verse_node: int, graph: CantGraph, alignments: list[WordAlignment]) -> None:
        """Add a complete canonical verse without collapsing overlapping BHSA slots."""
        if not self.max_slot < verse_node <= self.base_max_node:
            raise ValueError("BHSA verse node outside the original non-slot ID range")
        if verse_node in self._verses or graph.osis_id in self._osis_ids:
            raise ValueError("duplicate verse or OSIS identifier")
        if not graph.osis_id or not graph.words or not graph.units:
            raise ValueError("Cannot materialize an empty verse graph")

        words = list(graph.words.items())
        if [a.source.source_id for a in alignments] != [w[0] for w in words]:
            raise ValueError("Graph source word order differs from source alignments")
        if not all(
            source.source.text == word.text
            and source.slots == word.slots
            for source, (_, word) in zip(alignments, words, strict=True)
        ):
            raise ValueError("Graph source metadata differs from source alignments")

        unit_ids = list(graph.units)
        all_ids = set(graph.units) | set(graph.phrases)
        if graph.root not in all_ids or graph.root in graph.parents:
            raise ValueError("Invalid graph root")
        if (
            len(graph.phrases) != len(graph.units) - 1
            or set(graph.cuts) != set(graph.phrases)
            or set(graph.terminals) != set(graph.units)
            or set(graph.parents) != all_ids - {graph.root}
        ):
            raise ValueError("Graph binary structure or terminal/cut edges are incomplete")
        child_places: dict[str, set[int]] = {}
        for child_id, (parent_id, position) in graph.parents.items():
            if parent_id not in graph.phrases or position not in (1, 2):
                raise ValueError("Invalid graph parent link")
            child_places.setdefault(parent_id, set()).add(position)
        if any(child_places.get(pid) != {1, 2} for pid in graph.phrases):
            raise ValueError("Graph parent positions do not form full binary branches")

        for phrase_id, phrase in graph.phrases.items():
            expected_cut = f"{graph.osis_id}#u{phrase.cut_after_unit}"
            if graph.cuts[phrase_id] != expected_cut:
                raise ValueError("Graph cut unit is not the recorded span boundary")
            if expected_cut not in graph.units or phrase.accent != graph.units[expected_cut].accent:
                raise ValueError("Graph cut accent does not match the unit closing the split")

        member_ids = [word_id for unit in graph.units.values() for word_id in unit.source_ids]
        if member_ids != list(graph.words):
            raise ValueError("Graph source words do not match unit member order")
        if any(
            graph.terminals[unit_id] != unit.source_ids[-1]
            for unit_id, unit in graph.units.items()
        ):
            raise ValueError("Graph unit terminal does not match final MorphHB source word")
        # Also fail on forged or cyclic graph that cannot reconstruct a binary JSON tree.
        reconstruct_tree(graph)

        entries: dict[str, list[tuple[str, set[int], dict]]] = {t: [] for t in TYPES}
        for word_id, word in words:
            source = alignments[word.ordinal - 1].source
            features = {
                "cant_word_id": word_id,
                "cant_word_ordinal": word.ordinal,
                "cant_word_text": word.text,
                "cant_word_accent": source.accent_name,
                "cant_word_role": source.accent_type,
                "cant_word_status": "catalogued" if source.accent_catalogued else "unicode-fallback",
            }
            if source.path is not None:
                features["cant_word_path"] = source.path
            if source.accent_marks:
                features["cant_word_marks"] = source.accent_marks
            if source.accent_catalogued and source.accent_rank is not None:
                features["cant_word_catalog_rank"] = source.accent_rank
            if source.accent_catalogued and source.accent_final is not None:
                features["cant_word_catalog_final"] = int(source.accent_final)
            entries["cant_word"].append(
                (word_id, _dedup_slots(word.slots, self.max_slot), features)
            )

        for unit_id, unit in graph.units.items():
            features = {
                "cant_unit_id": unit_id,
                "cant_unit_ordinal": unit.ordinal,
                "cant_unit_path": unit.path,
                "cant_unit_text": unit.text,
                "cant_terminal_accent": unit.accent,
                "cant_unit_word_count": len(unit.source_ids),
                "cant_unit_slot_count": len(unit.slots),
            }
            entries["cant_unit"].append(
                (unit_id, _dedup_slots(unit.slots, self.max_slot), features)
            )

        prefix = [0]
        for unit in graph.units.values():
            prefix.append(prefix[-1] + len(unit.source_ids))
        for phrase_id, phrase in sorted(
            graph.phrases.items(), key=lambda item: (item[1].first_unit, item[1].last_unit)
        ):
            features = {
                "cant_phrase_id": phrase_id,
                "cant_cut_accent": phrase.accent,
                "cant_phrase_depth": phrase.depth,
                "cant_phrase_unit_count": phrase.last_unit - phrase.first_unit + 1,
                "cant_phrase_word_count": (
                    prefix[phrase.last_unit] - prefix[phrase.first_unit - 1]
                ),
                "cant_first_unit": phrase.first_unit,
                "cant_last_unit": phrase.last_unit,
                "cant_cut_after_unit": phrase.cut_after_unit,
            }
            entries["cant_phrase"].append(
                (phrase_id, _dedup_slots(phrase.slots, self.max_slot), features)
            )

        local_ids: dict[str, tuple[str, int]] = {}
        for node_type in TYPES:
            start = len(self._records[node_type])
            for offset, (key, _, _) in enumerate(entries[node_type], start=1):
                if key in local_ids:
                    raise ValueError("Duplicate canonical graph identifier")
                local_ids[key] = (node_type, start + offset)

        # Commit only after all validations succeed.
        for node_type in TYPES:
            self._records[node_type].extend(
                (slots, features) for _, slots, features in entries[node_type]
            )
        for child_id, (parent_id, position) in graph.parents.items():
            self._links["cant_parent"].append((local_ids[child_id], local_ids[parent_id], position))
        for phrase_id, unit_id in graph.cuts.items():
            self._links["cant_cut_after"].append((local_ids[phrase_id], local_ids[unit_id], 0))
        for unit_id, word_id in graph.terminals.items():
            self._links["cant_terminal"].append((local_ids[unit_id], local_ids[word_id], 0))
        for unit_id, unit in graph.units.items():
            for word_id in unit.source_ids:
                self._links["cant_member"].append((local_ids[word_id], local_ids[unit_id], 0))
        self._links["cant_root"].append((verse_node, local_ids[graph.root], 0))
        self._verses.add(verse_node)
        self._osis_ids.add(graph.osis_id)

    def finalize(self) -> GraphTFBatch:
        counts = {t: len(self._records[t]) for t in TYPES if self._records[t]}
        ranges = {}
        current = self.base_max_node
        for node_type in TYPES:  # Must match modify()'s alphabetical sorting.
            if node_type not in counts:
                continue
            ranges[node_type] = (current + 1, current + counts[node_type])
            current += counts[node_type]

        add_types = {}
        for node_type in counts:
            rows = self._records[node_type]
            node_slots = {}
            features: dict[str, dict[int, int | str]] = {}
            for ordinal, (slots, attributes) in enumerate(rows, start=1):
                node_slots[ordinal] = slots
                for name, value in attributes.items():
                    features.setdefault(name, {})[ordinal] = value
            add_types[node_type] = {
                "nodeFrom": 1,
                "nodeTo": len(rows),
                "nodeSlots": node_slots,
                "nodeFeatures": features,
            }

        def global_id(node):
            if isinstance(node, int):
                return node
            node_type, local_id = node
            return ranges[node_type][0] + local_id - 1

        edges: dict[str, dict[int, dict[int, int] | set[int]]] = {name: {} for name in EDGES}
        for feature, links in self._links.items():
            for source, target, position in links:
                src, tgt = global_id(source), global_id(target)
                if feature == "cant_parent":
                    edges[feature].setdefault(src, {})[tgt] = position
                else:
                    edges[feature].setdefault(src, set()).add(tgt)
        return GraphTFBatch(add_types, edges, ranges, counts)


def materialize_graph_types(core: Path, target: Path, batch: GraphTFBatch) -> None:
    """Save full derived TF dataset and cross-type graph edges in separate stages."""
    from tf.dataset import modify
    from tf.fabric import Fabric

    if target.exists() and any(target.iterdir()):
        raise ValueError("Derived TF output must be a new empty directory")
    if not batch.add_types:
        raise ValueError("Refusing to materialize a graph without node types")

    feature_meta = {}
    for spec in batch.add_types.values():
        for name, values in spec["nodeFeatures"].items():
            sample = next(iter(values.values()))
            feature_meta[name] = {"valueType": "int" if type(sample) is int else "str"}
    if not modify(str(core), str(target), addTypes=batch.add_types, featureMeta=feature_meta,
                  silent="deep"):
        raise RuntimeError("Text-Fabric modify(addTypes) failed for cantillation graph")

    edge_meta = {
        name: {"edgeValues": True, "valueType": "int"} if name == "cant_parent" else {}
        for name in EDGES
    }
    if not Fabric(locations=str(target), silent="deep").save(
        edgeFeatures={name: values for name, values in batch.edges.items() if values},
        metaData=edge_meta,
        silent="deep",
    ):
        raise RuntimeError("Text-Fabric failed to save cantillation cross-type edges")
