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
_ASSENT = "MINISTRY OF LAW AND JUSTICE"  # starts the assent block on page 1
_TRAILING_ACT_NOTE = re.compile(
    r"(?<=[.;:,])\d{1,3} of \d{4}\.$"
)  # "...enactments.10 of 1897.": a margin note run onto the line before it
_RUNNING_HEAD = re.compile(
    r"^(?:\d+|SEC\. \d+\]) THE GAZETTE OF INDIA"
)  # one line on top: "2 THE GAZETTE ..." (even pages), "SEC. 1] THE GAZETTE ..." (odd pages
# of the CPA and Labour Codes); the BNS prints put it last, as a footer
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
        if line.strip() == _ASSENT:
            skipping = True
            _pop_marginals(out)
            continue
        if (
            _DEVANAGARI.search(line)
            or "xxxGID" in line
            or line.startswith(("CG-DL-", "jftLV"))
            or "REGISTERED NO" in line
        ):
            continue
        out.append(line)
    return out


def _gazette_page_body(page: str) -> tuple[list[str], bool]:
    """The page's body lines, and whether the Act proper ended on this page."""
    lines = [l.rstrip() for l in _strip_cover(page.splitlines())]
    lines = [_TRAILING_ACT_NOTE.sub("", l) for l in lines]
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
    if end is not None:
        # A short last body line such as "the effect of repeal." looks like a side-heading.
        # A real run of side-headings is several lines, so a trailing run shorter than that
        # stays (the BNS's own run still goes, as before).
        while lines and _ACT_NOTE.match(lines[-1].strip()):
            lines.pop()
        trailing = lines[:]
        _pop_marginals(trailing)
        if len(lines) - len(trailing) >= _MIN_RUN:
            lines = trailing
    else:
        _pop_marginals(lines)  # page 1 of BNSS has no footer
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


def follows(prev: tuple[int, str] | None, base: int, suffix: str, gap: int = 1) -> bool:
    """A heading counts only if it is the next section number, so list items don't start one.

    `gap` > 1 lets a source that lost a section through: 334 may follow 332.
    """
    if prev is None:
        return base == 1 and not suffix
    pbase, psuffix = prev
    return (pbase < base <= pbase + gap and not suffix) or (
        base == pbase and suffix > psuffix
    )


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


_IEA_HEAD = re.compile(
    r"^(?:\d+\[)?(\d+)([A-Z]{0,2})\.\s+(\S.{0,240}?)\s*[–—―]{1,3}\s*(.*)$", re.DOTALL
)  # "1. Short title.  ––This Act ..."; a hyphen is not a dash, so "Interpretation-clause" is safe
_IEA_HEAD_NO_DASH = re.compile(
    r"^(?:\d+\[)?(\d+)([A-Z]{0,2})\.\s+([A-Z][^.]{0,200}\.)\s{2,}(\S.*)$", re.DOTALL
)  # section 86: the PDF leaves two spaces where the dash should be
_IEA_CHAPTER = re.compile(r"^CHAPTER\s+([IVXL]+)\s*[.–—]")
_IEA_PART = re.compile(r"^PART\s+[IVX]+\s*$")
_IEA_START = (
    "WHEREAS it is expedient"  # the preamble; the contents list ahead of it has no text
)
_IEA_END = re.compile(r"^THE SCHEDULE\.")


def iea_sections(pages: list[str]) -> list[dict]:
    """Sections of the Indian Evidence Act from the India Code PDF text, in order.

    Skips the contents list (everything before the preamble), page footnotes (under a line of
    spaces), page numbers, PART headings and amendment markers. A heading counts only if it
    is the next section number and has the "––" between title and text. Each record also
    carries the section's `title`.
    """
    lines: list[str] = []
    for page in pages:
        for line in page.splitlines():
            if not line.strip() and len(line) >= _FOOTNOTE_RULE_MIN:
                break  # footnotes follow
            if line.strip() and not line.strip().isdigit():
                lines.append(line.strip())
    start = next((i for i, l in enumerate(lines) if _IEA_START in l), None)
    if start is None:
        raise ValueError(f"no line has the preamble marker {_IEA_START!r}")
    records: list[dict] = []
    chapter, prev = "", None
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if _IEA_END.match(line):
            break
        head, used = _iea_heading(lines, i)
        if head and not follows(prev, int(head[0]), head[1]):
            # a footnote marker can be glued to the number: "1145." is 145
            head = next(
                (
                    (head[0][k:], *head[1:])
                    for k in (1, 2)
                    if len(head[0]) > k and follows(prev, int(head[0][k:]), head[1])
                ),
                None,
            )
        if head and follows(prev, int(head[0]), head[1]):
            prev = (int(head[0]), head[1])
            records.append(
                {
                    "section": head[0] + head[1],
                    "chapter": chapter,
                    "title": head[2],
                    "text": head[3],
                }
            )
            i += used
            continue
        m = _IEA_CHAPTER.match(line)
        if m:
            chapter = f"Chapter {m.group(1)}"
        elif _IEA_PART.match(line):
            # "PART II" is followed by a subtitle line, then the CHAPTER line
            i += 1 if _IEA_CHAPTER.match(lines[i + 1]) else 2
            continue
        elif records:
            records[-1]["text"] += "\n" + line
        i += 1
    return [
        {
            **r,
            "title": _tidy_iea(r["title"]),
            "text": _tidy_iea(r["text"]),
        }
        for r in records
    ]


def _iea_heading(
    lines: list[str], i: int
) -> tuple[tuple[str, str, str, str] | None, int]:
    for used in (1, 2):
        m = _IEA_HEAD.match(" ".join(lines[i : i + used]))
        if m:
            return (m.group(1), m.group(2), m.group(3), m.group(4)), used
    m = _IEA_HEAD_NO_DASH.match(lines[i])  # raw line: its two spaces are the only cue
    if m:
        return (m.group(1), m.group(2), m.group(3), m.group(4)), 1
    return None, 0


def _tidy_iea(text: str) -> str:
    """Drop amendment markers ("2[" ... "]") but keep the Act's own square brackets."""
    out: list[str] = []
    stack: list[bool] = []  # True for an amendment marker's bracket
    pos = 0
    for m in re.finditer(r"(\d+)?\[|\]", text):
        out.append(text[pos : m.start()])
        pos = m.end()
        if m.group(0) == "]":
            if not stack:
                continue  # closes a marker opened ahead of the section heading
            if not stack.pop():
                out.append("]")
        elif m.group(1):
            stack.append(True)
        else:
            stack.append(False)
            out.append("[")
    out.append(text[pos:])
    return re.sub(r"[ \t]+", " ", "".join(out)).strip()


# --- Indian Penal Code, from Indian Kanoon (unofficial; no current official copy exists) ---

_KANOON_CHARS = str.maketrans(
    {"□": "", "−": "", "€": "—", "‚": "“", "ƒ": "”", "„": "’"}
)
# a hyphenated word broken across a line (□ or −), a dash (€), quotation marks (‚ ƒ), an
# apostrophe („). "†begging„" is a quoted word; the PDF has † for the opening mark.
_ENUMERATOR = re.compile(
    r"(?<![A-Za-z0-9])(\((?:\d+|[a-z]{1,4}|[A-Z])\))(?=[A-Za-z“‘])"
)  # "(1)any" -> "(1) any"; not "2(a) of"
_GLUED_LABEL = re.compile(
    r"(?<=[.;:])(?=(?:Illustrations?|Explanation|Exception|Provided)\b)|(?<=[a-z,])(?=Illustrations?(?=[A-Z(]))"
)  # "both.Illustrations", "bothIllustrationA"
_LABEL_THEN_ITEM = re.compile(
    r"\b(Illustrations?)(?=[A-Z(])"
)  # "Illustrations(a)A", "IllustrationA,"
_KANOON_FURNITURE = re.compile(r"^(?:Indian Kanoon - |The Indian Penal Code, 1860$)")
_KANOON_PART = re.compile(r"^Part\s+\d+\s+[–—-]\s+\S")  # "Part 5 – Of Kidnapping, ..."
_KANOON_HEAD = re.compile(r"^(\d+)([A-Z]{0,3})\.\s+(\S.*)$")
_KANOON_CHAPTER = re.compile(r"^Chapter\s+(\d+|[IVXL]+)([A-Z]?)\s*$")
_ROMAN = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


# Words the Kanoon text layer splits at a line end, with a space or a hyphen: every case in the
# PDF, checked against the other IPC copies. "imprison-ment" is not a compound word.
_KANOON_SPLIT_WORDS = (
    ("de", "scription"), ("sen", "tenced"), ("instiga", "tion"), ("commis", "sion"),
    ("represen", "tation"), ("fabri", "cates"), ("inves", "tigation"), ("infor", "mation"),
    ("homi", "cide"), ("impris", "onment"), ("informa", "tion"), ("mer", "chant"),
    ("im", "prisonment"), ("reli", "gious"), ("imprison", "ment"), ("sec", "tion"),
)  # fmt: skip
_KANOON_SPLIT = re.compile(
    r"\b(?:" + "|".join(f"{a}[\\s-]+{b}" for a, b in _KANOON_SPLIT_WORDS) + r")\b"
)
_KANOON_NOTE_DIGIT = re.compile(
    r"(?<![\w.(\[])\d{1,2}(?=[A-Za-z]{2,}\b)(?!(?:st|nd|rd|th)\b)"
)  # a footnote marker stuck to the next word: "1Indian coin"
_KANOON_RUN_ON = re.compile(
    r"\bor(?=(?:with|if|who|where|Consent|Secondly|Thirdly|Fourthly|Fifthly|Sixthly)\b)|\bof(?=Indian\b)"
)  # "orwith", "orSecondly", "ofIndian": the space after "or"/"of" went missing


def repair_kanoon(text: str) -> str:
    """Undo the damage the Indian Kanoon PDF's text layer does to characters and spacing."""
    text = re.sub(r"†(\w+)„", r"“\1”", text).translate(_KANOON_CHARS)
    text = _KANOON_SPLIT.sub(lambda m: re.sub(r"[\s-]+", "", m.group(0)), text)
    text = _KANOON_RUN_ON.sub(lambda m: m.group(0) + " ", text)
    text = _KANOON_NOTE_DIGIT.sub("", text)
    text = _GLUED_LABEL.sub(" ", text)
    text = _LABEL_THEN_ITEM.sub(r"\1 ", text)
    text = _ENUMERATOR.sub(r"\1 ", text)
    return re.sub(r"\)\s{2,}", ") ", text)


def _roman(n: int) -> str:
    out = ""
    for value, numeral in _ROMAN:
        while n >= value:
            out, n = out + numeral, n - value
    return out


def _kanoon_chapter(number: str, suffix: str) -> str:
    return f"Chapter {_roman(int(number)) if number.isdigit() else number}{suffix}"


def kanoon_ipc_sections(
    pages: list[str], after: tuple[int, str] | None = None
) -> list[dict]:
    """Sections of the Indian Penal Code from the Indian Kanoon PDF text, in order.

    A heading is a line "N. Title" whose N is the next section number (`after` names the
    section before the first one, for excerpts). A title that wraps ends on a later line with
    a dash; repealed sections are single "[Title.] Rep. by ..." lines; a few headings (376AB)
    carry no dash at all. Page furniture and chapter titles are dropped; characters are
    repaired by `repair_kanoon`. Each record also carries the section's `title`.
    """
    lines = [
        l.strip()
        for page in pages
        for l in repair_kanoon(page).splitlines()
        if l.strip() and not _KANOON_FURNITURE.match(l.strip())
    ]
    records: list[dict] = []
    chapter, in_chapter_heading, prev = "", False, after
    repeated, dropping = "", False
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _KANOON_CHAPTER.match(line)
        h = _KANOON_HEAD.match(line)
        if m:
            chapter, in_chapter_heading = _kanoon_chapter(*m.groups()), True
            i += 1
        elif _KANOON_PART.match(line):
            i += 1  # a sub-division heading of the chapter, not statute text
        elif h and prev and line == repeated:
            dropping = (
                True  # Kanoon prints some headings twice, with the body each time
            )
            i += 1
        elif h and follows(prev, int(h.group(1)), h.group(2), gap=2):
            prev, dropping = (int(h.group(1)), h.group(2)), False
            repeated = line
            title, text, used = _kanoon_heading(lines, i, h.group(3))
            records.append(
                {
                    "section": h.group(1) + h.group(2),
                    "chapter": chapter,
                    "title": title,
                    "text": text,
                }
            )
            in_chapter_heading = False
            i += used
        else:
            if records and not in_chapter_heading and not dropping:
                records[-1]["text"] += "\n" + line
            i += 1
    if not records:
        raise ValueError("no sections found in the Indian Kanoon text")
    return [{**r, "text": _drop_note(r["text"]).strip()} for r in records]


def _drop_note(text: str) -> str:
    """Cut the case-law note Kanoon appends to a few sections: a bracket holding a web link.

    Brackets that close before the link are the Act's own amendments and stay.
    """
    link = text.find("https:")
    if link < 0:
        return text
    depth, opened = 0, []
    for pos, ch in enumerate(text[:link]):
        if ch == "[":
            depth += 1
            if depth == 1:
                opened.append(pos)
        elif ch == "]":
            depth = max(0, depth - 1)
    return text[: opened[-1]] if depth and opened else text


def _kanoon_heading(lines: list[str], i: int, first: str) -> tuple[str, str, int]:
    """The heading at line i as (title, text on its own lines, lines used)."""
    first = first.removeprefix(
        ". "
    )  # "61. . [Sentence of forfeiture of property.] Rep. ..."
    if first.startswith("["):
        return "", first, 1  # repealed or omitted: the whole entry is the text
    title = first
    if not first.endswith("—"):
        for k in (1, 2):
            if i + k >= len(lines) or lines[i + k - 1].endswith("—"):
                break
            tail = lines[i + k]
            if not (tail[:1].islower() or re.match(r"[IVXL]+\b", tail)):
                break
            if tail.endswith("—"):
                title = " ".join([first, *lines[i + 1 : i + k + 1]])
                return title.rstrip("— ").strip(), "", k + 1
    return title.rstrip("— ").strip(), "", 1


_TPA_FURNITURE = re.compile(r"International\s+Insolvency\s+Institute")
_TPA_HEAD = re.compile(r"^(?:\d+\[)?(\d+)([A-Z]?)\.\s+\S")
_TPA_FOOTNOTE = re.compile(
    r"^\d{1,2} (?:Subs?\.|Ins\.|Added|Omitted|Rep\.|The words?\b|As to\b)"
)
_TPA_FOOTNOTE_END = (
    ".",
    "¨",
    ")",
    '"',
)  # a footnote line not ending so wraps onto the next
_TPA_SUBHEADING_MAX = 60
_TPA_BODY_STARTS = ("Illustration", "Provided", "Explanation", "Exception", "Nothing")
_TPA_PUNCT_END = (".", ";", ":", ",", "—", "-")
_DELETED = re.compile(r"\s*\d*\[\*+\]")  # "5[***]": words the amendments deleted


def _drop_tpa_footnotes(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _TPA_FOOTNOTE.match(lines[i]):
            while not lines[i].endswith(_TPA_FOOTNOTE_END) and i + 1 < len(lines):
                i += 1
        else:
            out.append(lines[i])
        i += 1
    return out


def _is_tpa_subheading(prev: str | None, line: str, nxt: str | None) -> bool:
    return bool(
        prev
        and nxt
        and prev.endswith(_TPA_PUNCT_END)
        and len(line) <= _TPA_SUBHEADING_MAX
        and line[0].isupper()
        and not line.endswith(_TPA_PUNCT_END)
        and not line.startswith(_TPA_BODY_STARTS)
        and (nxt[0].isupper() or nxt[0] == "(")
    )


def tpa_lease_sections(pages: list[str]) -> list[dict]:
    """Sections 105-117 (Chapter V, leases) of the Transfer of Property Act, in order.

    Source is the International Insolvency Institute's print of the Act: an unofficial text
    with its amendment footnotes dropped into the middle of sections, a footnote number glued
    onto some section numbers ("2107." is section 107), and sub-headings run into the body.
    The footnotes, sub-headings and amendment markers are removed.
    """
    lines = [
        l.strip()
        for page in pages
        for l in page.splitlines()
        if l.strip() and not _TPA_FURNITURE.search(l)
    ]
    start = next(i for i, l in enumerate(lines) if re.fullmatch(r"CHAPTER V", l))
    end = next(
        (
            i
            for i, l in enumerate(lines)
            if i > start and re.fullmatch(r"CHAPTER VI", l)
        ),
        len(lines),
    )
    lines = _drop_tpa_footnotes(lines[start + 1 : end])
    lines = [l for l in lines if not re.fullmatch(r"OF LEASES.*", l)]
    records: list[dict] = []
    bodies: list[list[str]] = []
    prev: tuple[int, str] = (104, "")  # the chapter's first section is 105
    for line in lines:
        m = _TPA_HEAD.match(line)
        if m:
            digits, suffix = m.group(1), m.group(2)
            # drop leading digits until the number fits: "2107." is footnote 2 and section 107
            number = next(
                (
                    int(digits[k:])
                    for k in range(len(digits))
                    if follows(prev, int(digits[k:]), suffix, gap=3)
                ),
                None,
            )
            if number is not None:
                prev = (number, suffix)
                records.append({"section": f"{number}{suffix}", "chapter": "Chapter V"})
                bodies.append([])
                continue
        if bodies:
            bodies[-1].append(line)
    for rec, body in zip(records, bodies):
        kept = [
            l
            for i, l in enumerate(body)
            if not _is_tpa_subheading(
                body[i - 1] if i else None,
                l,
                body[i + 1] if i + 1 < len(body) else None,
            )
        ]
        text = _DELETED.sub("", "\n".join(kept))
        rec["text"] = _AMENDMENT_MARK.sub("", text).replace("]", "").strip()
    return records
