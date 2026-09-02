"""End-to-end converter from MorphHB structure to a BHSA TF module."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from tf.fabric import Fabric

from .alignment import align_words
from .books import BOOKS
from .model import WordAlignment
from .morphhb import accent_system, load_accent_catalog, normalize_consonants, read_book
from .tree import build_tree, make_units


@dataclass(frozen=True)
class BuildStats:
    verses: int
    source_words: int
    units: int
    exact_verses: int
    fuzzy_verses: int
    max_distance: int
    catalog_fallback_words: int


FEATURE_META = {
    "cantillation_accent": {
        "description": "name of the MorphHB cantillation accent on the orthographic word",
        "valueType": "str",
    },
    "cantillation_accent_type": {
        "description": "MorphHB cantillation role (conjunctive or disjunctive)",
        "valueType": "str",
    },
    "cantillation_marks": {
        "description": "raw Unicode cantillation marks and structural punctuation",
        "valueType": "str",
    },
    "cantillation_accent_status": {
        "description": "whether the accent combination occurs in the MorphHB catalogue",
        "valueType": "str",
    },
    "cantillation_source_id": {
        "description": "source word identifier in MorphHB",
        "valueType": "str",
    },
    "cantillation_path": {
        "description": "MorphHB structural path on the final word of an accentual unit",
        "valueType": "str",
    },
    "cantillation_unit": {
        "description": "one-based unit ordinal; multiple values use a vertical-bar separator",
        "valueType": "str",
    },
    "cantillation_unit_path": {
        "description": "MorphHB structural path copied to every BHSA slot in the unit",
        "valueType": "str",
    },
    "cantillation_system": {
        "description": "cantillation system used in the verse (prose or poetic)",
        "valueType": "str",
    },
    "cantillation_tree": {
        "description": "binary prosodic tree serialized as compact JSON",
        "valueType": "str",
    },
    "cantillation_alignment": {
        "description": "MorphHB-to-BHSA verse alignment quality (exact or fuzzy)",
        "valueType": "str",
    },
}


def _append_value(
    feature: dict[int, str | int], node: int, value: str | int, separator: str = " | "
) -> None:
    text = str(value)
    previous = feature.get(node)
    feature[node] = text if previous is None else f"{previous}{separator}{text}"


def _metadata(version: str, source_commit: str | None) -> dict:
    source = "https://github.com/openscriptures/morphhb"
    if source_commit:
        source = f"{source}/tree/{source_commit}"
    generic = {
        "dataset": "BHSA cantillation trees",
        "datasetName": "BHSA cantillation trees derived from MorphHB",
        "version": version,
        "coreData": "BHSA",
        "coreVersion": "2021",
        "source": source,
        "provenance": "https://github.com/alexsosn/BHSA-cantillation-trees",
        "license": "CC BY 4.0",
    }
    return {
        "": generic,
        **{
            feature: {**generic, **feature_metadata}
            for feature, feature_metadata in FEATURE_META.items()
        },
    }


def _load_bhsa(path: Path):
    fabric = Fabric(locations=str(path), silent="deep")
    api = fabric.load(
        "book chapter verse g_cons_utf8 g_word_utf8 trailer_utf8",
        silent="deep",
    )
    if api is None:
        raise RuntimeError(f"Could not load BHSA from {path}")
    return api


def build_module(
    bhsa_path: Path,
    morphhb_path: Path,
    output_path: Path,
    *,
    version: str = "2021",
    max_verse_distance: int = 12,
    source_commit: str | None = None,
) -> BuildStats:
    """Build and save all Text-Fabric node features."""
    api = _load_bhsa(bhsa_path)
    F, L = api.F, api.L
    bhsa_books = tuple(F.book.v(node) for node in F.otype.s("book"))
    expected_books = tuple(bhsa for _, bhsa in BOOKS)
    if bhsa_books != expected_books:
        raise ValueError("BHSA book order/names do not match the supported 2021 release")

    catalog_path = morphhb_path / "structure/OshbVerse/Script/AccentCatalog.js"
    catalog = load_accent_catalog(catalog_path)
    verse_index = {}
    for verse_node in F.otype.s("verse"):
        book_node = L.u(verse_node, otype="book")[0]
        chapter_node = L.u(verse_node, otype="chapter")[0]
        verse_index[
            (F.book.v(book_node), F.chapter.v(chapter_node), F.verse.v(verse_node))
        ] = verse_node
    features: dict[str, dict[int, str | int]] = {name: {} for name in FEATURE_META}
    report: list[dict] = []
    verse_count = source_word_count = unit_count = exact_count = fuzzy_count = 0
    max_distance = 0
    fallback_count = 0
    fallback_patterns: Counter[tuple[str, str, str, str]] = Counter()

    for osis_book, bhsa_book in BOOKS:
        xml_path = morphhb_path / "wlc" / f"{osis_book}.xml"
        if not xml_path.exists():
            raise FileNotFoundError(xml_path)
        for osis_id, source_words in read_book(xml_path, catalog):
            _, chapter_text, verse_text = osis_id.split(".")
            section = (bhsa_book, int(chapter_text), int(verse_text))
            verse_node = verse_index.get(section)
            if verse_node is None:
                raise ValueError(f"No BHSA verse for {osis_id}: {section}")
            slots = list(L.d(verse_node, otype="word"))
            target_text = [normalize_consonants(F.g_cons_utf8.v(slot) or "") for slot in slots]
            result = align_words(source_words, slots, target_text)
            if result.distance > max_verse_distance:
                raise ValueError(
                    f"Alignment distance {result.distance} exceeds "
                    f"{max_verse_distance} at {osis_id}"
                )

            word_alignments = [
                WordAlignment(source=source, slots=group)
                for source, group in zip(source_words, result.groups, strict=True)
            ]
            units = make_units(word_alignments)
            tree = build_tree(units)
            system = accent_system(osis_id)

            for alignment in word_alignments:
                endpoint = alignment.slots[-1]
                source = alignment.source
                _append_value(features["cantillation_accent"], endpoint, source.accent_name)
                _append_value(features["cantillation_accent_type"], endpoint, source.accent_type)
                _append_value(features["cantillation_source_id"], endpoint, source.source_id)
                status = "catalogued" if source.accent_catalogued else "unicode-fallback"
                _append_value(features["cantillation_accent_status"], endpoint, status)
                if source.accent_marks:
                    _append_value(features["cantillation_marks"], endpoint, source.accent_marks)
                if source.path is not None:
                    _append_value(features["cantillation_path"], endpoint, source.path)
                if not source.accent_catalogued:
                    fallback_count += 1
                    fallback_patterns[
                        (system, source.accent_type, source.accent_marks, source.accent_name)
                    ] += 1

            for unit in units:
                for slot in unit.slots:
                    _append_value(features["cantillation_unit"], slot, unit.ordinal)
                    _append_value(features["cantillation_unit_path"], slot, unit.path)

            features["cantillation_system"][verse_node] = system
            features["cantillation_tree"][verse_node] = json.dumps(
                tree, ensure_ascii=False, separators=(",", ":")
            )
            features["cantillation_alignment"][verse_node] = result.status

            verse_count += 1
            source_word_count += len(source_words)
            unit_count += len(units)
            max_distance = max(max_distance, result.distance)
            if result.distance:
                fuzzy_count += 1
                report.append(
                    {
                        "osis_id": osis_id,
                        "bhsa_section": section,
                        "distance": result.distance,
                        "source": [word.consonants for word in source_words],
                        "target": target_text,
                        "groups": [list(group) for group in result.groups],
                    }
                )
            else:
                exact_count += 1

    output_path.mkdir(parents=True, exist_ok=True)
    output_fabric = Fabric(locations=str(output_path), silent="deep")
    if not output_fabric.save(
        nodeFeatures=features,
        edgeFeatures={},
        metaData=_metadata(version, source_commit),
        silent="deep",
    ):
        raise RuntimeError(f"Text-Fabric failed to save module to {output_path}")

    stats = BuildStats(
        verses=verse_count,
        source_words=source_word_count,
        units=unit_count,
        exact_verses=exact_count,
        fuzzy_verses=fuzzy_count,
        max_distance=max_distance,
        catalog_fallback_words=fallback_count,
    )
    report_path = output_path / "alignment-report.json"
    report_path.write_text(
        json.dumps(
            {
                "stats": asdict(stats),
                "non_exact": report,
                "uncatalogued_patterns": [
                    {
                        "system": key[0],
                        "accent_type": key[1],
                        "marks": key[2],
                        "fallback_name": key[3],
                        "count": count,
                    }
                    for key, count in fallback_patterns.most_common()
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return stats
