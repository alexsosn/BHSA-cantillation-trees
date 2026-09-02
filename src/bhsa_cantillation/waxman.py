"""Comparison helpers for Josh Waxman's serialized cantillation trees."""

from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .alignment import edit_distance
from .model import SourceWord
from .morphhb import normalize_consonants
from .tree import build_tree

WAXMAN_BOOKS = {
    "Genesis": "Gen",
    "Exodus": "Exod",
    "Leviticus": "Lev",
    "Numbers": "Num",
    "Deuteronomy": "Deut",
    "Joshua": "Josh",
    "Judges": "Judg",
    "I Samuel": "1Sam",
    "II Samuel": "2Sam",
    "I Kings": "1Kgs",
    "II Kings": "2Kgs",
    "Isaiah": "Isa",
    "Jeremiah": "Jer",
    "Ezekiel": "Ezek",
    "Hosea": "Hos",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadiah": "Obad",
    "Jonah": "Jonah",
    "Micah": "Mic",
    "Nahum": "Nah",
    "Habakkuk": "Hab",
    "Zephaniah": "Zeph",
    "Haggai": "Hag",
    "Zechariah": "Zech",
    "Malachi": "Mal",
    "Ruth": "Ruth",
    "Song of Songs": "Song",
    "Ecclesiastes": "Eccl",
    "Lamentations": "Lam",
    "Esther": "Esth",
    "Daniel": "Dan",
    "Ezra": "Ezra",
    "Nehemiah": "Neh",
    "I Chronicles": "1Chr",
    "II Chronicles": "2Chr",
}

LINE_RE = re.compile(r"^(.+?) (\d+) (\d+): (.*)$")

# Normalize spelling and compound-mark readings to the disjunctive function used
# in Waxman's node labels. The two legarmeh labels are intentionally conflated:
# MorphHB calls both of them Legarmeh.
MORPHHB_ACCENT = {
    "Atnach": "ETNACHTA",
    "Atnach with Pashta": "ETNACHTA",
    "Geresh": "GERESH",
    "Gershayim": "GERSHAYIM",
    "Gershayim with Telisha Gedola": "TELISHA_GEDOLA",
    "HEBREW ACCENT MAHAPAKH + HEBREW ACCENT TIPEHA": "TIPCHA",
    "HEBREW ACCENT QADMA": "PASHTA",
    "HEBREW ACCENT QADMA + HEBREW ACCENT PASHTA + HEBREW PUNCTUATION PASEQ": "PASHTA",
    "Legarmeh": "LEGARMEH",
    "Mahpakh with Pashta": "PASHTA",
    "Merkha with Atnach": "ETNACHTA",
    "Merkha with Tevir": "TEVIR",
    "Merkha with Tipcha": "TIPCHA",
    "Munnach with Atnach": "ETNACHTA",
    "Munnach with Pazer": "PAZER",
    "Munnach with Revia": "REVIA",
    "Munnach with Zaqef Qatan": "ZAKEF_KATON",
    "Mëayla with Atnach": "ETNACHTA",
    "Mëayla with Sof Pasuq": "SILLUQ",
    "Pashta": "PASHTA",
    "Pazer": "PAZER",
    "Qadma with Geresh": "GERESH",
    "Qadma with Zaqef Qatan": "ZAKEF_KATON",
    "Qarney Para": "KARNEI_PARA",
    "Revia": "REVIA",
    "Segol": "SEGOLTA",
    "Shalshelet": "SHALSHELET",
    "Sof Pasuq": "SILLUQ",
    "Telisha Gedola": "TELISHA_GEDOLA",
    "Telisha Gedola with Gershayim": "GERSHAYIM",
    "Telisha Gedola with Geresh": "GERESH",
    "Telisha Gedola with Revia": "REVIA",
    "Tevir": "TEVIR",
    "Tipcha": "TIPCHA",
    "Yetiv": "YETIV",
    "Zaqef Gadol": "ZAKEF_GADOL",
    "Zaqef Qatan": "ZAKEF_KATON",
    "Zarqa": "ZARQA",
}

WAXMAN_ACCENT = {
    "MUNACH_LEGARMEIH": "LEGARMEH",
    "MUNACH_LEGARMEIH2": "LEGARMEH",
}


@dataclass(frozen=True)
class Unit:
    """Minimum AccentUnit interface needed by :func:`build_tree`."""

    path: str
    slots: tuple[int, int]
    text: str
    accent_name: str


def read_waxman(path: Path) -> dict[str, dict]:
    """Read ``prodosic_trees.txt`` without executing its Python literals."""
    verses = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = LINE_RE.fullmatch(line)
        if match is None:
            raise ValueError(f"Invalid Waxman line {line_number}")
        book, chapter, verse, literal = match.groups()
        if book not in WAXMAN_BOOKS:
            raise ValueError(f"Unknown Waxman book on line {line_number}: {book}")
        osis_id = f"{WAXMAN_BOOKS[book]}.{chapter}.{verse}"
        tree = ast.literal_eval(literal)
        if not isinstance(tree, dict) or tree.get("name") != "PASUK":
            raise ValueError(f"Invalid Waxman tree on line {line_number}")
        verses[osis_id] = tree
    return verses


def source_units(words: list[SourceWord]) -> list[Unit]:
    """Represent MorphHB accentual units on consonantal character offsets."""
    result = []
    pending = []
    position = 0
    for word in words:
        pending.append(word)
        if word.path is None:
            continue
        # The serialized TF tree uses the displayed MorphHB reading (qere when
        # supplied), whereas SourceWord.consonants deliberately retains ketiv
        # for alignment with BHSA.
        text = "".join(normalize_consonants(item.text) for item in pending)
        end = position + len(text)
        result.append(Unit(word.path, (position, end), text, word.accent_name))
        position = end
        pending = []
    if pending:
        raise ValueError("Verse ends with words not closed by a structural path")
    return result


def waxman_spans(tree: dict) -> tuple[str, list[dict]]:
    """Return consonantal text and all internal-node character spans."""
    nodes = []
    text_parts = []

    def walk(node: dict, start: int) -> int:
        children = node.get("children")
        if children is None:
            text = normalize_consonants(node["name"])
            text_parts.append(text)
            return start + len(text)
        position = start
        child_spans = []
        for child in children:
            child_start = position
            position = walk(child, position)
            child_accent = child["name"] if "children" in child else None
            child_spans.append((child_start, position, child_accent))
        nodes.append(
            {
                "start": start,
                "end": position,
                "accent": WAXMAN_ACCENT.get(node["name"], node["name"]),
                "children": child_spans,
            }
        )
        return position

    walk(tree, 0)
    return "".join(text_parts), nodes


def waxman_leaves(tree: dict) -> list[str]:
    """Return normalized leaf strings in reading order."""
    if "children" not in tree:
        return [normalize_consonants(tree["name"])]
    return [text for child in tree["children"] for text in waxman_leaves(child)]


def morphhb_leaves(words: list[SourceWord]) -> list[str]:
    """Return MorphHB orthographic leaves, joining words linked by maqqef."""
    leaves = []
    pending = []
    for word in words:
        pending.append(normalize_consonants(word.text))
        if "־" not in word.trailing:
            leaves.append("".join(pending))
            pending = []
    if pending:
        leaves.append("".join(pending))
    return leaves


def morphhb_spans(words: list[SourceWord]) -> tuple[str, list[dict]]:
    """Build the TF module's unit tree and return its character spans."""
    units = source_units(words)
    tree = build_tree(units)
    nodes = []

    def walk(node: dict) -> tuple[int, int]:
        children = node.get("children")
        if children is None:
            start, end = node["slots"]
            nodes.append(
                {
                    "start": start,
                    "end": end,
                    "kind": "unit",
                    "accent": MORPHHB_ACCENT.get(node["accent"]),
                    "raw_accent": node["accent"],
                    "cut": None,
                }
            )
            return start, end
        left = walk(children[0])
        right = walk(children[1])
        nodes.append(
            {
                "start": left[0],
                "end": right[1],
                "kind": "branch",
                "accent": MORPHHB_ACCENT.get(node["accent"]),
                "raw_accent": node["accent"],
                "cut": left[1],
            }
        )
        return left[0], right[1]

    walk(tree)
    return "".join(normalize_consonants(word.text) for word in words), nodes


def compare_verse(waxman: dict, words: list[SourceWord]) -> dict:
    """Compare one verse by text, constituent spans, cuts, and labels."""
    waxman_text, waxman_nodes = waxman_spans(waxman)
    morphhb_text, morphhb_nodes = morphhb_spans(words)
    result = {
        "text_exact": waxman_text == morphhb_text,
        "edit_distance": edit_distance(waxman_text, morphhb_text),
        "leaf_segmentation_exact": waxman_leaves(waxman) == morphhb_leaves(words),
    }
    if not result["text_exact"]:
        return result

    waxman_by_span = defaultdict(list)
    for node in waxman_nodes:
        waxman_by_span[node["start"], node["end"]].append(node)
    waxman_span_set = set(waxman_by_span)
    morphhb_span_set = {(node["start"], node["end"]) for node in morphhb_nodes}
    result.update(
        {
            "morphhb_nodes": len(morphhb_span_set),
            "covered_nodes": len(morphhb_span_set & waxman_span_set),
            "all_spans_covered": morphhb_span_set <= waxman_span_set,
            "exact_span_set": morphhb_span_set == waxman_span_set,
            "branches": 0,
            "cuts_found": 0,
            "labels_compared": 0,
            "labels_matched": 0,
            "unmapped_accents": Counter(),
            "label_disagreements": Counter(),
        }
    )
    for node in morphhb_nodes:
        if node["kind"] != "branch":
            continue
        result["branches"] += 1
        candidates = []
        for waxman_node in waxman_by_span[node["start"], node["end"]]:
            for _, child_end, child_name in waxman_node["children"]:
                if child_end == node["cut"] and child_name is not None:
                    candidates.append(WAXMAN_ACCENT.get(child_name, child_name))
        if not candidates:
            continue
        result["cuts_found"] += 1
        if node["accent"] is None:
            result["unmapped_accents"][node["raw_accent"]] += 1
            continue
        result["labels_compared"] += 1
        if node["accent"] in candidates:
            result["labels_matched"] += 1
        else:
            key = f"{node['raw_accent']} -> {node['accent']} / {', '.join(candidates)}"
            result["label_disagreements"][key] += 1
    return result
