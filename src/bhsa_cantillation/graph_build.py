"""Build and independently verify a separate full BHSA cantillation graph dataset."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tf.fabric import Fabric

from .alignment import align_words
from .books import BOOKS
from .build import FEATURE_META
from .graph import project_graph, reconstruct_tree
from .graph_tf import GraphTFBatch, GraphTFCollector, materialize_graph_types, verify_graph_dataset
from .model import WordAlignment
from .morphhb import load_accent_catalog, normalize_consonants, read_book
from .tree import build_tree, make_units


@dataclass(frozen=True)
class GraphBuildStats:
    verses: int
    source_words: int
    units: int
    phrases: int
    fuzzy_verses: int
    original_max_node: int
    derived_max_node: int


def check_graph_stats(
    batch: GraphTFBatch, *, verses: int, source_words: int, units: int
) -> None:
    """Fail closed on missing, extra, or nonbinary graph nodes/edges."""
    expected = {
        "cant_word": source_words,
        "cant_unit": units,
        "cant_phrase": units - verses,
    }
    for name, count in expected.items():
        if batch.counts.get(name, 0) != count:
            raise ValueError(f"Graph {name} count differs from expected full-binary source data")
    expected_edges = {
        "cant_root": verses,
        "cant_parent": 2 * (units - verses),
        "cant_cut_after": units - verses,
        "cant_terminal": units,
        "cant_member": source_words,
    }
    for name, count in expected_edges.items():
        measured = sum(len(destinations) for destinations in batch.edges[name].values())
        if measured != count:
            raise ValueError(f"Graph {name} edge count differs from expected source data")


def build_graph_dataset(
    bhsa_path: Path,
    module_path: Path,
    morphhb_path: Path,
    output_path: Path,
    *,
    source_commit: str | None = None,
    max_verse_distance: int = 12,
) -> GraphBuildStats:
    """Build, reload and verify the complete BHSA 2021 + cantillation graph."""
    if output_path.exists() and any(output_path.iterdir()):
        raise ValueError("Separate derived TF output directory must be empty")

    paths = {
        "BHSA warp": bhsa_path / "otype.tf",
        "cantillation module": module_path / "cantillation_tree.tf",
        "MorphHB accent catalogue": (
            morphhb_path / "structure/OshbVerse/Script/AccentCatalog.js"
        ),
    }
    for label, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"{label} is missing: {path}")

    fabric = Fabric(locations=[str(bhsa_path), str(module_path)], silent="deep")
    feature_list = (
        "book chapter verse g_cons_utf8 cantillation_tree cantillation_source_id"
    )
    api = fabric.load(feature_list, silent="deep")
    if api is None:
        raise RuntimeError("Cannot load pinned BHSA and the lightweight cantillation module")
    F, L = api.F, api.L
    books = tuple(F.book.v(node) for node in F.otype.s("book"))
    if books != tuple(book for _, book in BOOKS):
        raise ValueError("BHSA 2021 book order differs from the pinned corpus")

    original_verses = set(F.otype.s("verse"))
    verse_index = {}
    for verse_node in sorted(original_verses):
        book_node = L.u(verse_node, otype="book")[0]
        chapter_node = L.u(verse_node, otype="chapter")[0]
        key = (F.book.v(book_node), F.chapter.v(chapter_node), F.verse.v(verse_node))
        if key in verse_index:
            raise ValueError(f"Duplicate BHSA verse section: {key}")
        verse_index[key] = verse_node

    catalog = load_accent_catalog(paths["MorphHB accent catalogue"])
    collector = GraphTFCollector(F.otype.maxNode, F.otype.maxSlot)
    reference_trees: dict[int, dict] = {}
    fuzzy_count = word_count = unit_count = 0

    for osis_book, bhsa_book in BOOKS:
        xml_path = morphhb_path / "wlc" / f"{osis_book}.xml"
        if not xml_path.is_file():
            raise FileNotFoundError(f"Pinned MorphHB book is missing: {xml_path}")
        for osis_id, source_words in read_book(xml_path, catalog):
            _, chapter, verse = osis_id.split(".")
            section = (bhsa_book, int(chapter), int(verse))
            verse_node = verse_index.get(section)
            if verse_node is None or verse_node in reference_trees:
                raise ValueError(f"Missing or duplicated BHSA verse alignment: {osis_id}")
            slots = tuple(L.d(verse_node, otype="word"))
            target_text = [
                normalize_consonants(F.g_cons_utf8.v(slot) or "") for slot in slots
            ]
            result = align_words(source_words, list(slots), target_text)
            if result.distance > max_verse_distance:
                raise ValueError(
                    f"Alignment distance {result.distance} exceeds {max_verse_distance} "
                    f"at {osis_id}"
                )
            alignments = [
                WordAlignment(source, group)
                for source, group in zip(source_words, result.groups, strict=True)
            ]
            # The source identities must match the *already released* lightweight data.
            expected_ids: dict[int, list[str]] = {}
            for alignment in alignments:
                expected_ids.setdefault(alignment.slots[-1], []).append(
                    alignment.source.source_id
                )
            for slot in slots:
                expected = " | ".join(expected_ids.get(slot, ())) or None
                if F.cantillation_source_id.v(slot) != expected:
                    raise ValueError(f"Published source-word identity drift at {osis_id}")

            units = make_units(alignments)
            tree = build_tree(units)
            old_tree = json.loads(F.cantillation_tree.v(verse_node))
            if tree != old_tree:
                raise ValueError(f"Canonical tree changed since pinned module: {osis_id}")
            graph = project_graph(osis_id, alignments, units, tree)
            if reconstruct_tree(graph) != old_tree:
                raise ValueError(f"Canonical graph projection changed the tree: {osis_id}")
            collector.append(verse_node, graph, alignments)
            reference_trees[verse_node] = old_tree
            word_count += len(source_words)
            unit_count += len(units)
            fuzzy_count += int(result.distance != 0)

    if set(reference_trees) != original_verses:
        raise ValueError("MorphHB coverage does not equal the complete BHSA verse inventory")

    batch = collector.finalize()
    check_graph_stats(
        batch, verses=len(reference_trees), source_words=word_count, units=unit_count
    )

    # The original lightweight node features are copied into the *derived* TF
    # dataset; BHSA's original warp and other features remain untouched.
    published = {
        name: api.Fs(name).data
        for name in FEATURE_META
    }
    published_meta = {
        name: dict(api.TF.features[name].metaData)
        for name in FEATURE_META
    }
    materialize_graph_types(
        bhsa_path,
        output_path,
        batch,
        extra_node_features=published,
        extra_feature_meta=published_meta,
        provenance=(
            f"https://github.com/openscriptures/morphhb/tree/{source_commit}"
            if source_commit else None
        ),
    )
    verify_graph_dataset(bhsa_path, output_path, batch, reference_trees)

    stats = GraphBuildStats(
        verses=len(reference_trees),
        source_words=word_count,
        units=unit_count,
        phrases=unit_count - len(reference_trees),
        fuzzy_verses=fuzzy_count,
        original_max_node=F.otype.maxNode,
        derived_max_node=batch.max_node,
    )
    (output_path / "graph-build-stats.json").write_text(
        json.dumps(asdict(stats), indent=2) + "\n", encoding="utf-8"
    )
    return stats
