"""What POST /ask/stream does itself: Server-Sent Events framing, keepalives, the error frame,
and stopping the work when the reader leaves. How a Query is answered is tested at the
Answerer (test_answering.py)."""

import asyncio
import gc
import logging
import threading
import time

import pytest
from conftest import (
    QUERY,
    BrokenLLM,
    FakeEmbedder,
    FakeFallback,
    FakeLLM,
    GenerationFailsLLM,
    ScopeFailsLLM,
    parse_sse,
)
from fastapi.testclient import TestClient

from legallens import main
from legallens.answer_cache import AnswerCache
from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.models import AskRequest
from legallens.request_log import LOGGER_NAME


@pytest.fixture
def make_app(make_corpus):
    def make(llm, **kw):
        return create_app(corpus=make_corpus(), llm=llm, fallback=FakeFallback(), **kw)

    return make


def stream(app, query=QUERY):
    r = TestClient(app).post("/ask/stream", json={"query": query})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def names(events):
    return [n for n, _ in events]


def test_stages_then_one_answer_frame_equal_to_ask(make_app):
    app = make_app(FakeLLM(score=0.9))
    events = stream(app)
    assert names(events) == ["stage"] * 5 + ["answer"]
    assert events[0] == (
        "stage",
        {"id": "scope_check", "label": "Checking your question"},
    )
    assert events[-1][1] == TestClient(app).post("/ask", json={"query": QUERY}).json()


def test_a_failure_streams_the_stages_so_far_then_one_error_frame_naming_the_stage(
    make_app,
):
    events = stream(make_app(GenerationFailsLLM(score=0.9)))
    assert [d["id"] for n, d in events if n == "stage"] == [
        "scope_check",
        "retrieval",
        "grading",
        "generation",
    ]
    assert names(events)[-1] == "error" and names(events).count("error") == 1
    assert events[-1][1]["stage"] == "generation"
    assert "unavailable" in events[-1][1]["message"]
    assert "answer" not in names(events)


@pytest.mark.parametrize(
    ("llm", "stage"), [(ScopeFailsLLM(), "scope_check"), (BrokenLLM(), "grading")]
)
def test_the_error_frame_carries_the_failed_stage(make_app, llm, stage):
    assert stream(make_app(llm))[-1][1]["stage"] == stage


def test_unavailable_dependencies_give_503_before_the_stream_starts(
    tmp_path, monkeypatch
):
    def broken_llm():
        raise RuntimeError("no api key")

    monkeypatch.setattr(main, "GeminiLLM", broken_llm)
    app = create_app(
        corpus=Corpus(tmp_path / "c", FakeEmbedder()), fallback=FakeFallback()
    )
    r = TestClient(app).post("/ask/stream", json={"query": QUERY})
    assert r.status_code == 503
    assert not r.headers["content-type"].startswith("text/event-stream")


def test_a_slow_stage_is_covered_by_keepalive_comments(make_app, monkeypatch):
    monkeypatch.setattr(main, "KEEPALIVE_SECONDS", 0.02)

    class SlowLLM(FakeLLM):
        def classify(self, query):
            time.sleep(0.2)
            return super().classify(query)

    r = TestClient(make_app(SlowLLM())).post("/ask/stream", json={"query": QUERY})
    assert ": keepalive\n\n" in r.text
    assert names(parse_sse(r.text))[-1] == "answer"


def test_a_cache_hit_streams_a_single_answer_frame(make_app):
    app = make_app(FakeLLM(), cache=AnswerCache())
    answer = TestClient(app).post("/ask", json={"query": QUERY}).json()
    assert stream(app) == [("answer", answer)]


def test_a_reader_who_leaves_cancels_the_work(make_app, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    gate = threading.Event()

    class GatedLLM(FakeLLM):
        graded = False

        def classify(self, query):
            gate.wait(timeout=5)  # the reader leaves while this runs
            return super().classify(query)

        def grade(self, query, provisions):
            self.graded = True
            return super().grade(query, provisions)

    llm = GatedLLM()
    route = next(r for r in make_app(llm).routes if r.path == "/ask/stream")
    body = route.endpoint(AskRequest(query=QUERY)).body_iterator

    async def read_one_frame_then_leave():
        first = await body.__anext__()
        assert first.startswith("event: stage")  # the first Stage was sent
        await body.aclose()  # disconnect

    asyncio.run(read_one_frame_then_leave())
    gc.collect()
    gate.set()

    deadline = time.monotonic() + 5
    while "client_gone" not in caplog.text and time.monotonic() < deadline:
        time.sleep(0.01)
    assert '"outcome": "client_gone"' in caplog.text
    assert not llm.graded
