import re

import pytest
from fastapi.testclient import TestClient
from test_ask import ART_21, IPC_302, FakeEmbedder, FakeFallback, FakeLLM

from legallens.corpus import Corpus
from legallens.llm import Generation, ProvisionRef, ScopeDecision
from legallens.main import create_app

HINDI_LIBERTY = "क्या मुझे व्यक्तिगत स्वतंत्रता से वंचित किया जा सकता है?"
HINDI_ANSWER = "अनुच्छेद 21 के अनुसार, कानून की प्रक्रिया के बिना किसी को जीवन या स्वतंत्रता से वंचित नहीं किया जा सकता।"

# Stands in for a multilingual embedding model: Hindi words land on the same
# dimensions as their English equivalents.
HINDI_TO_ENGLISH = {"स्वतंत्रता": "liberty", "व्यक्तिगत": "personal", "वंचित": "deprived"}


class MultilingualFakeEmbedder(FakeEmbedder):
    def embed(self, texts, *, is_query):
        def translate(t):
            for hi, en in HINDI_TO_ENGLISH.items():
                t = t.replace(hi, en)
            return t

        return super().embed([translate(t) for t in texts], is_query=is_query)


class LanguageAwareLLM(FakeLLM):
    """Answers in the language it is asked for, citing the top Provision."""

    def generate(self, query, provisions, sources=(), language="en"):
        top = provisions[0]
        answer = (
            HINDI_ANSWER if language == "hi" else f"Summary of {top.act} {top.number}."
        )
        return Generation(
            answer=answer,
            language=language,
            citations=[ProvisionRef(act=top.act, number=top.number)],
        )


@pytest.fixture
def client(tmp_path):
    corpus = Corpus(tmp_path / "chroma", MultilingualFakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return TestClient(
        create_app(corpus=corpus, llm=LanguageAwareLLM(), fallback=FakeFallback())
    )


def test_hindi_query_retrieves_the_expected_article(client):
    body = client.post("/ask", json={"query": HINDI_LIBERTY}).json()
    top = body["citations"][0]
    assert (top["act"], top["number"]) == ("Constitution of India", "21")


def test_hindi_query_gets_hindi_answer_with_unchanged_english_citation(client):
    body = client.post("/ask", json={"query": HINDI_LIBERTY}).json()
    assert body["answer_language"] == "hi"
    assert re.search(r"[ऀ-ॿ]", body["answer"])
    assert body["citations"][0]["text"] == ART_21.text


def test_english_query_still_gets_english_answer(client):
    body = client.post(
        "/ask", json={"query": "Can I be deprived of personal liberty?"}
    ).json()
    assert body["answer_language"] == "en"
    assert not re.search(r"[ऀ-ॿ]", body["answer"])


def test_mixed_script_query_with_mostly_hindi_is_hindi(client):
    body = client.post(
        "/ask", json={"query": "Article 21 क्या है और स्वतंत्रता का अधिकार क्या है?"}
    ).json()
    assert body["answer_language"] == "hi"


def test_hindi_refusal_reports_hindi(tmp_path):
    class Refusing(LanguageAwareLLM):
        def classify(self, query):
            return ScopeDecision(
                category="personal_advice", reason="मैं सलाह नहीं दे सकता।"
            )

    corpus = Corpus(tmp_path / "chroma", MultilingualFakeEmbedder())
    corpus.add([ART_21])
    c = TestClient(create_app(corpus=corpus, llm=Refusing(), fallback=FakeFallback()))
    body = c.post("/ask", json={"query": "क्या मुझे मुकदमा करना चाहिए?"}).json()
    assert body["response_type"] == "refusal"
    assert body["answer_language"] == "hi"


@pytest.mark.parametrize(
    ("query", "expected"),
    [("", "en"), ("12345 ?", "en"), ("What is Article 21?", "en"), ("अनुच्छेद 21 क्या है", "hi")],
)
def test_detect_language(query, expected):
    from legallens.language import detect_language

    assert detect_language(query) == expected
