"""The migration to several Contract conversations per Contract, run on rows saved the old way:
one conversation per Contract, with the Contract brief as its first message.

Needs a Postgres with pgvector (see the README) and skips without one. Drops `public`."""

import json
from datetime import UTC, datetime

import psycopg
import pytest
from conftest import TEST_DB, FakeEmbedder, FakeVerifier, auth_for, connect
from fastapi.testclient import TestClient

from legallens.corpus import Corpus
from legallens.db import Database
from legallens.main import create_app
from legallens.migrate import upgrade

WITH_QUERIES = "11111111-1111-1111-1111-111111111111"
BRIEF_ONLY = "22222222-2222-2222-2222-222222222222"
BEFORE_BRIEFS = "33333333-3333-3333-3333-333333333333"

LONG_QUERY = (
    "What happens to my security deposit if I leave the flat before the year ends?"
)
BRIEF = {
    "parties": ["Asha Rao (Landlord)", "Ravi Kumar (Tenant)"],
    "purpose": "Rent of a flat.",
    "key_terms": [{"label": "Rent", "value": "Rs. 20,000 a month", "clause": "2"}],
    "obligations": [],
    "flagged_clauses": [],
}


def at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 3, day, hour, tzinfo=UTC)


def answer(text: str) -> dict:
    return {
        "response_type": "answer",
        "answer": text,
        "answer_language": "en",
        "trust_label": "none",
        "citations": [],
        "fallback_sources": [],
    }


def seed(conn) -> None:
    """Rows as the schema before the migration (0004) stored them."""
    conn.execute("INSERT INTO users (id) VALUES ('user_a')")
    for cid in (WITH_QUERIES, BRIEF_ONLY, BEFORE_BRIEFS):
        conn.execute(
            "INSERT INTO contracts (id, user_id, title, text, page_count) "
            "VALUES (%s, 'user_a', 'Rent agreement', 'text', 1)",
            (cid,),
        )

    def message(cid, role, payload, created):
        conn.execute(
            "INSERT INTO contract_messages (contract_id, role, payload, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (cid, role, json.dumps(payload), created),
        )

    def query(cid, turn, text, created):
        message(cid, "user", {"type": "query", "turn": turn, "text": text}, created)

    def answered(cid, turn, text, created):
        payload = {"type": "answer", "turn": turn, "response": answer(text)}
        message(cid, "assistant", payload, created)

    brief = {"type": "brief", **BRIEF}
    message(WITH_QUERIES, "assistant", brief, at(1))
    message(BRIEF_ONLY, "assistant", brief, at(1))
    # Two turns whose messages are interleaved, as two Queries saved at once could be.
    query(WITH_QUERIES, "t1", LONG_QUERY, at(2))
    query(WITH_QUERIES, "t2", "And the rent?", at(3))
    answered(WITH_QUERIES, "t1", "First answer.", at(4))
    answered(WITH_QUERIES, "t2", "Second answer.", at(5))
    # A Contract uploaded before briefs existed has only its Queries.
    query(BEFORE_BRIEFS, "t3", "What is the notice period?", at(6))
    answered(BEFORE_BRIEFS, "t3", "Two months.", at(6, 13))


@pytest.fixture(scope="module")
def migrated():
    """A test Postgres seeded at revision 0004, then upgraded to head."""
    try:
        with connect() as conn:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
    except psycopg.OperationalError as exc:
        pytest.skip(f"no test Postgres at TEST_DATABASE_URL ({exc})")
    upgrade(TEST_DB, "0004")
    with connect() as conn:
        seed(conn)
    upgrade(TEST_DB)


@pytest.fixture
def client(migrated, tmp_path):
    app = create_app(
        corpus=Corpus(tmp_path / "chroma", FakeEmbedder()),
        verifier=FakeVerifier(),
        database=Database(TEST_DB, pooled=False),
    )
    return TestClient(app, headers=auth_for("user_a"))


def scalar(sql: str, *args):
    with connect() as conn:
        return conn.execute(sql, args).fetchone()[0]


def test_saved_queries_become_one_conversation_titled_with_the_first(client):
    [conversation] = client.get(f"/contracts/{WITH_QUERIES}").json()["conversations"]
    assert conversation["title"] == (
        "What happens to my security deposit if I leave the flat…"
    )
    # Dated from its first and last messages, not from the brief or the migration.
    assert datetime.fromisoformat(conversation["created_at"]) == at(2)
    assert datetime.fromisoformat(conversation["updated_at"]) == at(5)
    turns = client.get(
        f"/contracts/{WITH_QUERIES}/conversations/{conversation['id']}"
    ).json()
    assert [(t["query"], t["response"]["answer"]) for t in turns] == [
        (LONG_QUERY, "First answer."),
        ("And the rent?", "Second answer."),
    ]


def test_each_contract_gets_its_own_conversation(client):
    [conversation] = client.get(f"/contracts/{BEFORE_BRIEFS}").json()["conversations"]
    assert conversation["title"] == "What is the notice period?"
    turns = client.get(
        f"/contracts/{BEFORE_BRIEFS}/conversations/{conversation['id']}"
    ).json()
    assert [t["query"] for t in turns] == ["What is the notice period?"]


def test_a_contract_with_no_queries_gets_no_conversation(client):
    assert client.get(f"/contracts/{BRIEF_ONLY}").json()["conversations"] == []


def test_the_brief_moves_to_the_contract(client):
    for cid in (WITH_QUERIES, BRIEF_ONLY):
        assert client.get(f"/contracts/{cid}").json()["brief"] == BRIEF
    assert client.get(f"/contracts/{BEFORE_BRIEFS}").json()["brief"] is None
    assert (
        scalar(
            "SELECT count(*) FROM contract_messages WHERE payload->>'type' = 'brief'"
        )
        == 0
    )


def test_every_message_must_belong_to_a_conversation(client):
    assert (
        scalar(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = "
            "'contract_messages' AND column_name = 'conversation_id'"
        )
        == "NO"
    )
    assert scalar("SELECT count(*) FROM contract_messages") == 6
