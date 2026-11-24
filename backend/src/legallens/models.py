from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Status = Literal["in_force", "repealed", "model"]
ResponseType = Literal["answer", "refusal"]
# "none": the answer is a "cannot answer" message that no source supports.
TrustLabel = Literal["corpus", "fallback", "corpus_and_fallback", "none"]


class Provision(BaseModel):
    """One Chunk: a Provision as stored for retrieval (ADR 0002)."""

    act: str
    chapter: str
    number: str
    status: Status
    text: str
    # References are "<Act> <number>", "; "-separated when several (see refs.py).
    superseded_by: str | None = None  # set on a repealed Provision
    supersedes: str | None = None  # set on an in-force Provision: its old equivalent


class Citation(BaseModel):
    act: str
    chapter: str
    number: str
    status: Status
    text: str  # verbatim English Provision text, always taken from the Corpus
    superseded_by: str | None = None
    supersedes: str | None = None


class FallbackSource(BaseModel):
    title: str
    url: str
    snippet: str


class ActSummary(BaseModel):
    act: str
    provisions: int


class ProvisionSummary(BaseModel):
    """A Provision as listed in its Act's index: no full text, just its first line."""

    number: str
    chapter: str
    status: Status
    snippet: str


class ActIndex(BaseModel):
    act: str
    provisions: list[ProvisionSummary]


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
    response_type: ResponseType = "answer"
    refusal_reason: str | None = None
    suggested_reformulation: str | None = None
    answer: str
    answer_language: str
    trust_label: TrustLabel
    citations: list[Citation]
    fallback_sources: list[FallbackSource]


class ClauseOut(BaseModel):
    """A Clause of a Contract. Its text is verbatim; pieces of a long Clause are rejoined."""

    number: str
    heading: str
    text: str


class ContractSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    page_count: int
    clause_count: int


class ContractDetail(ContractSummary):
    clauses: list[ClauseOut]
