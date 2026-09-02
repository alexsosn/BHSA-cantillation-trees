"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .build import build_module


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="bhsa-cantillation")
    commands = root.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build the Text-Fabric module")
    build.add_argument("--bhsa", type=Path, required=True, help="BHSA tf/2021 directory")
    build.add_argument("--morphhb", type=Path, required=True, help="MorphHB repository root")
    build.add_argument("--output", type=Path, default=Path("tf/2021"))
    build.add_argument("--version", default="2021")
    build.add_argument("--source-commit", help="MorphHB git commit recorded in metadata")
    build.add_argument("--max-verse-distance", type=int, default=12)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "build":
        stats = build_module(
            args.bhsa,
            args.morphhb,
            args.output,
            version=args.version,
            max_verse_distance=args.max_verse_distance,
            source_commit=args.source_commit,
        )
        print(json.dumps(asdict(stats), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
