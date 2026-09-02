#!/usr/bin/env python3
"""Render exported BHSA cantillation trees as terminal art."""

from __future__ import annotations

import argparse
from pathlib import Path

from bhsa_cantillation.io import (
    load_tree_api,
    read_export,
    render_tree,
    select_records,
    tree_records,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="JSON or JSONL produced by export_trees.py")
    source.add_argument("--bhsa", type=Path, help="BHSA tf/2021 directory")
    parser.add_argument("--module", type=Path, default=Path("tf/2021"))
    parser.add_argument("--verse", help="required when the input contains multiple verses")
    parser.add_argument("--details", action="store_true", help="show paths and BHSA slot ranges")
    parser.add_argument("--unicode-lines", action="store_true", help="use box-drawing connectors")
    args = parser.parse_args()

    if args.input:
        records = read_export(args.input)
    else:
        records = tree_records(load_tree_api(args.bhsa, args.module))
    if args.verse:
        records = select_records(records, [args.verse])
    selected = list(records)
    if len(selected) != 1:
        raise SystemExit(f"Expected one tree, found {len(selected)}; specify --verse")
    record = selected[0]
    if "osis_id" in record:
        print(f"{record['osis_id']} ({record['system']}, {record['alignment']})")
    print(render_tree(record["tree"], details=args.details, unicode_lines=args.unicode_lines))


if __name__ == "__main__":
    main()
