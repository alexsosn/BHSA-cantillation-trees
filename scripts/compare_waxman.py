#!/usr/bin/env python3
"""Compare the generated tree model with Josh Waxman's tree corpus."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from bhsa_cantillation.morphhb import load_accent_catalog, read_book
from bhsa_cantillation.waxman import compare_verse, read_waxman


def percentage(value: int, total: int) -> float:
    return round(100 * value / total, 3) if total else 0.0


def waxman_diagnostics(trees: dict[str, dict]) -> dict:
    """Count representation quirks relevant to interpreting the comparison."""
    arities = Counter()
    leaves = 0
    empty_leaves = 0

    def walk(node: dict) -> None:
        nonlocal leaves, empty_leaves
        children = node.get("children")
        if children is None:
            leaves += 1
            if not any("א" <= char <= "ת" for char in node["name"]):
                empty_leaves += 1
            return
        arities[len(children)] += 1
        for child in children:
            walk(child)

    for tree in trees.values():
        walk(tree)
    return {
        "leaves": leaves,
        "leaves_without_hebrew_letters": empty_leaves,
        "internal_node_arity": dict(sorted(arities.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--waxman", type=Path, required=True)
    parser.add_argument("--morphhb", type=Path, required=True)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    waxman = read_waxman(args.waxman)
    catalog = load_accent_catalog(
        args.morphhb / "structure/OshbVerse/Script/AccentCatalog.js"
    )
    morphhb = {}
    for book_path in sorted((args.morphhb / "wlc").glob("*.xml")):
        morphhb.update(read_book(book_path, catalog))

    shared = sorted(set(waxman) & set(morphhb))
    totals = Counter()
    distances = Counter()
    unmapped = Counter()
    disagreements = Counter()
    examples = []
    structure_examples = []
    for osis_id in shared:
        comparison = compare_verse(waxman[osis_id], morphhb[osis_id])
        totals["verses"] += 1
        totals["leaf_segmentation_exact"] += comparison["leaf_segmentation_exact"]
        distances[comparison["edit_distance"]] += 1
        if comparison["text_exact"]:
            totals["text_exact"] += 1
        elif len(examples) < 20:
            examples.append({"verse": osis_id, "edit_distance": comparison["edit_distance"]})
        if not comparison["text_exact"]:
            continue
        for key in (
            "morphhb_nodes",
            "covered_nodes",
            "branches",
            "cuts_found",
            "labels_compared",
            "labels_matched",
        ):
            totals[key] += comparison[key]
        for key in ("all_spans_covered", "exact_span_set"):
            totals[key] += comparison[key]
        if not comparison["exact_span_set"] and len(structure_examples) < 20:
            structure_examples.append(osis_id)
        unmapped.update(comparison["unmapped_accents"])
        for disagreement, count in comparison["label_disagreements"].items():
            disagreements[f"{osis_id}: {disagreement}"] += count

    report = {
        "sources": {
            "waxman": {
                "repository": "https://github.com/joshwaxman/cantillation",
                "commit": "451f1ca91b7627c84023080e1a7baa18c3b31d89",
                "file": "prodosic_trees.txt",
            },
            "morphhb": {
                "repository": "https://github.com/openscriptures/morphhb",
                "commit": "3d15126fb1ef74867fc1434be1942e837932691f",
            },
        },
        "coverage": {
            "waxman_verses": len(waxman),
            "morphhb_verses": len(morphhb),
            "shared_verses": len(shared),
            "waxman_only": sorted(set(waxman) - set(morphhb)),
        },
        "text": {
            "exact_verses": totals["text_exact"],
            "exact_percent": percentage(totals["text_exact"], totals["verses"]),
            "edit_distance_distribution": dict(sorted(distances.items())),
            "exact_leaf_segmentation_verses": totals["leaf_segmentation_exact"],
            "exact_leaf_segmentation_percent": percentage(
                totals["leaf_segmentation_exact"], totals["verses"]
            ),
            "first_nonexact": examples,
        },
        "waxman_representation": waxman_diagnostics(waxman),
        "structure_on_exact_text": {
            "verses": totals["text_exact"],
            "all_module_spans_present": totals["all_spans_covered"],
            "all_module_spans_present_percent": percentage(
                totals["all_spans_covered"], totals["text_exact"]
            ),
            "exact_distinct_span_set": totals["exact_span_set"],
            "exact_distinct_span_set_percent": percentage(
                totals["exact_span_set"], totals["text_exact"]
            ),
            "module_constituent_spans": totals["morphhb_nodes"],
            "covered_constituent_spans": totals["covered_nodes"],
            "covered_constituent_spans_percent": percentage(
                totals["covered_nodes"], totals["morphhb_nodes"]
            ),
            "module_branch_cuts": totals["branches"],
            "waxman_cuts_found": totals["cuts_found"],
            "waxman_cuts_found_percent": percentage(
                totals["cuts_found"], totals["branches"]
            ),
            "labels_compared": totals["labels_compared"],
            "labels_matched": totals["labels_matched"],
            "labels_matched_percent": percentage(
                totals["labels_matched"], totals["labels_compared"]
            ),
            "unmapped_accents": dict(unmapped.most_common()),
            "label_disagreements": dict(disagreements.most_common()),
            "first_nonexact_span_sets": structure_examples,
        },
        "method": {
            "text": (
                "NFD Hebrew consonants only; vocalization, accents, punctuation, "
                "and spaces removed"
            ),
            "structure": (
                "distinct consonantal character spans of accentual units and binary branches"
            ),
            "labels": "MorphHB cut accent compared with the Waxman child ending at the same cut",
        },
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
