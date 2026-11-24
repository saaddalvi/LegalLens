"""The users table, created on a user's first signed-in request and removed by Clerk's
`user.deleted` webhook. These run against a real Postgres with pgvector (see the README)."""

import base64
import json
import os
import time
from datetime import UTC, datetime

import psycopg
import pytest
from conftest import (
    ART_21,
    IPC_302,
    FakeEmbedder,
    FakeFallback,
    FakeLLM,
    FakeVerifier,
    auth_for,
)
from fastapi.testclient import TestClient
from svix.webhooks import Webhook

from legallens.corpus import Corpus
from legallens.db import Database
from legallens.main import create_app
from legallens.migrate import upgrade

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:54329/legallens_test"
)
SECRET = "whsec_" + base64.b64encode(b"test-signing-secret-bytes").decode()


def _connect():
    return psycopg.connect(TEST_DB, autocommit=True, connect_timeout=3)


@pytest.fixture(scope="module")
def pg():
    try:
        with _connect() as conn:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
    except psycopg.OperationalError as exc:
        pytest.skip(f"no test Postgres at TEST_DATABASE_URL ({exc})")
    upgrade(TEST_DB)


@pytest.fixture
def rows(pg):
    with _connect() as conn:
        conn.execute("TRUNCATE users CASCADE")

        def read() -> list[str]:
            return [r[0] for r in conn.execute("SELECT id FROM users ORDER BY id")]

        yield read


@pytest.fixture
def make_client(tmp_path, pg):
    def make(**kw):
        corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
        corpus.add([ART_21, IPC_302])
        return TestClient(
            create_app(
                corpus=corpus,
                llm=FakeLLM(),
                fallback=FakeFallback(),
                verifier=FakeVerifier(),
                database=Database(TEST_DB, pooled=False),
                webhook_secret=SECRET,
                **kw,
            )
        )

    return make


def signed(payload: dict, secret: str = SECRET) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    now = datetime.now(UTC)
    sig = Webhook(secret).sign("msg_1", now, body.decode())
    return body, {
        "svix-id": "msg_1",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": sig,
        "content-type": "application/json",
    }


def test_upgrade_on_an_empty_database_creates_users_and_enables_vector(pg):
    with _connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            )
        }
        extensions = {r[0] for r in conn.execute("SELECT extname FROM pg_extension")}
    assert "users" in tables
    assert "vector" in extensions


def test_first_signed_in_request_creates_one_row_and_later_ones_do_not_duplicate(
    make_client, rows
):
    client = make_client()
    for _ in range(3):
        r = client.post("/ask", json={"query": "liberty?"}, headers=auth_for("user_a"))
        assert r.status_code == 200
    assert rows() == ["user_a"]
    client.post("/ask", json={"query": "liberty?"}, headers=auth_for("user_b"))
    assert rows() == ["user_a", "user_b"]


def test_a_refused_token_creates_no_row(make_client, rows):
    r = make_client().post("/ask", json={"query": "x"})
    assert r.status_code == 401
    assert rows() == []


@pytest.mark.parametrize(
    "headers", [None, {"svix-id": "x"}, "tampered", "wrong-secret"]
)
def test_webhook_with_a_bad_or_missing_signature_is_400_and_changes_nothing(
    make_client, rows, headers
):
    client = make_client()
    client.post("/ask", json={"query": "q"}, headers=auth_for("user_a"))
    payload = {"type": "user.deleted", "data": {"id": "user_a"}}
    body, good = signed(payload)
    if headers == "tampered":
        body, headers = body.replace(b"user_a", b"user_b"), good
    elif headers == "wrong-secret":
        body, headers = signed(
            payload, "whsec_" + base64.b64encode(b"another-secret-bytes!").decode()
        )
    r = client.post("/webhooks/clerk", content=body, headers=headers or {})
    assert r.status_code == 400
    assert rows() == ["user_a"]


def test_valid_user_deleted_removes_the_row_and_a_new_request_recreates_it(
    make_client, rows
):
    client = make_client()
    client.post("/ask", json={"query": "q"}, headers=auth_for("user_a"))
    client.post("/ask", json={"query": "q"}, headers=auth_for("user_b"))
    body, headers = signed({"type": "user.deleted", "data": {"id": "user_a"}})
    assert (
        client.post("/webhooks/clerk", content=body, headers=headers).status_code == 200
    )
    assert rows() == ["user_b"]


def test_other_webhook_events_are_accepted_and_ignored(make_client, rows):
    client = make_client()
    client.post("/ask", json={"query": "q"}, headers=auth_for("user_a"))
    body, headers = signed({"type": "user.updated", "data": {"id": "user_a"}})
    assert (
        client.post("/webhooks/clerk", content=body, headers=headers).status_code == 200
    )
    assert rows() == ["user_a"]


def test_ask_works_with_no_database(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    client = TestClient(
        create_app(
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
            verifier=FakeVerifier(),
        )
    )
    r = client.post("/ask", json={"query": "liberty?"}, headers=auth_for("u"))
    assert r.status_code == 200
    body, headers = signed({"type": "user.deleted", "data": {"id": "u"}})
    assert (
        client.post("/webhooks/clerk", content=body, headers=headers).status_code == 503
    )


def test_ask_still_works_when_the_database_is_down(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    client = TestClient(
        create_app(
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
            verifier=FakeVerifier(),
            database=Database(
                "postgresql://x:y@127.0.0.1:1/none?connect_timeout=1", pooled=False
            ),
        )
    )
    r = client.post("/ask", json={"query": "liberty?"}, headers=auth_for("u"))
    assert r.status_code == 200
