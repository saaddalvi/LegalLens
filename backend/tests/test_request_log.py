import json
import logging

import pytest
from fastapi.testclient import TestClient
from test_ask import (
    ART_21,
    IPC_302,
    AlwaysHallucinatingLLM,
    FakeEmbedder,
    FakeLLM,
    HallucinatingThenValidLLM,
)
from test_ask_stream import HINDI_QUERY, BrokenLLM, OutOfScopeLLM
from test_crag import QUERY, RecordingFallback

from legallens.answer_cache import AnswerCache
from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.request_log import LOGGER_NAME, RequestLog


def make_client(tmp_path, llm, fallback=None, **kwargs):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return TestClient(
        create_app(
            corpus=corpus, llm=llm, fallback=fallback or RecordingFallback(), **kwargs
        )
    )


@pytest.fixture
def logged(caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    def records() -> list[dict]:
        return [
            json.loads(r.getMessage()) for r in caplog.records if r.name == LOGGER_NAME
        ]

    records.text = lambda: caplog.text
    return records


def ask(client, path="/ask", query=QUERY):
    return client.post(path, json={"query": query})


@pytest.mark.parametrize(
    ("path", "endpoint"), [("/ask", "ask"), ("/ask/stream", "ask_stream")]
)
def test_each_request_writes_one_structured_record(tmp_path, logged, path, endpoint):
    ask(make_client(tmp_path, FakeLLM(score=0.9)), path)
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


@pytest.mark.parametrize("path", ["/ask", "/ask/stream"])
def test_the_query_and_the_answer_are_never_logged(tmp_path, logged, path):
    # Queries can describe people's personal situations.
    client = make_client(tmp_path, FakeLLM(score=0.9))
    body = ask(
        client, path, "My landlord is hiding from me, Priya Sharma, flat 12"
    ).text
    assert "Plain-language summary" in body  # an answer was produced
    assert len(logged()) == 1  # and logged, so the checks below are not vacuous
    text = logged.text()
    assert "Priya" not in text and "landlord" not in text
    assert "Plain-language summary" not in text


def test_a_hindi_query_is_logged_by_language_and_length_only(tmp_path, logged):
    ask(make_client(tmp_path, FakeLLM()), "/ask/stream", HINDI_QUERY)
    (record,) = logged()
    assert record["language"] == "hi"
    assert record["query_chars"] == len(HINDI_QUERY)
    assert HINDI_QUERY not in logged.text()


def test_the_graders_score_and_verdict_are_logged_for_tuning_the_thresholds(
    tmp_path, logged
):
    fallback = RecordingFallback()
    ask(make_client(tmp_path, FakeLLM(score=0.5), fallback))
    (record,) = logged()
    assert record["grader_score"] == 0.5
    assert record["verdict"] == "ambiguous"
    assert record["fallback_sources"] == 1
    assert record["trust_label"] == "corpus_and_fallback"
    assert "fallback" in record["stages_ms"]


def test_a_correct_verdict_logs_no_fallback(tmp_path, logged):
    ask(make_client(tmp_path, FakeLLM(score=0.9)))
    (record,) = logged()
    assert record["verdict"] == "correct"
    assert "fallback_sources" not in record


def test_a_failed_fallback_is_logged_as_no_sources(tmp_path, logged):
    ask(make_client(tmp_path, FakeLLM(score=0.5), RecordingFallback(fail=True)))
    (record,) = logged()
    assert record["fallback_sources"] == 0


def test_a_citation_recheck_is_logged(tmp_path, logged):
    ask(make_client(tmp_path, HallucinatingThenValidLLM()))
    (record,) = logged()
    assert record["citation_recheck"] is True
    assert "citation_blocked" not in record
    assert record["trust_label"] == "corpus"


def test_a_blocked_answer_is_logged(tmp_path, logged):
    ask(make_client(tmp_path, AlwaysHallucinatingLLM()))
    (record,) = logged()
    assert record["citation_recheck"] is True
    assert record["citation_blocked"] is True
    assert record["trust_label"] == "none"


def test_a_refusal_is_logged_with_only_the_scope_check(tmp_path, logged):
    ask(make_client(tmp_path, OutOfScopeLLM()), "/ask/stream")
    (record,) = logged()
    assert record["response_type"] == "refusal"
    assert list(record["stages_ms"]) == ["scope_check"]


@pytest.mark.parametrize("path", ["/ask", "/ask/stream"])
def test_a_failure_is_logged_with_the_stage_that_failed(tmp_path, logged, path):
    ask(make_client(tmp_path, BrokenLLM()), path)
    records = [r for r in logged() if r["event"] == "request"]
    assert len(records) == 1
    assert records[0]["outcome"] == "error"
    assert records[0]["error_stage"] == "grading"
    assert "response_type" not in records[0]


def test_a_cache_hit_is_logged_as_one_without_stages(tmp_path, logged):
    client = make_client(tmp_path, FakeLLM(), cache=AnswerCache())
    ask(client)
    ask(client, "/ask/stream")
    first, second = logged()
    assert first["cache_hit"] is False and second["cache_hit"] is True
    assert second["endpoint"] == "ask_stream"
    assert second["stages_ms"] == {}
    assert second["trust_label"] == "corpus"


def test_the_log_does_not_change_the_answer(tmp_path, logged):
    client = make_client(tmp_path, FakeLLM(score=0.9))
    assert ask(client).json()["answer"].startswith("Plain-language summary")


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
