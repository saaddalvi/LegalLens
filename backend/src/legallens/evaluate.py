"""Run the evaluation: `python -m legallens.evaluate` (needs GOOGLE_API_KEY, and a built Corpus).

Asks every golden case through the endpoint in plain-RAG and CRAG modes against the real
Corpus and writes a Markdown report (default `backend/evaluation/report.md`) and prints it.
"""

import argparse
import sys
from pathlib import Path

from .evaluation import (
    GeminiJudge,
    RateLimiter,
    ThrottledJudge,
    ThrottledLLM,
    load_golden_set,
    render_report,
    run_evaluation,
)
from .fallback import default_fallback
from .llm import GeminiLLM
from .main import BACKEND_DIR, default_corpus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--golden", type=Path, default=BACKEND_DIR / "evaluation" / "golden_set.json"
    )
    ap.add_argument(
        "--report", type=Path, default=BACKEND_DIR / "evaluation" / "report.md"
    )
    ap.add_argument(
        "--per-minute", type=int, default=15, help="Gemini requests per minute"
    )
    ap.add_argument(
        "--category", action="append", help="run only these categories (repeatable)"
    )
    args = ap.parse_args()

    corpus = default_corpus()
    if corpus.count() < 1000:
        print(
            f"Corpus has only {corpus.count()} Chunks: run `python -m legallens.build_corpus` first.",
            file=sys.stderr,
        )
        return 1
    limiter = RateLimiter(args.per_minute)  # one quota shared by the LLM and the judge
    result = run_evaluation(
        [
            c
            for c in load_golden_set(args.golden)
            if not args.category or c.category in args.category
        ],
        corpus=corpus,
        llm=ThrottledLLM(GeminiLLM(), limiter),
        fallback=default_fallback(),
        judge=ThrottledJudge(GeminiJudge(), limiter),
    )
    report = render_report(result)
    args.report.write_text(report)
    print(report)
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
