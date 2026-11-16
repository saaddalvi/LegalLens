from pydantic import BaseModel

from .corpus import Corpus
from .llm import ProvisionRef
from .models import Citation


class CitationCheckResult(BaseModel):
    """Verdict on a generation's Citations against the Corpus."""

    valid: list[Citation]
    hallucinated: list[ProvisionRef]

    @property
    def all_valid(self) -> bool:
        return not self.hallucinated


def check_citations(
    citations: list[ProvisionRef], *, corpus: Corpus
) -> CitationCheckResult:
    """Verify every cited Provision is present in the Corpus.

    Reused by the evaluation harness (ticket 11) to report citation validity.
    """
    valid: list[Citation] = []
    hallucinated: list[ProvisionRef] = []
    seen: set[tuple[str, str]] = set()
    for ref in citations:
        if (ref.act, ref.number) in seen:
            continue
        seen.add((ref.act, ref.number))
        provision = corpus.get(ref.act, ref.number)
        if provision is None:
            hallucinated.append(ref)
        else:
            valid.append(Citation(**provision.model_dump()))
    return CitationCheckResult(valid=valid, hallucinated=hallucinated)
