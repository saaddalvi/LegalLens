"""Check the criminal-law Chunks (all six Acts) against independent evidence.

The Acts are built from one official PDF each, so there is no second copy of the same text to
diff against for CrPC and IEA; what this script can do, per Act:

* count and number checks: the Chunk count is the Act's published total and the base numbers
  run 1..N without a gap;
* index check (BNS, BNSS, BSA, CrPC, IEA): the section numbers match an index that is not our
  parse of the body: the NCRB compilation's own index for BNS, BNSS and BSA, the PDF's table
  of contents for CrPC and IEA;
* text check (BNS, BNSS, BSA): the NCRB compilation prints the whole Act again, extracted
  separately from the Gazette PDF; every word of our Chunk must appear in order in its
  section there. It catches lost or garbled text and leftover page furniture, but not text
  that is truncated in both;
* mapping check (BNSS-CrPC, BSA-IEA, BNS-IPC): every new-Act section is a mapping target or a
  "New Section", every old-Act section a mapping source or "Deleted" (or listed in the sources
  file as absent from the table), and every mapping names a real section;
* IPC text check: the only IPC with every section is the unofficial Indian Kanoon print, so
  each section is compared word for word with two older copies (India Code, pre-2013, and an
  unattributed one of about 2016). A section whose words all appear in order in the India Code
  copy is "official"; one that matches only the 2016 copy, or neither (sections amended or
  added since), is listed in the sources file as unverified, and the script fails if that list
  changes.

It does not replace the last ticket-08 checkbox: comparison against India Code itself.
Usage:

    python scripts/verify_criminal_codes.py [--raw-dir DIR] [--sources PATH] [--threshold 0.97]
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

from legallens.ingestion import apply_mappings, parse_criminal_code
from legallens.ingestion.criminal_codes import CRIMINAL_ACTS
from legallens.ingestion.mapping_tables import (
    parse_bns_table,
    parse_bsa_table,
    parse_corresponding_table,
    section_key,
)
from legallens.ingestion.pdf_text import follows
from legallens.ingestion.sources import load_criminal_codes, read_pinned_pdf_pages

BACKEND_DIR = Path(__file__).resolve().parents[1]
_NUMBERED = re.compile(r"^(\d+)(-?[A-Z]{0,3})\.(?!\d)\s*\S")  # "105-I.", "144A.Power"
_NCRB_OLD_TITLE = {
    "bns": "Indian Penal Code, 1860",
    "bnss": "Code of Criminal Procedure, 1973",
    "bsa": "INDIAN EVIDENCE ACT, 1872",
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def recall(ours: str, official: str) -> float:
    a, b = _words(ours), _words(official)
    if not a:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(m.size for m in sm.get_matching_blocks()) / len(a)


def index_numbers(lines: list[str]) -> list[str]:
    """Section numbers listed in an index, in order, each once."""
    seen: list[str] = []
    for line in lines:
        m = _NUMBERED.match(line.strip())
        if m:
            n = m.group(1) + m.group(2).replace("-", "")
            if n not in seen:
                seen.append(n)
    return seen


def official_spans(lines: list[str]) -> dict[str, str]:
    """Split a re-printed Act into sections: headings must follow one another in order."""
    spans: dict[str, list[str]] = {}
    prev: tuple[int, str] | None = None
    current: str | None = None
    for line in lines:
        m = re.match(r"^(\d+)([A-Z]{0,3})\.(?!\d)", line.strip())
        if m and follows(prev, int(m.group(1)), m.group(2)):
            prev = (int(m.group(1)), m.group(2))
            current = m.group(1) + m.group(2)
            spans[current] = []
        if current:
            spans[current].append(line)
    return {n: "\n".join(ls) for n, ls in spans.items()}


def ncrb_index_and_text(raw_dir: Path, key: str) -> tuple[list[str], dict[str, str]]:
    pages = read_pinned_pdf_pages(raw_dir, f"ncrb_{key}")
    table_start = next(
        i
        for i, p in enumerate(pages)
        if any(l.strip() == _NCRB_OLD_TITLE[key] for l in p.splitlines())
    )
    act_start = next(
        i
        for i in range(table_start + 1, len(pages))
        if "Chapters and Sections" in pages[i]
    )
    index_lines = [l for p in pages[:table_start] for l in p.splitlines()]
    act_lines = [l for p in pages[act_start:] for l in p.splitlines()]
    return index_numbers(index_lines), official_spans(act_lines)


def crpc_toc(raw_dir: Path) -> list[str]:
    lines = [l for p in read_pinned_pdf_pages(raw_dir, "crpc") for l in p.splitlines()]
    body = next(
        i for i, l in enumerate(lines) if re.match(r"^1\.\s+Short title.*\.\s*[—–-]", l)
    )
    return index_numbers(lines[:body])


def iea_toc(raw_dir: Path) -> list[str]:
    lines = [l for p in read_pinned_pdf_pages(raw_dir, "iea") for l in p.splitlines()]
    body = next(i for i, l in enumerate(lines) if "WHEREAS it is expedient" in l)
    return index_numbers(lines[:body])


_IPC_2016_HEAD = re.compile(r"^Section (\d+)([A-Z]{0,3})\.")
_IPC_2012_HEAD = re.compile(
    r"^(\d+)([A-Z]{0,3})\.\s*$"
)  # the margin number above each heading
_REFERENCE_END = re.compile(
    r"CLASSIFICATION OF OFFENCE|\n\s*1\*?\. (?:Subs|Ins|Rep|Omitted|The words|Added)"
)  # a section's own text ends where its classification or first footnote starts


def ipc_reference_spans(raw_dir: Path, key: str) -> dict[str, str]:
    """Section texts of an older IPC copy. Headings must follow in order, allowing a gap
    (the copies leave out repealed sections). The India Code copy prints each section's number
    alone in the margin above its heading; footnotes also start "2. Subs." so only that counts."""
    head = _IPC_2016_HEAD if key == "ipc_unknown_2016" else _IPC_2012_HEAD
    spans: dict[str, list[str]] = {}
    prev: tuple[int, str] | None = None
    current: str | None = None
    for page in read_pinned_pdf_pages(raw_dir, key):
        for line in page.splitlines():
            m = head.match(line.strip())
            if m and follows(prev, int(m.group(1)), m.group(2), gap=8):
                prev, current = (int(m.group(1)), m.group(2)), m.group(1) + m.group(2)
                spans.setdefault(current, [])
            if current:
                spans[current].append(line)
    return {n: _REFERENCE_END.split("\n".join(ls))[0] for n, ls in spans.items()}


def ipc_text_check(args, provisions, notes, report) -> None:
    spans = {
        k: ipc_reference_spans(args.raw_dir, k)
        for k in ("ipc_ic_2012", "ipc_unknown_2016")
    }
    ours = {p.number for p in provisions}
    seen_in_copies = set().union(*(set(sp) for sp in spans.values()))
    report(
        seen_in_copies <= ours,
        f"IPC: sections the older copies print that we lack: {sorted(seen_in_copies - ours, key=section_key)}"
        f" (the Kanoon print adds {len(ours - seen_in_copies)} they lack)",
    )
    official: list[str] = []
    only_2016: list[str] = []
    neither: list[str] = []
    for p in provisions:
        r = {
            k: recall(p.text, sp[p.number]) if p.number in sp else None
            for k, sp in spans.items()
        }
        if (r["ipc_ic_2012"] or 0) >= args.threshold:
            official.append(p.number)
        elif (r["ipc_unknown_2016"] or 0) >= args.threshold:
            only_2016.append(p.number)
        else:
            neither.append(p.number)
    recorded = notes["ipc_verification"]
    report(
        True,
        f"IPC: {len(official)} of {len(provisions)} Chunks match the India Code copy of before"
        f" 2013, {len(only_2016)} only the 2016 copy, {len(neither)} neither",
    )
    for name, found in (("only_2016_copy", only_2016), ("neither_copy", neither)):
        want = list(recorded[name])
        report(
            found == want,
            f"IPC sections matching {name.replace('_', ' ')}: {len(found)} as recorded;"
            f" new {sorted(set(found) - set(want), key=section_key)},"
            f" gone {sorted(set(want) - set(found), key=section_key)}",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--raw-dir", type=Path, default=BACKEND_DIR / "data" / "raw")
    ap.add_argument(
        "--sources", type=Path, default=BACKEND_DIR / "sources" / "criminal_codes.json"
    )
    ap.add_argument("--threshold", type=float, default=0.97)
    args = ap.parse_args()

    notes = json.loads(args.sources.read_text(encoding="utf-8"))
    accepted: dict[str, dict[str, str]] = notes.get("accepted_differences", {})
    records, mappings = load_criminal_codes(args.raw_dir)
    problems = 0

    def report(ok: bool, message: str) -> None:
        nonlocal problems
        print(("ok    " if ok else "FAIL  ") + message)
        problems += not ok

    parsed = {k: parse_criminal_code(k, rs) for k, rs in records.items()}
    indexes = {"crpc": crpc_toc(args.raw_dir), "iea": iea_toc(args.raw_dir)}
    official: dict[str, dict[str, str]] = {}
    for k in ("bns", "bnss", "bsa"):
        indexes[k], official[k] = ncrb_index_and_text(args.raw_dir, k)

    for key, provisions in parsed.items():
        act = CRIMINAL_ACTS[key]
        numbers = [p.number for p in provisions]
        lo, hi = act.expected_count
        report(
            lo <= len(numbers) <= hi,
            f"{act.name}: {len(numbers)} Chunks (expected {lo}-{hi})",
        )
        bases = {section_key(n)[0] for n in numbers}
        gaps = [n for n in range(1, max(bases) + 1) if n not in bases]
        report(
            not gaps, f"{act.name}: section numbers 1..{max(bases)} with gaps {gaps}"
        )
        if key in indexes:
            ours, theirs = set(numbers), set(indexes[key])
            report(
                ours == theirs,
                f"{act.name}: matches its independent index ({len(theirs)} sections);"
                f" only ours {sorted(ours - theirs, key=section_key)},"
                f" only index {sorted(theirs - ours, key=section_key)}",
            )
        if key in official:
            ok_accepted = accepted.get(key, {})
            low = [
                (p.number, recall(p.text, official[key].get(p.number, "")))
                for p in provisions
            ]
            low = [(n, r) for n, r in low if r < args.threshold]
            unexpected = [(n, r) for n, r in low if n not in ok_accepted]
            report(
                not unexpected,
                f"{act.name}: {len(low)} Chunks below {args.threshold:.2f} word recall against"
                f" the NCRB text ({len(low) - len(unexpected)} accepted, see sources file)",
            )
            for n, r in sorted(unexpected, key=lambda x: x[1]):
                print(f"        {n}: {r:.3f}")

    all_provisions = [p for ps in parsed.values() for p in ps]
    tables = {
        ("bnss", "crpc"): parse_corresponding_table(
            read_pinned_pdf_pages(args.raw_dir, "ncrb_bnss"),
            new_act=CRIMINAL_ACTS["bnss"].name,
            old_act=CRIMINAL_ACTS["crpc"].name,
            old_title=_NCRB_OLD_TITLE["bnss"],
        ),
        ("bns", "ipc"): parse_bns_table(
            read_pinned_pdf_pages(args.raw_dir, "ncrb_bns"),
            new_act=CRIMINAL_ACTS["bns"].name,
            old_act=CRIMINAL_ACTS["ipc"].name,
        ),
        ("bsa", "iea"): parse_bsa_table(
            read_pinned_pdf_pages(args.raw_dir, "ncrb_bsa"),
            new_act=CRIMINAL_ACTS["bsa"].name,
            old_act=CRIMINAL_ACTS["iea"].name,
        ),
    }
    for (new_key, old_key), table in tables.items():
        new_name, old_name = CRIMINAL_ACTS[new_key].name, CRIMINAL_ACTS[old_key].name
        new_numbers = {p.number for p in parsed[new_key]}
        old_numbers = {p.number for p in parsed[old_key]}
        targets = {m["new_number"] for m in table.mappings} | set(table.new)
        sources = {m["old_number"] for m in table.mappings} | set(table.deleted)
        label = f"{new_key.upper()}-{old_key.upper()}"
        report(
            not new_numbers - targets,
            f"{label}: {new_key.upper()} sections without a mapping row:"
            f" {sorted(new_numbers - targets, key=section_key)}",
        )
        absent = set(notes.get("not_in_mapping_table", {}).get(old_key, {}))
        report(
            not old_numbers - sources - absent,
            f"{label}: {old_key.upper()} sections without a mapping row:"
            f" {sorted(old_numbers - sources - absent, key=section_key)}"
            f" ({len(absent)} accepted, see sources file)",
        )
        report(
            not absent & sources,
            f"{label}: accepted sections that the table does list after all:"
            f" {sorted(absent & sources, key=section_key)}",
        )
        report(
            targets <= new_numbers and sources <= old_numbers,
            f"{label}: mapping rows naming sections not in the Acts:"
            f" {sorted(targets - new_numbers, key=section_key)}"
            f" {sorted(sources - old_numbers, key=section_key)}",
        )
        mine = [
            m for m in mappings if (m["new_act"], m["old_act"]) == (new_name, old_name)
        ]
        try:
            apply_mappings(all_provisions, mine)
            report(
                True,
                f"{len(mine)} {label} mappings apply cleanly"
                f" ({len(table.deleted)} {old_key.upper()} sections deleted,"
                f" {len(table.new)} {new_key.upper()} sections new)",
            )
        except ValueError as e:
            report(False, str(e))
    ipc_text_check(args, parsed["ipc"], notes, report)
    print("\nNot checked: comparison with India Code (ticket 08, last checkbox).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
