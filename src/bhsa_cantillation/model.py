"""Internal immutable data structures."""

from dataclasses import dataclass, field


@dataclass
class SourceWord:
    source_id: str
    text: str
    consonants: str
    morph_count: int
    accent_text: str = ""
    path: str | None = None
    trailing: str = ""
    accent_marks: str = ""
    accent_type: str = "conjunctive"
    accent_name: str = ""
    accent_catalogued: bool = False


@dataclass(frozen=True)
class WordAlignment:
    source: SourceWord
    slots: tuple[int, ...]


@dataclass(frozen=True)
class AccentUnit:
    ordinal: int
    path: str
    slots: tuple[int, ...]
    text: str
    accent_name: str
    source_words: tuple[SourceWord, ...] = field(repr=False)


@dataclass(frozen=True)
class AlignmentResult:
    groups: tuple[tuple[int, ...], ...]
    distance: int

    @property
    def status(self) -> str:
        return "exact" if self.distance == 0 else "fuzzy"
