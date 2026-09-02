"""Derived signatures and shape metrics for cantillation trees."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class _Stats:
    leaves: int
    depth: int
    sackin: int
    colless: int
    ladder_prefix: int
    longest_ladder: int
    accent_prefix: int
    longest_accent_run: int
    accent: str
    shape: str
    branch_signature: str
    accent_signature: str


def _label(accent: str) -> str:
    """Make an accent name unambiguous inside a parenthesized signature."""
    return re.sub(r"\W+", "_", accent, flags=re.UNICODE).strip("_") or "None"


def _walk(node: dict) -> _Stats:
    accent = _label(node["accent"])
    children = node.get("children")
    if children is None:
        return _Stats(
            leaves=1,
            depth=0,
            sackin=0,
            colless=0,
            ladder_prefix=0,
            longest_ladder=0,
            accent_prefix=1,
            longest_accent_run=1,
            accent=accent,
            shape="L",
            branch_signature="L",
            accent_signature=accent,
        )

    if len(children) != 2:
        raise ValueError("Cantillation metric input must be a binary tree")
    left = _walk(children[0])
    right = _walk(children[1])
    leaves = left.leaves + right.leaves
    sackin = left.sackin + right.sackin + leaves
    colless = left.colless + right.colless + abs(left.leaves - right.leaves)

    left_is_leaf = left.depth == 0
    right_is_leaf = right.depth == 0
    if left_is_leaf != right_is_leaf:
        internal = right if left_is_leaf else left
        ladder_prefix = 1 + internal.ladder_prefix
    else:
        ladder_prefix = 0

    child_accent_prefix = max(
        left.accent_prefix if left.accent == accent else 0,
        right.accent_prefix if right.accent == accent else 0,
    )
    accent_prefix = 1 + child_accent_prefix
    return _Stats(
        leaves=leaves,
        depth=1 + max(left.depth, right.depth),
        sackin=sackin,
        colless=colless,
        ladder_prefix=ladder_prefix,
        longest_ladder=max(ladder_prefix, left.longest_ladder, right.longest_ladder),
        accent_prefix=accent_prefix,
        longest_accent_run=max(
            accent_prefix,
            left.longest_accent_run,
            right.longest_accent_run,
        ),
        accent=accent,
        shape=f"({left.shape},{right.shape})",
        branch_signature=f"{accent}({left.branch_signature},{right.branch_signature})",
        accent_signature=f"{accent}({left.accent_signature},{right.accent_signature})",
    )


def _ratio(numerator: int, denominator: int) -> str:
    value = numerator / denominator if denominator else 0
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def tree_features(tree: dict) -> dict[str, int | str]:
    """Calculate all persisted verse-level features for one binary tree."""
    stats = _walk(tree)
    max_colless = (stats.leaves - 1) * (stats.leaves - 2) // 2
    return {
        "cantillation_shape": stats.shape,
        "cantillation_branch_signature": stats.branch_signature,
        "cantillation_accent_signature": stats.accent_signature,
        "cantillation_depth": stats.depth,
        "cantillation_leaf_count": stats.leaves,
        "cantillation_mean_leaf_depth": _ratio(stats.sackin, stats.leaves),
        "cantillation_colless": stats.colless,
        "cantillation_colless_normalized": _ratio(stats.colless, max_colless),
        "cantillation_sackin": stats.sackin,
        "cantillation_longest_ladder": stats.longest_ladder,
        "cantillation_longest_accent_run": stats.longest_accent_run,
        "cantillation_depth_leaf_ratio": _ratio(stats.depth, stats.leaves),
    }
