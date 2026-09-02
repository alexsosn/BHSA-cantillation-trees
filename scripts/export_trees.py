#!/usr/bin/env python3
"""Export BHSA cantillation trees as JSON or JSON Lines."""

from __future__ import annotations

import argparse
import sys
from contextlib import nullcontext
from pathlib import Path

from bhsa_cantillation.io import load_tree_api, select_records, tree_records, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bhsa", type=Path, required=True, help="BHSA tf/2021 directory")
    parser.add_argument("--module", type=Path, default=Path("tf/2021"))
    parser.add_argument("--output", type=Path, help="output file; stdout when omitted")
    parser.add_argument(
        "--verse",
        action="append",
        default=[],
        help="repeatable OSIS or BHSA reference, e.g. Gen.1.1 or 'Genesis 1:1'",
    )
    parser.add_argument("--jsonl", action="store_true", help="write one compact record per line")
    parser.add_argument("--pretty", action="store_true", help="indent JSON array output")
    args = parser.parse_args()

    api = load_tree_api(args.bhsa, args.module)
    records = tree_records(api)
    if args.verse:
        records = select_records(records, args.verse)
    stream = args.output.open("w", encoding="utf-8") if args.output else nullcontext(sys.stdout)
    with stream as output:
        write_json(records, output, json_lines=args.jsonl, pretty=args.pretty)


if __name__ == "__main__":
    main()
