"""Check the Constitution Chunks against the official Constitution of India PDF.

Limits: it checks that every word of our text appears in order in the official Article (so stale
or wrong text is caught) and that no official Article is missing. It does not detect text that
is merely truncated. Headings it cannot locate in the PDF body are listed for a manual check.

The PDF is the Ministry of Law and Justice text ("as on May 2022") hosted on the India Code
CDN. Prints Articles missing from the Corpus, Articles missing from the PDF, and Articles whose
text differs from the PDF. Usage:

    python scripts/verify_constitution.py OFFICIAL.pdf [--raw PATH] [--patches PATH]
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from legallens.ingestion import parse_constitution
from legallens.ingestion.sources import fetch_constitution, load_patches

BACKEND_DIR = Path(__file__).resolve().parents[1]
_NOT_FOOTNOTE = r"(?!Ins\.|Subs\.|Added|Rep\.|Renumbered|The (?:words?|brackets|figures?)|Clauses?|Sub-clause)"
HEADING = r"^\s*(?:\d*\[)?{num}\.\s+" + _NOT_FOOTNOTE + r"(?:\d*\[)?[A-Z\[]"
ANY_HEADING = re.compile(
    r"^\s*(?:\d*\[)?(\d+[A-Z]{0,3})\.\s+" + _NOT_FOOTNOTE + r"(?:\d*\[)?[A-Z\[]"
)


def pdf_lines(path: Path) -> list[str]:
    return "\n".join(p.extract_text() for p in PdfReader(path).pages).splitlines()


def toc_numbers(lines: list[str]) -> tuple[list[str], int]:
    """Article numbers in the table of contents, and the line where the body starts."""
    body = next(
        i
        for i, l in enumerate(lines)
        if re.match(r"\s*1\. Name and territory", l) and i > 1000
    )
    nums: list[str] = []
    for l in lines[:body]:
        m = ANY_HEADING.match(l)
        if m and m.group(1) not in nums:
            nums.append(m.group(1))
    return nums, body


def clean_pdf_text(chunk: list[str]) -> str:
    """Drop page headers and footnote blocks, strip amendment markers."""
    out, skipping = [], False
    i = 0
    while i < len(chunk):
        line = chunk[i]
        if re.match(r"^_{10,}", line):
            skipping = True
        elif re.match(r"^\s*THE CONSTITUTION OF\s+INDIA", line):
            skipping = False
            i += 3  # header, Part line, page number
            continue
        if not skipping:
            out.append(line)
        i += 1
    text = "\n".join(out)
    text = re.sub(r"\d+\[", "", text).replace("]", "")
    return text


def article_spans(lines: list[str], nums: list[str], body: int) -> dict[str, str]:
    starts: dict[str, int] = {}
    pos = body
    for n in nums:
        pat = re.compile(HEADING.format(num=n))
        for i in range(
            pos, min(pos + 600, len(lines))
        ):  # a heading far away is a mis-sync
            if pat.match(lines[i]):
                starts[n] = i
                pos = i + 1
                break
    ordered = list(starts)
    spans = {}
    for k, n in enumerate(ordered):
        end = starts[ordered[k + 1]] if k + 1 < len(ordered) else len(lines)
        spans[n] = clean_pdf_text(lines[starts[n] : end])
    return spans


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def recall(ours: str, official: str) -> float:
    a, b = words(ours), words(official)
    if not a:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(m.size for m in sm.get_matching_blocks()) / len(a)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument(
        "--raw",
        type=Path,
        default=BACKEND_DIR / "data" / "raw" / "constitution_of_india.json",
    )
    ap.add_argument(
        "--patches",
        type=Path,
        default=BACKEND_DIR / "sources" / "constitution_patches.json",
    )
    ap.add_argument("--threshold", type=float, default=0.97)
    args = ap.parse_args()

    patches = load_patches(args.patches)
    raw = fetch_constitution(args.raw)
    ours = {p.number: p for p in parse_constitution(raw, patches)}
    lines = pdf_lines(args.pdf)
    end = next(
        i
        for i, l in enumerate(lines)
        if re.match(r"^\d*\[?FIRST SCHEDULE\s*$", l) and i > 5000
    )
    lines = lines[:end]
    nums, body = toc_numbers(lines)
    # The TOC parse misses a few headings the Corpus has; merge so span boundaries are right.
    nums = sorted({*nums, *ours}, key=lambda n: (int(re.match(r"\d+", n).group()), n))
    spans = article_spans(lines, nums, body)

    notes = json.loads(args.patches.read_text(encoding="utf-8"))
    excluded = set(notes.get("excluded_from_corpus", []))
    accepted = set(notes.get("accepted_differences", {}))
    missing = [n for n in nums if n not in ours]
    unexpected_missing = [n for n in missing if n not in excluded]
    extra = [n for n in ours if n not in nums]
    print(f"official Articles: {len(nums)}  ours: {len(ours)}")
    print("in official, missing from Corpus:", missing)
    print("in Corpus, not in official TOC:", extra)
    bad = []
    unlocated = [n for n in ours if n not in spans]
    print(
        "Articles whose heading was not found in the PDF body (check by hand):",
        unlocated,
    )
    for n, p in ours.items():
        if n in spans:
            r = recall(p.text, spans[n])
            if r < args.threshold:
                bad.append((n, r))
    print(f"{len(bad)} Articles below {args.threshold:.2f} word recall:")
    for n, r in sorted(bad, key=lambda x: x[1]):
        print(
            f"  {n}: {r:.3f}"
            + ("  (accepted, see patches file)" if n in accepted else "")
        )
    unexpected_bad = [n for n, _ in bad if n not in accepted]
    return 1 if unexpected_missing or unexpected_bad else 0


if __name__ == "__main__":
    sys.exit(main())
