"""Parser for the civictech-India Constitution JSON: one Chunk per Article (ADR 0002)."""

import re
from collections import Counter

from ..models import Provision

ACT = "Constitution of India"

# (first Article, Part). Parts are contiguous in Article order, so a Chunk's Part is the
# last entry whose start is not after its number. Ordering key: (digits, letter suffix).
_PART_STARTS = [
    ("1", "I"), ("5", "II"), ("12", "III"), ("36", "IV"), ("51A", "IVA"), ("52", "V"),
    ("152", "VI"), ("238", "VII"), ("239", "VIII"), ("243", "IX"), ("243P", "IXA"),
    ("243ZH", "IXB"), ("244", "X"), ("245", "XI"), ("264", "XII"), ("301", "XIII"),
    ("308", "XIV"), ("323A", "XIVA"), ("324", "XV"), ("330", "XVI"), ("343", "XVII"),
    ("352", "XVIII"), ("361", "XIX"), ("368", "XX"), ("369", "XXI"), ("393", "XXII"),
]  # fmt: skip

_NUMBER = re.compile(r"^(\d+)([A-Z]*)$")
_REPEALED = re.compile(r"^(\[[^\]]*\]\s*)?(Rep\.|Omitted|Repealed)", re.IGNORECASE)


def _key(number: str) -> tuple[int, str]:
    m = _NUMBER.match(number)
    return int(m.group(1)), m.group(2)


def _part(number: str) -> str:
    key = _key(number)
    name = None
    for start, part in _PART_STARTS:
        if _key(start) <= key:
            name = part
    if name is None:
        raise ValueError(f"Article {number} precedes Article 1")
    return f"Part {name}"


def _normalise_number(raw: int | str) -> str:
    number = re.sub(r"\s+", "", str(raw)).upper()
    if not _NUMBER.match(number):
        raise ValueError(f"unparseable Article number: {raw!r}")
    return number


def _clean(text: str) -> str:
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _provision(number: str, text: str) -> Provision:
    return Provision(
        act=ACT,
        chapter=_part(number),
        number=number,
        status="repealed" if _REPEALED.match(text) else "in_force",
        text=text,
    )


def _apply_patches(provisions: list[Provision], patches: list[dict]) -> list[Provision]:
    """Patches correct the source after checking it against the official text.

    Each has an `op` ("add" or "replace"), the Article `number`, the official `text`, and a
    `reason`. Patching an Article that is absent, or adding one already present, is an error:
    it means the source changed and the patch needs reviewing.
    """
    by_number = {p.number: p for p in provisions}
    for patch in patches:
        number = _normalise_number(patch["number"])
        text = _clean(patch["text"])
        if patch["op"] == "add":
            if number in by_number:
                raise ValueError(
                    f"patch adds Article {number} but the source already has it"
                )
        elif patch["op"] == "replace":
            if number not in by_number:
                raise ValueError(
                    f"patch replaces Article {number} but the source lacks it"
                )
        else:
            raise ValueError(f"unknown patch op: {patch['op']!r}")
        by_number[number] = _provision(number, text)
    return sorted(by_number.values(), key=lambda p: _key(p.number))


def parse_constitution(
    records: list[dict], patches: list[dict] | None = None
) -> list[Provision]:
    provisions = [
        _provision(_normalise_number(rec["article"]), _clean(rec["description"]))
        for rec in records
        if str(rec["article"]).strip() != "0"  # the Preamble is not an Article
    ]
    counts = Counter(p.number for p in provisions)
    dupes = sorted(n for n, c in counts.items() if c > 1)
    if dupes:
        raise ValueError(f"duplicate Article numbers in source: {', '.join(dupes)}")
    return _apply_patches(provisions, patches or [])
