"""Align MorphHB orthographic words to BHSA morphological word slots."""

from __future__ import annotations

from .model import AlignmentResult, SourceWord


def edit_distance(left: str, right: str) -> int:
    """Compute Levenshtein distance with O(min(n, m)) memory."""
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _character_mapping(source: str, target: str) -> tuple[list[int | None], int]:
    """Map source character indices to target indices by Levenshtein backtrace."""
    rows = len(source) + 1
    columns = len(target) + 1
    matrix = [[0] * columns for _ in range(rows)]
    for row in range(rows):
        matrix[row][0] = row
    for column in range(columns):
        matrix[0][column] = column

    for row in range(1, rows):
        for column in range(1, columns):
            matrix[row][column] = min(
                matrix[row - 1][column] + 1,
                matrix[row][column - 1] + 1,
                matrix[row - 1][column - 1] + (source[row - 1] != target[column - 1]),
            )

    mapping: list[int | None] = [None] * len(source)
    row = len(source)
    column = len(target)
    while row or column:
        if row and column:
            substitution = source[row - 1] != target[column - 1]
            if matrix[row][column] == matrix[row - 1][column - 1] + substitution:
                mapping[row - 1] = column - 1
                row -= 1
                column -= 1
                continue
        if row and matrix[row][column] == matrix[row - 1][column] + 1:
            row -= 1
            continue
        column -= 1
    return mapping, matrix[-1][-1]


def _source_spans(source_words: list[SourceWord]) -> list[tuple[int, int]]:
    spans = []
    start = 0
    for word in source_words:
        end = start + len(word.consonants)
        spans.append((start, end))
        start = end
    return spans


def _target_character_slots(target_slots: list[int], target_text: list[str]) -> list[int]:
    return [slot for slot, text in zip(target_slots, target_text, strict=True) for _ in text]


def align_words(
    source_words: list[SourceWord],
    target_slots: list[int],
    target_text: list[str],
) -> AlignmentResult:
    """Align whole-verse consonants, allowing word-boundary disagreements.

    MorphHB uses orthographic words while BHSA generally uses morphological
    words. In a few places one BHSA slot also covers two MorphHB words. Mapping
    character spans, rather than partitioning the slot list, preserves both
    kinds of disagreement.
    """
    if len(target_slots) != len(target_text):
        raise ValueError("target_slots and target_text must have equal length")
    if not source_words or not target_slots:
        if not source_words and not target_slots:
            return AlignmentResult((), 0)
        raise ValueError("Cannot align an empty sequence to a non-empty sequence")
    if any(not word.consonants for word in source_words):
        raise ValueError("MorphHB word without consonantal content")

    source_text = "".join(word.consonants for word in source_words)
    target_flat = "".join(target_text)
    if not target_flat:
        raise ValueError("BHSA verse without consonantal content")
    if source_text == target_flat:
        char_mapping: list[int | None] = list(range(len(source_text)))
        distance = 0
    else:
        char_mapping, distance = _character_mapping(source_text, target_flat)

    target_char_slots = _target_character_slots(target_slots, target_text)
    groups: list[list[int]] = []
    for start, end in _source_spans(source_words):
        mapped_indices = [index for index in char_mapping[start:end] if index is not None]
        if not mapped_indices:
            before = next(
                (index for index in reversed(char_mapping[:start]) if index is not None),
                None,
            )
            after = next((index for index in char_mapping[end:] if index is not None), None)
            nearest = after if after is not None else before
            if nearest is None:
                raise ValueError("Could not anchor a MorphHB word in the BHSA verse")
            mapped_indices = [nearest]
        first = min(mapped_indices)
        last = max(mapped_indices)
        group = list(dict.fromkeys(target_char_slots[first : last + 1]))
        groups.append(group)

    # BHSA has a handful of empty slots. Attach them to the closest preceding
    # source word (or the first word when the empty slot opens a verse).
    used_slots = {slot for group in groups for slot in group}
    slot_positions = {slot: index for index, slot in enumerate(target_slots)}
    for target_index, slot in enumerate(target_slots):
        if slot in used_slots:
            continue
        preceding = [
            group_index
            for group_index, group in enumerate(groups)
            if group and slot_positions[group[-1]] < target_index
        ]
        owner = preceding[-1] if preceding else 0
        groups[owner].append(slot)
        groups[owner].sort(key=slot_positions.get)

    return AlignmentResult(tuple(tuple(group) for group in groups), distance)
