import os
from collections.abc import Callable
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from .language import LANGUAGE_NAMES, Language
from .models import FallbackSource, Provision


class ProvisionRef(BaseModel):
    act: str = Field(
        description="The Act name exactly as listed after 'Act:', without the number"
    )
    number: str = Field(
        description="Exactly one Provision number as listed after 'Section:' (e.g. 35 or 498A); "
        "one Citation per Provision, never a list"
    )


class Generation(BaseModel):
    answer: str
    citations: list[ProvisionRef]


class RelevanceScore(BaseModel):
    score: float  # 0.0 (irrelevant) to 1.0 (fully answers the question)


class RewrittenQuery(BaseModel):
    query: str


class ScopeDecision(BaseModel):
    """Whether a Query is in scope; refusals carry a reason and a suggested reformulation."""

    category: Literal["in_scope", "not_indian_law", "personal_advice"]
    reason: str = ""
    suggested_reformulation: str = ""


class LLM(Protocol):
    def generate(
        self,
        query: str,
        provisions: list[Provision],
        sources: list[FallbackSource] = ...,
        language: Language = ...,
    ) -> Generation:
        """Answer in `language` ("en" or "hi"); Citations still refer to English Provisions."""
        ...

    def classify(self, query: str) -> ScopeDecision:
        """Whether the Query is in scope, or an Out-of-scope query to refuse."""
        ...

    def grade(self, query: str, provisions: list[Provision]) -> float:
        """Relevance of the retrieved Chunks to the Query, in [0, 1]."""
        ...

    def rewrite(self, query: str) -> str:
        """A web-search-friendly rewrite of the Query."""
        ...


_PROMPT = """You answer laypeople's questions about Indian law using ONLY the Provisions and
web sources below. Write the answer in {language_name}. Provision text is English: refer to
Provisions by Act name and number exactly as listed, and do not translate the Act names.
Use plain language. Cite only Provisions listed below, by exact Act name and number, with
the Act name and the number in separate fields and one Citation per Provision; never
cite web sources as Provisions. If the material does not answer the question, say so and
cite nothing. When there are no Provisions, answer from the web sources, say plainly that the
answer rests on less reliable web sources and not on statute text, and still cite nothing.
Do not give personal advice.
Provisions marked "repealed" are no longer law since 1 July 2024: say so, point to the
Provision that replaced them, and prefer citing the in-force Provision. When an in-force
Provision lists the old Provision it replaces, mention that old equivalent.
Provisions marked "model" come from a model Act, a template that States may adopt: it is not
law in force by itself. Whenever you cite one, say it is a template and not binding law, and
tell the user their own State's law may differ and that they should check it.

Provisions:
{provisions}
{web}
Question: {query}"""

_WEB_NOTE = """
Web sources (less reliable than Provisions; never cite them as Provisions, and say
when an answer rests on them):
{sources}
"""

_SCOPE_PROMPT = """Classify this question for an assistant that explains Indian law to laypeople.
- "not_indian_law": not about Indian law (other countries' law, or no legal topic at all).
- "personal_advice": asks what the user personally should do (e.g. whether to sue, sign,
  plead or settle). General questions about what the law says are NOT personal advice.
- "in_scope": anything else about Indian law.
For the first two, write a short polite reason, in the language of the question, and a
suggested reformulation that the assistant could answer (for personal_advice, ask what the
law says about the situation). Leave both empty for in_scope.

Question: {query}"""

_GRADE_PROMPT = """Rate from 0.0 to 1.0 how well the Provisions below answer the question
(1.0 = they directly answer it, 0.5 = partly relevant or incomplete, 0.0 = irrelevant).

Provisions:
{provisions}

Question: {query}"""

_REWRITE_PROMPT = """Rewrite this question about Indian law as a concise English web search
query that uses precise legal terms and names the relevant Indian statute if clear.

Question: {query}"""


def _gemini_chat(model: str):
    """A Gemini chat model that retries transient errors (429, 503) with backoff."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model, temperature=0, timeout=30, max_retries=3)


class GeminiLLM:
    """Gemini behind the LLM interface. Reads GOOGLE_API_KEY from the environment.

    When `fallback_model` (or GEMINI_FALLBACK_MODEL) names a second model, a call that
    still fails after the primary model's retries is tried once on the second model.
    Free-tier quotas are per model, so the second model also covers an exhausted quota.
    `chat_factory` builds a chat model from a model name; tests replace it.
    """

    def __init__(
        self,
        model: str | None = None,
        fallback_model: str | None = None,
        chat_factory: Callable[[str], Any] = _gemini_chat,
    ):
        self._model_name = model or os.environ.get(
            "GEMINI_MODEL", "gemini-3.5-flash-lite"
        )
        fallback = fallback_model or os.environ.get("GEMINI_FALLBACK_MODEL")
        self._fallback_name = fallback if fallback != self._model_name else None
        self._chat_factory = chat_factory
        self._chats: dict[str, Any] = {}

    def _chat(self, name: str):
        if name not in self._chats:
            self._chats[name] = self._chat_factory(name)
        return self._chats[name]

    def _structured(self, schema):
        primary = self._chat(self._model_name).with_structured_output(schema)
        if not self._fallback_name:
            return primary
        secondary = self._chat(self._fallback_name).with_structured_output(schema)
        return primary.with_fallbacks([secondary])

    @staticmethod
    def _format(provisions: list[Provision]) -> str:
        return (
            "\n\n".join(
                f"[Act: {p.act} | Section: {p.number}]"
                + (f" ({p.status})" if p.status != "in_force" else "")
                + f" {p.text}"
                for p in provisions
            )
            or "(none)"
        )

    def generate(
        self,
        query: str,
        provisions: list[Provision],
        sources: list[FallbackSource] = (),
        language: Language = "en",
    ) -> Generation:
        web = ""
        if sources:
            web = _WEB_NOTE.format(
                sources="\n".join(
                    f"- {s.title} ({s.url}): {s.snippet}" for s in sources
                )
            )
        return self._structured(Generation).invoke(
            _PROMPT.format(
                provisions=self._format(provisions),
                web=web,
                query=query,
                language_name=LANGUAGE_NAMES[language],
            )
        )

    def classify(self, query: str) -> ScopeDecision:
        return self._structured(ScopeDecision).invoke(_SCOPE_PROMPT.format(query=query))

    def grade(self, query: str, provisions: list[Provision]) -> float:
        if not provisions:
            return 0.0
        out = self._structured(RelevanceScore).invoke(
            _GRADE_PROMPT.format(provisions=self._format(provisions), query=query)
        )
        return min(1.0, max(0.0, out.score))

    def rewrite(self, query: str) -> str:
        return (
            self._structured(RewrittenQuery)
            .invoke(_REWRITE_PROMPT.format(query=query))
            .query
        )
