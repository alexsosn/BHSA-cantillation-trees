#!/usr/bin/env python3
"""Write a reproducible comparison with Hitin-Mashiah (2016), pp. 202, 206."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from bhsa_cantillation.hitin_mashiah import build_report, load_graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True, help="saved full TF graph")
    parser.add_argument("--output", type=Path, required=True, help="JSON comparison report")
    args = parser.parse_args()
    report = build_report(load_graph(args.graph))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.output.parent,
            prefix=f".{args.output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, args.output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    for name, cells in report["tables"].items():
        print(f"{name}:")
        for cell in cells:
            print(
                f"  {cell['category']:12} {cell['length_bin']:4} "
                f"published={cell['published']:4} observed={cell['observed']:4} "
                f"delta={cell['delta']:+}"
            )
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
