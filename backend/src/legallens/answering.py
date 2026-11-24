"""Answering a Query: the one module `/ask`, `/ask/stream` and the evaluation answer through.

An Answerer owns the answer cache, the corrective loop (pipeline.answer_query, which is
its implementation, not a second interface), the Stages with their labels, cancellation and
the request log line. Callers get an `Answered`, or one of two typed errors.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from .answer_cache import AnswerCache
from .corpus import Corpus
from .fallback import WebFallback
from .language import Language, detect_language
from .llm import LLM
from .models import AskResponse
from .pipeline import Cancelled, Decisions, answer_query
from .request_log import RequestLog

__all__ = ["Answered", "Answerer", "Cancelled", "Decisions", "Stage", "StageFailed"]

log = logging.getLogger(__name__)

# The Stages of answering a Query, with plain-language labels.
_STAGE_LABELS: dict[str, dict[Language, str]] = {
    "scope_check": {
        "en": "Checking your question",
        "hi": "आपके प्रश्न की जाँच हो रही है",
    },
    "retrieval": {
        "en": "Searching the statutes",
        "hi": "कानूनों में खोज हो रही है",
    },
    "grading": {
        "en": "Checking whether the statutes answer your question",
        "hi": "जाँच हो रही है कि कानून आपके प्रश्न का उत्तर देते हैं या नहीं",
    },
    "fallback": {
        "en": "Searching the web for more information",
        "hi": "अधिक जानकारी के लिए वेब पर खोज हो रही है",
    },
    "generation": {
        "en": "Writing the answer",
        "hi": "उत्तर लिखा जा रहा है",
    },
    "citation_check": {
        "en": "Verifying citations against the statutes",
        "hi": "उद्धरणों की कानूनों से पुष्टि हो रही है",
    },
    "citation_recheck": {
        "en": "A citation could not be verified; rewriting and rechecking",
        "hi": "एक उद्धरण की पुष्टि नहीं हो सकी; उत्तर दोबारा लिखकर जाँचा जा रहा है",
    },
}


@dataclass(frozen=True)
class Stage:
    id: str
    label: str  # plain language, in the Query's language


@dataclass
class Answered:
    response: AskResponse
    decisions: Decisions  # what the corrective loop decided; all unset on a cache hit


class StageFailed(Exception):
    """The corrective loop failed. `stage` is the Stage that was running (None before the first)."""

    def __init__(self, stage: str | None):
        super().__init__(f"answering failed in stage {stage}")
        self.stage = stage


class Answerer:
    """Answers Queries in one mode: Corrective RAG (crag=True) or the plain-RAG baseline.

    cache remembers answers to repeated Queries; None means every Query is answered afresh.
    Its key is the Query alone, so a cache belongs to one Answerer: do not share it across modes.
    """

    def __init__(
        self,
        *,
        corpus: Corpus,
        llm: LLM,
        fallback: WebFallback,
        crag: bool = True,
        cache: AnswerCache | None = None,
    ):
        self._corpus, self._llm, self._fallback = corpus, llm, fallback
        self._crag = crag
        self._cache = cache

    def answer(
        self,
        query: str,
        *,
        endpoint: str,
        on_stage: Callable[[Stage], None] | None = None,
        cancel: Event | None = None,
    ) -> Answered:
        """Answer a Query, writing its request log line whatever the outcome.

        `endpoint` labels the log line. `on_stage` hears each Stage as it starts. `cancel`,
        once set, stops the work at the next Stage boundary with `Cancelled`. Any other
        failure is raised as `StageFailed`.
        """
        rlog = RequestLog(endpoint, query)
        decisions = Decisions()
        if self._cache and (hit := self._cache.get(query)):
            # No Stages to show: the verified answer is already known.
            rlog.finish("answer", hit, cache_hit=True)
            return Answered(hit, decisions)
        language: Language = detect_language(query)
        current: list[str] = []

        def stage(stage_id: str) -> None:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            current[:] = [stage_id]
            rlog.stage(stage_id)
            if on_stage:
                on_stage(Stage(stage_id, _STAGE_LABELS[stage_id][language]))

        try:
            response = answer_query(
                query,
                corpus=self._corpus,
                llm=self._llm,
                fallback=self._fallback,
                crag=self._crag,
                on_stage=stage,
                decisions=decisions,
            )
            if self._cache:
                self._cache.put(query, response)
        except Cancelled:
            rlog.finish("client_gone", decisions=decisions)
            raise
        except Exception as exc:
            log.exception("answer generation failed")
            rlog.finish("error", decisions=decisions)
            raise StageFailed(current[0] if current else None) from exc
        rlog.finish("answer", response, decisions=decisions)
        return Answered(response, decisions)
