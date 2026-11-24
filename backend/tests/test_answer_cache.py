import pytest
from conftest import ART_21, IPC_302, QUERY, FakeEmbedder, FakeFallback, FakeLLM
from fastapi.testclient import TestClient

from legallens.answer_cache import AnswerCache
from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.models import AskResponse
from legallens.rate_limit import RateLimiter

# How the Answerer uses the cache (hits, misses, what is kept) is tested in test_answering.py.


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def response(text="x", trust="corpus") -> AskResponse:
    return AskResponse(
        answer=text,
        answer_language="en",
        trust_label=trust,
        citations=[],
        fallback_sources=[],
    )


def test_a_hit_returns_the_stored_response_unchanged_ignoring_spacing_and_case():
    cache = AnswerCache()
    cache.put("Q  one", response())
    assert cache.get(" q ONE ") == response()
    assert cache.get("another") is None


def test_an_entry_expires_after_the_ttl():
    clock = Clock()
    cache = AnswerCache(ttl_seconds=60, clock=clock)
    cache.put("q", response())
    clock.now += 59
    assert cache.get("q") is not None
    clock.now += 2
    assert cache.get("q") is None


def test_the_least_recently_used_entry_is_evicted():
    cache = AnswerCache(max_entries=2)
    cache.put("first", response("1"))
    cache.put("second", response("2"))
    cache.get("first")  # refreshes the first
    cache.put("third", response("3"))  # evicts the second
    assert cache.get("first") and cache.get("third")
    assert cache.get("second") is None


def test_a_cannot_answer_message_is_not_stored():
    cache = AnswerCache()
    cache.put("q", response("cannot answer", trust="none"))
    assert cache.get("q") is None


def test_a_refusal_is_stored():
    cache = AnswerCache()
    refusal = response("no", trust="none").model_copy(
        update={"response_type": "refusal"}
    )
    cache.put("q", refusal)
    assert cache.get("q") == refusal


def test_the_rate_limit_still_applies_to_cached_answers(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    client = TestClient(
        create_app(
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
            cache=AnswerCache(),
            rate_limiter=RateLimiter(per_minute=1, per_day=10),
        )
    )
    assert client.post("/ask", json={"query": QUERY}).status_code == 200
    assert client.post("/ask", json={"query": QUERY}).status_code == 429


@pytest.mark.parametrize(
    ("size", "enabled"), [("500", True), ("0", False)], ids=["on", "zero-disables"]
)
def test_from_env(monkeypatch, size, enabled):
    monkeypatch.setenv("ANSWER_CACHE_SIZE", size)
    monkeypatch.setenv("ANSWER_CACHE_TTL_SECONDS", "120")
    cache = AnswerCache.from_env()
    assert (cache is not None) == enabled
    if cache:
        assert cache.ttl_seconds == 120
