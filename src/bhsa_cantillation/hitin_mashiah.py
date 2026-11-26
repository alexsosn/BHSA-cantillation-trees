"""Reproduce the two objective tables of Hitin-Mashiah (Textus 26, 2016).

Count maqqef-linked MorphHB source records as one printed word. Retain
all original counts and labels; never fit the counts to the publication.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .boundaries import REQUIRED_FEATURES, iter_boundary_rows

PAPER = (
    "https://openscholar.huji.ac.il/sites/default/files/he_bible_project/files/"
    "main_division_in_the_verse_in_the_21.pdf"
)
MAQQEF = "־"
CUT_LABELS = {
    "Atnach": "Atnah",
    "Mëayla with Atnach": "Atnah",
    "Munnach with Atnach": "Atnah",
    "Merkha with Atnach": "Atnah",
    "Atnach with Pashta": "Atnah",
    "Tipcha": "Tipha",
    "Merkha with Tipcha": "Tipha",
    "Zaqef Qatan": "Zaqef",
    "Zaqef Gadol": "Zaqef",
    "Munnach with Zaqef Qatan": "Zaqef",
    "Qadma with Zaqef Qatan": "Zaqef",
}
FINAL_LABELS = {"Sof Pasuq", "Mëayla with Sof Pasuq", "Merkha with Sof Pasuq"}
# Printed pages 202 and 206; counts, not the differently normalized percentages.
PUBLISHED = {
    "one_word": {
        "Atnah": (0, 15, 36),
        "Tipha": (193, 121, 43),
    },
    "two_words": {
        "Atnah": (33, 272, 871),
        "Tipha/Zaqef": (337, 227, 92),
    },
}
BINS = {"one_word": ("2-4", "5-8", "9+"), "two_words": ("3-4", "5-6", "7+")}


def classify_root(osis, system, alignment, cut, marks, accent, final):
    """Classify a source-record root cut, keeping every reason for non-inclusion explicit."""
    total = len(marks)
    if type(cut) is not int or not 0 < cut < total:
        raise ValueError(f"Invalid source cut in {osis}: {cut}/{total}")
    links = [MAQQEF in (m or "") for m in marks]
    words = total - sum(links[:-1])
    right = total - cut - sum(links[cut:-1])
    category = CUT_LABELS.get(accent)
    status = "included"
    if osis.split(".", 1)[0] in {"Ps", "Prov", "Job"} or system != "prose":
        status = "outside_21_books"
    elif links[-1]:
        status = "terminal_maqqef"
    elif links[cut - 1]:
        status = "split_maqqef"
    elif right not in (1, 2):
        status = "other_right_length"
    elif alignment != "exact":
        status = "fuzzy_alignment"
    elif final not in FINAL_LABELS:
        status = "unmapped_final_accent"
    elif category is None or (right == 1 and category == "Zaqef"):
        status = "unmapped_cut_accent"
    elif right == 1 and category == "Atnah" and final == "Mëayla with Sof Pasuq":
        # p.202 n.9 excludes these; p.206 does not state that they were added.
        status = "maayla_exclusion"
    if right == 2 and category in {"Tipha", "Zaqef"}:
        category = "Tipha/Zaqef"
    return {
        "osis_id": osis, "system": system, "alignment": alignment,
        "source_words": total, "source_right_words": total - cut,
        "words": words, "right_words": right,
        "cut_source_index": cut, "cut_accent": accent,
        "final_accent": final, "category": category, "status": status,
    }


def summarize(rows):
    """Retain contributing IDs and published/observed/delta for every table cell."""
    rows = sorted(rows, key=lambda row: row["osis_id"])
    if len({row["osis_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate verse in reproduction report")
    counts = Counter(row["status"] for row in rows)
    cells = defaultdict(list)
    for row in rows:
        if row["status"] != "included":
            continue
        right = row["right_words"]
        key = "one_word" if right == 1 else "two_words"
        length = row["words"]
        bucket = 0 if length <= 4 else 1 if length <= (8 if right == 1 else 6) else 2
        cells[key, row["category"], bucket].append(row["osis_id"])
    tables = {}
    for key, categories in PUBLISHED.items():
        tables[key] = []
        for category, expected in categories.items():
            for i, published in enumerate(expected):
                ids = cells[key, category, i]
                tables[key].append({
                    "category": category, "length_bin": BINS[key][i],
                    "published": published, "observed": len(ids),
                    "delta": len(ids) - published, "verses": ids,
                })
    if sum(c["observed"] for t in tables.values() for c in t) != counts["included"]:
        raise ValueError("Included verse not assigned to a published table cell")
    return {
        "paper": {"url": PAPER, "pages": [202, 206], "year": 2016},
        "scope": "21 books: excludes Job, Psalms, Proverbs; exact BHSA alignment",
        "word_definition": "direct MorphHB source records joined across maqqef",
        "status_counts": dict(sorted(counts.items())),
        "tables": tables,
        # Keep every selected/excluded candidate, including prose Job frames.
        "candidates": [
            r for r in rows if r.get("right_words") in (1, 2)
            or r["status"] in {"split_maqqef", "terminal_maqqef"}
        ],
        "no_root_verses": [r["osis_id"] for r in rows if r["status"] == "no_root"],
    }


def load_graph(path: Path):
    from tf.fabric import Fabric

    if not (path / "otype.tf").is_file():
        raise FileNotFoundError(f"Not a saved graph: {path}")
    features = (*REQUIRED_FEATURES, "cant_word_marks", "cant_word_accent")
    api = Fabric(locations=str(path), silent="deep").load(" ".join(features), silent="deep")
    if api is None:
        raise RuntimeError(f"Cannot load source word marks from {path}")
    return api


def build_report(api):
    """Read only the saved graph, fully validate it, and measure its original source words."""
    F, E = api.F, api.E
    roots = {
        row["verse_node"]: row for row in iter_boundary_rows(api) if row["depth"] == 0
    }
    by_osis = defaultdict(list)
    for unit in F.otype.s("cant_unit"):
        osis = F.cant_unit_id.v(unit).rsplit("#u", 1)[0]
        by_osis[osis].append(unit)
    rows = []
    for verse in F.otype.s("verse"):
        root = E.cant_root.f(verse)[0]
        if verse not in roots:
            rows.append({"osis_id": F.cant_unit_id.v(root).rsplit("#u", 1)[0],
                         "status": "no_root"})
            continue
        row = roots[verse]
        osis = row["osis_id"]
        units = sorted(by_osis[osis], key=F.cant_unit_ordinal.v)
        words = sorted(
            (word for unit in units for word in E.cant_member.t(unit)),
            key=F.cant_word_ordinal.v,
        )
        if len(words) != row["phrase_word_count"]:
            raise ValueError(f"Root source-word count differs at {osis}")
        cut = row["cut_after_word_index"]
        if (E.cant_terminal.f(units[-1]) != (words[-1],)
                or F.cant_word_id.v(words[cut - 1]) != row["cut_terminal_word_id"]):
            raise ValueError(f"Wrong terminal source word at {osis}")
        accent = F.cant_word_accent.v(words[cut - 1])
        final = F.cant_word_accent.v(words[-1])
        if accent != row["cut_accent"] or final != F.cant_terminal_accent.v(units[-1]):
            raise ValueError(f"Terminal accent differs from source word at {osis}")
        rows.append(classify_root(
            osis, row["system"], row["alignment"], cut,
            [F.cant_word_marks.v(w) for w in words], accent, final,
        ))
    report = summarize(rows)
    report["source_uri"] = api.TF.features["cant_word_id"].metaData.get("source")
    report["graph_verses"] = len(rows)
    return report
