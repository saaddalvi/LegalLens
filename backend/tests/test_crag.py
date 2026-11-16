import pytest
from fastapi.testclient import TestClient
from test_ask import ART_21, IPC_302, FakeEmbedder, FakeLLM

from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.models import FallbackSource

WEB = FallbackSource(title="Explainer", url="https://example.org/x", snippet="Web snippet.")
QUERY = "Can I be deprived of personal liberty?"


class RecordingFallback:
    def __init__(self, results=(WEB,), fail=False):
        self.results = list(results)
        self.fail = fail
        self.queries: list[str] = []

    def search(self, query):
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("provider down")
        return self.results


class RewritingLLM(FakeLLM):
    def rewrite(self, query):
        return f"rewritten: {query}"


def make_client(tmp_path, llm, fallback, **kw):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return TestClient(create_app(corpus=corpus, llm=llm, fallback=fallback, **kw))


def test_correct_verdict_uses_corpus_only(tmp_path):
    fb = RecordingFallback()
    body = make_client(tmp_path, FakeLLM(score=0.9), fb).post("/ask", json={"query": QUERY}).json()
    assert body["trust_label"] == "corpus"
    assert body["fallback_sources"] == []
    assert body["citations"]
    assert fb.queries == []


def test_incorrect_verdict_answers_from_fallback_with_rewritten_query(tmp_path):
    fb = RecordingFallback()
    llm = RewritingLLM(score=0.1)
    body = make_client(tmp_path, llm, fb).post("/ask", json={"query": QUERY}).json()
    assert fb.queries == [f"rewritten: {QUERY}"]
    assert body["trust_label"] == "fallback"
    assert body["fallback_sources"] == [WEB.model_dump()]
    assert body["citations"] == []
    assert llm.sources_seen == (WEB,) or list(llm.sources_seen) == [WEB]


def test_ambiguous_verdict_combines_corpus_and_fallback(tmp_path):
    fb = RecordingFallback()
    body = make_client(tmp_path, RewritingLLM(score=0.5), fb).post("/ask", json={"query": QUERY}).json()
    assert fb.queries == [f"rewritten: {QUERY}"]
    assert body["trust_label"] == "corpus_and_fallback"
    assert body["fallback_sources"] == [WEB.model_dump()]
    assert body["citations"]


@pytest.mark.parametrize("fb", [RecordingFallback(fail=True), RecordingFallback(results=())])
def test_ambiguous_with_failed_fallback_degrades_to_corpus_only(tmp_path, fb):
    r = make_client(tmp_path, FakeLLM(score=0.5), fb).post("/ask", json={"query": QUERY})
    assert r.status_code == 200
    body = r.json()
    assert body["trust_label"] == "corpus"
    assert body["fallback_sources"] == []
    assert body["citations"]


@pytest.mark.parametrize("fb", [RecordingFallback(fail=True), RecordingFallback(results=())])
def test_incorrect_with_failed_fallback_says_it_cannot_answer(tmp_path, fb):
    r = make_client(tmp_path, FakeLLM(score=0.1), fb)
    r = r.post("/ask", json={"query": QUERY})
    assert r.status_code == 200
    body = r.json()
    assert "cannot answer" in body["answer"].lower()
    assert body["citations"] == []
    assert body["fallback_sources"] == []


def test_plain_rag_mode_never_grades_or_falls_back(tmp_path):
    fb = RecordingFallback()
    body = make_client(tmp_path, FakeLLM(score=0.0), fb, crag=False).post("/ask", json={"query": QUERY}).json()
    assert fb.queries == []
    assert body["trust_label"] == "corpus"
    assert body["citations"]


def test_incorrect_verdict_never_returns_citations_even_if_model_cites(tmp_path):
    class CitingLLM(FakeLLM):
        def generate(self, query, provisions, sources=(), language="en"):
            from legallens.llm import Generation, ProvisionRef

            return Generation(
                answer="x", citations=[ProvisionRef(act=ART_21.act, number="21")]
            )

    body = make_client(tmp_path, CitingLLM(score=0.1), RecordingFallback()).post(
        "/ask", json={"query": QUERY}
    ).json()
    assert body["citations"] == []


def test_rewrite_failure_degrades_like_a_fallback_failure(tmp_path):
    class BrokenRewriteLLM(FakeLLM):
        def rewrite(self, query):
            raise RuntimeError("quota")

    r = make_client(tmp_path, BrokenRewriteLLM(score=0.5), RecordingFallback()).post(
        "/ask", json={"query": QUERY}
    )
    assert r.status_code == 200
    assert r.json()["trust_label"] == "corpus"
