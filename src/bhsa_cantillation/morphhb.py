"""Read MorphHB verses, structural paths, and accent catalogues."""

from __future__ import annotations

import json
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

from .model import SourceWord

NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
W = f"{NS}w"
VERSE = f"{NS}verse"
NOTE = f"{NS}note"
RDG = f"{NS}rdg"
SEG = f"{NS}seg"


def normalize_consonants(text: str) -> str:
    """Return Hebrew consonants only, normalized for alignment."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(
        char
        for char in decomposed
        if "\u05d0" <= char <= "\u05ea" and not unicodedata.combining(char)
    )


def extract_marks(text: str) -> str:
    """Extract cantillation marks and structurally relevant punctuation."""
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if "\u0591" <= char <= "\u05af" or char in {"\u05bd", "\u05be", "\u05c0", "\u05c3"}
    )


def accent_system(osis_id: str) -> str:
    """Select the prose or poetic accent catalogue following MorphHB."""
    book, chapter_text, verse_text = osis_id.split(".")
    chapter = int(chapter_text)
    verse = int(verse_text)
    if book in {"Ps", "Prov"}:
        return "poetic"
    prose_job = chapter < 3 or (chapter == 42 and verse > 6) or (chapter == 3 and verse == 1)
    if book == "Job" and not prose_job:
        return "poetic"
    return "prose"


def load_accent_catalog(path: Path) -> dict:
    """Parse MorphHB's JSON-compatible JavaScript accent catalogue."""
    content = path.read_text(encoding="utf-8")
    start = content.index("{")
    end = content.rindex("}") + 1
    catalog = json.loads(content[start:end])
    if set(catalog) != {"prose", "poetic"}:
        raise ValueError(f"Unexpected accent catalogue sections in {path}")
    return catalog


def _accent_entry(catalog: dict, system: str, accent_type: str, marks: str) -> dict | None:
    entries = catalog[system][accent_type]
    entry = entries.get(marks)
    if entry is None and marks.replace("\u05bd", ""):
        # Meteg may accompany another accent without changing its catalogue name.
        entry = entries.get(marks.replace("\u05bd", ""))
    return entry


def _qere_words(note: ET.Element) -> list[ET.Element]:
    if note.tag != NOTE or note.get("type") != "variant":
        return []
    reading = note.find(RDG)
    return reading.findall(W) if reading is not None else []


def parse_verse(verse: ET.Element, catalog: dict) -> list[SourceWord]:
    """Convert direct verse children into MorphHB orthographic words."""
    osis_id = verse.get("osisID")
    if not osis_id:
        raise ValueError("MorphHB verse without osisID")
    system = accent_system(osis_id)
    words: list[SourceWord] = []

    for child in list(verse):
        if child.tag == W:
            text = "".join(child.itertext())
            words.append(
                SourceWord(
                    source_id=child.get("id", ""),
                    text=text,
                    consonants=normalize_consonants(text),
                    morph_count=text.count("/") + 1,
                    accent_text=text,
                    path=child.get("n"),
                )
            )
        elif child.tag == NOTE and words:
            qere_words = _qere_words(child)
            if qere_words:
                words[-1].text = " ".join("".join(word.itertext()) for word in qere_words)
                words[-1].accent_text = "".join(qere_words[-1].itertext())
                paths = [word.get("n") for word in qere_words if word.get("n") is not None]
                words[-1].path = paths[-1] if paths else words[-1].path
        elif child.tag == SEG and words:
            words[-1].trailing += "".join(child.itertext())

    for word in words:
        word.accent_type = "disjunctive" if word.path is not None else "conjunctive"
        word.accent_marks = extract_marks(word.accent_text + word.trailing)
        entry = _accent_entry(catalog, system, word.accent_type, word.accent_marks)
        if entry:
            word.accent_name = entry["name"]
            word.accent_catalogued = True
        else:
            names = [unicodedata.name(char, f"U+{ord(char):04X}") for char in word.accent_marks]
            word.accent_name = " + ".join(names) if names else "None"
    return words


def read_book(path: Path, catalog: dict):
    """Yield `(osis_id, words)` pairs from one MorphHB book."""
    root = ET.parse(path).getroot()
    for verse in root.iter(VERSE):
        osis_id = verse.get("osisID")
        if osis_id:
            yield osis_id, parse_verse(verse, catalog)
