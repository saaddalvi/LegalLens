import pytest
from fastapi.testclient import TestClient
from test_ask import ART_21, IPC_302, FakeEmbedder, FakeFallback, FakeLLM

from legallens import main
from legallens.corpus import Corpus
from legallens.main import create_app


class RecordingEmbedder(FakeEmbedder):
    def __init__(self):
        self.query_embeds = 0

    def embed(self, texts, *, is_query):
        self.query_embeds += is_query
        return super().embed(texts, is_query=is_query)


@pytest.fixture(autouse=True)
def fake_embedder_and_clean_env(monkeypatch):
    """The default Corpus would download a 1.1 GB model; use the fake embedder instead."""
    monkeypatch.setattr(main, "LocalEmbedder", FakeEmbedder)
    for name in ("REQUIRE_CORPUS", "WARM_START"):
        monkeypatch.delenv(name, raising=False)


def built_store(path):
    Corpus(path, FakeEmbedder()).add([ART_21, IPC_302])


def test_ready_reports_how_many_provisions_are_served(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    client = TestClient(
        create_app(corpus=corpus, llm=FakeLLM(), fallback=FakeFallback())
    )
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "provisions": 2, "fixture": False}


def test_ready_says_when_only_the_sample_fixture_is_served(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "empty"))
    client = TestClient(create_app(llm=FakeLLM(), fallback=FakeFallback()))
    body = client.get("/ready").json()
    assert body["fixture"] is True
    assert body["provisions"] == 3


def test_the_fixture_is_still_reported_on_the_next_boot(tmp_path, monkeypatch):
    # The fixture is persisted when first seeded, so a later boot finds a non-empty store.
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    TestClient(create_app(llm=FakeLLM(), fallback=FakeFallback())).get("/ready")
    later = TestClient(create_app(llm=FakeLLM(), fallback=FakeFallback()))
    assert later.get("/ready").json()["fixture"] is True


def test_require_corpus_refuses_to_seed_the_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("REQUIRE_CORPUS", "1")
    client = TestClient(create_app(llm=FakeLLM(), fallback=FakeFallback()))
    assert client.get("/ready").status_code == 503
    # Questions get the same friendly 503 as any unavailable service, never a 500.
    assert client.post("/ask", json={"query": "Is liberty a right?"}).status_code == 503
    assert (
        client.post("/ask/stream", json={"query": "Is liberty a right?"}).status_code
        == 503
    )


def test_require_corpus_accepts_a_built_store(tmp_path, monkeypatch):
    built_store(tmp_path / "chroma")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("REQUIRE_CORPUS", "1")
    client = TestClient(create_app(llm=FakeLLM(), fallback=FakeFallback()))
    assert client.get("/ready").json() == {
        "status": "ready",
        "provisions": 2,
        "fixture": False,
    }


def test_health_stays_a_plain_liveness_check_even_when_not_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("REQUIRE_CORPUS", "1")
    client = TestClient(create_app(llm=FakeLLM(), fallback=FakeFallback()))
    assert client.get("/health").json() == {"status": "ok"}


def test_warm_start_loads_the_embedder_before_the_first_question(tmp_path, monkeypatch):
    monkeypatch.setenv("WARM_START", "1")
    embedder = RecordingEmbedder()
    corpus = Corpus(tmp_path / "chroma", embedder)
    corpus.add([ART_21, IPC_302])
    app = create_app(corpus=corpus, llm=FakeLLM(), fallback=FakeFallback())
    assert embedder.query_embeds == 0
    with TestClient(app):  # entering runs the app's startup
        assert embedder.query_embeds == 1


def test_without_warm_start_nothing_loads_until_the_first_question(tmp_path):
    embedder = RecordingEmbedder()
    corpus = Corpus(tmp_path / "chroma", embedder)
    corpus.add([ART_21, IPC_302])
    app = create_app(corpus=corpus, llm=FakeLLM(), fallback=FakeFallback())
    with TestClient(app):
        assert embedder.query_embeds == 0


def test_a_failed_warm_start_leaves_the_server_up_and_not_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("REQUIRE_CORPUS", "1")
    monkeypatch.setenv("WARM_START", "1")
    app = create_app(llm=FakeLLM(), fallback=FakeFallback())
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
