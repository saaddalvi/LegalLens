"""Uploading a Contract: the Stages, the refusals, what is stored, and who can see it.

Tests marked with the `pg` fixture need a Postgres with pgvector (see the README) and skip
without one. The rest run against an unreachable database, which also shows that a refusal
or a failure never reaches the database."""

import io
import json
import logging
import zipfile

import pytest
from conftest import (
    ART_21,
    IPC_302,
    TEST_DB,
    FakeEmbedder,
    FakeFallback,
    FakeLLM,
    FakeVerifier,
    auth_for,
    connect,
    parse_sse,
)
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from legallens.contract_intake import MAX_PAGES
from legallens.corpus import Corpus
from legallens.db import Database
from legallens.llm import ContractCheck
from legallens.main import create_app

RENT = """RENT AGREEMENT
Made on 1 April 2025 between Asha Rao (Landlord) and Ravi Kumar (Tenant).

1. Term
The tenancy lasts eleven months.

2. Rent
The Tenant shall pay Rs. 20,000 each month.

3. Deposit
The Tenant pays a deposit of Rs. 1,00,000.
"""
STAGES = ["reading", "contract_check", "splitting", "indexing"]
UNREACHABLE = "postgresql://x:y@127.0.0.1:1/none?connect_timeout=1"


class Embedder1024(FakeEmbedder):
    dim = 1024


class ContractLLM(FakeLLM):
    """Reads PDFs as `pdf_text` and checks Contracts as `check` says."""

    def __init__(self, check=None, pdf_text=RENT):
        super().__init__()
        self.check = check or ContractCheck(
            is_contract=True, is_english=True, title="Rent agreement"
        )
        self.pdf_text = pdf_text
        self.reads = 0

    def read_document(self, data, mime_type):
        self.reads += 1
        return self.pdf_text

    def check_contract(self, excerpt):
        return self.check


def pdf_bytes(pages=1) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def docx_bytes(paragraphs: list[str]) -> bytes:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("word/document.xml", xml)
    return out.getvalue()


@pytest.fixture
def make_app(tmp_path):
    def make(url=UNREACHABLE, llm=None):
        corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
        corpus.add([ART_21, IPC_302])
        return create_app(
            corpus=corpus,
            llm=llm or ContractLLM(),
            fallback=FakeFallback(),
            verifier=FakeVerifier(),
            database=Database(url, pooled=False),
            embedder=Embedder1024(),
        )

    return make


@pytest.fixture
def client(make_app):
    """A signed-in client over an unreachable database."""
    return TestClient(make_app(), headers=auth_for("user_a"))


def upload_text(client, text=RENT, **kw):
    r = client.post("/contracts/stream", data={"text": text}, **kw)
    assert r.status_code == 200
    return parse_sse(r.text)


# --- refusals: no database needed, since none is touched --------------------------------


def test_upload_needs_sign_in(make_app):
    anon = TestClient(make_app())
    assert anon.post("/contracts/stream", data={"text": RENT}).status_code == 401
    assert anon.get("/contracts").status_code == 401
    assert (
        anon.get("/contracts/00000000-0000-0000-0000-000000000000").status_code == 401
    )


def test_sending_nothing_or_both_is_422(client):
    assert client.post("/contracts/stream", data={"text": "  "}).status_code == 422
    both = client.post(
        "/contracts/stream",
        data={"text": RENT},
        files={"file": ("a.pdf", pdf_bytes(), "application/pdf")},
    )
    assert both.status_code == 422


def test_not_a_contract_is_refused_after_the_first_two_stages(make_app):
    llm = ContractLLM(ContractCheck(is_contract=False, is_english=True))
    events = upload_text(TestClient(make_app(llm=llm), headers=auth_for("u")))
    assert [e for e, _ in events] == ["stage", "stage", "refusal"]
    assert events[-1][1]["reason"] == "not_a_contract"
    assert "only explains Contracts" in events[-1][1]["message"]


def test_a_hindi_contract_is_refused(make_app):
    llm = ContractLLM(ContractCheck(is_contract=True, is_english=False))
    events = upload_text(
        TestClient(make_app(llm=llm), headers=auth_for("u")), "किराया समझौता"
    )
    assert events[-1][0] == "refusal"
    assert events[-1][1]["reason"] == "not_english"
    assert "English" in events[-1][1]["message"]


def test_an_over_long_pdf_is_refused_before_anything_is_read(make_app):
    llm = ContractLLM()
    c = TestClient(make_app(llm=llm), headers=auth_for("u"))
    r = c.post(
        "/contracts/stream",
        files={"file": ("big.pdf", pdf_bytes(MAX_PAGES + 1), "application/pdf")},
    )
    events = parse_sse(r.text)
    assert [e for e, _ in events] == ["refusal"]
    assert events[0][1]["reason"] == "too_long"
    assert str(MAX_PAGES) in events[0][1]["message"]
    assert llm.reads == 0


def test_over_long_pasted_text_is_refused(client):
    events = upload_text(client, "1. Clause\n" + "word " * 40_000)
    assert [e for e, _ in events] == ["refusal"]
    assert events[0][1]["reason"] == "too_long"


def test_a_file_that_is_neither_pdf_nor_docx_is_refused(client):
    r = client.post(
        "/contracts/stream", files={"file": ("a.png", b"\x89PNG....", "image/png")}
    )
    assert parse_sse(r.text)[0][1]["reason"] == "unsupported_file"


def test_a_pdf_with_no_readable_text_is_refused(make_app):
    c = TestClient(make_app(llm=ContractLLM(pdf_text="  ")), headers=auth_for("u"))
    r = c.post(
        "/contracts/stream", files={"file": ("s.pdf", pdf_bytes(), "application/pdf")}
    )
    events = parse_sse(r.text)
    assert events[-1][1]["reason"] == "unreadable"


# --- privacy ----------------------------------------------------------------------------


class LeakyLLM(ContractLLM):
    """Fails the way a library does when it quotes the prompt in its error."""

    def check_contract(self, excerpt):
        raise RuntimeError(f"bad request for prompt: {excerpt}")


def test_contract_text_never_reaches_the_log_or_an_error(make_app, caplog):
    secret = "Aadhaar 1234-5678-9012 of Asha Rao"
    c = TestClient(make_app(llm=LeakyLLM()), headers=auth_for("u"))
    with caplog.at_level(logging.DEBUG):
        r = c.post(
            "/contracts/stream", data={"text": f"1. Parties\n{secret}\n2. Rent\nRs 5."}
        )
    assert secret not in r.text
    assert "error" in [e for e, _ in parse_sse(r.text)]
    assert secret not in caplog.text
    line = [m for m in caplog.messages if '"event": "request"' in m]
    assert line and json.loads(line[-1])["outcome"] == "error"


# --- with a database ---------------------------------------------------------------------


@pytest.fixture
def db(pg):
    with connect() as conn:
        conn.execute("TRUNCATE users CASCADE")

        def one(sql, *args):
            return conn.execute(sql, args).fetchone()[0]

        yield one


@pytest.fixture
def pg_client(make_app, pg):
    with connect() as conn:
        conn.execute("TRUNCATE users CASCADE")

    def make(user="user_a", llm=None):
        return TestClient(make_app(TEST_DB, llm), headers=auth_for(user))

    return make


def test_a_valid_upload_streams_the_stages_and_stores_the_contract(pg_client, db):
    events = upload_text(pg_client())
    assert [e for e, _ in events] == ["stage"] * 4 + ["answer"]
    assert [d["id"] for e, d in events if e == "stage"] == STAGES
    _, answer = events[-1]
    assert answer["title"] == "Rent agreement"
    assert answer["clause_count"] == 4  # recitals as Clause 0, then 1, 2, 3
    assert db("SELECT count(*) FROM contracts") == 1
    assert db("SELECT count(*) FROM clauses") == 4
    assert db("SELECT count(*) FROM clauses WHERE vector_dims(embedding) = 1024") == 4
    assert db("SELECT text FROM contracts") == RENT.strip()


def test_pdf_and_docx_uploads_work(pg_client, db):
    c = pg_client()
    r = c.post(
        "/contracts/stream", files={"file": ("r.pdf", pdf_bytes(2), "application/pdf")}
    )
    events = parse_sse(r.text)
    assert events[-1][0] == "answer"
    assert db("SELECT page_count FROM contracts") == 2
    docx = docx_bytes(RENT.strip().split("\n"))
    r = c.post(
        "/contracts/stream",
        files={"file": ("r.docx", docx, "application/octet-stream")},
    )
    events = parse_sse(r.text)
    assert events[-1][0] == "answer"
    assert events[-1][1]["clause_count"] == 4


@pytest.mark.parametrize(
    "check",
    [
        ContractCheck(is_contract=False, is_english=True),
        ContractCheck(is_contract=True, is_english=False),
    ],
)
def test_refusals_store_nothing(pg_client, db, check):
    events = upload_text(pg_client(llm=ContractLLM(check)))
    assert events[-1][0] == "refusal"
    assert db("SELECT count(*) FROM contracts") == 0
    assert db("SELECT count(*) FROM clauses") == 0


def test_a_failure_after_reading_stores_nothing(pg_client, db):
    events = upload_text(pg_client(llm=LeakyLLM()))
    assert events[-1][0] == "error"
    assert db("SELECT count(*) FROM contracts") == 0


def test_a_long_clause_is_stored_as_pieces_and_listed_whole(pg_client, db):
    body = "The Tenant shall keep the premises clean. " * 60
    text = f"1. Short\nok.\n2. Long\n{body}\n3. End\nok."
    c = pg_client()
    cid = upload_text(c, text)[-1][1]["id"]
    assert db("SELECT count(*) FROM clauses WHERE number = '2'") > 1
    detail = c.get(f"/contracts/{cid}").json()
    assert [x["number"] for x in detail["clauses"]] == ["1", "2", "3"]
    assert detail["clauses"][1]["text"] == f"2. Long\n{body.strip()}"


def test_listing_shows_only_the_callers_contracts(pg_client):
    a, b = pg_client("user_a"), pg_client("user_b")
    id_a = upload_text(a)[-1][1]["id"]
    id_b = upload_text(b, "1. Other\nx.\n2. Other\ny.")[-1][1]["id"]
    listed = a.get("/contracts").json()
    assert [c["id"] for c in listed] == [id_a]
    assert listed[0]["title"] == "Rent agreement"
    assert listed[0]["clause_count"] == 4
    assert [c["id"] for c in b.get("/contracts").json()] == [id_b]
    assert pg_client("user_c").get("/contracts").json() == []


def test_another_users_contract_is_404_and_so_is_a_made_up_id(pg_client):
    a, b = pg_client("user_a"), pg_client("user_b")
    cid = upload_text(a)[-1][1]["id"]
    assert a.get(f"/contracts/{cid}").status_code == 200
    assert b.get(f"/contracts/{cid}").status_code == 404
    assert b.get("/contracts/00000000-0000-0000-0000-000000000000").status_code == 404
    assert b.get("/contracts/not-a-uuid").status_code == 404


def test_clause_retrieval_is_filtered_to_one_contract(make_app, pg_client):
    emb = Embedder1024()
    a, b = pg_client("user_a"), pg_client("user_b")
    id_a = upload_text(a, RENT)[-1][1]["id"]
    id_b = upload_text(
        b, "1. Rent\nThe rent is Rs. 20,000.\n2. Deposit\nRent deposit is Rs. 1,00,000."
    )[-1][1]["id"]
    db = Database(TEST_DB, pooled=False)
    vec = emb.embed(["rent Rs. 20,000 each month"], is_query=True)[0]

    import asyncio

    hits_a = asyncio.run(db.search_clauses("user_a", id_a, vec, k=10))
    assert hits_a and all("Asha" in h.text or h.number in "0123" for h in hits_a)
    assert len(hits_a) == 4  # every piece of A, none of B's
    hits_b = asyncio.run(db.search_clauses("user_b", id_b, vec, k=10))
    assert {h.number for h in hits_b} == {"1", "2"}
    # Someone else's Contract id returns nothing, whoever asks.
    assert asyncio.run(db.search_clauses("user_b", id_a, vec, k=10)) == []
    assert asyncio.run(db.search_clauses("user_a", id_b, vec, k=10)) == []
