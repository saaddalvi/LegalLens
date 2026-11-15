from .corpus import Corpus
from .fallback import WebFallback
from .llm import LLM
from .models import AskResponse, Citation

TOP_K = 5


def answer_query(query: str, *, corpus: Corpus, llm: LLM, fallback: WebFallback) -> AskResponse:
    """Retrieve, generate, and build Citations from Corpus text only.

    The Fallback is held for the CRAG loop (ticket 05); the skeleton is Corpus-only.
    """
    provisions = corpus.search(query, TOP_K)
    gen = llm.generate(query, provisions)
    by_ref = {(p.act, p.number): p for p in provisions}
    citations: list[Citation] = []
    for ref in gen.citations:
        p = by_ref.get((ref.act, ref.number))
        if p and all((c.act, c.number) != (p.act, p.number) for c in citations):
            citations.append(Citation(**p.model_dump()))
    return AskResponse(
        answer=gen.answer,
        answer_language=gen.language,
        trust_label="corpus",
        citations=citations,
        fallback_sources=[],
    )
