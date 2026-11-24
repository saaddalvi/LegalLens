"""Fakes shared across test files: a deterministic embedder, LLMs that behave or misbehave
in one way each, and Fallbacks that return, record or fail."""

import hashlib
import json
import os
import re

import psycopg
import pytest
from fastapi.testclient import TestClient

from legallens.answering import Answerer
from legallens.auth import InvalidToken
from legallens.corpus import Corpus
from legallens.llm import Generation, ProvisionRef, ScopeDecision
from legallens.migrate import upgrade
from legallens.models import FallbackSource, Provision

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

TOKEN_PREFIX = "test-token-"


def auth_for(user_id: str) -> dict[str, str]:
    """The Authorization header FakeVerifier accepts for `user_id`."""
    return {"Authorization": f"Bearer {TOKEN_PREFIX}{user_id}"}


AUTH = auth_for("user_test")


class FakeVerifier:
    """Accepts `test-token-<user id>` and nothing else, standing in for Clerk."""

    def verify(self, token: str) -> str:
        if not token.startswith(TOKEN_PREFIX):
            raise InvalidToken("not a test token")
        return token[len(TOKEN_PREFIX) :]


def signed_in(app, **kw):
    """A TestClient that sends AUTH on every request."""
    return TestClient(app, headers=AUTH, **kw)


QUERY = "Can I be deprived of personal liberty?"
HINDI_QUERY = "क्या मुझे जीवन और स्वतंत्रता का अधिकार है?"
WEB = FallbackSource(
    title="Explainer", url="https://example.org/x", snippet="Web snippet."
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


class GradingStub:
    """Grader and rewriter defaults: retrieval is judged fully relevant."""

    score = 1.0

    def classify(self, query):
        return ScopeDecision(category="in_scope")

    def grade(self, query, provisions):
        return self.score

    def rewrite(self, query):
        return query


class FakeLLM(GradingStub):
    """Cites the top retrieved Provision, as a well-behaved Gemini would."""

    def __init__(self, score: float = 1.0):
        self.score = score
        self.seen: list[Provision] = []
        self.sources_seen = ()

    def generate(self, query, provisions, sources=(), language="en"):
        self.seen = provisions
        self.sources_seen = sources
        if not provisions:
            return Generation(answer="Web-based summary.", citations=[])
        top = provisions[0]
        return Generation(
            answer=f"Plain-language summary of {top.act} {top.number}.",
            citations=[ProvisionRef(act=top.act, number=top.number)],
        )


class FakeFallback:
    def search(self, query):
        return []


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


class HallucinatingThenValidLLM(GradingStub):
    """Cites a Provision absent from the Corpus once, then recovers on regeneration."""

    def __init__(self):
        self.calls = 0

    def generate(self, query, provisions, sources=(), language="en"):
        self.calls += 1
        if self.calls == 1:
            return Generation(
                answer="Ghost citation answer.",
                citations=[ProvisionRef(act="Indian Penal Code", number="420")],
            )
        top = provisions[0]
        return Generation(
            answer=f"Plain-language summary of {top.act} {top.number}.",
            citations=[ProvisionRef(act=top.act, number=top.number)],
        )


class AlwaysHallucinatingLLM(GradingStub):
    """Cites a Provision absent from the Corpus on every call."""

    def __init__(self):
        self.calls = 0

    def generate(self, query, provisions, sources=(), language="en"):
        self.calls += 1
        return Generation(
            answer="Ghost citation answer.",
            citations=[ProvisionRef(act="Indian Penal Code", number="420")],
        )


class OutOfScopeLLM(FakeLLM):
    def classify(self, query):
        return ScopeDecision(category="personal_advice", reason="Not for me.")


class BrokenLLM(FakeLLM):
    """Fails in the Grader."""

    def grade(self, query, provisions):
        raise RuntimeError("gemini down")


class GenerationFailsLLM(FakeLLM):
    def generate(self, *args, **kwargs):
        raise RuntimeError("gemini 503")


class ScopeFailsLLM(FakeLLM):
    def classify(self, query):
        raise RuntimeError("gemini 503")


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """The (event, data) pairs of a Server-Sent Events body; keepalive comments are skipped."""
    events = []
    for frame in text.strip().split("\n\n"):
        if not frame or frame.startswith(":"):
            continue
        lines = dict(line.split(": ", 1) for line in frame.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


@pytest.fixture
def make_corpus(tmp_path):
    """A real Corpus on tmp_path, holding the given Provisions (default: Art. 21 and IPC 302)."""

    def make(provisions=(ART_21, IPC_302), embedder=None) -> Corpus:
        corpus = Corpus(tmp_path / "chroma", embedder or FakeEmbedder())
        corpus.add(list(provisions))
        return corpus

    return make


@pytest.fixture
def make_answerer(make_corpus):
    """An Answerer over a real Corpus; fakes stand in for the LLM and the Fallback."""

    def make(llm, fallback=None, *, provisions=(ART_21, IPC_302), embedder=None, **kw):
        return Answerer(
            corpus=make_corpus(provisions, embedder),
            llm=llm,
            fallback=fallback or RecordingFallback(),
            **kw,
        )

    return make


TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:54329/legallens_test"
)


def connect():
    return psycopg.connect(TEST_DB, autocommit=True, connect_timeout=3)


@pytest.fixture(scope="module")
def pg():
    """A migrated, empty test Postgres, or a skip when there is none. Drops `public`."""
    try:
        with connect() as conn:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
    except psycopg.OperationalError as exc:
        pytest.skip(f"no test Postgres at TEST_DATABASE_URL ({exc})")
    upgrade(TEST_DB)
