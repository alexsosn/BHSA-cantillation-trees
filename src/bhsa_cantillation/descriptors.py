"""MorphHB orthographic-word counts and directional root-cut measurements."""

from __future__ import annotations

from .model import AccentUnit


def _leaf_count(node: dict) -> int:
    """Count leaves, rejecting non-binary internal nodes."""
    children = node.get("children")
    if children is None:
        return 1
    if not isinstance(children, list) or len(children) != 2:
        raise ValueError("Cantillation root-cut input must be a binary tree")
    return _leaf_count(children[0]) + _leaf_count(children[1])


def _decimal(numerator: int, denominator: int) -> str:
    """Match the existing at-most-six-decimal Text-Fabric string convention."""
    return f"{numerator / denominator:.6f}".rstrip("0").rstrip(".") or "0"


def main_cut_features(units: list[AccentUnit], tree: dict) -> dict[str, str | int]:
    """Describe the root split using MorphHB orthographic words, not BHSA slots.

    The main cut falls after the final source word in the root's first child.
    A one-unit verse has no internal cut and therefore only a word count.
    """
    if not units:
        raise ValueError("Cannot compute cantillation word metrics without units")

    word_counts = [len(unit.source_words) for unit in units]
    if not all(word_counts):
        raise ValueError("Each accentual unit must contain source words")
    total_words = sum(word_counts)

    if _leaf_count(tree) != len(units):
        raise ValueError("Cantillation tree leaf count does not match accentual units")

    features: dict[str, int | str] = {"cantillation_word_count": total_words}
    if len(units) == 1:
        return features

    first_units = _leaf_count(tree["children"][0])
    first_words = sum(word_counts[:first_units])
    second_words = total_words - first_words
    if not first_words or not second_words:
        raise ValueError("Root cut must separate nonempty source-word spans")

    features.update(
        cantillation_main_cut_word_index=first_words,
        cantillation_main_first_word_count=first_words,
        cantillation_main_second_word_count=second_words,
        cantillation_main_cut_fraction=_decimal(first_words, total_words),
        cantillation_main_signed_split=_decimal(second_words - first_words, total_words),
    )
    return features
