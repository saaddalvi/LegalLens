import pytest
from fastapi.testclient import TestClient
from test_ask import ART_21, IPC_302, FakeEmbedder, FakeFallback, FakeLLM
from test_ask_stream import OutOfScopeLLM, parse

from legallens.answer_cache import AnswerCache
from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.models import AskResponse
from legallens.rate_limit import RateLimiter

QUERY = "Can I be deprived of my life or personal liberty?"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class CountingLLM(FakeLLM):
    """Counts scope checks: one per question that reaches the pipeline."""

    def __init__(self, score: float = 1.0):
        super().__init__(score)
        self.questions = 0

    def classify(self, query):
        self.questions += 1
        return super().classify(query)


class CountingOutOfScopeLLM(OutOfScopeLLM):
    def __init__(self):
        super().__init__()
        self.questions = 0

    def classify(self, query):
        self.questions += 1
        return super().classify(query)


def make_client(tmp_path, llm, cache, **kwargs):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    app = create_app(
        corpus=corpus, llm=llm, fallback=FakeFallback(), cache=cache, **kwargs
    )
    return TestClient(app)


def ask(client, query=QUERY):
    r = client.post("/ask", json={"query": query})
    assert r.status_code == 200
    return r.json()


def stream(client, query=QUERY):
    r = client.post("/ask/stream", json={"query": query})
    assert r.status_code == 200
    return parse(r.text)


def test_an_identical_query_is_answered_without_calling_the_llm_again(tmp_path):
    llm = CountingLLM()
    client = make_client(tmp_path, llm, AnswerCache())
    first = ask(client)
    assert llm.questions == 1
    # Spacing and case do not make a different Query.
    assert (
        ask(client, "  can I be deprived   of my LIFE or personal liberty? ") == first
    )
    assert llm.questions == 1


def test_a_different_query_is_not_served_from_the_cache(tmp_path):
    llm = CountingLLM()
    client = make_client(tmp_path, llm, AnswerCache())
    ask(client)
    ask(client, "What is the punishment for murder?")
    assert llm.questions == 2


def test_a_cached_stream_sends_only_the_answer_event_equal_to_ask(tmp_path):
    llm = CountingLLM()
    client = make_client(tmp_path, llm, AnswerCache())
    body = ask(client)
    assert stream(client) == [("answer", body)]
    assert llm.questions == 1


def test_an_answer_found_by_streaming_is_cached_for_ask(tmp_path):
    llm = CountingLLM()
    client = make_client(tmp_path, llm, AnswerCache())
    events = stream(client)
    assert [name for name, _ in events][-1] == "answer"
    assert ask(client) == events[-1][1]
    assert llm.questions == 1


def test_a_cannot_answer_message_is_not_cached(tmp_path):
    # Grader says the Corpus does not answer and the Fallback finds nothing, so
    # the answer is "cannot answer" (Trust label none): the Fallback may work next time.
    llm = CountingLLM(score=0.0)
    client = make_client(tmp_path, llm, AnswerCache())
    assert ask(client)["trust_label"] == "none"
    ask(client)
    assert llm.questions == 2


def test_a_refusal_is_cached(tmp_path):
    llm = CountingOutOfScopeLLM()
    client = make_client(tmp_path, llm, AnswerCache())
    first = ask(client, "What is the US tax code?")
    assert first["response_type"] == "refusal"
    assert ask(client, "What is the US tax code?") == first
    assert llm.questions == 1


def test_an_entry_expires_after_the_ttl(tmp_path):
    clock = Clock()
    llm = CountingLLM()
    client = make_client(tmp_path, llm, AnswerCache(ttl_seconds=60, clock=clock))
    ask(client)
    clock.now += 59
    ask(client)
    assert llm.questions == 1
    clock.now += 2
    ask(client)
    assert llm.questions == 2


def test_the_least_recently_used_entry_is_evicted(tmp_path):
    llm = CountingLLM()
    client = make_client(tmp_path, llm, AnswerCache(max_entries=2))
    ask(client, "first question about liberty")
    ask(client, "second question about murder")
    ask(client, "first question about liberty")  # refreshes the first
    ask(client, "third question about fines")  # evicts the second
    assert llm.questions == 3
    ask(client, "first question about liberty")
    assert llm.questions == 3
    ask(client, "second question about murder")
    assert llm.questions == 4


def test_the_rate_limit_still_applies_to_cached_answers(tmp_path):
    client = make_client(
        tmp_path,
        CountingLLM(),
        AnswerCache(),
        rate_limiter=RateLimiter(per_minute=1, per_day=10),
    )
    assert client.post("/ask", json={"query": QUERY}).status_code == 200
    assert client.post("/ask", json={"query": QUERY}).status_code == 429


def test_no_cache_means_every_question_runs(tmp_path):
    llm = CountingLLM()
    client = make_client(tmp_path, llm, None)
    ask(client)
    ask(client)
    assert llm.questions == 2


def test_a_cache_hit_returns_the_stored_response_unchanged():
    cache = AnswerCache()
    response = AskResponse(
        answer="x",
        answer_language="en",
        trust_label="corpus",
        citations=[],
        fallback_sources=[],
    )
    cache.put("Q", True, response)
    assert cache.get(" q ", True) == response
    assert cache.get("q", False) is None  # plain RAG and CRAG answers differ


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
