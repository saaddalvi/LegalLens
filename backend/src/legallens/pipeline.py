import logging
from typing import Literal

from .citation_check import check_citations
from .corpus import Corpus
from .fallback import WebFallback
from .language import Language, detect_language
from .llm import LLM
from .models import AskResponse, FallbackSource, Provision, TrustLabel

TOP_K = 5

# Verdict thresholds on the Grader's relevance score (recorded in ADR 0004).
CORRECT_THRESHOLD = 0.7
INCORRECT_THRESHOLD = 0.3

Verdict = Literal["correct", "ambiguous", "incorrect"]

CANNOT_ANSWER_RELIABLY = (
    "LegalLens cannot answer reliably: it could not confirm this answer's citations "
    "against the Corpus. Please try rephrasing your question."
)
CANNOT_ANSWER_NO_SOURCES = (
    "LegalLens cannot answer this question: the Corpus does not cover it and the web "
    "search could not supply reliable sources. Please try rephrasing your question."
)

DEFAULT_REFUSAL_REASON = (
    "LegalLens only explains Indian law and cannot advise on personal decisions."
)

DEFAULT_REFORMULATION = (
    "What does Indian law say about the situation you are asking about?"
)

log = logging.getLogger(__name__)


def verdict_for(score: float) -> Verdict:
    if score >= CORRECT_THRESHOLD:
        return "correct"
    if score <= INCORRECT_THRESHOLD:
        return "incorrect"
    return "ambiguous"


def _refusal(message: str) -> AskResponse:
    return AskResponse(
        answer=message,
        answer_language="en",
        trust_label="corpus",
        citations=[],
        fallback_sources=[],
    )


def _search_fallback(
    query: str, *, llm: LLM, fallback: WebFallback
) -> list[FallbackSource]:
    """Rewrite the Query and run the Fallback; any provider failure yields no sources."""
    try:
        return fallback.search(llm.rewrite(query))
    except Exception:
        log.exception("web Fallback failed")
        return []


def _answer(
    query: str,
    provisions: list[Provision],
    sources: list[FallbackSource],
    *,
    corpus: Corpus,
    llm: LLM,
    trust_label: TrustLabel,
    language: Language,
) -> AskResponse:
    """Generate, verifying Citations against the Corpus (one regeneration, then block)."""
    if not provisions:
        # Fallback-only answer: web sources are listed, never cited as Provisions.
        gen = llm.generate(query, provisions, sources, language=language)
        return AskResponse(
            answer=gen.answer,
            answer_language=language,
            trust_label=trust_label,
            citations=[],
            fallback_sources=sources,
        )
    gen = llm.generate(query, provisions, sources, language=language)
    result = check_citations(gen.citations, corpus=corpus)
    if not result.all_valid:
        gen = llm.generate(query, provisions, sources, language=language)
        result = check_citations(gen.citations, corpus=corpus)
    if not result.all_valid:
        return _refusal(CANNOT_ANSWER_RELIABLY)
    return AskResponse(
        answer=gen.answer,
        answer_language=language,
        trust_label=trust_label,
        citations=result.valid,
        fallback_sources=sources,
    )


def answer_query(
    query: str,
    *,
    corpus: Corpus,
    llm: LLM,
    fallback: WebFallback,
    crag: bool = True,
) -> AskResponse:
    """Corrective RAG (ADR 0001); with crag=False, the plain-RAG baseline.

    Out-of-scope queries are refused first, before any retrieval. The Grader scores retrieved Chunks into a Verdict. Correct: answer from Chunks.
    Ambiguous: Chunks plus Fallback results. Incorrect: Fallback results only. A
    Fallback failure degrades to a Corpus-only answer (ambiguous) or an explicit
    "cannot answer" (incorrect).
    """
    language = detect_language(query)
    scope = llm.classify(query)
    if scope.category != "in_scope":
        reason = scope.reason or DEFAULT_REFUSAL_REASON
        return AskResponse(
            response_type="refusal",
            answer=reason,
            answer_language=language,
            trust_label="corpus",
            citations=[],
            fallback_sources=[],
            refusal_reason=reason,
            suggested_reformulation=scope.suggested_reformulation
            or DEFAULT_REFORMULATION,
        )

    provisions = corpus.search(query, TOP_K)
    if not crag:
        return _answer(
            query,
            provisions,
            [],
            corpus=corpus,
            llm=llm,
            trust_label="corpus",
            language=language,
        )

    verdict = verdict_for(llm.grade(query, provisions))
    if verdict == "correct":
        return _answer(
            query,
            provisions,
            [],
            corpus=corpus,
            llm=llm,
            trust_label="corpus",
            language=language,
        )

    sources = _search_fallback(query, llm=llm, fallback=fallback)
    if verdict == "ambiguous":
        if not sources:
            return _answer(
                query,
                provisions,
                [],
                corpus=corpus,
                llm=llm,
                trust_label="corpus",
                language=language,
            )
        return _answer(
            query,
            provisions,
            sources,
            corpus=corpus,
            llm=llm,
            trust_label="corpus_and_fallback",
            language=language,
        )
    if not sources:
        return _refusal(CANNOT_ANSWER_NO_SOURCES)
    return _answer(
        query,
        [],
        sources,
        corpus=corpus,
        llm=llm,
        trust_label="fallback",
        language=language,
    )
