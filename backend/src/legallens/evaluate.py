"""Run the evaluation: `python -m legallens.evaluate` (needs GOOGLE_API_KEY, and a built Corpus).

Asks every golden case through the endpoint in plain-RAG and CRAG modes against the real
Corpus and writes a Markdown report (default `backend/evaluation/report.md`) and prints it.

`python -m legallens.evaluate --contracts` runs the Contract evaluation instead: the sample
Contracts in `backend/fixtures/contracts/` are uploaded and asked about through the Contract
endpoints, and its section replaces the Contract section of the report, leaving the `/ask`
results alone. It needs a Postgres with pgvector, migrated, that it may write to
(`--database-url`, or EVAL_DATABASE_URL; it does not fall back to DATABASE_URL, which is
usually production). Each sample Contract is deleted when it has been scored.
"""

import argparse
import os
import sys
from pathlib import Path

from .auth import InvalidToken
from .contract_evaluation import (
    keep_contract_section,
    load_samples,
    render_contracts_report,
    run_contract_evaluation,
    write_report,
)
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

EVAL_USER = "legallens-evaluation"


class _EvalVerifier:
    """Signs the harness in as one throwaway user; there is no Clerk behind the harness."""

    def verify(self, token: str) -> str:
        if token != EVAL_USER:
            raise InvalidToken("not the evaluation token")
        return EVAL_USER


class _ThrottledAll:
    """Wraps an LLM so every call, whatever its name, goes through a shared RateLimiter."""

    def __init__(self, llm, limiter: RateLimiter):
        self._llm, self._limiter = llm, limiter

    def __getattr__(self, name):
        attr = getattr(self._llm, name)
        if not callable(attr):
            return attr

        def throttled(*args, **kwargs):
            self._limiter.wait()
            return attr(*args, **kwargs)

        return throttled


def run_contracts(args, corpus, limiter: RateLimiter) -> int:
    url = (args.database_url or os.environ.get("EVAL_DATABASE_URL", "")).strip()
    if not url:
        print(
            "Set --database-url or EVAL_DATABASE_URL to a migrated Postgres the evaluation may "
            "write to (it does not use DATABASE_URL).",
            file=sys.stderr,
        )
        return 1
    from fastapi.testclient import TestClient

    from .db import Database
    from .main import create_app

    app = create_app(
        corpus=corpus,
        llm=_ThrottledAll(GeminiLLM(), limiter),
        fallback=default_fallback(),
        verifier=_EvalVerifier(),
        database=Database(url, pooled=False),
    )
    with TestClient(app, headers={"Authorization": f"Bearer {EVAL_USER}"}) as client:
        result = run_contract_evaluation(
            load_samples(args.contract_cases),
            client=client,
            judge=ThrottledJudge(GeminiJudge(), limiter),
        )
    section = render_contracts_report(result)
    write_report(args.report, section)
    print(section)
    print(f"Wrote {args.report}")
    return 0


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
    ap.add_argument(
        "--contracts",
        action="store_true",
        help="run the Contract evaluation instead of the /ask golden set",
    )
    ap.add_argument(
        "--contract-cases",
        type=Path,
        default=BACKEND_DIR / "fixtures" / "contracts" / "cases.json",
    )
    ap.add_argument(
        "--database-url", help="Postgres for --contracts (default: EVAL_DATABASE_URL)"
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
    if args.contracts:
        return run_contracts(args, corpus, limiter)
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
    args.report.write_text(keep_contract_section(args.report, report))
    print(report)
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
