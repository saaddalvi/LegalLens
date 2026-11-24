"""Check the Contract Act, consumer, tenancy and labour Chunks (tickets 09 and contract-explainer 03)
against independent evidence.

Per Act:

* Indian Contract Act: the sections are exactly the Act's live ones (1-75 with 19A, 124-238 with
  178A: Chapter VII, sections 76-123, and Chapter XI, 239-266, are repealed and have no text);
  they equal, in order, the non-repealed entries of the print's own "Arrangement of Sections"
  (a separate list from the body) with the same titles; the chapters are Preliminary and
  Chapters I-VI, VIII, IX and X; sections 27 and 74 hold their operative words;

* count check: the Chunk count is the Act's published section total (CPA 107, Model Tenancy Act 47, Code on Wages
  69, Industrial Relations Code 104, Code on Social Security 164, OSH Code 143), the numbers
  run 1..N without a gap, and the chapter count is the published one (8, 8, 9, 14, 14, 14);
* index check (Code on Social Security only): the section numbers equal the "Arrangement of
  Sections" of the India Code copy as on 21 November 2025, which is a separate document;
* Transfer of Property Act: Chapter V is sections 105-117 plus the inserted 114A (14), and
  every Chunk's chapter is Chapter V;
* text hygiene: no Chunk keeps Gazette furniture or footnotes, and the Transfer of Property
  Act's print leaves no amendment marker (`1[`, `[***]`).

NOT done for the Indian Contract Act: comparison with India Code's own text. India Code answers
the download with a 504, so the text is the Legislative Department print as mirrored by Drishti
Judiciary (a third party), not a file taken from the Department or India Code. Count, numbering
and titles agree with the print's own contents list and the Act's published numbering; the body
text has not been diffed against an independent copy, and the print's own amendment footnotes
(which date its currency) are dropped, not checked.

NOT done: comparison with India Code's own text of the CPA, the other three Labour Codes and
the Transfer of Property Act (the Model Tenancy Act is not on India Code at all). India Code answers these downloads with 504s, so the last
checkbox of ticket 09 is only partly met: count and numbering agree with the published totals
above, the text has not been diffed against India Code.

Usage:

    python scripts/verify_everyday_acts.py [--raw-dir DIR]
"""

import argparse
import re
import sys
from pathlib import Path

from legallens.ingestion import EVERYDAY_ACTS, parse_everyday_act
from legallens.ingestion.sources import load_everyday_acts, read_everyday_pdf_pages

# Section and chapter totals as published (the Acts' own last section and last chapter).
PUBLISHED = {
    "cpa": (107, 8),
    "mta": (47, 8),
    "wages": (69, 9),
    "ir": (104, 14),
    "ss": (164, 14),
    "osh": (143, 14),
}
TPA_SECTIONS = [str(n) for n in range(105, 118)]
TPA_SECTIONS.insert(TPA_SECTIONS.index("115"), "114A")

FURNITURE = re.compile(
    r"GAZETTE OF INDIA|MINISTRY OF LAW|REGISTERED NO|CG-DL|jftLV|International Insolvency"
    r"|^\d+ (?:Subs|Ins)\."
)
AMENDMENT_MARKS = re.compile(r"\d\[|\*\*\*")  # the Transfer of Property Act print only


def india_code_index(raw_dir: Path) -> list[str]:
    """Section numbers of the India Code Social Security Code's table of contents."""
    pages = read_everyday_pdf_pages(raw_dir, "ss_ic")
    toc = "\n".join(pages[2:8])
    body = toc.split("ARRANGEMENT OF SECTIONS", 1)[1]
    numbers: list[int] = []
    for n in map(int, re.findall(r"^\s*(\d+)\.\s+\S", body, re.MULTILINE)):
        if numbers and n <= numbers[-1]:
            break  # the body of the Act has begun
        numbers.append(n)
    return [str(n) for n in numbers]


CONTRACT_SECTIONS = [str(n) for n in [*range(1, 76), *range(124, 239)]]
CONTRACT_SECTIONS.insert(CONTRACT_SECTIONS.index("20"), "19A")
CONTRACT_SECTIONS.insert(CONTRACT_SECTIONS.index("179"), "178A")
CONTRACT_CHAPTERS = [
    "Preliminary", "Chapter I", "Chapter II", "Chapter III", "Chapter IV", "Chapter V",
    "Chapter VI", "Chapter VIII", "Chapter IX", "Chapter X",
]  # fmt: skip
CONTRACT_PHRASES = {
    "27": "restrained from\nexercising a lawful profession, trade or business of any kind, is to that extent void",
    "74": "reasonable compensation not exceeding the amount so named",
}


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text).strip().lower()


def contract_act_index(raw_dir: Path) -> list[tuple[str, str]]:
    """(number, title) of the live sections in the print's "Arrangement of Sections"."""
    pages = read_everyday_pdf_pages(raw_dir, "contract")
    start = next(i for i, p in enumerate(pages) if "[25th April, 1872.]" in p)
    toc = "\n".join(pages[: start + 1]).split("[25th April, 1872.]")[0]
    entries: list[tuple[str, str]] = []
    lines = [l.strip() for l in toc.splitlines()]
    for i, line in enumerate(lines):
        m = re.match(r"^(\d+[A-Z]?)\.\s*(\S.*)$", line)
        if not m or "Repealed" in line or "Rep." in line:
            continue
        title = m.group(2)
        if not title.rstrip().endswith("."):  # a title wrapped onto the next line
            title += " " + lines[i + 1]
        entries.append((m.group(1), title))
    return entries


def check_contract_act(chunks, raw_dir: Path) -> list[str]:
    failures: list[str] = []
    name = "Indian Contract Act"
    numbers = [c.number for c in chunks]
    if numbers != CONTRACT_SECTIONS:
        missing = sorted(set(CONTRACT_SECTIONS) - set(numbers))
        extra = sorted(set(numbers) - set(CONTRACT_SECTIONS))
        failures.append(f"{name}: sections differ (missing {missing}, extra {extra})")
    chapters = list(dict.fromkeys(c.chapter for c in chunks))
    if chapters != CONTRACT_CHAPTERS:
        failures.append(f"{name}: chapters {chapters}, expected {CONTRACT_CHAPTERS}")
    index = contract_act_index(raw_dir)
    print(f"  print's contents list has {len(index)} live sections")
    if [n for n, _ in index] != numbers:
        failures.append(f"{name}: sections differ from the print's own contents list")
    for n, title in index:
        if (
            n in CONTRACT_PHRASES
            and _norm(title)[:20]
            != _norm(
                {
                    "27": "Agreement in restraint of trade",
                    "74": "Compensation for breach",
                }[n]
            )[:20]
        ):
            failures.append(f"{name} {n}: contents title {title!r}")
    by_number = {c.number: c for c in chunks}
    for n, phrase in CONTRACT_PHRASES.items():
        if phrase not in by_number[n].text:
            failures.append(f"{name} {n}: missing {phrase!r}")
    for c in chunks:
        if re.search(r"\d\[|\*\*|Rep\. by|Bare Act", c.text):
            failures.append(f"{name} {c.number}: stray marker in text")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = ap.parse_args()
    records = load_everyday_acts(args.raw_dir)
    failures: list[str] = []

    for key, act in EVERYDAY_ACTS.items():
        chunks = parse_everyday_act(key, records[key])
        numbers = [c.number for c in chunks]
        chapters = list(dict.fromkeys(c.chapter for c in chunks))
        print(f"{act.name}: {len(chunks)} Chunks, {len(chapters)} chapters")
        if key == "contract":
            failures += check_contract_act(chunks, args.raw_dir)
        elif key == "tpa":
            expected = TPA_SECTIONS
            if numbers != expected or chapters != ["Chapter V"]:
                failures.append(f"{act.name}: sections {numbers}, expected {expected}")
        else:
            total, n_chapters = PUBLISHED[key]
            if numbers != [str(n) for n in range(1, total + 1)]:
                failures.append(f"{act.name}: sections are not 1..{total}")
            if len(chapters) != n_chapters:
                failures.append(
                    f"{act.name}: {len(chapters)} chapters, published {n_chapters}"
                )
        for c in chunks:
            for line in c.text.splitlines():
                if FURNITURE.search(line) or (
                    key == "tpa" and AMENDMENT_MARKS.search(line)
                ):
                    failures.append(f"{act.name} {c.number}: stray text {line[:60]!r}")
        if key == "ss":
            index = india_code_index(args.raw_dir)
            print(f"  India Code index lists {len(index)} sections")
            if index != numbers:
                failures.append(
                    f"{act.name}: sections differ from the India Code index "
                    f"({len(index)} listed, {len(numbers)} parsed)"
                )

    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    print("OK" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
