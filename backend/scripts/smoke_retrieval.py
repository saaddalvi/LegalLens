"""Retrieval smoke check against the built Corpus: is an expected Provision in the top 10?

Uses the real embedding model and the store at CHROMA_PATH (default backend/data/chroma), so it
is a script rather than part of the test suite. Exits non-zero if a check fails.

    python scripts/smoke_retrieval.py
"""

import sys

from legallens.main import default_corpus

# (Query, Act, section number) that must be among the top 10 Provisions.
CHECKS = [
    ("is a non-compete after leaving a job valid", "Indian Contract Act", "27"),
    (
        "can my landlord or employer charge a penalty for breaking the contract",
        "Indian Contract Act",
        "74",
    ),
]


def main() -> int:
    corpus = default_corpus()
    failed = 0
    for query, act, number in CHECKS:
        found = [(p.act, p.number) for p in corpus.search(query, 10)]
        rank = found.index((act, number)) + 1 if (act, number) in found else None
        print(f"{'ok  ' if rank else 'FAIL'} {act} {number} at rank {rank}: {query}")
        failed += rank is None
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
