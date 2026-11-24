"""Deleting a Contract and the per-user daily caps, through the HTTP endpoints.

These need a Postgres with pgvector (see the README) and skip without one."""

import base64
import json
import time
from datetime import UTC, datetime, timedelta

import pytest
from conftest import (
    ART_21,
    IPC_302,
    TEST_DB,
    FakeEmbedder,
    FakeVerifier,
    RecordingFallback,
    auth_for,
    connect,
    parse_sse,
)
from fastapi.testclient import TestClient
from svix.webhooks import Webhook
from test_contract_conversation import ASK, ConversationLLM
from test_contracts import RENT, Embedder1024

from legallens.corpus import Corpus
from legallens.db import Database
from legallens.main import create_app
from legallens.rate_limit import DailyCaps

SECRET = "whsec_" + base64.b64encode(b"test-signing-secret-bytes").decode()
ID_NEVER = "00000000-0000-0000-0000-000000000000"
TABLES = ["users", "contracts", "clauses", "contract_messages", "usage"]


class Clock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


NOON = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)


@pytest.fixture
def make_client(tmp_path, pg):
    with connect() as conn:
        conn.execute("TRUNCATE users CASCADE")

    def make(user="user_a", caps=None, llm=None):
        corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
        corpus.add([ART_21, IPC_302])
        app = create_app(
            corpus=corpus,
            llm=llm or ConversationLLM(),
            fallback=RecordingFallback(results=[]),
            verifier=FakeVerifier(),
            database=Database(TEST_DB, pooled=False),
            embedder=Embedder1024(),
            daily_caps=caps,
            webhook_secret=SECRET,
        )
        return TestClient(app, headers=auth_for(user))

    return make


def count(table: str) -> int:
    with connect() as conn:
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def upload_raw(client, text=RENT):
    return client.post("/contracts/stream", data={"text": text})


def upload(client, text=RENT) -> str:
    events = parse_sse(upload_raw(client, text).text)
    assert events[-1][0] == "answer", events
    return events[-1][1]["id"]


def ask_raw(client, cid):
    return client.post(f"/contracts/{cid}/ask/stream", json={"query": ASK})


# --- deletion ------------------------------------------------------------------------------


def test_deleting_a_contract_removes_its_rows_from_every_table(make_client):
    c = make_client()
    cid = upload(c)
    assert ask_raw(c, cid).status_code == 200
    other = upload(c)
    assert count("clauses") > 0 and count("contract_messages") == 4  # 2 briefs + a turn
    assert c.delete(f"/contracts/{cid}").status_code == 204
    assert c.get(f"/contracts/{cid}").status_code == 404
    assert [x["id"] for x in c.get("/contracts").json()] == [other]
    assert count("contracts") == 1
    with connect() as conn:
        assert conn.execute(
            "SELECT count(*) FROM clauses WHERE contract_id = %s", (cid,)
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM contract_messages WHERE contract_id = %s", (cid,)
        ).fetchone() == (0,)


def test_deleting_another_users_contract_is_404_and_changes_nothing(make_client):
    cid = upload(make_client("user_a"))
    assert make_client("user_b").delete(f"/contracts/{cid}").status_code == 404
    assert count("contracts") == 1


def test_deleting_a_made_up_or_malformed_id_is_404(make_client):
    c = make_client()
    assert c.delete(f"/contracts/{ID_NEVER}").status_code == 404
    assert c.delete("/contracts/not-a-uuid").status_code == 404


def test_deleting_needs_sign_in(make_client):
    c = make_client()
    c.headers.pop("Authorization")
    assert c.delete(f"/contracts/{ID_NEVER}").status_code == 401


def test_the_clerk_user_deleted_webhook_removes_everything_of_the_user(make_client):
    a, b = make_client("user_a"), make_client("user_b")
    cid = upload(a)
    ask_raw(a, cid)
    upload(b)
    body = json.dumps({"type": "user.deleted", "data": {"id": "user_a"}}).encode()
    sig = Webhook(SECRET).sign("msg_1", datetime.now(UTC), body.decode())
    headers = {
        "svix-id": "msg_1",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": sig,
    }
    assert a.post("/webhooks/clerk", content=body, headers=headers).status_code == 200
    with connect() as conn:
        for table in ["contracts", "usage", "users"]:
            col = "id" if table == "users" else "user_id"
            assert conn.execute(
                f"SELECT count(*) FROM {table} WHERE {col} = 'user_a'"
            ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM contract_messages WHERE contract_id = %s", (cid,)
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM clauses WHERE contract_id = %s", (cid,)
        ).fetchone() == (0,)
    assert count("contracts") == 1  # user_b's is untouched


# --- daily caps ----------------------------------------------------------------------------


def test_the_sixth_contract_in_a_day_is_429_with_retry_after_and_stores_nothing(
    make_client,
):
    clock = Clock(NOON)
    c = make_client(caps=DailyCaps(contracts=5, queries=50, clock=clock))
    for _ in range(5):
        upload(c)
    r = upload_raw(c)
    assert r.status_code == 429
    assert r.headers["Retry-After"] == str(12 * 3600)  # until midnight UTC
    assert r.headers["X-Limit-Scope"] == "daily"
    assert count("contracts") == 5


def test_the_fifty_first_query_in_a_day_is_429_with_retry_after(make_client):
    clock = Clock(NOON)
    c = make_client(caps=DailyCaps(contracts=5, queries=2, clock=clock))
    cid = upload(c)
    assert ask_raw(c, cid).status_code == 200
    assert ask_raw(c, cid).status_code == 200
    r = ask_raw(c, cid)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) == 12 * 3600
    assert count("contract_messages") == 1 + 4  # nothing was saved for the refused one


def test_caps_are_per_user_and_the_two_counters_are_separate(make_client):
    caps = DailyCaps(contracts=1, queries=1, clock=Clock(NOON))
    a = make_client("user_a", caps)
    cid = upload(a)
    assert upload_raw(a).status_code == 429
    assert ask_raw(a, cid).status_code == 200  # queries have their own counter
    assert upload_raw(make_client("user_b", caps)).status_code == 200


def test_a_refused_upload_does_not_consume_the_cap(make_client):
    caps = DailyCaps(contracts=1, queries=50, clock=Clock(NOON))
    c = make_client(caps=caps)
    events = parse_sse(upload_raw(c, "x" * 500_000).text)  # far over the length limit
    assert events[-1][0] == "refusal"
    upload(c)  # the one allowed Contract still goes through
    assert upload_raw(c).status_code == 429


def test_a_contract_check_refusal_does_not_consume_the_cap(make_client):
    from test_contracts import ContractLLM

    class NotAContract(ContractLLM):
        def check_contract(self, *a, **k):
            r = super().check_contract(*a, **k)
            return r.model_copy(update={"is_contract": False})

    caps = DailyCaps(contracts=1, queries=50, clock=Clock(NOON))
    refused = make_client(caps=caps, llm=NotAContract())
    assert parse_sse(upload_raw(refused).text)[-1][0] == "refusal"
    upload(make_client(caps=caps))


def test_the_count_resets_the_next_day(make_client):
    clock = Clock(NOON)
    c = make_client(caps=DailyCaps(contracts=1, queries=50, clock=clock))
    upload(c)
    assert upload_raw(c).status_code == 429
    clock.now = NOON + timedelta(hours=12)  # midnight UTC
    upload(c)


def test_a_cap_of_zero_turns_it_off(make_client):
    c = make_client(caps=DailyCaps(contracts=0, queries=0, clock=Clock(NOON)))
    cid = upload(c)
    upload(c)
    for _ in range(3):
        assert ask_raw(c, cid).status_code == 200


def test_a_query_about_someone_elses_contract_is_404_and_not_counted(make_client):
    caps = DailyCaps(contracts=5, queries=1, clock=Clock(NOON))
    cid = upload(make_client("user_a", caps))
    b = make_client("user_b", caps)
    assert ask_raw(b, cid).status_code == 404
    assert ask_raw(b, upload(b)).status_code == 200


def test_caps_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("DAILY_CONTRACT_CAP", raising=False)
    monkeypatch.delenv("DAILY_QUERY_CAP", raising=False)
    caps = DailyCaps.from_env()
    assert (caps.contracts, caps.queries) == (5, 50)
    monkeypatch.setenv("DAILY_CONTRACT_CAP", "2")
    monkeypatch.setenv("DAILY_QUERY_CAP", "0")
    caps = DailyCaps.from_env()
    assert (caps.contracts, caps.queries) == (2, 0)


def test_a_refusal_after_midnight_gives_back_the_day_it_was_reserved_on(make_client):
    clock = Clock(NOON.replace(hour=23, minute=59))
    caps = DailyCaps(contracts=1, queries=50, clock=clock)

    from test_contracts import ContractLLM

    class SlowNotAContract(ContractLLM):
        def check_contract(self, *a, **k):
            clock.now += timedelta(minutes=2)  # the day turns while it is read
            r = super().check_contract(*a, **k)
            return r.model_copy(update={"is_contract": False})

    slow = make_client(caps=caps, llm=SlowNotAContract())
    assert parse_sse(upload_raw(slow).text)[-1][0] == "refusal"
    with connect() as conn:
        assert conn.execute("SELECT sum(contracts) FROM usage").fetchone() == (0,)


def test_the_browser_may_read_retry_after_across_origins(make_client):
    c = make_client(caps=DailyCaps(contracts=1, queries=50, clock=Clock(NOON)))
    upload(c)
    r = upload_raw_with_origin(c)
    assert r.status_code == 429
    exposed = r.headers["access-control-expose-headers"].lower()
    assert "retry-after" in exposed and "x-limit-scope" in exposed


def upload_raw_with_origin(client):
    return client.post(
        "/contracts/stream",
        data={"text": RENT},
        headers={"Origin": "http://localhost:3000"},
    )
