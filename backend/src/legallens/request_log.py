"""One structured log line per request, to see where time and quota go once the app is live.

Each line is a JSON object: how long each Stage took, what the Grader and the Citation check
did, how the request ended. It never holds the Query or the answer, only the Query's length
and language, because Queries can describe people's personal situations.
"""

import json
import logging
import time
from collections.abc import Callable

from .language import detect_language
from .models import AskResponse
from .pipeline import Decisions

LOGGER_NAME = "legallens.request"

log = logging.getLogger(LOGGER_NAME)
log.setLevel(logging.INFO)
if not log.handlers and not logging.getLogger().handlers:
    # Under uvicorn nothing else prints our INFO lines; a plain handler puts them on stderr,
    # where a host's log viewer (a Space's Logs tab) picks them up.
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_handler)


class RequestLog:
    """Times one request and writes its record when it ends. The record includes what the
    corrective loop decided (the Grader's score and Verdict, whether the Citation check
    forced a rewrite), when it got that far."""

    def __init__(
        self,
        endpoint: str,
        query: str,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.endpoint = endpoint
        self._language = detect_language(query)
        self._query_chars = len(query)
        self._clock = clock
        self._started = clock()
        self._stages: list[tuple[str, float]] = []  # (id, when it started)

    def stage(self, stage_id: str) -> None:
        self._stages.append((stage_id, self._clock()))

    def finish(
        self,
        outcome: str,
        result: AskResponse | None = None,
        *,
        cache_hit: bool = False,
        decisions: Decisions | None = None,
    ) -> None:
        """outcome: "answer", "error", or "client_gone" (the reader left mid-stream)."""
        end = self._clock()
        # A Stage lasts until the next one starts. A Stage that runs twice (generation, after
        # a rewrite) adds up.
        stages_ms: dict[str, int] = {}
        for i, (stage_id, started) in enumerate(self._stages):
            until = self._stages[i + 1][1] if i + 1 < len(self._stages) else end
            stages_ms[stage_id] = stages_ms.get(stage_id, 0) + round(
                (until - started) * 1000
            )
        record: dict = {
            "event": "request",
            "endpoint": self.endpoint,
            "outcome": outcome,
            "language": self._language,
            "query_chars": self._query_chars,
            "cache_hit": cache_hit,
            "total_ms": round((end - self._started) * 1000),
            "stages_ms": stages_ms,
            **_decided(decisions),
        }
        if result is not None:
            record["response_type"] = result.response_type
            record["trust_label"] = result.trust_label
        if outcome == "error" and self._stages:
            record["error_stage"] = self._stages[-1][0]
        log.info(json.dumps(record))


def _decided(d: Decisions | None) -> dict:
    """The Decisions that were reached, as record fields."""
    if d is None:
        return {}
    out: dict = {}
    if d.clause_score is not None:
        out["clause_grader_score"] = d.clause_score
    if d.grader_score is not None:
        out["grader_score"] = d.grader_score
        out["verdict"] = d.verdict
    if d.fallback_sources is not None:
        out["fallback_sources"] = d.fallback_sources
    if d.citation_recheck:
        out["citation_recheck"] = True
    if d.citation_blocked:
        out["citation_blocked"] = True
    return out
