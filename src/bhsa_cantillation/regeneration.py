"""Check a regenerated TF cantillation module against the pinned reference.

Old feature *data* must be identical; metadata creation timestamps may change.
The BHSA core warp is loaded separately to check the new verse measurements.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from .build import FEATURE_META

MEASURES = (
    "cantillation_catalog_rank",
    "cantillation_catalog_final",
    "cantillation_word_count",
    "cantillation_main_cut_word_index",
    "cantillation_main_first_word_count",
    "cantillation_main_second_word_count",
    "cantillation_main_cut_fraction",
    "cantillation_main_signed_split",
)


def _read_tf(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    if "\n\n" not in content:
        raise ValueError(f"Invalid TF feature header or missing data: {path.name}")
    return content.split("\n\n", 1)


def _source(header: str) -> str | None:
    return next(
        (line[len("@source=") :] for line in header.splitlines() if line.startswith("@source=")),
        None,
    )


def verify_module_files(reference: Path, candidate: Path, morphhb_sha: str) -> dict:
    """Check feature inventory, old values, provenance and alignment statistics."""
    baseline = {p.name: p for p in reference.glob("cantillation_*.tf")}
    generated = {p.name: p for p in candidate.glob("cantillation_*.tf")}
    expected = {f"{name}.tf" for name in FEATURE_META}

    if not baseline:
        raise ValueError("No baseline cantillation feature files")
    if set(generated) != expected:
        missing = sorted(expected - set(generated))
        extra = sorted(set(generated) - expected)
        raise ValueError(f"Generated TF feature inventory differs: missing={missing}, extra={extra}")

    target_source = f"https://github.com/openscriptures/morphhb/tree/{morphhb_sha}"
    for filename, file_path in generated.items():
        header, body = _read_tf(file_path)
        if not body.strip():
            raise ValueError(f"Empty TF feature: {filename}")
        if _source(header) != target_source:
            raise ValueError(f"Wrong pinned MorphHB source for {filename}")
        if filename in baseline:
            _, old_body = _read_tf(baseline[filename])
            if body != old_body:
                raise ValueError(f"Existing TF feature data changed: {filename}")

    for filename in baseline:
        if filename not in generated:
            raise ValueError(f"Previously shipped feature was removed: {filename}")

    original_report = json.loads((reference / "alignment-report.json").read_text(encoding="utf-8"))
    new_report = json.loads((candidate / "alignment-report.json").read_text(encoding="utf-8"))
    for field in ("stats", "non_exact", "uncatalogued_patterns"):
        if original_report.get(field) != new_report.get(field):
            raise ValueError(f"Alignment report drift in {field}")

    return original_report["stats"]


def _require(value, label: str) -> int:
    if value is None or isinstance(value, bool):
        raise ValueError(f"Missing or nonnumeric {label}")
    return int(value)


def verify_verse_features(api, stats: dict) -> None:
    """Validate measured source counts and split ratios against actual BHSA slots."""
    F, L = api.F, api.L
    verses = F.otype.s("verse")
    if len(verses) != stats["verses"]:
        raise ValueError("Verse count differs from the pinned alignment report")

    n_words = n_units = n_singles = 0
    tolerance = Decimal("0.00000051")
    for verse in verses:
        word_count = _require(F.cantillation_word_count.v(verse), "source word count")
        leaf_count = _require(F.cantillation_leaf_count.v(verse), "unit leaf count")
        source_words = sum(
            len(source_ids.split(" | "))
            for slot in L.d(verse, otype="word")
            if (source_ids := F.cantillation_source_id.v(slot)) is not None
        )
        if word_count < 1 or word_count != source_words:
            raise ValueError(f"Verse {verse} source word count differs from source identifiers")
        if leaf_count < 1 or leaf_count > word_count:
            raise ValueError(f"Verse {verse} unit count outside source word bounds")
        n_words += word_count
        n_units += leaf_count
        fields = (
            F.cantillation_main_cut_word_index.v(verse),
            F.cantillation_main_first_word_count.v(verse),
            F.cantillation_main_second_word_count.v(verse),
            F.cantillation_main_cut_fraction.v(verse),
            F.cantillation_main_signed_split.v(verse),
        )
        if leaf_count == 1:
            n_singles += 1
            if any(value is not None for value in fields):
                raise ValueError(f"Verse {verse} singleton must have no main-cut fields")
            continue

        index, first, second, fraction, signed = fields
        first = _require(first, "main first count")
        second = _require(second, "main second count")
        index = _require(index, "main cut word index")
        if not (0 < first < word_count and second > 0 and index == first):
            raise ValueError(f"Verse {verse} invalid root cut position")
        if first + second != word_count:
            raise ValueError(f"Verse {verse} root cut word counts do not add up")
        if fraction is None or signed is None:
            raise ValueError(f"Verse {verse} missing split ratios")
        if abs(Decimal(str(fraction)) - Decimal(first) / Decimal(word_count)) > tolerance:
            raise ValueError(f"Verse {verse} wrong root cut fraction")
        expected_signed = Decimal(second - first) / Decimal(word_count)
        if abs(Decimal(str(signed)) - expected_signed) > tolerance:
            raise ValueError(f"Verse {verse} wrong signed root split ratio")

    if n_words != stats["source_words"] or n_units != stats["units"]:
        raise ValueError("Corpus source word or unit totals differ from pinned statistics")
    if stats["verses"] == 23213 and n_singles != 11:
        raise ValueError("Singleton verse count differs from the pinned 2021 dataset")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bhsa", type=Path, required=True)
    parser.add_argument("--morphhb-sha", required=True)
    args = parser.parse_args(argv)
    stats = verify_module_files(args.reference, args.candidate, args.morphhb_sha)

    from tf.fabric import Fabric

    fabric = Fabric(locations=[str(args.bhsa), str(args.candidate)], silent="deep")
    requested = " ".join(
        (
            "cantillation_leaf_count",
            "cantillation_source_id",
            "cantillation_word_count",
            "cantillation_main_cut_word_index",
            "cantillation_main_first_word_count",
            "cantillation_main_second_word_count",
            "cantillation_main_cut_fraction",
            "cantillation_main_signed_split",
        )
    )
    api = fabric.load(requested, silent="deep")
    if api is None:
        raise RuntimeError("Cannot load BHSA core with regenerated cantillation feature module")
    verify_verse_features(api, stats)
    print(json.dumps({"validated": stats, "source_commit": args.morphhb_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
