from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Status = Literal["in_force", "repealed", "model"]
ResponseType = Literal["answer", "refusal"]
# "none": the answer is a "cannot answer" message that no source supports. The "contract" values
# are for answers in a Contract conversation that rest, at least in part, on the user's Clauses.
TrustLabel = Literal[
    "corpus",
    "fallback",
    "corpus_and_fallback",
    "contract",
    "contract_and_corpus",
    "contract_and_fallback",
    "contract_corpus_and_fallback",
    "none",
]


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


class ClauseReference(BaseModel):
    """A Clause of the user's Contract, quoted: the number and its verbatim stored text."""

    number: str
    text: str


class ContractAnswer(AskResponse):
    """An answer in a Contract conversation: an AskResponse that also quotes the Clauses of the
    user's Contract it rests on, each with its verbatim stored text."""

    clause_references: list[ClauseReference] = []
    # A Query about neither the Contract nor its law: the user is pointed to /ask.
    redirect_to_ask: bool = False


class ConversationTurn(BaseModel):
    """One Query in a Contract conversation and the answer it got."""

    query: str
    response: ContractAnswer


class BriefTerm(BaseModel):
    label: str
    value: str
    clause: str  # a Clause number that exists in the Contract


class Obligation(BaseModel):
    text: str
    clauses: list[str]  # Clause numbers that exist in the Contract


class PartyObligations(BaseModel):
    party: str
    obligations: list[Obligation]


class FlaggedClause(BaseModel):
    """A Clause that differs from what Indian law provides. Always has a Clause reference and
    at least one Citation verified against the Corpus."""

    clause_reference: ClauseReference
    how_it_differs: str
    citations: list[Citation]


class ContractBrief(BaseModel):
    """The structured explanation of a Contract. Every Clause number in it is one of the
    Contract's own, and every Citation was checked against the Corpus."""

    parties: list[str]
    purpose: str
    key_terms: list[BriefTerm]
    obligations: list[PartyObligations]
    flagged_clauses: list[FlaggedClause]


class ContractSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    page_count: int
    clause_count: int


class ContractDetail(ContractSummary):
    clauses: list[ClauseOut]
    brief: ContractBrief | None = (
        None  # None for a Contract uploaded before briefs existed
    )
    conversation: list[
        ConversationTurn
    ] = []  # the Queries after the brief, oldest first
