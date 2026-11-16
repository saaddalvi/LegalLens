import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ask import FakeEmbedder, FakeFallback, FakeLLM

from legallens.build_corpus import build
from legallens.corpus import Corpus
from legallens.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"
CODES = json.loads((FIXTURES / "criminal_codes_raw.json").read_text())
MAPPINGS = json.loads((FIXTURES / "criminal_code_mappings.json").read_text())[
    "mappings"
]
CONSTITUTION = json.loads((FIXTURES / "constitution_raw.json").read_text())


@pytest.fixture
def served(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    build(corpus, CONSTITUTION, patches=[], criminal_codes=CODES, mappings=MAPPINGS)
    llm = FakeLLM()
    client = TestClient(create_app(corpus=corpus, llm=llm, fallback=FakeFallback()))
    return client, llm


def refs(body):
    return [(c["act"], c["number"]) for c in body["citations"]]


def test_query_citing_old_ipc_section_surfaces_the_bns_superseding_provision(served):
    client, llm = served
    body = client.post("/ask", json={"query": "What is IPC 302?"}).json()
    first = body["citations"][0]
    assert (first["act"], first["number"], first["status"]) == (
        "Indian Penal Code",
        "302",
        "repealed",
    )
    assert first["superseded_by"] == "Bharatiya Nyaya Sanhita 103"
    assert ("Bharatiya Nyaya Sanhita", "103") in refs(body)
    assert ("Bharatiya Nyaya Sanhita", "103") in [(p.act, p.number) for p in llm.seen]


@pytest.mark.parametrize(
    "query", ["section 420 of the IPC", "Section 498A IPC", "IPC section 376"]
)
def test_old_section_reference_phrasings_find_the_section(served, query):
    client, _ = served
    body = client.post("/ask", json={"query": query}).json()
    assert body["citations"][0]["act"] == "Indian Penal Code"
    assert body["citations"][0]["superseded_by"]


def test_old_crpc_reference_points_to_bnss(served):
    client, _ = served
    body = client.post("/ask", json={"query": "What does CrPC 154 say?"}).json()
    assert (
        body["citations"][0]["superseded_by"]
        == "Bharatiya Nagarik Suraksha Sanhita 173"
    )


def test_plain_words_query_cites_the_in_force_provision_with_old_equivalent(served):
    client, _ = served
    body = client.post(
        "/ask", json={"query": "punishment for murder death imprisonment for life fine"}
    ).json()
    first = body["citations"][0]
    assert (first["act"], first["number"], first["status"]) == (
        "Bharatiya Nyaya Sanhita",
        "103",
        "in_force",
    )
    assert first["supersedes"] == "Indian Penal Code 302"
    assert first["superseded_by"] is None


def test_citation_text_stays_verbatim_for_superseding_provision(served):
    client, _ = served
    body = client.post("/ask", json={"query": "What is IPC 302?"}).json()
    bns = next(c for c in body["citations"] if c["number"] == "103")
    assert bns["text"] == CODES["bns"][0]["text"]
