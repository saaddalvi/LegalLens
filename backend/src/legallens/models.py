from typing import Literal

from pydantic import BaseModel, Field, field_validator

Status = Literal["in_force", "repealed"]
TrustLabel = Literal["corpus", "fallback", "corpus_and_fallback"]


class Provision(BaseModel):
    """One Chunk: a Provision as stored for retrieval (ADR 0002)."""

    act: str
    chapter: str
    number: str
    status: Status
    text: str
    superseded_by: str | None = None


class Citation(BaseModel):
    act: str
    chapter: str
    number: str
    status: Status
    text: str  # verbatim English Provision text, always taken from the Corpus
    superseded_by: str | None = None


class FallbackSource(BaseModel):
    title: str
    url: str
    snippet: str


class AskRequest(BaseModel):
    query: str = Field(max_length=2000)

    @field_validator("query")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be blank")
        return v


class AskResponse(BaseModel):
    answer: str
    answer_language: str
    trust_label: TrustLabel
    citations: list[Citation]
    fallback_sources: list[FallbackSource]
