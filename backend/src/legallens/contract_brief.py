"""Writing a Contract's brief and checking it before anyone sees it.

The model drafts the brief from the whole Contract and from Provisions retrieved from the
Corpus for the Clauses that might differ from the law. Nothing in the draft is trusted. Every
Clause number is looked up in the Contract's stored Clauses, every flag's Citations go through
the Citation check, and the Clause text shown is the stored text, never the model's words.

A Hallucinated clause reference or Hallucinated citation causes one regeneration. What still
fails afterwards is dropped rather than shown: a term, obligation or flag whose Clause number
is not in the Contract, and a flag with no verified Citation.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass

from .citation_check import check_citations
from .clauses import ClausePiece
from .corpus import Corpus
from .llm import BriefDraft, DocumentLLM
from .models import (
    BriefTerm,
    ClauseReference,
    ContractBrief,
    FlaggedClause,
    Obligation,
    PartyObligations,
    Provision,
)

PROVISIONS_PER_CLAUSE = 2
MAX_PROVISIONS = 20  # what the model is shown, so the prompt stays small
SEARCH_CHARS = 600  # of a Clause, enough to say what it is about
MAX_CLAUSES_SEARCHED = 40

BRIEF_STAGE_LABELS = {
    "brief": "Writing the brief",
    "citation_check": "Verifying Clause references and Citations",
    "citation_recheck": "Something could not be verified; rewriting and rechecking",
}


def clause_texts(pieces: list[ClausePiece]) -> dict[str, str]:
    """Each Clause number with its whole verbatim text, in order."""
    out: dict[str, str] = {}
    for p in pieces:
        out[p.number] = out.get(p.number, "") + p.text
    return out


def clause_number(raw: str) -> str:
    """ "Clause 7.2." -> "7.2": a leading word and a trailing full stop are not part of it."""
    return re.sub(
        r"^(clause|section|article)\s+", "", raw.strip(), flags=re.IGNORECASE
    ).rstrip(".")


@dataclass
class Checked:
    brief: ContractBrief
    hallucinated: bool  # a Clause number or Citation that does not exist was found


def check_brief(draft: BriefDraft, clauses: dict[str, str], corpus: Corpus) -> Checked:
    """Keeps only what verifies, and says whether anything made up was found."""
    bad = False

    def known(raw: str) -> str | None:
        nonlocal bad
        n = clause_number(raw)
        if n in clauses:
            return n
        bad = True
        return None

    terms = [
        BriefTerm(label=t.label, value=t.value, clause=n)
        for t in draft.key_terms
        if (n := known(t.clause))
    ]
    obligations = []
    for party in draft.obligations:
        kept = []
        for o in party.obligations:
            nums = [known(c) for c in o.clauses]
            # One made-up Clause number puts the whole obligation in doubt: drop it rather
            # than quietly change which Clauses it claims to rest on.
            if nums and all(nums):
                kept.append(Obligation(text=o.text, clauses=nums))
        if kept:
            obligations.append(PartyObligations(party=party.party, obligations=kept))
    flags = []
    for f in draft.flagged_clauses:
        n = known(f.clause)
        result = check_citations(f.citations, corpus=corpus)
        bad = bad or not result.all_valid
        if n and result.valid:
            flags.append(
                FlaggedClause(
                    clause_reference=ClauseReference(number=n, text=clauses[n]),
                    how_it_differs=f.how_it_differs,
                    citations=result.valid,
                )
            )
    brief = ContractBrief(
        parties=draft.parties,
        purpose=draft.purpose,
        key_terms=terms,
        obligations=obligations,
        flagged_clauses=flags,
    )
    return Checked(brief, bad)


def candidate_provisions(clauses: dict[str, str], corpus: Corpus) -> list[Provision]:
    """Provisions from the Corpus that might bear on the Contract's Clauses, closest first
    for each Clause. The Corpus is local, so no Contract text leaves the service."""
    found: dict[tuple[str, str], Provision] = {}
    searched = 0
    for number, text in clauses.items():
        if number == "0":  # the parties and recitals
            continue
        if searched == MAX_CLAUSES_SEARCHED or len(found) >= MAX_PROVISIONS:
            break
        searched += 1
        for p in corpus.search(text[:SEARCH_CHARS], PROVISIONS_PER_CLAUSE):
            found.setdefault((p.act, p.number), p)
    return list(found.values())[:MAX_PROVISIONS]


class BriefWriter:
    def __init__(self, *, llm: DocumentLLM, corpus: Corpus):
        self._llm, self._corpus = llm, corpus

    async def write(
        self,
        text: str,
        pieces: list[ClausePiece],
        *,
        on_stage: Callable[[str, str], None],
    ) -> ContractBrief:
        """The checked brief. Raises whatever the model call raises."""
        clauses = clause_texts(pieces)

        def stage(stage_id: str) -> None:
            on_stage(stage_id, BRIEF_STAGE_LABELS[stage_id])

        stage("brief")
        provisions = await asyncio.to_thread(
            candidate_provisions, clauses, self._corpus
        )
        numbers = list(clauses)

        async def draft() -> BriefDraft:
            return await asyncio.to_thread(
                self._llm.write_brief, text, numbers, provisions
            )

        first = await draft()
        stage("citation_check")
        checked = await asyncio.to_thread(check_brief, first, clauses, self._corpus)
        if checked.hallucinated:
            stage("citation_recheck")
            second = await draft()
            checked = await asyncio.to_thread(
                check_brief, second, clauses, self._corpus
            )
        return checked.brief
