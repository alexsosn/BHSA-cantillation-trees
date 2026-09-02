from bhsa_cantillation.alignment import align_words, edit_distance
from bhsa_cantillation.model import SourceWord


def word(text: str, morph_count: int = 1) -> SourceWord:
    return SourceWord("id", text, text, morph_count, accent_text=text)


def test_edit_distance():
    assert edit_distance("אלהים", "אלהים") == 0
    assert edit_distance("הוא", "היא") == 1


def test_exact_alignment_groups_bhsa_morphemes():
    source = [word("בראשית", 2), word("ברא"), word("אלהים")]
    result = align_words(source, [1, 2, 3, 4], ["ב", "ראשית", "ברא", "אלהים"])
    assert result.distance == 0
    assert result.groups == ((1, 2), (3,), (4,))


def test_fuzzy_alignment_is_explicit():
    source = [word("הוא"), word("טוב")]
    result = align_words(source, [10, 11], ["היא", "טוב"])
    assert result.status == "fuzzy"
    assert result.distance == 1
    assert result.groups == ((10,), (11,))


def test_one_bhsa_slot_can_cover_two_morphhb_words():
    source = [word("תובל"), word("קין"), word("לטש")]
    result = align_words(source, [20, 21], ["תובלקין", "לטש"])
    assert result.distance == 0
    assert result.groups == ((20,), (20,), (21,))
