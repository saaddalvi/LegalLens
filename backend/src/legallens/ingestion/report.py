from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..models import Provision
from .constitution import ACT
from .criminal_codes import CRIMINAL_ACTS

# Plausible Chunk counts per Act (inclusive). A count outside the range usually means a
# parser boundary bug. Each ingested Act adds its range here.
EXPECTED_COUNTS: dict[str, tuple[int, int]] = {
    ACT: (
        480,
        520,
    ),  # 395 original Articles plus lettered insertions; the built Corpus has 499
    **{a.name: a.expected_count for a in CRIMINAL_ACTS.values()},
}


@dataclass
class Report:
    counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)


def build_report(provisions: list[Provision], required: Sequence[str] = ()) -> Report:
    counts = dict(Counter(p.act for p in provisions))
    warnings: list[str] = []
    for act, n in counts.items():
        if act in EXPECTED_COUNTS:
            lo, hi = EXPECTED_COUNTS[act]
            if not lo <= n <= hi:
                warnings.append(f"{act}: {n} Chunks, expected {lo}-{hi}")
        else:
            warnings.append(f"{act}: {n} Chunks but no expected range is configured")
    for act in required:  # a build that silently lost a whole Act is wrong
        if act not in counts:
            lo, hi = EXPECTED_COUNTS[act]
            warnings.append(f"{act}: no Chunks, expected {lo}-{hi}")
    seen = Counter((p.act, p.number) for p in provisions)
    for (act, number), n in seen.items():
        if n > 1:
            warnings.append(f"{act}: duplicate number {number} ({n} Chunks)")
    for p in provisions:
        if not p.text.strip():
            warnings.append(f"{p.act}: empty text for {p.number}")
    return Report(counts, warnings)
