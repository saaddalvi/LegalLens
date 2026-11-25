"""Splitting a Contract's text into Clauses. Deterministic code, not a model call.

Clause numbers follow the Contract's own numbering (1, 1.1, 7(a), 7.2.1, ...), so the number
LegalLens quotes is the number on the user's paper. Text before the first numbered Clause
(the title, the parties, the recitals) is Clause "0". A Contract with no numbering has its
paragraphs numbered in order. A Clause longer than PIECE_CHARS is cut into pieces that keep
its number, so each piece is searchable (as long Provisions are, ADR 0002); joining the
pieces of a Clause gives its text exactly.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

PIECE_CHARS = 800
HEADING_MAX = 80

_WORD = r"(?:(?:clause|section|article)\s+)?"
# "1." or "12)" (punctuation required, so "12 March" and "5000 rupees" are not Clauses)
_PLAIN = re.compile(
    rf"^{_WORD}(\d{{1,3}})[.)](?:\s+(?P<rest>\S.*)|\s*$)", re.IGNORECASE
)
# "7.2" or "7.2.1." (punctuation optional)
_DOTTED = re.compile(
    rf"^{_WORD}(\d{{1,3}}(?:\.\d{{1,3}})+)\.?\s+(?P<rest>\S.*)", re.IGNORECASE
)
# "7(a)" or "7.2(b)"
_EXPLICIT_SUB = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3})*)\(([a-z]|[ivx]+)\)\s+(?P<rest>\S.*)"
)
# "(a)" or "(iv)" under the Clause above
_BARE_SUB = re.compile(r"^\(([a-z]|[ivx]+)\)\s+(?P<rest>\S.*)")
_ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


@dataclass(frozen=True)
class ClausePiece:
    number: str
    heading: str
    text: str
    piece: int  # 0 for the first (often only) piece


def split_clauses(text: str) -> list[ClausePiece]:
    """The Clauses of `text` as pieces, in order. Empty for blank text."""
    if not text.strip():
        return []
    marked = _numbered(text)
    if marked is None:
        return [
            piece
            for i, body in enumerate(_paragraphs(text), start=1)
            for piece in _pieces(str(i), "", body)
        ]
    return [
        piece
        for number, heading, body in marked
        for piece in _pieces(number, heading, body)
    ]


def count_clauses(numbers: Iterable[str]) -> int:
    """How many Clauses a reader would count on paper: the distinct top-level numbers.
    "7.2" and "7(a)" count under 7, and Clause "0" (the recitals) is not counted. `numbers`
    may repeat, as the pieces of a long Clause do."""
    return len({re.match(r"\d+", n)[0] for n in numbers if n != "0"})


def _paragraphs(text: str) -> list[str]:
    """Paragraphs split at blank lines; a text with no blank lines (a DOCX's paragraphs
    arrive one per line) is split at line ends instead."""
    paras = [p.strip() for p in re.split(r"\n[ \t]*\n", text.strip())]
    if len(paras) == 1:
        paras = [ln.strip() for ln in paras[0].split("\n")]
    return [p for p in paras if p]


def _numbered(text: str) -> list[tuple[str, str, str]] | None:
    """(number, heading, text) per Clause, or None when the text has no numbering."""
    sections: list[tuple[str, str, list[str]]] = []  # number, heading, lines
    seen: set[str] = set()
    base: str | None = None  # the last numeric Clause, parent of "(a)"
    last_letter: str | None = None
    preamble: list[str] = []
    markers = 0

    for line in text.splitlines():
        stripped = line.strip()
        found = _marker(stripped, base, last_letter)
        if found is not None and found[0] not in seen:
            number, rest, new_base, new_letter = found
            seen.add(number)
            base, last_letter = new_base, new_letter
            markers += 1
            heading = (
                rest
                if rest and len(rest) <= HEADING_MAX and not rest.endswith(".")
                else ""
            )
            sections.append((number, heading, [stripped]))
        elif sections:
            sections[-1][2].append(line.rstrip())
        else:
            preamble.append(line.rstrip())
    if markers < 2:
        return None
    out = [(n, h, "\n".join(lines).strip()) for n, h, lines in sections]
    if "".join(preamble).strip():
        out.insert(0, ("0", "", "\n".join(preamble).strip()))
    return out


def _marker(line: str, base: str | None, last_letter: str | None):
    """(number, rest of line, new base, new last letter) if `line` opens a Clause, else None."""
    if m := _EXPLICIT_SUB.match(line):
        return f"{m[1]}({m[2]})", m["rest"], m[1], m[2]
    if m := _DOTTED.match(line):
        return m[1], m["rest"], m[1], None
    if m := _PLAIN.match(line):
        return m[1], m["rest"] or "", m[1], None
    if base is not None and (m := _BARE_SUB.match(line)):
        token = m[1]
        is_letter_next = len(token) == 1 and (
            last_letter is None
            or token not in _ROMAN
            or ord(token) == ord(last_letter) + 1
        )
        if token in _ROMAN and last_letter is not None and not is_letter_next:
            return f"{base}({last_letter})({token})", m["rest"], base, last_letter
        if len(token) == 1:
            return f"{base}({token})", m["rest"], base, token
    return None


def _pieces(number: str, heading: str, text: str) -> list[ClausePiece]:
    out, rest = [], text
    while len(rest) > PIECE_CHARS:
        cut = _cut(rest)
        out.append(rest[:cut])
        rest = rest[cut:]
    out.append(rest)
    return [ClausePiece(number, heading, t, i) for i, t in enumerate(out)]


def _cut(text: str) -> int:
    """Where to end the next piece: after a line end, else a sentence end, else a space."""
    window = text[:PIECE_CHARS]
    floor = PIECE_CHARS // 4
    for sep in ("\n", ". ", " "):
        i = window.rfind(sep)
        if i >= floor:
            return i + len(sep)
    return PIECE_CHARS
