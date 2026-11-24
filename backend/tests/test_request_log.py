import json
import logging
import threading

import pytest
from conftest import (
    HINDI_QUERY,
    QUERY,
    AlwaysHallucinatingLLM,
    BrokenLLM,
    FakeFallback,
    FakeLLM,
    FakeVerifier,
    HallucinatingThenValidLLM,
    OutOfScopeLLM,
    RecordingFallback,
    signed_in,
)

from legallens.answer_cache import AnswerCache
from legallens.answering import Cancelled, StageFailed
from legallens.main import create_app
from legallens.request_log import LOGGER_NAME, RequestLog


@pytest.fixture
def logged(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    def records() -> list[dict]:
        return [
            json.loads(r.getMessage()) for r in caplog.records if r.name == LOGGER_NAME
        ]

    records.text = lambda: caplog.text
    return records


def ask(answerer, query=QUERY, endpoint="ask", **kw):
    return answerer.answer(query, endpoint=endpoint, **kw)


@pytest.mark.parametrize("endpoint", ["ask", "ask_stream"])
def test_each_request_writes_one_structured_record(make_answerer, logged, endpoint):
    ask(make_answerer(FakeLLM(score=0.9)), endpoint=endpoint)
    (record,) = logged()
    assert record["event"] == "request"
    assert record["endpoint"] == endpoint
    assert record["outcome"] == "answer"
    assert record["response_type"] == "answer"
    assert record["trust_label"] == "corpus"
    assert record["cache_hit"] is False
    assert record["language"] == "en"
    assert record["query_chars"] == len(QUERY)
    assert record["total_ms"] >= 0
    assert {
        "scope_check",
        "retrieval",
        "grading",
        "generation",
        "citation_check",
    } <= set(record["stages_ms"])
    assert all(ms >= 0 for ms in record["stages_ms"].values())


def test_the_routes_label_their_records(make_corpus, logged):
    client = signed_in(
        create_app(
            verifier=FakeVerifier(),
            corpus=make_corpus(),
            llm=FakeLLM(),
            fallback=FakeFallback(),
        )
    )
    client.post("/ask", json={"query": QUERY})
    client.post("/ask/stream", json={"query": QUERY})
    assert [r["endpoint"] for r in logged()] == ["ask", "ask_stream"]


def test_the_query_and_the_answer_are_never_logged(make_answerer, logged):
    # Queries can describe people's personal situations.
    answered = ask(
        make_answerer(FakeLLM(score=0.9)),
        "My landlord is hiding from me, Priya Sharma, flat 12",
    )
    assert (
        "Plain-language summary" in answered.response.answer
    )  # an answer was produced
    assert len(logged()) == 1  # and logged, so the checks below are not vacuous
    text = logged.text()
    assert "Priya" not in text and "landlord" not in text
    assert "Plain-language summary" not in text


def test_a_hindi_query_is_logged_by_language_and_length_only(make_answerer, logged):
    ask(make_answerer(FakeLLM()), HINDI_QUERY)
    (record,) = logged()
    assert record["language"] == "hi"
    assert record["query_chars"] == len(HINDI_QUERY)
    assert HINDI_QUERY not in logged.text()


def test_the_graders_score_and_verdict_are_logged_for_tuning_the_thresholds(
    make_answerer, logged
):
    ask(make_answerer(FakeLLM(score=0.5), RecordingFallback()))
    (record,) = logged()
    assert record["grader_score"] == 0.5
    assert record["verdict"] == "ambiguous"
    assert record["fallback_sources"] == 1
    assert record["trust_label"] == "corpus_and_fallback"
    assert "fallback" in record["stages_ms"]


def test_a_correct_verdict_logs_no_fallback(make_answerer, logged):
    ask(make_answerer(FakeLLM(score=0.9)))
    (record,) = logged()
    assert record["verdict"] == "correct"
    assert "fallback_sources" not in record
    assert "citation_recheck" not in record


def test_a_failed_fallback_is_logged_as_no_sources(make_answerer, logged):
    ask(make_answerer(FakeLLM(score=0.5), RecordingFallback(fail=True)))
    (record,) = logged()
    assert record["fallback_sources"] == 0


def test_a_citation_recheck_is_logged(make_answerer, logged):
    ask(make_answerer(HallucinatingThenValidLLM()))
    (record,) = logged()
    assert record["citation_recheck"] is True
    assert "citation_blocked" not in record
    assert record["trust_label"] == "corpus"


def test_a_blocked_answer_is_logged(make_answerer, logged):
    ask(make_answerer(AlwaysHallucinatingLLM()))
    (record,) = logged()
    assert record["citation_recheck"] is True
    assert record["citation_blocked"] is True
    assert record["trust_label"] == "none"


def test_a_refusal_is_logged_with_only_the_scope_check(make_answerer, logged):
    ask(make_answerer(OutOfScopeLLM()))
    (record,) = logged()
    assert record["response_type"] == "refusal"
    assert list(record["stages_ms"]) == ["scope_check"]


def test_a_failure_is_logged_with_the_stage_that_failed(make_answerer, logged):
    with pytest.raises(StageFailed):
        ask(make_answerer(BrokenLLM()))
    (record,) = logged()
    assert record["outcome"] == "error"
    assert record["error_stage"] == "grading"
    assert "response_type" not in record


def test_a_cancelled_request_is_logged_as_client_gone(make_answerer, logged):
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        ask(make_answerer(FakeLLM()), cancel=cancel)
    (record,) = logged()
    assert record["outcome"] == "client_gone"
    assert "response_type" not in record


def test_a_cache_hit_is_logged_as_one_without_stages(make_answerer, logged):
    answerer = make_answerer(FakeLLM(), cache=AnswerCache())
    ask(answerer)
    ask(answerer, endpoint="ask_stream")
    first, second = logged()
    assert first["cache_hit"] is False and second["cache_hit"] is True
    assert second["endpoint"] == "ask_stream"
    assert second["stages_ms"] == {}
    assert second["trust_label"] == "corpus"


# ── RequestLog on its own, with a clock the test controls ──────────────────


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def test_a_stage_lasts_until_the_next_one_starts_and_repeats_add_up(logged):
    clock = Clock()
    log = RequestLog("ask", "a question", clock=clock)
    log.stage("generation")
    clock.now += 2
    log.stage("citation_check")
    clock.now += 1
    log.stage("generation")  # a regeneration after a recheck
    clock.now += 4
    log.finish("answer")
    (record,) = logged()
    assert record["stages_ms"] == {"generation": 6000, "citation_check": 1000}
    assert record["total_ms"] == 7000


def test_a_request_that_ends_in_error_names_the_last_stage(logged):
    log = RequestLog("ask_stream", "q", clock=Clock())
    log.stage("scope_check")
    log.stage("retrieval")
    log.finish("error")
    (record,) = logged()
    assert record["error_stage"] == "retrieval"
