import logging
from typing import Literal

from .citation_check import check_citations
from .corpus import Corpus
from .fallback import WebFallback
from .language import Language, detect_language
from .llm import LLM
from .models import AskResponse, Citation, FallbackSource, Provision, TrustLabel
from .refs import find_references, split_refs

TOP_K = 10  # the evaluation found expected Provisions ranked 6th-10th by the embeddings

# Verdict thresholds on the Grader's relevance score (recorded in ADR 0004).
CORRECT_THRESHOLD = 0.7
INCORRECT_THRESHOLD = 0.3

Verdict = Literal["correct", "ambiguous", "incorrect"]

CANNOT_ANSWER_RELIABLY: dict[Language, str] = {
    "en": (
        "LegalLens cannot answer reliably: it could not confirm this answer's citations "
        "against the Corpus. Please try rephrasing your question."
    ),
    "hi": (
        "LegalLens भरोसेमंद उत्तर नहीं दे सकता: यह उत्तर के उद्धरणों की पुष्टि Corpus से "
        "नहीं कर सका। कृपया अपना प्रश्न दूसरे शब्दों में पूछें।"
    ),
}
CANNOT_ANSWER_NO_SOURCES: dict[Language, str] = {
    "en": (
        "LegalLens cannot answer this question: the Corpus does not cover it and the web "
        "search could not supply reliable sources. Please try rephrasing your question."
    ),
    "hi": (
        "LegalLens इस प्रश्न का उत्तर नहीं दे सकता: Corpus में यह विषय नहीं है और वेब खोज से "
        "भरोसेमंद स्रोत नहीं मिले। कृपया अपना प्रश्न दूसरे शब्दों में पूछें।"
    ),
}

DEFAULT_REFUSAL_REASON: dict[Language, str] = {
    "en": "LegalLens only explains Indian law and cannot advise on personal decisions.",
    "hi": "LegalLens केवल भारतीय कानून समझाता है और निजी फैसलों पर सलाह नहीं दे सकता।",
}

DEFAULT_REFORMULATION: dict[Language, str] = {
    "en": "What does Indian law say about the situation you are asking about?",
    "hi": "आप जिस स्थिति के बारे में पूछ रहे हैं, उसके बारे में भारतीय कानून क्या कहता है?",
}

log = logging.getLogger(__name__)


def verdict_for(score: float) -> Verdict:
    if score >= CORRECT_THRESHOLD:
        return "correct"
    if score <= INCORRECT_THRESHOLD:
        return "incorrect"
    return "ambiguous"


def _refusal(message: dict[Language, str], language: Language) -> AskResponse:
    """A "cannot answer" message: no source supports it, so its Trust label is "none"."""
    return AskResponse(
        answer=message[language],
        answer_language=language,
        trust_label="none",
        citations=[],
        fallback_sources=[],
    )


def _retrieve(query: str, corpus: Corpus) -> list[Provision]:
    """Chunks for a Query: Provisions it names, then matches without a Superseding provision, then the superseded ones.

    A repealed Provision brings along its Superseding provision so the answer can point
    to current law. Search matches that have a Superseding provision rank behind those that do not.
    """
    named = [p for ref in find_references(query) if (p := corpus.get(*ref))]
    found = [
        p for p in corpus.search(query, TOP_K) if (p.act, p.number) not in _ids(named)
    ]
    found.sort(key=lambda p: bool(p.superseded_by))  # stable: keeps similarity order
    chunks = named + found
    for p in list(chunks):
        for ref in split_refs(p.superseded_by):
            if ref not in _ids(chunks) and (current := corpus.get(*ref)):
                chunks.append(current)
    return chunks


def _ids(provisions: list[Provision]) -> set[tuple[str, str]]:
    return {(p.act, p.number) for p in provisions}


def _with_superseding(citations: list[Citation], corpus: Corpus) -> list[Citation]:
    """Add the current Provision for every cited repealed one, so users see its text."""
    out = list(citations)
    cited = {(c.act, c.number) for c in citations}
    for c in citations:
        for ref in split_refs(c.superseded_by):
            if ref not in cited and (current := corpus.get(*ref)):
                cited.add(ref)
                out.append(Citation(**current.model_dump()))
    return out


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
        return _refusal(CANNOT_ANSWER_RELIABLY, language)
    return AskResponse(
        answer=gen.answer,
        answer_language=language,
        trust_label=trust_label,
        citations=_with_superseding(result.valid, corpus),
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
        reason = scope.reason or DEFAULT_REFUSAL_REASON[language]
        return AskResponse(
            response_type="refusal",
            answer=reason,
            answer_language=language,
            trust_label="corpus",
            citations=[],
            fallback_sources=[],
            refusal_reason=reason,
            suggested_reformulation=scope.suggested_reformulation
            or DEFAULT_REFORMULATION[language],
        )

    provisions = _retrieve(query, corpus)
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
        return _refusal(CANNOT_ANSWER_NO_SOURCES, language)
    return _answer(
        query,
        [],
        sources,
        corpus=corpus,
        llm=llm,
        trust_label="fallback",
        language=language,
    )
