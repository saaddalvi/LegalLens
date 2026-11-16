from .citation_check import check_citations
from .corpus import Corpus
from .fallback import WebFallback
from .llm import LLM
from .models import AskResponse

TOP_K = 5

CANNOT_ANSWER_RELIABLY = (
    "LegalLens cannot answer reliably: it could not confirm this answer's citations "
    "against the Corpus. Please try rephrasing your question."
)


def answer_query(query: str, *, corpus: Corpus, llm: LLM, fallback: WebFallback) -> AskResponse:
    """Retrieve, generate, and verify Citations against the Corpus.

    A Hallucinated citation (ticket 04) triggers one regeneration attempt; if that
    also hallucinates, the answer is blocked with a clear "cannot answer reliably"
    message instead of reaching the user. The Fallback is held for the CRAG loop
    (ticket 05); the skeleton is Corpus-only.
    """
    provisions = corpus.search(query, TOP_K)
    gen = llm.generate(query, provisions)
    result = check_citations(gen.citations, corpus=corpus)
    if not result.all_valid:
        gen = llm.generate(query, provisions)
        result = check_citations(gen.citations, corpus=corpus)
    if not result.all_valid:
        return AskResponse(
            answer=CANNOT_ANSWER_RELIABLY,
            answer_language="en",
            trust_label="corpus",
            citations=[],
            fallback_sources=[],
        )
    return AskResponse(
        answer=gen.answer,
        answer_language=gen.language,
        trust_label="corpus",
        citations=result.valid,
        fallback_sources=[],
    )
