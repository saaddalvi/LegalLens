import pytest
from fastapi.testclient import TestClient
from test_ask import ART_21, IPC_302, FakeEmbedder, FakeFallback, FakeLLM

from legallens.corpus import Corpus
from legallens.llm import ScopeDecision
from legallens.main import create_app


class ScopedLLM(FakeLLM):
    def __init__(self, decision: ScopeDecision):
        super().__init__()
        self.decision = decision
        self.generated = False

    def classify(self, query):
        return self.decision

    def generate(self, query, provisions, sources=(), language="en"):
        self.generated = True
        return super().generate(query, provisions, sources, language)


def client(tmp_path, llm):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return TestClient(create_app(corpus=corpus, llm=llm, fallback=FakeFallback()))


def test_non_indian_law_query_is_refused_with_reason_and_reformulation(tmp_path):
    decision = ScopeDecision(
        category="not_indian_law",
        reason="This question is about US law, which LegalLens does not cover.",
        suggested_reformulation="Ask what Indian law says about the same situation.",
    )
    fake = ScopedLLM(decision)
    body = client(tmp_path, fake).post("/ask", json={"query": "What is the US tax code?"}).json()
    assert body["response_type"] == "refusal"
    assert body["refusal_reason"] == decision.reason
    assert body["suggested_reformulation"] == decision.suggested_reformulation
    assert body["citations"] == []
    assert not fake.generated


@pytest.mark.parametrize("query", ["Should I sue my landlord?", "Should I sign this contract?"])
def test_personal_advice_query_is_refused_without_recommendation(tmp_path, query):
    decision = ScopeDecision(
        category="personal_advice",
        reason="LegalLens explains the law but cannot advise whether you should sue or sign.",
        suggested_reformulation="What does Indian law say about recovering a rent deposit?",
    )
    fake = ScopedLLM(decision)
    body = client(tmp_path, fake).post("/ask", json={"query": query}).json()
    assert body["response_type"] == "refusal"
    assert body["refusal_reason"]
    assert body["suggested_reformulation"]
    assert not fake.generated


def test_in_scope_query_is_not_refused(tmp_path):
    fake = ScopedLLM(ScopeDecision(category="in_scope"))
    body = client(tmp_path, fake).post(
        "/ask", json={"query": "Can I be deprived of personal liberty?"}
    ).json()
    assert body["response_type"] == "answer"
    assert body["refusal_reason"] is None
    assert body["citations"]
    assert fake.generated


def test_refusal_always_suggests_a_reformulation_and_reason(tmp_path):
    fake = ScopedLLM(ScopeDecision(category="not_indian_law"))
    body = client(tmp_path, fake).post("/ask", json={"query": "Best pizza in Rome?"}).json()
    assert body["response_type"] == "refusal"
    assert body["refusal_reason"]
    assert body["suggested_reformulation"]
