"""Answering a follow-up Query in a Contract conversation, beside `Answerer` (answering.py).

A ContractAnswerer takes the same collaborators as an Answerer (Corpus, LLM, WebFallback) plus a
store of the user's Contract, and speaks the same interface: Stages through `on_stage`,
cancellation through `cancel`, an `Answered` or a typed error back, and one request log line.

The steps: the scope check (extended for Contract conversations), retrieval of the Contract's
Clauses and the Grader on them, the existing corrective loop on the Corpus (the Fallback
included), generation with the last few turns as context, and the Clause reference check and
the Citation check. Contract text stays inside this module's calls to the model and the
store: it is never logged, and the Fallback's web Query is built from the user's Query alone.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from threading import Event
from typing import Protocol

from .answering import STAGE_LABELS, Answered, Stage, StageFailed
from .citation_check import check_citations
from .contract_brief import clause_number
from .corpus import Corpus
from .db import ClauseHit
from .embeddings import Embedder
from .fallback import WebFallback
from .language import Language, detect_language
from .llm import LLM, ContractGeneration, ConversationLLM
from .models import (
    AskResponse,
    ClauseReference,
    ContractAnswer,
    ConversationTurn,
    FallbackSource,
    Provision,
    TrustLabel,
)
from .pipeline import (
    CANNOT_ANSWER_RELIABLY,
    Cancelled,
    Decisions,
    refusal,
    retrieve,
    search_fallback,
    verdict_for,
    with_superseding,
)
from .request_log import RequestLog

__all__ = ["ContractAnswerer", "ContractStore"]

log = logging.getLogger(__name__)

HISTORY_TURNS = 3  # earlier Queries and answers the model is shown
CLAUSE_PIECES = 5  # Clause pieces fetched by similarity
MAX_CLAUSES = 5  # whole Clauses the model is shown

_NAMED_CLAUSE = re.compile(r"\bclause\s+(\d+(?:\.\d+)*(?:\([a-z]+\))*)", re.IGNORECASE)

STAGE_LABELS_CONTRACT: dict[str, dict[Language, str]] = {
    **{
        k: STAGE_LABELS[k]
        for k in ("scope_check", "retrieval", "grading", "fallback", "generation")
    },
    "clause_retrieval": {
        "en": "Searching your Contract",
        "hi": "आपके Contract में खोज हो रही है",
    },
    "clause_grading": {
        "en": "Checking whether your Contract answers your question",
        "hi": "जाँच हो रही है कि आपका Contract आपके प्रश्न का उत्तर देता है या नहीं",
    },
    "citation_check": {
        "en": "Verifying Clause references and citations",
        "hi": "Clause संदर्भों और उद्धरणों की पुष्टि हो रही है",
    },
    "citation_recheck": {
        "en": "A reference could not be verified; rewriting and rechecking",
        "hi": "एक संदर्भ की पुष्टि नहीं हो सकी; उत्तर दोबारा लिखकर जाँचा जा रहा है",
    },
}

CONTRACT_SILENT: dict[Language, str] = {
    "en": "Your Contract does not address this question.",
    "hi": "आपका Contract इस प्रश्न को संबोधित नहीं करता।",
}
CONTRACT_SILENT_NO_LAW: dict[Language, str] = {
    "en": (
        "Your Contract does not address this question, and LegalLens could not find reliable "
        "law or sources on it either. Please try rephrasing your question."
    ),
    "hi": (
        "आपका Contract इस प्रश्न को संबोधित नहीं करता, और LegalLens को इस पर भरोसेमंद कानून या "
        "स्रोत भी नहीं मिले। कृपया अपना प्रश्न दूसरे शब्दों में पूछें।"
    ),
}
PERSONAL_ADVICE_REASON: dict[Language, str] = {
    "en": (
        "LegalLens can explain what your Contract and Indian law say, but it cannot advise "
        "whether to sign, accept or take any other step."
    ),
    "hi": (
        "LegalLens बता सकता है कि आपका Contract और भारतीय कानून क्या कहते हैं, पर यह सलाह नहीं दे "
        "सकता कि आप हस्ताक्षर करें, स्वीकार करें या कोई और कदम उठाएँ।"
    ),
}
UNRELATED_REASON: dict[Language, str] = {
    "en": "That question is not about your Contract or the law that governs it.",
    "hi": "यह प्रश्न आपके Contract या उस पर लागू कानून के बारे में नहीं है।",
}
ASK_POINTER: dict[Language, str] = {
    "en": "For general questions about Indian law, use the Ask page at /ask.",
    "hi": "भारतीय कानून के सामान्य प्रश्नों के लिए /ask पेज का उपयोग करें।",
}
SUGGESTED: dict[Language, str] = {
    "en": "What does my Contract say about this, and what does Indian law provide?",
    "hi": "इस बारे में मेरा Contract क्या कहता है, और भारतीय कानून क्या प्रावधान करता है?",
}


class ContractStore(Protocol):
    """The user's Contract as stored. Every call is scoped to one user's one Contract, so
    nothing of another Contract or another user can come back. `Database` is one."""

    async def search_clauses(
        self, user_id: str, contract_id: str, vector: list[float], k: int = ...
    ) -> list[ClauseHit]: ...

    async def get_clauses(self, user_id: str, contract_id: str) -> dict[str, str]: ...

    async def recent_turns(
        self, user_id: str, contract_id: str, count: int
    ) -> list[ConversationTurn]: ...

    async def add_turn(
        self, user_id: str, contract_id: str, query: str, response: ContractAnswer
    ) -> None: ...


class _ContractAndLLM(LLM, ConversationLLM, Protocol):
    pass


def _trust(clauses: bool, provisions: bool, sources: bool) -> TrustLabel:
    return {
        (True, True, True): "contract_corpus_and_fallback",
        (True, True, False): "contract_and_corpus",
        (True, False, True): "contract_and_fallback",
        (True, False, False): "contract",
        (False, True, True): "corpus_and_fallback",
        (False, True, False): "corpus",
        (False, False, True): "fallback",
    }[(clauses, provisions, sources)]


def _as_contract(response: AskResponse, **extra) -> ContractAnswer:
    return ContractAnswer(**response.model_dump(), **extra)


class ContractAnswerer:
    def __init__(
        self,
        *,
        corpus: Corpus,
        llm: _ContractAndLLM,
        fallback: WebFallback,
        store: ContractStore,
        embedder: Embedder,
    ):
        self._corpus, self._llm, self._fallback = corpus, llm, fallback
        self._store, self._embedder = store, embedder

    async def answer(
        self,
        user_id: str,
        contract_id: str,
        query: str,
        *,
        endpoint: str,
        on_stage: Callable[[Stage], None] | None = None,
        cancel: Event | None = None,
    ) -> Answered:
        """Answer a Query about one of the user's Contracts and append the Query and its answer
        to the Contract conversation, writing the request log line whatever the outcome.

        `on_stage` hears each Stage as it starts. `cancel`, once set, stops the work at the next
        Stage boundary with `Cancelled`, and nothing is saved. Any other failure is raised as
        `StageFailed`; its cause is logged by type only, since it may quote the Contract.
        There is no answer cache: Contract answers are private to the Contract.
        """
        rlog = RequestLog(endpoint, query)
        decisions = Decisions()
        language: Language = detect_language(query)
        current: list[str] = []

        def stage(stage_id: str) -> None:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            current[:] = [stage_id]
            rlog.stage(stage_id)
            if on_stage:
                on_stage(Stage(stage_id, STAGE_LABELS_CONTRACT[stage_id][language]))

        try:
            response = await self._answer(
                user_id, contract_id, query, language, stage, decisions
            )
            if cancel is not None and cancel.is_set():
                raise Cancelled()  # the reader left during the last Stage: save nothing
            await self._store.add_turn(user_id, contract_id, query, response)
        except Cancelled:
            rlog.finish("client_gone", decisions=decisions)
            raise
        except Exception as exc:
            log.error(
                "contract answering failed in stage %s: %s",
                current[0] if current else None,
                type(exc).__name__,
            )
            rlog.finish("error", decisions=decisions)
            raise StageFailed(current[0] if current else None) from exc
        rlog.finish("answer", response, decisions=decisions)
        return Answered(response, decisions)

    async def _answer(
        self,
        user_id: str,
        contract_id: str,
        query: str,
        language: Language,
        stage: Callable[[str], None],
        decisions: Decisions,
    ) -> ContractAnswer:
        llm = self._llm
        history = await self._store.recent_turns(user_id, contract_id, HISTORY_TURNS)

        stage("scope_check")
        scope = await asyncio.to_thread(llm.classify_contract_query, query, history)
        if scope.category == "personal_advice":
            reason = scope.reason or PERSONAL_ADVICE_REASON[language]
            return self._refused(reason, scope.suggested_reformulation, language)
        if scope.category == "unrelated":
            reason = scope.reason or UNRELATED_REASON[language]
            return self._refused(
                f"{reason} {ASK_POINTER[language]}",
                scope.suggested_reformulation,
                language,
                redirect_to_ask=True,
            )

        stage("clause_retrieval")
        all_clauses = await self._store.get_clauses(user_id, contract_id)
        if not all_clauses:
            raise LookupError("no such Contract")
        found = await self._find_clauses(user_id, contract_id, query, all_clauses)

        stage("clause_grading")
        clause_score = await asyncio.to_thread(llm.grade_clauses, query, found)
        decisions.clause_score = round(clause_score, 2)
        # Clauses that do not bear on the Query are not shown to the model at all.
        clauses = found if verdict_for(clause_score) != "incorrect" else []

        stage("retrieval")
        provisions = await asyncio.to_thread(retrieve, query, self._corpus)
        stage("grading")
        score = await asyncio.to_thread(llm.grade, query, provisions)
        verdict = verdict_for(score)
        decisions.grader_score = round(score, 2)
        decisions.verdict = verdict
        sources: list[FallbackSource] = []
        if verdict != "correct":
            stage("fallback")
            # The Query alone goes to the rewrite and the web: never any Clause text.
            sources = await asyncio.to_thread(
                search_fallback, query, llm=llm, fallback=self._fallback
            )
            decisions.fallback_sources = len(sources)
            if verdict == "incorrect":
                provisions = []

        if not (clauses or provisions or sources):
            return _as_contract(refusal(CONTRACT_SILENT_NO_LAW, language))
        trust = _trust(bool(clauses), bool(provisions), bool(sources))
        return await self._generate(
            query,
            clauses,
            provisions,
            sources,
            history,
            language,
            trust,
            stage,
            decisions,
        )

    async def _find_clauses(
        self, user_id: str, contract_id: str, query: str, all_clauses: dict[str, str]
    ) -> list[ClauseReference]:
        """The Clauses the Query names ("clause 7.2"), then those closest to it."""
        vector = (
            await asyncio.to_thread(self._embedder.embed, [query], is_query=True)
        )[0]
        hits = await self._store.search_clauses(
            user_id, contract_id, vector, CLAUSE_PIECES
        )
        numbers = [m for m in _NAMED_CLAUSE.findall(query) if m in all_clauses]
        numbers += [h.number for h in hits]
        ordered = list(dict.fromkeys(numbers))[:MAX_CLAUSES]
        return [ClauseReference(number=n, text=all_clauses[n]) for n in ordered]

    async def _generate(
        self,
        query: str,
        clauses: list[ClauseReference],
        provisions: list[Provision],
        sources: list[FallbackSource],
        history: list[ConversationTurn],
        language: Language,
        trust: TrustLabel,
        stage: Callable[[str], None],
        decisions: Decisions,
    ) -> ContractAnswer:
        """Generate, verifying Clause references against the Contract and Citations against the
        Corpus (one regeneration, then block)."""

        async def generate() -> ContractGeneration:
            return await asyncio.to_thread(
                self._llm.generate_contract_answer,
                query,
                clauses,
                provisions,
                sources,
                history,
                language,
            )

        def checked(gen: ContractGeneration):
            numbers = list(dict.fromkeys(clause_number(n) for n in gen.clause_numbers))
            # Only a Clause the model was shown can be quoted: a made-up number, a real Clause
            # the Grader set aside, and any number when no Clause was shown all fail.
            shown = {c.number: c for c in clauses}
            refs = (
                [shown[n] for n in numbers]
                if all(n in shown for n in numbers)
                else None
            )
            cites = (
                check_citations(gen.citations, corpus=self._corpus)
                if provisions
                else None
            )
            ok = (refs is not None or not clauses) and (
                cites is None or cites.all_valid
            )
            return ok, refs or [], cites.valid if cites else []

        stage("generation")
        gen = await generate()
        ok = True
        refs: list[ClauseReference] = []
        valid: list = []
        if clauses or provisions:
            stage("citation_check")
            ok, refs, valid = checked(gen)
            decisions.citation_recheck = not ok
            if not ok:
                stage("citation_recheck")
                gen = await generate()
                ok, refs, valid = checked(gen)
        if not ok:
            decisions.citation_blocked = True
            log.warning(
                "answer blocked: a reference could not be verified after a rewrite"
            )
            return _as_contract(refusal(CANNOT_ANSWER_RELIABLY, language))
        # The Trust label says what the answer rests on: a Clause counts only if it is quoted.
        trust = (
            _trust(bool(refs), bool(provisions), bool(sources))
            if (refs or provisions or sources)
            else "none"
        )
        text = gen.answer
        if not clauses:
            text = f"{CONTRACT_SILENT[language]}\n\n{text}"
        return ContractAnswer(
            answer=text,
            answer_language=language,
            trust_label=trust,
            citations=with_superseding(valid, self._corpus),
            fallback_sources=sources,
            clause_references=refs,
        )

    @staticmethod
    def _refused(
        reason: str,
        suggestion: str,
        language: Language,
        *,
        redirect_to_ask: bool = False,
    ) -> ContractAnswer:
        return ContractAnswer(
            response_type="refusal",
            answer=reason,
            answer_language=language,
            trust_label="none",
            citations=[],
            fallback_sources=[],
            refusal_reason=reason,
            suggested_reformulation=suggestion or SUGGESTED[language],
            redirect_to_ask=redirect_to_ask,
        )
