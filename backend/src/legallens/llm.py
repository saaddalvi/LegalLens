import os
from typing import Protocol

from pydantic import BaseModel

from .models import FallbackSource, Provision


class ProvisionRef(BaseModel):
    act: str
    number: str


class Generation(BaseModel):
    answer: str
    language: str  # "en" or "hi"
    citations: list[ProvisionRef]


class RelevanceScore(BaseModel):
    score: float  # 0.0 (irrelevant) to 1.0 (fully answers the question)


class RewrittenQuery(BaseModel):
    query: str


class LLM(Protocol):
    def generate(
        self,
        query: str,
        provisions: list[Provision],
        sources: list[FallbackSource] = ...,
    ) -> Generation: ...

    def grade(self, query: str, provisions: list[Provision]) -> float:
        """Relevance of the retrieved Chunks to the Query, in [0, 1]."""
        ...

    def rewrite(self, query: str) -> str:
        """A web-search-friendly rewrite of the Query."""
        ...


_PROMPT = """You answer laypeople's questions about Indian law using ONLY the Provisions and
web sources below. Reply in the language of the question (language code "en" or "hi").
Use plain language. Cite only Provisions listed below, by exact Act name and number; never
cite web sources as Provisions. If the material does not answer the question, say so and
cite nothing. Do not give personal advice.

Provisions:
{provisions}
{web}
Question: {query}"""

_WEB_NOTE = """
Web sources (less reliable than Provisions; never cite them as Provisions, and say
when an answer rests on them):
{sources}
"""

_GRADE_PROMPT = """Rate from 0.0 to 1.0 how well the Provisions below answer the question
(1.0 = they directly answer it, 0.5 = partly relevant or incomplete, 0.0 = irrelevant).

Provisions:
{provisions}

Question: {query}"""

_REWRITE_PROMPT = """Rewrite this question about Indian law as a concise English web search
query that uses precise legal terms and names the relevant Indian statute if clear.

Question: {query}"""


class GeminiLLM:
    """Gemini behind the LLM interface. Reads GOOGLE_API_KEY from the environment."""

    def __init__(self, model: str | None = None):
        self._model_name = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self._model = None

    def _structured(self, schema):
        if self._model is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._model = ChatGoogleGenerativeAI(
                model=self._model_name, temperature=0, timeout=30, max_retries=1
            )
        return self._model.with_structured_output(schema)

    @staticmethod
    def _format(provisions: list[Provision]) -> str:
        return "\n\n".join(f"[{p.act} {p.number}] {p.text}" for p in provisions) or "(none)"

    def generate(
        self,
        query: str,
        provisions: list[Provision],
        sources: list[FallbackSource] = (),
    ) -> Generation:
        web = ""
        if sources:
            web = _WEB_NOTE.format(
                sources="\n".join(f"- {s.title} ({s.url}): {s.snippet}" for s in sources)
            )
        return self._structured(Generation).invoke(
            _PROMPT.format(provisions=self._format(provisions), web=web, query=query)
        )

    def grade(self, query: str, provisions: list[Provision]) -> float:
        if not provisions:
            return 0.0
        out = self._structured(RelevanceScore).invoke(
            _GRADE_PROMPT.format(provisions=self._format(provisions), query=query)
        )
        return min(1.0, max(0.0, out.score))

    def rewrite(self, query: str) -> str:
        return self._structured(RewrittenQuery).invoke(_REWRITE_PROMPT.format(query=query)).query
