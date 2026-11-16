"""Evaluation harness: a golden Q&A set run through the question endpoint in plain-RAG and
CRAG modes against a Corpus, scored on retrieval hit-rate, answer accuracy and citation validity.

Run it with `python -m legallens.evaluate`.
"""

import json
import logging
import os
import time
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Literal, Protocol

from fastapi.testclient import TestClient
from pydantic import BaseModel

from .citation_check import check_citations
from .corpus import Corpus
from .fallback import WebFallback
from .llm import LLM, ProvisionRef
from .main import create_app
from .models import AskResponse

Category = Literal[
    "english", "hindi", "repealed_code", "out_of_scope", "poor_retrieval"
]
Mode = Literal["plain", "crag"]
MODE_NAMES: dict[str, str] = {"plain": "Plain RAG", "crag": "CRAG"}


class GoldenCase(BaseModel):
    id: str
    category: Category
    query: str
    # Retrieval is a hit when the response cites at least one of these Provisions.
    expected_provisions: list[ProvisionRef] = []
    # Key points a correct answer states; the judge compares the answer with this.
    reference: str = ""
    expect_refusal: bool = False


class Judge(Protocol):
    def is_accurate(self, case: GoldenCase, response: AskResponse) -> bool:
        """Whether the answer states the case's reference points correctly."""
        ...


class Metrics(BaseModel):
    cases: int
    retrieval_hit_rate: float | None  # None when no case has expected Provisions
    answer_accuracy: float
    citation_validity: float


class CaseOutcome(BaseModel):
    case_id: str
    error: str | None = (
        None  # set when the case could not be scored; it is left out of the metrics
    )
    category: Category
    retrieval_hit: bool | None
    accurate: bool
    citations_valid: bool
    trust_label: str
    response_type: str


class ModeResult(Metrics):
    by_category: dict[str, Metrics]
    outcomes: list[CaseOutcome]


class EvaluationResult(BaseModel):
    modes: dict[str, ModeResult]


log = logging.getLogger(__name__)
RETRIES = 4


def _with_retries(fn, *, sleep=time.sleep):
    """Call fn, retrying transient provider failures (e.g. Gemini 503s) with growing waits."""
    for attempt in range(RETRIES):
        try:
            return fn()
        except Exception:
            if attempt == RETRIES - 1:
                raise
            log.warning("evaluation call failed, retrying", exc_info=True)
            sleep(5 * (attempt + 1))


def _ratio(flags: list[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def _metrics(outcomes: list[CaseOutcome]) -> Metrics:
    outcomes = [o for o in outcomes if o.error is None]
    hits = [o.retrieval_hit for o in outcomes if o.retrieval_hit is not None]
    return Metrics(
        cases=len(outcomes),
        retrieval_hit_rate=_ratio(hits),
        answer_accuracy=_ratio([o.accurate for o in outcomes]) or 0.0,
        citation_validity=_ratio([o.citations_valid for o in outcomes]) or 0.0,
    )


def _evaluate_case(
    case: GoldenCase, response: AskResponse, *, corpus: Corpus, judge: Judge
) -> CaseOutcome:
    cited = [ProvisionRef(act=c.act, number=c.number) for c in response.citations]
    hit = None
    if case.expected_provisions:
        expected = {(p.act, p.number) for p in case.expected_provisions}
        hit = any((c.act, c.number) in expected for c in cited)
    refused = response.response_type == "refusal"
    if case.expect_refusal:
        accurate = refused
    elif refused or (case.category == "hindi" and response.answer_language != "hi"):
        accurate = False
    else:
        accurate = _with_retries(lambda: judge.is_accurate(case, response))
    return CaseOutcome(
        case_id=case.id,
        category=case.category,
        retrieval_hit=hit,
        accurate=accurate,
        citations_valid=check_citations(cited, corpus=corpus).all_valid,
        trust_label=response.trust_label,
        response_type=response.response_type,
    )


def _ask(client: TestClient, query: str) -> AskResponse:
    r = client.post("/ask", json={"query": query})
    r.raise_for_status()
    return AskResponse(**r.json())


def run_evaluation(
    cases: list[GoldenCase],
    *,
    corpus: Corpus,
    llm: LLM,
    fallback: WebFallback,
    judge: Judge,
) -> EvaluationResult:
    """Ask every case through the endpoint in both modes and score the responses."""
    modes: dict[str, ModeResult] = {}
    for mode, crag in (("plain", False), ("crag", True)):
        client = TestClient(
            create_app(corpus=corpus, llm=llm, fallback=fallback, crag=crag)
        )
        outcomes = []
        for case in cases:
            try:
                r = _with_retries(partial(_ask, client, case.query))
                outcomes.append(_evaluate_case(case, r, corpus=corpus, judge=judge))
            except Exception as exc:
                log.exception("case %s failed in %s mode", case.id, mode)
                outcomes.append(
                    CaseOutcome(
                        case_id=case.id,
                        category=case.category,
                        retrieval_hit=None,
                        accurate=False,
                        citations_valid=True,
                        trust_label="-",
                        response_type="-",
                        error=type(exc).__name__,
                    )
                )
        grouped: dict[str, list[CaseOutcome]] = defaultdict(list)
        for o in outcomes:
            grouped[o.category].append(o)
        modes[mode] = ModeResult(
            **_metrics(outcomes).model_dump(),
            by_category={c: _metrics(os) for c, os in grouped.items()},
            outcomes=outcomes,
        )
    return EvaluationResult(modes=modes)


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def render_report(result: EvaluationResult) -> str:
    """Markdown report: plain RAG versus CRAG on every metric, overall and per category."""
    plain, crag = result.modes["plain"], result.modes["crag"]
    metrics = (
        ("Retrieval hit-rate", "retrieval_hit_rate"),
        ("Answer accuracy", "answer_accuracy"),
        ("Citation validity", "citation_validity"),
    )

    def table(title: str, a: Metrics, b: Metrics) -> list[str]:
        lines = [
            f"## {title} ({a.cases} cases)",
            "",
            f"| Metric | {MODE_NAMES['plain']} | {MODE_NAMES['crag']} |",
            "|---|---|---|",
        ]
        for label, attr in metrics:
            lines.append(
                f"| {label} | {_pct(getattr(a, attr))} | {_pct(getattr(b, attr))} |"
            )
        return lines + [""]

    out = ["# LegalLens evaluation", ""]
    out += table("Overall", plain, crag)
    for category in plain.by_category:
        out += table(category, plain.by_category[category], crag.by_category[category])
    out += ["## Per case", "", "| Case | Plain RAG | CRAG |", "|---|---|---|"]
    for p, c in zip(plain.outcomes, crag.outcomes):
        out.append(f"| {p.case_id} | {_case_cell(p)} | {_case_cell(c)} |")
    errored = [o for m in result.modes.values() for o in m.outcomes if o.error]
    if errored:
        out += [
            "",
            f"{len(errored)} case runs failed after retries and are excluded from the metrics: "
            + ", ".join(f"{o.case_id} ({o.error})" for o in errored),
        ]
    return "\n".join(out) + "\n"


def _case_cell(o: CaseOutcome) -> str:
    if o.error:
        return f"error ({o.error})"
    hit = "" if o.retrieval_hit is None else f", {'hit' if o.retrieval_hit else 'miss'}"
    cite = "" if o.citations_valid else ", HALLUCINATED"
    return f"{'correct' if o.accurate else 'wrong'}{hit}{cite} ({o.trust_label})"


class _Accuracy(BaseModel):
    accurate: bool


_JUDGE_PROMPT = """You grade an answer from an Indian-law assistant against reference points.
The answer is accurate if it states the reference points correctly and does not contradict
them. Wording, language and extra detail do not matter. An answer that says it cannot answer,
or that rests on unrelated law, is not accurate.

Question: {query}
Reference points: {reference}
Answer: {answer}"""


class GeminiJudge:
    """LLM judge of answer accuracy against a case's reference points."""

    def __init__(self, model: str | None = None):
        self._model_name = model or os.environ.get(
            "GEMINI_MODEL", "gemini-3.5-flash-lite"
        )
        self._model = None

    def is_accurate(self, case: GoldenCase, response: AskResponse) -> bool:
        if self._model is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._model = ChatGoogleGenerativeAI(
                model=self._model_name, temperature=0, timeout=30, max_retries=1
            ).with_structured_output(_Accuracy)
        return self._model.invoke(
            _JUDGE_PROMPT.format(
                query=case.query, reference=case.reference, answer=response.answer
            )
        ).accurate


def load_golden_set(path: Path) -> list[GoldenCase]:
    return [GoldenCase(**c) for c in json.loads(path.read_text())]


class RateLimiter:
    """Spaces calls so at most `per_minute` happen per minute (Gemini free-tier quota)."""

    def __init__(self, per_minute: int = 15, *, clock=time.monotonic, sleep=time.sleep):
        self._interval = 60.0 / per_minute
        self._clock, self._sleep = clock, sleep
        self._next = 0.0

    def wait(self) -> None:
        now = self._clock()
        if now < self._next:
            self._sleep(self._next - now)
            now = self._next
        self._next = now + self._interval


class ThrottledLLM:
    """Wraps an LLM so every call goes through a shared RateLimiter."""

    def __init__(self, llm: LLM, limiter: RateLimiter):
        self._llm, self._limiter = llm, limiter

    def generate(self, *args, **kwargs):
        self._limiter.wait()
        return self._llm.generate(*args, **kwargs)

    def classify(self, query):
        self._limiter.wait()
        return self._llm.classify(query)

    def grade(self, query, provisions):
        self._limiter.wait()
        return self._llm.grade(query, provisions)

    def rewrite(self, query):
        self._limiter.wait()
        return self._llm.rewrite(query)


class ThrottledJudge:
    def __init__(self, judge: Judge, limiter: RateLimiter):
        self._judge, self._limiter = judge, limiter

    def is_accurate(self, case: GoldenCase, response: AskResponse) -> bool:
        self._limiter.wait()
        return self._judge.is_accurate(case, response)
