import pytest
from conftest import (
    ART_21,
    IPC_302,
    FakeEmbedder,
    FakeFallback,
    FakeLLM,
    FakeVerifier,
    auth_for,
    signed_in,
)
from fastapi.testclient import TestClient

from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.rate_limit import RateLimiter

QUERY = "Can I be deprived of my life or personal liberty?"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_app(tmp_path, limiter):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return create_app(
        verifier=FakeVerifier(),
        corpus=corpus,
        llm=FakeLLM(),
        fallback=FakeFallback(),
        rate_limiter=limiter,
    )


def ask(client, path="/ask"):
    return client.post(path, json={"query": QUERY})


@pytest.mark.parametrize("path", ["/ask", "/ask/stream"])
def test_requests_beyond_the_limit_get_429_with_retry_after(tmp_path, path):
    client = signed_in(make_app(tmp_path, RateLimiter(per_minute=2, per_day=10)))
    assert ask(client, path).status_code == 200
    assert ask(client, path).status_code == 200
    r = ask(client, path)
    assert r.status_code == 429  # a plain HTTP response, not an SSE event
    assert not r.headers["content-type"].startswith("text/event-stream")
    assert int(r.headers["retry-after"]) >= 1
    assert "too many" in r.json()["detail"].lower()


def test_both_endpoints_share_one_allowance(tmp_path):
    client = signed_in(make_app(tmp_path, RateLimiter(per_minute=2, per_day=10)))
    assert ask(client, "/ask").status_code == 200
    assert ask(client, "/ask/stream").status_code == 200
    assert ask(client, "/ask").status_code == 429


def test_each_user_is_counted_separately(tmp_path):
    app = make_app(tmp_path, RateLimiter(per_minute=1, per_day=10))
    alice = TestClient(app, headers=auth_for("alice"))
    bob = TestClient(app, headers=auth_for("bob"))
    assert ask(alice).status_code == 200
    assert ask(alice).status_code == 429
    assert ask(bob).status_code == 200


def test_health_is_not_limited(tmp_path):
    client = signed_in(make_app(tmp_path, RateLimiter(per_minute=1, per_day=1)))
    assert ask(client).status_code == 200
    assert ask(client).status_code == 429
    assert client.get("/health").status_code == 200


def test_allowance_returns_after_the_minute(tmp_path):
    clock = Clock()
    client = signed_in(
        make_app(tmp_path, RateLimiter(per_minute=1, per_day=10, clock=clock))
    )
    assert ask(client).status_code == 200
    r = ask(client)
    assert r.status_code == 429
    assert r.headers["retry-after"] == "60"
    clock.now += 61
    assert ask(client).status_code == 200


def test_daily_limit_applies_even_when_the_minute_limit_does_not(tmp_path):
    clock = Clock()
    client = signed_in(
        make_app(tmp_path, RateLimiter(per_minute=5, per_day=2, clock=clock))
    )
    assert ask(client).status_code == 200
    clock.now += 120
    assert ask(client).status_code == 200
    clock.now += 120
    r = ask(client)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) > 3600  # the day, not the minute
    clock.now += 86400
    assert ask(client).status_code == 200


def test_rejected_requests_do_not_extend_the_wait(tmp_path):
    clock = Clock()
    limiter = RateLimiter(per_minute=1, per_day=10, clock=clock)
    assert limiter.check("a") is None
    clock.now += 30
    assert limiter.check("a") == 30
    clock.now += 31  # 61s after the one allowed request
    assert limiter.check("a") is None


def test_no_limiter_means_no_limit(tmp_path):
    client = signed_in(make_app(tmp_path, None))
    assert all(ask(client).status_code == 200 for _ in range(10))


def test_from_env_reads_limits_and_zero_disables(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.setenv("RATE_LIMIT_PER_DAY", "7")
    limiter = RateLimiter.from_env()
    assert (limiter.per_minute, limiter.per_day) == (3, 7)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_DAY", "0")
    assert RateLimiter.from_env() is None
