"""Recorded fixes to a source's section records, for defects found by checking it against others.

A patch set is `{"replacements": [...], "texts": [...], "insertions": [...]}`. A replacement
names a section and a `find` text that must occur once in the section's text; a text patch
fills in a section the source printed with no text; an insertion adds a whole section the
source lost, after the section named in `after`. Each patch carries a `reason`
(unused here) saying what the other source showed. A patch that no longer fits is an error:
the source changed or the patch was wrong.
"""

import re


def apply_record_patches(records: list[dict], patches: dict) -> list[dict]:
    out = [dict(r) for r in records]
    by_section = {r["section"]: r for r in out}
    for p in patches.get("replacements", []):
        rec = by_section.get(p["section"])
        if rec is None:
            raise ValueError(
                f"patch names section {p['section']}, which is not in the source"
            )
        # the source wraps lines mid-phrase, so any run of whitespace matches a space
        found = re.compile(r"\s+".join(map(re.escape, p["find"].split())))
        n = len(found.findall(rec["text"]))
        if n != 1:
            raise ValueError(
                f"section {p['section']}: patch text {p['find']!r} found {n} times, expected 1"
            )
        rec["text"] = found.sub(lambda _, new=p["replace"]: new, rec["text"])
    for p in patches.get("texts", []):
        rec = by_section.get(p["section"])
        if rec is None or rec["text"].strip():
            raise ValueError(
                f"section {p['section']}: text patch needs a section with no text"
            )
        rec["text"] = p["text"]
    for p in patches.get("insertions", []):
        if p["section"] in by_section:
            raise ValueError(
                f"section {p['section']} is in the source already; drop its insertion"
            )
        after = next((i for i, r in enumerate(out) if r["section"] == p["after"]), None)
        if after is None:
            raise ValueError(
                f"insertion of {p['section']} follows {p['after']}, which is not in the source"
            )
        rec = {k: p[k] for k in ("section", "chapter", "title", "text")}
        out.insert(after + 1, rec)
        by_section[p["section"]] = rec
    return out
