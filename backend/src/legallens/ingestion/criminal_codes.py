"""Parser for the six criminal-law Acts: one Chunk per Section (ADR 0002).

All six share one section-record format, `{"section", "chapter", "text"}` (an optional
"title" is ignored), so one parser serves them. The adapters that turn the official PDFs into
these records are in `pdf_text`; parsing is deliberately separate from that.
"""

import re
from collections import Counter
from dataclasses import dataclass

from ..models import Provision, Status
from ..refs import format_ref, join_refs

_NUMBER = re.compile(r"^\d+[A-Z]{0,3}$")


@dataclass(frozen=True)
class CriminalAct:
    name: str
    status: Status  # the old codes are repealed, the new ones in force
    expected_count: tuple[int, int]  # plausible Chunk range, for the ingestion report


# BNS, BNSS, BSA and CrPC have exact counts: the section totals of the pinned PDFs (see
# `sources.CRIMINAL_PDFS`), cross-checked by scripts/verify_criminal_codes.py. The CrPC's 535
# includes lettered insertions such as 41A and 105A-105L. The IPC and Indian Evidence Act
# ranges are still provisional: neither is ingested yet (ticket 08).
CRIMINAL_ACTS: dict[str, CriminalAct] = {
    "ipc": CriminalAct("Indian Penal Code", "repealed", (490, 580)),
    "crpc": CriminalAct("Code of Criminal Procedure", "repealed", (535, 535)),
    "iea": CriminalAct("Indian Evidence Act", "repealed", (160, 190)),
    "bns": CriminalAct("Bharatiya Nyaya Sanhita", "in_force", (358, 358)),
    "bnss": CriminalAct("Bharatiya Nagarik Suraksha Sanhita", "in_force", (531, 531)),
    "bsa": CriminalAct("Bharatiya Sakshya Adhiniyam", "in_force", (170, 170)),
}


def _number(raw: object) -> str:
    number = re.sub(r"\s+", "", str(raw)).upper()
    if not _NUMBER.match(number):
        raise ValueError(f"unparseable section number: {raw!r}")
    return number


def _key(number: str) -> tuple[int, str]:
    m = re.match(r"(\d+)(.*)", number)
    return int(m.group(1)), m.group(2)  # type: ignore[union-attr]


def _clean(text: str) -> str:
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def parse_criminal_code(act_key: str, records: list[dict]) -> list[Provision]:
    act = CRIMINAL_ACTS[act_key]
    provisions = [
        Provision(
            act=act.name,
            chapter=rec["chapter"].strip(),
            number=_number(rec["section"]),
            status=act.status,
            text=_clean(rec["text"]),
        )
        for rec in records
    ]
    dupes = sorted(n for n, c in Counter(p.number for p in provisions).items() if c > 1)
    if dupes:
        raise ValueError(
            f"{act.name}: duplicate section numbers in source: {', '.join(dupes)}"
        )
    return sorted(provisions, key=lambda p: _key(p.number))


def apply_mappings(
    provisions: list[Provision], mappings: list[dict]
) -> list[Provision]:
    """Record repealed-to-superseding links on both ends.

    Each mapping names `old_act`/`old_number` and `new_act`/`new_number`. A mapping that
    names a Provision absent from `provisions` is an error: the mapping or the source is wrong.
    """
    by_id = {(p.act, p.number): p for p in provisions}
    forward: dict[tuple[str, str], list[str]] = {}
    backward: dict[tuple[str, str], list[str]] = {}
    for m in mappings:
        old = (m["old_act"], _number(m["old_number"]))
        new = (m["new_act"], _number(m["new_number"]))
        for side in (old, new):
            if side not in by_id:
                raise ValueError(f"mapping names missing Provision {side[0]} {side[1]}")
        forward.setdefault(old, []).append(format_ref(*new))
        backward.setdefault(new, []).append(format_ref(*old))
    return [
        p.model_copy(
            update={
                "superseded_by": join_refs(forward.get((p.act, p.number), [])),
                "supersedes": join_refs(backward.get((p.act, p.number), [])),
            }
        )
        for p in provisions
    ]
