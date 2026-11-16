import hashlib
import re

import pytest
from fastapi.testclient import TestClient

from legallens.corpus import Corpus
from legallens.llm import Generation, ProvisionRef
from legallens.main import create_app
from legallens.models import Provision

ART_21 = Provision(
    act="Constitution of India",
    chapter="Part III",
    number="21",
    status="in_force",
    text="No person shall be deprived of his life or personal liberty except according to procedure established by law.",
)
IPC_302 = Provision(
    act="Indian Penal Code",
    chapter="Chapter XVI",
    number="302",
    status="repealed",
    text="Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
)


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder; no model download."""

    dim = 64

    def embed(self, texts: list[str], *, is_query: bool) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in re.findall(r"\w+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
            out.append(v)
        return out


class FakeLLM:
    """Cites the top retrieved Provision, as a well-behaved Gemini would."""

    def __init__(self):
        self.seen: list[Provision] = []

    def generate(self, query, provisions):
        self.seen = provisions
        top = provisions[0]
        return Generation(
            answer=f"Plain-language summary of {top.act} {top.number}.",
            language="en",
            citations=[ProvisionRef(act=top.act, number=top.number)],
        )


class FakeFallback:
    def search(self, query):
        return []


class HallucinatingThenValidLLM:
    """Cites a Provision absent from the Corpus once, then recovers on regeneration."""

    def __init__(self):
        self.calls = 0

    def generate(self, query, provisions):
        self.calls += 1
        if self.calls == 1:
            return Generation(
                answer="Ghost citation answer.",
                language="en",
                citations=[ProvisionRef(act="Indian Penal Code", number="420")],
            )
        top = provisions[0]
        return Generation(
            answer=f"Plain-language summary of {top.act} {top.number}.",
            language="en",
            citations=[ProvisionRef(act=top.act, number=top.number)],
        )


class AlwaysHallucinatingLLM:
    """Cites a Provision absent from the Corpus on every call."""

    def __init__(self):
        self.calls = 0

    def generate(self, query, provisions):
        self.calls += 1
        return Generation(
            answer="Ghost citation answer.",
            language="en",
            citations=[ProvisionRef(act="Indian Penal Code", number="420")],
        )


@pytest.fixture
def client(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return TestClient(create_app(corpus=corpus, llm=FakeLLM(), fallback=FakeFallback()))


def test_query_returns_answer_with_verbatim_citation(client):
    r = client.post("/ask", json={"query": "Can I be deprived of personal liberty?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["answer_language"] == "en"
    assert body["trust_label"] == "corpus"
    assert body["fallback_sources"] == []
    assert len(body["citations"]) >= 1
    c = body["citations"][0]
    assert c["act"] == "Constitution of India"
    assert c["number"] == "21"
    assert c["status"] == "in_force"
    assert c["text"] == ART_21.text


def test_repealed_provision_citation_carries_status(client):
    body = client.post("/ask", json={"query": "punishment for murder death imprisonment"}).json()
    assert body["citations"][0]["status"] == "repealed"


def test_empty_query_is_rejected(client):
    assert client.post("/ask", json={"query": "  "}).status_code == 422


def test_hallucinated_citation_triggers_regeneration(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21])
    llm = HallucinatingThenValidLLM()
    c = TestClient(create_app(corpus=corpus, llm=llm, fallback=FakeFallback()))
    r = c.post("/ask", json={"query": "Can I be deprived of personal liberty?"})
    assert r.status_code == 200
    body = r.json()
    assert llm.calls == 2
    refs = [(cit["act"], cit["number"]) for cit in body["citations"]]
    assert ("Indian Penal Code", "420") not in refs
    assert ("Constitution of India", "21") in refs


def test_hallucinated_citation_after_regeneration_is_blocked(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21])
    llm = AlwaysHallucinatingLLM()
    c = TestClient(create_app(corpus=corpus, llm=llm, fallback=FakeFallback()))
    r = c.post("/ask", json={"query": "Can I be deprived of personal liberty?"})
    assert r.status_code == 200
    body = r.json()
    assert llm.calls == 2
    assert body["citations"] == []
    assert "cannot answer reliably" in body["answer"].lower()


def test_llm_failure_returns_503(tmp_path):
    class BrokenLLM:
        def generate(self, query, provisions):
            raise RuntimeError("quota")

    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21])
    c = TestClient(create_app(corpus=corpus, llm=BrokenLLM(), fallback=FakeFallback()))
    r = c.post("/ask", json={"query": "liberty"})
    assert r.status_code == 503
