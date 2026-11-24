"""Sign-in at the HTTP edge: /ask and /ask/stream need a verified Clerk user; reading the law
and the health probes do not. The token verifier is injected, so these tests use a fake."""

import pytest
from conftest import (
    ART_21,
    AUTH,
    IPC_302,
    FakeEmbedder,
    FakeFallback,
    FakeLLM,
    FakeVerifier,
    auth_for,
)
from fastapi.testclient import TestClient

from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.rate_limit import RateLimiter

QUERY = "Can I be deprived of my life or personal liberty?"


class CountingLLM(FakeLLM):
    def __init__(self):
        super().__init__()
        self.classified = 0

    def classify(self, query):
        self.classified += 1
        return super().classify(query)


@pytest.fixture
def make_client(tmp_path):
    def make(llm=None, **kw):
        kw.setdefault("verifier", FakeVerifier())
        corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
        corpus.add([ART_21, IPC_302])
        return TestClient(
            create_app(
                corpus=corpus,
                llm=llm or FakeLLM(),
                fallback=FakeFallback(),
                **kw,
            )
        )

    return make


@pytest.mark.parametrize("path", ["/ask", "/ask/stream"])
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer garbage"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "Bearer "},
    ],
    ids=["no-token", "invalid-token", "wrong-scheme", "empty-token"],
)
def test_asking_without_a_valid_token_is_401_before_any_work(
    make_client, path, headers
):
    llm = CountingLLM()
    r = make_client(llm).post(path, json={"query": QUERY}, headers=headers)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert not r.headers["content-type"].startswith("text/event-stream")
    assert llm.classified == 0


@pytest.mark.parametrize("path", ["/ask", "/ask/stream"])
def test_asking_with_a_valid_token_works(make_client, path):
    r = make_client().post(path, json={"query": QUERY}, headers=AUTH)
    assert r.status_code == 200


def test_an_expired_token_is_401(make_client):
    class Expired:
        def verify(self, token):
            from legallens.auth import InvalidToken

            raise InvalidToken("expired")

    r = make_client(verifier=Expired()).post(
        "/ask", json={"query": QUERY}, headers=AUTH
    )
    assert r.status_code == 401


def test_without_a_configured_verifier_nothing_gated_is_served(make_client):
    r = make_client(verifier=None).post("/ask", json={"query": QUERY}, headers=AUTH)
    assert r.status_code == 401


def test_the_unauthenticated_endpoints_need_no_token(make_client):
    client = make_client()
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/acts").status_code == 200
    assert client.get("/acts/Indian Penal Code").status_code == 200
    assert client.get("/provision/Indian Penal Code/302").status_code == 200


def test_rate_limits_count_each_user_separately_from_one_address(make_client):
    client = make_client(rate_limiter=RateLimiter(per_minute=1, per_day=10))
    ask = lambda who: client.post("/ask", json={"query": QUERY}, headers=auth_for(who))
    assert ask("alice").status_code == 200
    assert ask("alice").status_code == 429
    assert ask("bob").status_code == 200  # same address, another user


def test_a_user_is_counted_across_addresses(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21])
    app = create_app(
        corpus=corpus,
        llm=FakeLLM(),
        fallback=FakeFallback(),
        verifier=FakeVerifier(),
        rate_limiter=RateLimiter(per_minute=1, per_day=10),
    )
    home = TestClient(app, client=("203.0.113.1", 1), headers=AUTH)
    cafe = TestClient(app, client=("203.0.113.2", 1), headers=AUTH)
    assert home.post("/ask", json={"query": QUERY}).status_code == 200
    assert cafe.post("/ask", json={"query": QUERY}).status_code == 429


def test_an_unauthenticated_request_does_not_use_up_anyones_allowance(make_client):
    client = make_client(rate_limiter=RateLimiter(per_minute=1, per_day=10))
    assert client.post("/ask", json={"query": QUERY}).status_code == 401
    assert client.post("/ask", json={"query": QUERY}, headers=AUTH).status_code == 200


def test_a_refused_token_is_logged_with_its_reason_but_not_the_token(
    make_client, caplog
):
    make_client().post(
        "/ask",
        json={"query": QUERY},
        headers={"Authorization": "Bearer secret-garbage"},
    )
    text = caplog.text
    assert "token refused: not a test token" in text
    assert "secret-garbage" not in text
