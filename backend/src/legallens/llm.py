import os
from typing import Protocol

from pydantic import BaseModel

from .models import Provision


class ProvisionRef(BaseModel):
    act: str
    number: str


class Generation(BaseModel):
    answer: str
    language: str  # "en" or "hi"
    citations: list[ProvisionRef]


class LLM(Protocol):
    def generate(self, query: str, provisions: list[Provision]) -> Generation: ...


_PROMPT = """You answer laypeople's questions about Indian law using ONLY the Provisions below.
Reply in the language of the question (language code "en" or "hi"). Use plain language.
Cite only Provisions listed below, by exact Act name and number. If they do not answer the
question, say so and cite nothing. Do not give personal advice.

Provisions:
{provisions}

Question: {query}"""


class GeminiLLM:
    """Gemini behind the LLM interface. Reads GOOGLE_API_KEY from the environment."""

    def __init__(self, model: str | None = None):
        self._model_name = model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        self._chain = None

    def generate(self, query: str, provisions: list[Provision]) -> Generation:
        if self._chain is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._chain = ChatGoogleGenerativeAI(
                model=self._model_name, temperature=0
            ).with_structured_output(Generation)
        text = "\n\n".join(f"[{p.act} {p.number}] {p.text}" for p in provisions)
        return self._chain.invoke(_PROMPT.format(provisions=text, query=query))
