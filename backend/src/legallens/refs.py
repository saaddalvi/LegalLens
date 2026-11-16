"""References to Provisions, as stored in `superseded_by` / `supersedes` and found in Queries."""

import re

# Aliases people use for each Act, longest first so "code of criminal procedure" beats "crpc".
ACT_ALIASES: dict[str, tuple[str, ...]] = {
    "Indian Penal Code": ("indian penal code", "i.p.c.", "ipc"),
    "Code of Criminal Procedure": ("code of criminal procedure", "cr.p.c.", "crpc"),
    "Indian Evidence Act": ("indian evidence act", "evidence act", "iea"),
    "Bharatiya Nyaya Sanhita": ("bharatiya nyaya sanhita", "bns"),
    "Bharatiya Nagarik Suraksha Sanhita": (
        "bharatiya nagarik suraksha sanhita",
        "bnss",
    ),
    "Bharatiya Sakshya Adhiniyam": ("bharatiya sakshya adhiniyam", "bsa"),
    "Consumer Protection Act": ("consumer protection act",),
    "Transfer of Property Act": ("transfer of property act", "tpa"),
    "Model Tenancy Act": ("model tenancy act", "mta"),
    "Code on Wages": ("code on wages",),
    "Industrial Relations Code": ("industrial relations code",),
    "Code on Social Security": ("code on social security",),
    "Occupational Safety, Health and Working Conditions Code": (
        "occupational safety, health and working conditions code",
        "osh code",
    ),
}

_ALIAS_TO_ACT = {
    alias: act for act, aliases in ACT_ALIASES.items() for alias in aliases
}
_ALIAS = "|".join(re.escape(a) for a in sorted(_ALIAS_TO_ACT, key=len, reverse=True))
_NUMBER = r"(\d+[a-z]{0,3})"
_SECTION = r"(?:sections?|sec\.?|s\.|धारा)"
# "IPC 302", "IPC section 302"  |  "section 302 of the IPC", "section 302 IPC"
_ACT_FIRST = re.compile(
    rf"(?<!\w)({_ALIAS})\s*{_SECTION}?\s*{_NUMBER}\b", re.IGNORECASE
)
_NUMBER_FIRST = (
    re.compile(  # needs "section"/"of" so "100 BNS 101" is not read as BNS 100
        rf"(?<!\w){_SECTION}\s*{_NUMBER}\s+(?:of\s+(?:the\s+)?)?({_ALIAS})(?!\w)",
        re.IGNORECASE,
    )
)


def format_ref(act: str, number: str) -> str:
    return f"{act} {number}"


def join_refs(refs: list[str]) -> str | None:
    return "; ".join(refs) or None


def split_refs(value: str | None) -> list[tuple[str, str]]:
    """Parse a stored reference string into (act, number) pairs."""
    if not value:
        return []
    return [tuple(r.rsplit(" ", 1)) for r in value.split("; ")]  # type: ignore[misc]


def find_references(query: str) -> list[tuple[str, str]]:
    """(act, number) pairs a Query names explicitly, such as "IPC 302", in order of appearance."""
    found: list[tuple[int, str, str]] = []
    for m in _ACT_FIRST.finditer(query):
        found.append((m.start(), _ALIAS_TO_ACT[m.group(1).lower()], m.group(2).upper()))
    for m in _NUMBER_FIRST.finditer(query):
        found.append((m.start(), _ALIAS_TO_ACT[m.group(2).lower()], m.group(1).upper()))
    out: list[tuple[str, str]] = []
    for _, act, number in sorted(found):
        if (act, number) not in out:
            out.append((act, number))
    return out
