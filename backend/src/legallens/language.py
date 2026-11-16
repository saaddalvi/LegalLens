"""Query language detection. LegalLens supports English and Hindi only."""

from typing import Literal

Language = Literal["en", "hi"]

LANGUAGE_NAMES: dict[Language, str] = {"en": "English", "hi": "Hindi"}

_DEVANAGARI = range(0x0900, 0x0980)


def detect_language(query: str) -> Language:
    """Hindi when Devanagari makes up most of the Query's letters, otherwise English."""
    letters = [c for c in query if c.isalpha()]
    if not letters:
        return "en"
    devanagari = sum(ord(c) in _DEVANAGARI for c in letters)
    return "hi" if devanagari * 2 > len(letters) else "en"
