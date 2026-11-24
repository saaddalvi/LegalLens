"""What POST /ask does itself: it turns the Answerer's result into JSON and its failure into a 503.
How a Query is answered is tested at the Answerer (test_answering.py)."""

import pytest
from conftest import ART_21, FakeEmbedder, FakeFallback, FakeLLM, GenerationFailsLLM
from fastapi.testclient import TestClient

from legallens import main
from legallens.corpus import Corpus
from legallens.main import create_app


@pytest.fixture
def make_client(make_corpus):
    def make(llm=None, **kw):
        return TestClient(
            create_app(
                corpus=make_corpus(),
                llm=llm or FakeLLM(),
                fallback=FakeFallback(),
                **kw,
            )
        )

    return make


def test_a_query_returns_the_answer_as_json(make_client):
    r = make_client().post(
        "/ask", json={"query": "Can I be deprived of personal liberty?"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["answer_language"] == "en"
    assert body["trust_label"] == "corpus"
    assert body["citations"][0]["text"] == ART_21.text


def test_a_blank_query_is_rejected(make_client):
    assert make_client().post("/ask", json={"query": "  "}).status_code == 422


def test_a_failure_while_answering_returns_503(make_client):
    r = make_client(GenerationFailsLLM(score=0.9)).post(
        "/ask", json={"query": "liberty"}
    )
    assert r.status_code == 503


def test_unavailable_dependencies_return_503(tmp_path, monkeypatch):
    def broken_llm():
        raise RuntimeError("no api key")

    monkeypatch.setattr(main, "GeminiLLM", broken_llm)
    app = create_app(
        corpus=Corpus(tmp_path / "c", FakeEmbedder()), fallback=FakeFallback()
    )
    assert TestClient(app).post("/ask", json={"query": "liberty"}).status_code == 503
