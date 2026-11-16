"""Adapters from extracted PDF text to the section records `parse_criminal_code` takes.

Each adapter takes the PDF's text page by page (pypdf `extract_text()` output) and yields
`{"section", "chapter", "text"}` records. Quirks of each source are handled here and
exercised by short real excerpts in the tests; nothing here is specific to one Act except
where a function says so.
"""

import re
from pathlib import Path

_SECTION_HEAD = re.compile(
    r"^(\d+)([A-Z]{0,3})\.(?!\d)(?:\s*(\S.*))?$"
)  # number may stand alone
_SUBHEADING = re.compile(
    r"^(?:Of\s+[a-z]|[A-Z]\.\s*[—–-]\s*\S)"
)  # "Of  hurt", "A.—Summons"
_CHAPTER = re.compile(r"^CHAPTER\s+([IVXL]+[A-Z]{0,2})\s*$")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_FOOTER = re.compile(r"^THE GAZETTE OF INDIA")
_RUNNING_HEAD = re.compile(
    r"^\d+ THE GAZETTE OF INDIA"
)  # the last page puts it on top, on one line
_END = re.compile(
    r"^(?:[—–-]{4,}|(?:THE (?:FIRST )?)?SCHEDULE\.?)$"
)  # end of the Act proper
_ACT_NOTE = re.compile(
    r"^\d+ of \d{4}\.$"
)  # "40 of 2019.": a marginal citation of an Act
_COVER_START = "vlk/kkj.k"  # Hindi-font "असाधारण", first line of the cover block
_COVER_END = "published for general information"
_MARGINAL_MAX = 24  # the side-heading column is narrow; body lines wrap far wider
_MIN_RUN = 4  # fewer consecutive short lines are more likely body text
_BODY_STARTS = ("(", "Explanation", "Illustration", "Provided", "Exception")
_BODY_ENDS = (";", ":", "—", "–")


def pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader

    return [p.extract_text() or "" for p in PdfReader(path).pages]


def _is_marginal(line: str) -> bool:
    if _ACT_NOTE.match(line):
        return True
    return (
        2 <= len(line) <= _MARGINAL_MAX
        and not line.isupper()  # CHAPTER / PART headings
        and not line.startswith(_BODY_STARTS)
        and not line.endswith(_BODY_ENDS)
        and not _SECTION_HEAD.match(line)
    )


def _is_bare_number(line: str) -> bool:
    """ "230." alone: a section's heading, unless it ends a side-heading ("with section 230.")."""
    m = _SECTION_HEAD.match(line)
    return bool(m) and not m.group(3)


def _pop_marginals(lines: list[str]) -> None:
    while lines and (
        _is_marginal(lines[-1])
        or (len(lines) > 1 and _is_bare_number(lines[-1]) and _is_marginal(lines[-2]))
    ):
        lines.pop()


def _drop_marginal_runs(lines: list[str]) -> list[str]:
    """Drop blocks of side-headings that the PDF left in mid-page, before more body text."""
    out: list[str] = []
    run: list[str] = []
    for line in lines + [""]:
        if line and _is_marginal(line):
            run.append(line)
            continue
        if len(run) < _MIN_RUN or not run[0][0].isupper():  # headings start capitalised
            out.extend(run)
        run = []
        if line:
            out.append(line)
    return out


def _strip_cover(lines: list[str]) -> list[str]:
    """Drop the Hindi-font cover block pypdf interleaves into page 1."""
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.strip() == _COVER_START:
            skipping = True
            _pop_marginals(
                out
            )  # BNS and BSA put page 1's side-heading before the block
        if skipping:
            if _COVER_END in line:
                skipping = False
            continue
        if _DEVANAGARI.search(line) or "xxxGID" in line or line.startswith("CG-DL-"):
            continue
        out.append(line)
    return out


def _gazette_page_body(page: str) -> tuple[list[str], bool]:
    """The page's body lines, and whether the Act proper ended on this page."""
    lines = [l.rstrip() for l in _strip_cover(page.splitlines())]
    lines = [l for l in lines if l.strip() and not re.fullmatch(r"_{5,}", l.strip())]
    lines = [l for l in lines if not _RUNNING_HEAD.match(l) and not l.strip().isdigit()]
    end = next((i for i, l in enumerate(lines) if _END.match(l.strip())), None)
    if end is not None:
        lines = lines[:end]
    footer = next((i for i, l in enumerate(lines) if _FOOTER.match(l)), None)
    if footer is not None:
        lines = lines[:footer]
        while lines and re.fullmatch(r"Sec\. \d+\]", lines[-1].strip()):
            lines.pop()
    _pop_marginals(lines)  # page 1 of BNSS and the last page have no footer
    lines = _drop_marginal_runs(lines)
    return lines, end is not None


def gazette_sections(pages: list[str]) -> list[dict]:
    """Sections of a Gazette-published Act (BNS, BNSS, BSA), in order.

    Side-headings and "40 of 2019." notes are collected by the PDF into a block just above
    each page footer; the block is dropped. Text before section 1 (title, preamble) belongs
    to no section and is dropped too.
    """
    records: list[dict] = []
    chapter = ""
    in_chapter_heading = False
    prev: tuple[int, str] | None = None
    for page in pages:
        body, ended = _gazette_page_body(page)
        for line in body:
            line = line.strip()
            m = _CHAPTER.match(line)
            if m:
                chapter, in_chapter_heading = f"Chapter {m.group(1)}", True
                continue
            h = _SECTION_HEAD.match(line)
            if h and follows(prev, int(h.group(1)), h.group(2)):
                prev = (int(h.group(1)), h.group(2))
                records.append(
                    {
                        "section": h.group(1) + h.group(2),
                        "chapter": chapter,
                        "text": h.group(3) or "",
                    }
                )
                in_chapter_heading = False
            elif records and not in_chapter_heading and not _SUBHEADING.match(line):
                records[-1]["text"] += "\n" + line
        if ended:
            break
    return [{**r, "text": r["text"].strip()} for r in records]


def follows(prev: tuple[int, str] | None, base: int, suffix: str) -> bool:
    """A heading counts only if it is the next section number, so list items don't start one."""
    if prev is None:
        return base == 1 and not suffix
    pbase, psuffix = prev
    return (base == pbase + 1 and not suffix) or (base == pbase and suffix > psuffix)


_CRPC_HEAD = re.compile(
    r"^(?:\d+\[)?(\d+)(-?[A-Z]{0,3})\.\s+([A-Z].{0,240}?)\.\s*[—–-](.*)$", re.DOTALL
)  # "154. Information in cognizable cases.—(1) ..."; the title may wrap onto a second line
_CRPC_END = re.compile(r"^THE FIRST SCHEDULE")
_FOOTNOTE_RULE_MIN = (
    20  # a blank line of this many spaces separates body from footnotes
)
_AMENDMENT_MARK = re.compile(r"\d+\[")


def crpc_sections(pages: list[str]) -> list[dict]:
    """Sections of the Code of Criminal Procedure from the India Code PDF text.

    Skips the table of contents (its headings lack the ".—" before the text), the
    footnotes under each page's rule, State amendment blocks, and amendment markers
    ("1[" and "]"). Each record also carries the section's `title`.
    """
    lines: list[str] = []
    for page in pages:
        for line in page.splitlines():
            if not line.strip() and len(line) >= _FOOTNOTE_RULE_MIN:
                break  # footnotes follow
            if line.strip() and not line.strip().isdigit():
                lines.append(line.strip())
    records: list[dict] = []
    chapter, in_chapter_heading, skipping, vide_closed = "", False, False, False
    prev: tuple[int, str] | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if records and _CRPC_END.match(line):
            break
        head, used = _crpc_heading(lines, i)
        if head and _increases(prev, head) and (not skipping or vide_closed):
            prev = (head[0], head[1])
            records.append(
                {
                    "section": f"{head[0]}{head[1]}",
                    "chapter": chapter,
                    "title": head[2],
                    "text": head[3],
                }
            )
            skipping = in_chapter_heading = False
            i += used
            continue
        if line.startswith("STATE AMENDMENT"):  # also the plural
            skipping = True
        if skipping and not _SUBHEADING.match(line):
            vide_closed = line.endswith(
                "]"
            )  # a state block's last line closes its [Vide ..]
        m = _CHAPTER.match(line)
        if m:
            chapter, in_chapter_heading, skipping = f"Chapter {m.group(1)}", True, False
        elif (
            records
            and not skipping
            and not in_chapter_heading
            and not _SUBHEADING.match(line)
        ):
            records[-1]["text"] += "\n" + line
        i += 1
    return [
        {**r, "text": _AMENDMENT_MARK.sub("", r["text"]).replace("]", "").strip()}
        for r in records
    ]


def _crpc_heading(
    lines: list[str], i: int
) -> tuple[tuple[int, str, str, str] | None, int]:
    """The heading starting at line i as (base, suffix, title, first text), and lines used."""
    for used in (1, 2):
        m = _CRPC_HEAD.match(" ".join(lines[i : i + used]))
        if m:
            suffix = m.group(2).replace("-", "")  # "105-I" is section 105I
            return (
                int(m.group(1)),
                suffix,
                m.group(3).strip(),
                m.group(4).strip(),
            ), used
    return None, 0


def _increases(prev: tuple[int, str] | None, head: tuple[int, str, str, str]) -> bool:
    return (
        prev is None
        and (head[0], head[1]) == (1, "")
        or (prev is not None and (head[0], head[1]) > prev)
    )
