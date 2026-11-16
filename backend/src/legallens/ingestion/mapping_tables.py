"""Parser for the NCRB "Corresponding Section Table" (new Act against the Act it repeals).

The PDF flattens a two-column table into text: the new Act's section first, then the repealed
Act's, each title wrapping onto further lines, so a row's numbers can land several lines
apart. Rows come in a few shapes, all handled here:

* `8. Court of Session 9. Court of Session.`: a plain pair, on one line or spread out.
* `Deleted 8. Metropolitan areas.`: an old section with no new counterpart.
* `86. ...` then `New Section`: a new section with no old counterpart.
* `35(1)`, `35(2) 41(2)`, `35(3), 35(4) 35(5), 35(6) 41A ...`, `43(3) New Sub-Section`:
  sub-section rows, which collapse to whole-section pairs. One new section can map to
  several old ones (35 to 41 and 41A) and the reverse.

A new section's heading is a plain number opening a line, above the last new number, in a
row whose old number is already known; anything else after the first number is an old section.
"""

import re
from dataclasses import dataclass, field

_NUMBER_KEY = re.compile(r"(\d+)(.*)")
_TOKEN = re.compile(
    r"(?<![\w(])(?:"
    r"(?P<sub>(?P<sb>\d+)(?P<ss>[A-Z]{0,3})\s?\(\d+[A-Za-z]?\))"  # 35(2), 41A(1)
    r"|(?P<dotted>(?P<db>\d+)(?P<ds>-?[A-Z]{0,3})\.\s+(?=\S))"  # 41A. Title, 105-I. Title
    r"|(?P<bare>(?P<bb>\d+)(?P<bs>[A-Z]{0,3})\s+(?=[A-Z][a-z]))"  # 41A Title, 151 Title (no dot)
    r")"
)
_DELETED = re.compile(r"^Deleted\s+(\d+)([A-Z]{0,3})\.")
_NEW_SECTION = re.compile(r"\bnew\s+section\b", re.IGNORECASE)


@dataclass
class MappingTable:
    mappings: list[dict] = field(default_factory=list)
    deleted: list[str] = field(
        default_factory=list
    )  # old sections with no new counterpart
    new: list[str] = field(default_factory=list)  # new sections with no old counterpart


def section_key(number: str) -> tuple[int, str]:
    m = _NUMBER_KEY.match(number)
    return int(m.group(1)), m.group(2)  # type: ignore[union-attr]


def _table_lines(pages: list[str], old_title: str) -> list[str]:
    start = next(
        (
            i
            for i, p in enumerate(pages)
            if any(l.strip() == old_title for l in p.splitlines())
        ),
        None,
    )
    if start is None:
        raise ValueError(f"no page of the table has the column heading {old_title!r}")
    lines: list[str] = []
    for n, page in enumerate(pages[start:]):
        if "Chapters and Sections" in page:
            break  # the Act's own text follows the table
        page_lines = page.splitlines()
        if n == 0:
            page_lines = page_lines[
                next(i for i, l in enumerate(page_lines) if l.strip() == old_title)
                + 1 :
            ]
        lines += [l.strip() for l in page_lines]
    return [l for l in lines if l]


def parse_corresponding_table(
    pages: list[str], new_act: str, old_act: str, old_title: str
) -> MappingTable:
    pairs: set[tuple[str, str]] = set()
    deleted: list[str] = []
    new: list[str] = []
    cur: str | None = None  # the new section whose row we are in
    last_new = 0  # new-Act numbers only ever increase down the table
    awaiting_old = False
    for line in _table_lines(pages, old_title):
        d = _DELETED.match(line)
        if d:
            deleted.append(d.group(1) + d.group(2))
            continue
        for m in _TOKEN.finditer(line):
            at_line_start = m.start() == 0
            if m.group("sub"):
                base = m.group("sb") + m.group("ss")
                if cur is not None and base != cur:
                    pairs.add((cur, base))  # the old side of a sub-section row
                continue
            dotted = m.group("dotted") is not None
            number = (
                (m.group("db") + m.group("ds"))
                if dotted
                else m.group("bb") + m.group("bs")
            )
            number = number.replace("-", "")
            plain = number.isdigit()
            if not dotted and plain and not awaiting_old:
                continue  # a bare number is only trusted where an old number is due
            row_has_old = any(n == cur for n, _ in pairs)
            starts_next_row = plain and at_line_start and int(number) > last_new
            if (
                awaiting_old
                and cur is not None
                and not (row_has_old and starts_next_row and dotted)
            ):
                pairs.add((cur, number))
                awaiting_old = False
            elif starts_next_row:
                cur, last_new, awaiting_old = number, int(number), True
            elif cur is not None:
                pairs.add((cur, number))  # a further old section of the same row
        if _NEW_SECTION.search(line) and awaiting_old and cur is not None:
            new.append(cur)
            awaiting_old = False
    mappings = [
        {"old_act": old_act, "old_number": o, "new_act": new_act, "new_number": n}
        for n, o in sorted(pairs, key=lambda p: (section_key(p[0]), section_key(p[1])))
    ]
    return MappingTable(
        mappings,
        sorted(set(deleted), key=section_key),
        sorted(set(new), key=section_key),
    )


_BSA_OLD_TITLE = "INDIAN EVIDENCE ACT, 1872"
_BSA_TOKEN = re.compile(
    r"(?P<deleted>DELETED\s+(?P<dn>\d+[A-Z]{0,3})\.)"  # an Evidence Act section with no BSA one
    r"|(?P<repealed>(?P<rn>\d+)\.\s+Repealed)"
    r"|(?P<proviso>\d+\.\s+Proviso(?:\s+\d(?!\d))?)"  # a BSA proviso row: the section's row goes on
    r"|(?P<newsec>New\s+Section)"
    r"|(?P<sub>(?<![\w.])\d+\(\d+[a-z]?\))"  # 23(1), 146(3): sub-sections of the BSA row
    r"|(?P<head>(?<![\w(])(?P<hn>\d+[A-Z]{0,3})\.\s+(?=\S))",
    re.IGNORECASE,
)


def parse_bsa_table(
    pages: list[str], new_act: str, old_act: str, first: int = 1
) -> MappingTable:
    """The NCRB BSA table against the Indian Evidence Act, as whole-section mappings.

    The BSA's section numbers run 1..170 in order, with no lettered sections, so a numbered
    heading is the next row's BSA section only when it is exactly the next number and the
    current row already has its Evidence Act counterpart (or is a "New Section"). Any other
    heading is an Evidence Act section of the current row. That settles rows such as BSA 2,
    whose Evidence Act sections 3 and 4 come ahead of BSA 3. Sub-section and proviso markers
    belong to the current row; an Evidence Act heading right after one is not a new row.
    `first` is the BSA section the table starts at (1 except in tests on excerpts).
    """
    pairs: set[tuple[str, str]] = set()
    deleted: list[str] = []
    new: list[str] = []
    cur: str | None = None
    last = first - 1
    row_closed = False  # the current row has an old section, or is a new one
    after_marker = False
    for line in _table_lines(pages, _BSA_OLD_TITLE):
        if line.startswith(("P a g e", "HomePage")):
            continue
        for m in _BSA_TOKEN.finditer(line):
            if m.group("deleted") or m.group("repealed"):
                deleted.append((m.group("dn") or m.group("rn")).upper())
            elif m.group("newsec"):
                if cur is not None and not row_closed:
                    new.append(cur)
                    row_closed = True
            elif m.group("sub") or m.group("proviso"):
                after_marker = True
                continue
            elif m.group("head"):
                number = m.group("hn").upper()
                if (
                    number.isdigit()
                    and int(number) == last + 1
                    and (cur is None or row_closed)
                    and not after_marker
                ):
                    cur, last, row_closed = number, int(number), False
                elif cur is not None:
                    pairs.add((cur, number))
                    row_closed = True
            after_marker = False
    mappings = [
        {"old_act": old_act, "old_number": o, "new_act": new_act, "new_number": n}
        for n, o in sorted(pairs, key=lambda p: (section_key(p[0]), section_key(p[1])))
    ]
    return MappingTable(
        mappings,
        sorted(set(deleted), key=section_key),
        sorted(set(new), key=section_key),
    )
