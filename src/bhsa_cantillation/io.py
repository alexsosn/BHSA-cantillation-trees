"""Export and render the generated cantillation trees."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import TextIO

from tf.fabric import Fabric

from .books import BOOKS

BHSA_TO_OSIS = {bhsa: osis for osis, bhsa in BOOKS}
SIGNATURE_FEATURES = (
    "cantillation_shape",
    "cantillation_branch_signature",
    "cantillation_accent_signature",
)
METRIC_FEATURES = (
    "cantillation_depth",
    "cantillation_leaf_count",
    "cantillation_mean_leaf_depth",
    "cantillation_colless",
    "cantillation_colless_normalized",
    "cantillation_sackin",
    "cantillation_longest_ladder",
    "cantillation_longest_accent_run",
    "cantillation_depth_leaf_ratio",
)
TREE_FEATURES = " ".join(
    (
        "book",
        "chapter",
        "verse",
        "cantillation_tree",
        "cantillation_system",
        "cantillation_alignment",
        *SIGNATURE_FEATURES,
        *METRIC_FEATURES,
    )
)


def load_tree_api(bhsa_path: Path, module_path: Path):
    """Load BHSA and this module into one Text-Fabric API."""
    fabric = Fabric(locations=(str(bhsa_path), str(module_path)), silent="deep")
    api = fabric.load(TREE_FEATURES, silent="deep")
    if api is None:
        raise RuntimeError("Could not load BHSA and cantillation-tree features")
    return api


def tree_records(api) -> Iterator[dict]:
    """Yield portable JSON records in canonical BHSA verse order."""
    F, L, T = api.F, api.L, api.T
    for verse_node in F.otype.s("verse"):
        serialized = F.cantillation_tree.v(verse_node)
        if serialized is None:
            continue
        book_node = L.u(verse_node, otype="book")[0]
        bhsa_book = F.book.v(book_node)
        _, chapter, verse = T.sectionFromNode(verse_node)
        osis_book = BHSA_TO_OSIS[bhsa_book]
        yield {
            "osis_id": f"{osis_book}.{chapter}.{verse}",
            "bhsa_section": [bhsa_book, chapter, verse],
            "system": F.cantillation_system.v(verse_node),
            "alignment": F.cantillation_alignment.v(verse_node),
            "signatures": {
                name.removeprefix("cantillation_"): getattr(F, name).v(verse_node)
                for name in SIGNATURE_FEATURES
            },
            "metrics": {
                name.removeprefix("cantillation_"): getattr(F, name).v(verse_node)
                for name in METRIC_FEATURES
            },
            "tree": json.loads(serialized),
        }


def record_references(record: Mapping) -> set[str]:
    """Return accepted reference spellings for one exported record."""
    bhsa_book, chapter, verse = record["bhsa_section"]
    osis_book = record["osis_id"].split(".", 1)[0]
    return {
        record["osis_id"],
        f"{osis_book} {chapter}:{verse}",
        f"{bhsa_book} {chapter}:{verse}",
    }


def select_records(records: Iterable[dict], references: Iterable[str]) -> Iterator[dict]:
    """Filter records by OSIS or human-readable verse references."""
    wanted = {reference.strip() for reference in references}
    found = set()
    for record in records:
        matches = wanted & record_references(record)
        if matches:
            found.update(matches)
            yield record
    missing = wanted - found
    if missing:
        raise ValueError(f"Verse reference not found: {', '.join(sorted(missing))}")


def write_json(records: Iterable[dict], output: TextIO, *, json_lines: bool, pretty: bool) -> int:
    """Write records without retaining a whole-corpus JSON document in memory."""
    count = 0
    if json_lines:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")
            count += 1
        return count

    output.write("[\n" if pretty else "[")
    for record in records:
        if count:
            output.write(",\n" if pretty else ",")
        rendered = json.dumps(record, ensure_ascii=False, indent=2 if pretty else None)
        if pretty:
            rendered = "\n".join(f"  {line}" for line in rendered.splitlines())
        output.write(rendered)
        count += 1
    output.write("\n]\n" if pretty else "]\n")
    return count


def node_label(node: Mapping, *, details: bool = False) -> str:
    """Create a terminal-safe label for a tree node."""
    if "children" in node:
        return str(node["accent"])
    label = f'{node["accent"]}: {node["text"]}'
    if details:
        start, end = node["slots"]
        label += f'  [path={node["path"]}; slots={start}-{end}]'
    return label


def render_tree(tree: Mapping, *, details: bool = False, unicode_lines: bool = False) -> str:
    """Render a compact tree using ASCII or box-drawing connectors."""
    tee, elbow, pipe, blank, dash = (
        ("├", "└", "│", " ", "── ")
        if unicode_lines
        else ("|", "`", "|", " ", "-- ")
    )
    lines = [node_label(tree, details=details)]

    def walk(node: Mapping, prefix: str) -> None:
        children = node.get("children", [])
        for index, child in enumerate(children):
            last = index == len(children) - 1
            connector = elbow if last else tee
            lines.append(f"{prefix}{connector}{dash}{node_label(child, details=details)}")
            continuation = blank if last else pipe
            walk(child, f"{prefix}{continuation}   ")

    walk(tree, "")
    return "\n".join(lines)


def read_export(path: Path) -> list[dict]:
    """Read a JSON array, one JSON record, a bare tree, or JSON Lines."""
    content = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = [json.loads(line) for line in content.splitlines() if line.strip()]
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and "tree" in parsed:
        return [parsed]
    if isinstance(parsed, dict) and ("children" in parsed or "path" in parsed):
        return [{"tree": parsed}]
    raise ValueError(f"Unsupported tree JSON in {path}")
