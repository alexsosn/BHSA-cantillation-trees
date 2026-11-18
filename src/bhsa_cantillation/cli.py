"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .books import OSIS_TO_BHSA
from .build import build_module


def _positive_chapter(raw: str) -> int:
    try:
        chapter = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("chapter must be a positive integer") from exc
    if chapter < 1:
        raise argparse.ArgumentTypeError("chapter must be a positive integer")
    return chapter


def _add_verse_selection(command: argparse.ArgumentParser, *, required: bool = False) -> None:
    selection = command.add_mutually_exclusive_group(required=required)
    selection.add_argument(
        "--verse", action="append", default=[], metavar="OSIS_ID",
        help="select an exact OSIS verse ID; repeat for multiple verses",
    )
    selection.add_argument(
        "--book", choices=tuple(OSIS_TO_BHSA), metavar="OSIS_BOOK",
        help="select a whole canonical OSIS book, optionally narrowed by --chapter",
    )
    command.add_argument(
        "--chapter", type=_positive_chapter, metavar="N",
        help="positive chapter number within --book",
    )


def _selected_verse_ids(api, args: argparse.Namespace) -> tuple[str, ...] | None:
    """Resolve book/chapter only through saved root IDs; writers validate the full graph."""
    if args.book is None:
        return tuple(args.verse) if args.verse else None

    F, E = api.F, api.E
    chosen: list[str] = []
    for verse in F.otype.s("verse"):
        roots = E.cant_root.f(verse)
        if len(roots) != 1:
            raise ValueError(f"Invalid saved cantillation root for BHSA verse {verse}")
        root = roots[0]
        node_type = F.otype.v(root)
        if node_type == "cant_phrase":
            identity, marker = F.cant_phrase_id.v(root), "#p"
        elif node_type == "cant_unit":
            identity, marker = F.cant_unit_id.v(root), "#u"
        else:
            raise ValueError(f"Invalid saved cantillation root type at {verse}")
        if not isinstance(identity, str) or marker not in identity:
            raise ValueError(f"Invalid saved cantillation OSIS identity at verse {verse}")
        osis = identity.split(marker, 1)[0]
        parts = osis.split(".")
        if (
            len(parts) != 3 or parts[0] not in OSIS_TO_BHSA
            or not parts[1].isdecimal() or not parts[2].isdecimal()
            or int(parts[1]) < 1 or int(parts[2]) < 1
        ):
            raise ValueError(f"Invalid saved cantillation OSIS identity: {osis}")
        if parts[0] == args.book and (
            args.chapter is None or int(parts[1]) == args.chapter
        ):
            chosen.append(osis)

    if not chosen:
        chapter = f" chapter {args.chapter}" if args.chapter is not None else ""
        raise ValueError(f"No verses in saved graph for {args.book}{chapter}")
    return tuple(chosen)


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

    graph = commands.add_parser(
        "build-graph", help="materialize a separate full BHSA+cantillation TF dataset"
    )
    graph.add_argument("--bhsa", type=Path, required=True)
    graph.add_argument("--module", type=Path, required=True)
    graph.add_argument("--morphhb", type=Path, required=True)
    graph.add_argument("--output", type=Path, required=True)
    graph.add_argument("--source-commit")
    graph.add_argument("--max-verse-distance", type=int, default=12)

    boundaries = commands.add_parser(
        "boundaries", help="export persisted cantillation phrase cuts as JSONL or TSV"
    )
    boundaries.add_argument("--graph", type=Path, required=True, help="derived graph TF directory")
    boundaries.add_argument("--format", choices=("jsonl", "tsv"), default="jsonl")
    _add_verse_selection(boundaries)
    boundaries.add_argument("--output", type=Path, required=True)

    halves = commands.add_parser(
        "compare-halves", help="compare saved root cuts to original BHSA half_verse spans"
    )
    halves.add_argument("--graph", type=Path, required=True, help="derived graph TF directory")
    halves.add_argument("--format", choices=("jsonl", "tsv"), default="jsonl")
    _add_verse_selection(halves)
    halves.add_argument("--output", type=Path, required=True)
    syntax = commands.add_parser(
        "compare-syntax", help="compare saved cantillation cuts with BHSA syntactic ends"
    )
    syntax.add_argument("--graph", type=Path, required=True, help="derived graph TF directory")
    syntax.add_argument("--format", choices=("jsonl", "tsv"), default="jsonl")
    _add_verse_selection(syntax)
    syntax.add_argument("--output", type=Path, required=True)

    relations = commands.add_parser(
        "syntax-relations",
        help="compare saved cantillation phrases with original BHSA syntax slot sets",
    )
    relations.add_argument("--graph", type=Path, required=True, help="derived graph TF directory")
    relations.add_argument("--format", choices=("jsonl", "tsv"), default="jsonl")
    _add_verse_selection(relations, required=True)
    relations.add_argument("--output", type=Path, required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    root_parser = parser()
    args = root_parser.parse_args(argv)
    graph_exports = ("boundaries", "compare-halves", "compare-syntax", "syntax-relations")
    if args.command in graph_exports:
        if args.chapter is not None and args.book is None:
            root_parser.error("--chapter requires --book")
        from .boundaries import load_boundary_api

        api = load_boundary_api(args.graph)
        chosen_verses = _selected_verse_ids(api, args)
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
    if args.command == "build-graph":
        from .graph_build import build_graph_dataset

        stats = build_graph_dataset(
            args.bhsa,
            args.module,
            args.morphhb,
            args.output,
            source_commit=args.source_commit,
            max_verse_distance=args.max_verse_distance,
        )
        print(json.dumps(asdict(stats), indent=2))
        return 0
    if args.command == "boundaries":
        from .boundaries import write_boundary_rows

        count = write_boundary_rows(
            api, args.output,
            fmt=args.format, verse_ids=chosen_verses,
        )
        print(json.dumps({"boundaries": count, "output": str(args.output)}, sort_keys=True))
        return 0
    if args.command == "compare-halves":
        from .half_verse import write_half_verse_rows

        stats = write_half_verse_rows(
            api, args.output,
            fmt=args.format, verse_ids=chosen_verses,
        )
        print(json.dumps({**stats, "output": str(args.output)}, sort_keys=True))
        return 0
    if args.command == "compare-syntax":
        from .syntax_boundary import write_syntax_boundary_rows

        stats = write_syntax_boundary_rows(
            api, args.output,
            fmt=args.format, verse_ids=chosen_verses,
        )
        print(json.dumps({**stats, "output": str(args.output)}, sort_keys=True))
        return 0
    if args.command == "syntax-relations":
        from .syntax_relations import write_syntax_relation_rows

        stats = write_syntax_relation_rows(
            api, args.output,
            fmt=args.format, verse_ids=chosen_verses,
        )
        print(json.dumps({**stats, "output": str(args.output)}, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
