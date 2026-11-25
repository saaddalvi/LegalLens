"""Follow-up Queries in a Contract conversation, through `POST /contracts/{id}/ask/stream`.

These need a Postgres with pgvector (see the README) and skip without one. The model, the
Corpus and the web Fallback are fakes; what is asserted is the HTTP status, the SSE events and
what a reopened Contract shows."""

import json
import logging
import threading

import pytest
from conftest import (
    ART_21,
    HINDI_QUERY,
    IPC_302,
    TEST_DB,
    FakeEmbedder,
    FakeVerifier,
    RecordingFallback,
    auth_for,
    connect,
    parse_sse,
    post_then_leave,
)
from fastapi.testclient import TestClient
from test_contracts import RENT, ContractLLM, Embedder1024

from legallens.answer_cache import AnswerCache
from legallens.corpus import Corpus
from legallens.db import Database
from legallens.llm import ContractGeneration, ContractScope, ProvisionRef
from legallens.main import create_app
from legallens.models import FallbackSource

DEPOSIT_CLAUSE = "3. Deposit\nThe Tenant pays a deposit of Rs. 1,00,000."
ASK = "What is the deposit?"
ID_NEVER = "00000000-0000-0000-0000-000000000000"
WEB = FallbackSource(title="Explainer", url="https://example.org/x", snippet="Snippet.")
ALL_STAGES = [
    "scope_check",
    "clause_retrieval",
    "clause_grading",
    "retrieval",
    "grading",
    "generation",
    "citation_check",
]


class ConversationLLM(ContractLLM):
    """A model that behaves: it grades as told, quotes the closest Clause it was given and cites
    the closest Provision. It records what it was shown."""

    def __init__(self, clause_score=1.0, score=1.0, scope=None, answers=None):
        super().__init__()
        self.clause_score = clause_score
        self.score = score
        self.scope = scope or ContractScope(category="in_scope")
        self.answers = answers  # optional: generations returned in turn
        self.generations = 0
        self.histories: list[list] = []  # what each call was given as earlier turns
        self.clauses_seen: list = []
        self.provisions_seen: list = []
        self.sources_seen: list = []
        self.languages: list[str] = []
        self.rewritten: list[str] = []

    def classify_contract_query(self, query, history):
        self.histories.append(list(history))
        return self.scope

    def grade_clauses(self, query, clauses):
        return self.clause_score

    def rewrite(self, query):
        self.rewritten.append(query)
        return f"rewritten: {query}"

    def generate_contract_answer(
        self, query, clauses, provisions, sources, history, language
    ):
        self.generations += 1
        self.histories.append(list(history))
        self.clauses_seen, self.provisions_seen = clauses, provisions
        self.sources_seen = sources
        self.languages.append(language)
        if self.answers:
            return self.answers[min(self.generations, len(self.answers)) - 1]
        return ContractGeneration(
            answer=f"Plain answer to: {query}",
            citations=(
                [ProvisionRef(act=provisions[0].act, number=provisions[0].number)]
                if provisions
                else []
            ),
            clause_numbers=[clauses[0].number] if clauses else [],
        )


@pytest.fixture
def make_client(tmp_path, pg):
    with connect() as conn:
        conn.execute("TRUNCATE users CASCADE")

    def make(user="user_a", llm=None, fallback=None, cache=None):
        corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
        corpus.add([ART_21, IPC_302])
        app = create_app(
            corpus=corpus,
            llm=llm or ConversationLLM(),
            fallback=fallback or RecordingFallback(results=[]),
            verifier=FakeVerifier(),
            database=Database(TEST_DB, pooled=False),
            embedder=Embedder1024(),
            cache=cache,
        )
        return TestClient(app, headers=auth_for(user))

    return make


def upload(client, text=RENT) -> str:
    r = client.post("/contracts/stream", data={"text": text})
    events = parse_sse(r.text)
    assert events[-1][0] == "answer", events
    return events[-1][1]["id"]


def ask(client, cid, query=ASK, conversation=None):
    """Asks in the given Contract conversation, or in a new one."""
    body = {"query": query}
    if conversation:
        body["conversation_id"] = conversation
    r = client.post(f"/contracts/{cid}/ask/stream", json=body)
    assert r.status_code == 200, r.text
    return parse_sse(r.text)


def conversation_of(events) -> str:
    """The id in the `conversation` event of an answered Query."""
    [data] = [d for e, d in events if e == "conversation"]
    return data["id"]


def conversations(client, cid) -> list[dict]:
    return client.get(f"/contracts/{cid}").json()["conversations"]


def turns(client, cid, conversation) -> list[dict]:
    r = client.get(f"/contracts/{cid}/conversations/{conversation}")
    assert r.status_code == 200, r.text
    return r.json()


def final(events):
    name, data = events[-1]
    assert name == "answer", events
    return data


def stage_ids(events):
    return [d["id"] for e, d in events if e == "stage"]


# --- the paths ------------------------------------------------------------------------------


def test_a_clause_supported_answer_quotes_the_clause_and_cites_the_law(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm)
    cid = upload(c)
    events = ask(c, cid)
    assert stage_ids(events) == ALL_STAGES
    answer = final(events)
    assert answer["response_type"] == "answer"
    assert answer["trust_label"] == "contract_and_corpus"
    # The Clause reference carries the stored text, verbatim.
    assert answer["clause_references"] == [{"number": "3", "text": DEPOSIT_CLAUSE}]
    assert llm.clauses_seen[0].number == "3"
    assert answer[
        "citations"
    ]  # a verified Provision, whichever the fake embedder ranks first
    assert answer["fallback_sources"] == []
    assert answer["redirect_to_ask"] is False


def test_a_clause_only_answer_when_the_law_does_not_bear_on_it(make_client):
    fb = RecordingFallback(results=[])
    c = make_client(llm=ConversationLLM(score=0.0), fallback=fb)
    answer = final(ask(c, upload(c)))
    assert answer["trust_label"] == "contract"
    assert answer["clause_references"][0]["number"] == "3"
    assert answer["citations"] == []
    assert len(fb.queries) == 1  # the corrective loop still tried the Fallback


def test_an_ambiguous_verdict_goes_to_the_fallback(make_client):
    fb = RecordingFallback(results=[WEB])
    llm = ConversationLLM(score=0.5)
    c = make_client(llm=llm, fallback=fb)
    events = ask(c, upload(c))
    assert stage_ids(events) == [*ALL_STAGES[:5], "fallback", *ALL_STAGES[5:]]
    answer = final(events)
    assert answer["trust_label"] == "contract_corpus_and_fallback"
    assert [s["url"] for s in answer["fallback_sources"]] == [WEB.url]
    assert answer["clause_references"] and answer["citations"]
    assert llm.sources_seen == [WEB]


def test_clauses_and_web_sources_without_provisions(make_client):
    c = make_client(
        llm=ConversationLLM(score=0.0), fallback=RecordingFallback(results=[WEB])
    )
    answer = final(ask(c, upload(c)))
    assert answer["trust_label"] == "contract_and_fallback"
    assert answer["citations"] == []


def test_a_law_only_answer_when_the_contract_is_silent(make_client):
    llm = ConversationLLM(clause_score=0.0)
    c = make_client(llm=llm)
    answer = final(ask(c, upload(c)))
    assert llm.clauses_seen == []  # no irrelevant Clause reaches generation
    assert answer["trust_label"] == "corpus"
    assert answer["clause_references"] == []
    assert answer["answer"].startswith("Your Contract does not address this question.")
    assert "Plain answer to:" in answer["answer"]  # the law is still explained
    assert answer["citations"]


def test_a_silent_contract_and_no_law_says_so_and_nothing_supports_it(make_client):
    c = make_client(llm=ConversationLLM(clause_score=0.0, score=0.0))
    answer = final(ask(c, upload(c)))
    assert answer["trust_label"] == "none"
    assert "Your Contract does not address this question" in answer["answer"]
    assert answer["clause_references"] == [] and answer["citations"] == []


def test_personal_advice_is_refused_before_any_retrieval(make_client):
    scope = ContractScope(
        category="personal_advice",
        reason="I can't say whether you should sign.",
        suggested_reformulation="What does the notice Clause say?",
    )
    c = make_client(llm=ConversationLLM(scope=scope))
    events = ask(c, upload(c), "Should I sign this?")
    assert stage_ids(events) == ["scope_check"]
    refusal = final(events)
    assert refusal["response_type"] == "refusal"
    assert refusal["trust_label"] == "none"
    assert refusal["refusal_reason"] == "I can't say whether you should sign."
    assert refusal["suggested_reformulation"] == "What does the notice Clause say?"
    assert refusal["redirect_to_ask"] is False


def test_an_unrelated_query_is_pointed_to_ask(make_client):
    scope = ContractScope(
        category="unrelated", reason="That isn't about your Contract."
    )
    c = make_client(llm=ConversationLLM(scope=scope))
    events = ask(c, upload(c), "What is the punishment for murder?")
    assert stage_ids(events) == ["scope_check"]
    refusal = final(events)
    assert refusal["response_type"] == "refusal"
    assert refusal["redirect_to_ask"] is True
    assert "That isn't about your Contract." in refusal["refusal_reason"]
    assert "use Ask a question" in refusal["refusal_reason"]


def test_a_refusal_with_no_reason_from_the_model_still_explains_itself(make_client):
    c = make_client(llm=ConversationLLM(scope=ContractScope(category="unrelated")))
    refusal = final(ask(c, upload(c), "Tell me a joke"))
    assert "use Ask a question" in refusal["refusal_reason"]
    assert refusal["suggested_reformulation"]


def test_a_hindi_query_gets_hindi_labels_and_an_english_clause(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm)
    events = ask(c, upload(c), HINDI_QUERY)
    labels = [d["label"] for e, d in events if e == "stage"]
    assert len(labels) == len(ALL_STAGES)
    assert all(any("ऀ" <= ch <= "ॿ" for ch in label) for label in labels)
    answer = final(events)
    assert answer["answer_language"] == "hi"
    assert llm.languages == ["hi"]
    assert answer["clause_references"][0]["text"].isascii()  # verbatim English


def test_the_refusal_of_a_hindi_query_is_in_hindi(make_client):
    c = make_client(llm=ConversationLLM(scope=ContractScope(category="unrelated")))
    refusal = final(ask(c, upload(c), HINDI_QUERY))
    assert any("ऀ" <= ch <= "ॿ" for ch in refusal["refusal_reason"])


# --- references are checked -------------------------------------------------------------------


def made_up_clause():
    return ContractGeneration(
        answer="Per Clause 99.", citations=[], clause_numbers=["99"]
    )


def test_a_made_up_clause_number_forces_one_rewrite(make_client):
    good = ContractGeneration(
        answer="Per Clause 3.", citations=[], clause_numbers=["3"]
    )
    llm = ConversationLLM(score=0.0, answers=[made_up_clause(), good])
    c = make_client(llm=llm)
    events = ask(c, upload(c))
    assert stage_ids(events)[-2:] == ["citation_check", "citation_recheck"]
    answer = final(events)
    assert answer["clause_references"] == [{"number": "3", "text": DEPOSIT_CLAUSE}]
    assert llm.generations == 2


def test_a_made_up_clause_number_twice_blocks_the_answer(make_client):
    llm = ConversationLLM(score=0.0, answers=[made_up_clause()])
    c = make_client(llm=llm)
    answer = final(ask(c, upload(c)))
    assert answer["trust_label"] == "none"
    assert answer["clause_references"] == []
    assert "cannot answer reliably" in answer["answer"]


def test_a_made_up_citation_forces_one_rewrite(make_client):
    ghost = ContractGeneration(
        answer="x",
        citations=[ProvisionRef(act="Indian Penal Code", number="420")],
        clause_numbers=["3"],
    )
    good = ContractGeneration(
        answer="y",
        citations=[ProvisionRef(act=ART_21.act, number=ART_21.number)],
        clause_numbers=["3"],
    )
    llm = ConversationLLM(answers=[ghost, good])
    c = make_client(llm=llm)
    events = ask(c, upload(c))
    assert stage_ids(events)[-1] == "citation_recheck"
    assert final(events)["citations"][0]["number"] == ART_21.number


# --- the conversation is remembered ------------------------------------------------------------


def test_a_first_query_starts_a_conversation_and_names_it_before_the_answer(
    make_client,
):
    c = make_client()
    cid = upload(c)
    events = ask(c, cid, "What is the deposit?")
    assert [e for e, _ in events if e != "stage"] == ["conversation", "answer"]
    assert events[-2][1] == {
        "id": conversation_of(events),
        "title": "What is the deposit?",
    }
    [listed] = conversations(c, cid)
    assert listed["id"] == conversation_of(events)
    assert listed["title"] == "What is the deposit?"
    assert listed["created_at"] and listed["updated_at"]
    [turn] = turns(c, cid, listed["id"])
    assert turn["query"] == "What is the deposit?"
    assert turn["response"] == final(events)


def test_a_query_in_a_conversation_is_appended_to_it(make_client):
    c = make_client()
    cid = upload(c)
    first = conversation_of(ask(c, cid, "What is the deposit?"))
    events = ask(c, cid, "What is the rent?", first)
    assert events[-2] == (
        "conversation",
        {"id": first, "title": "What is the deposit?"},  # still its first Query
    )
    assert [t["query"] for t in turns(c, cid, first)] == [
        "What is the deposit?",
        "What is the rent?",
    ]
    answered = turns(c, cid, first)[0]["response"]
    assert answered["answer"] == "Plain answer to: What is the deposit?"
    assert answered["clause_references"][0]["number"] == "3"
    assert answered["trust_label"] == "contract_and_corpus"
    [listed] = conversations(c, cid)
    assert listed["updated_at"] > listed["created_at"]


def test_conversations_are_listed_with_the_latest_asked_first(make_client):
    c = make_client()
    cid = upload(c)
    older = conversation_of(ask(c, cid, "What is the deposit?"))
    newer = conversation_of(ask(c, cid, "What is the rent?"))
    assert [x["id"] for x in conversations(c, cid)] == [newer, older]
    ask(c, cid, "And the notice period?", older)
    assert [x["id"] for x in conversations(c, cid)] == [older, newer]


def test_a_refusal_is_part_of_the_saved_conversation(make_client):
    c = make_client(llm=ConversationLLM(scope=ContractScope(category="unrelated")))
    cid = upload(c)
    conversation = conversation_of(ask(c, cid, "Tell me a joke"))
    [turn] = turns(c, cid, conversation)
    assert turn["query"] == "Tell me a joke"
    assert turn["response"]["response_type"] == "refusal"
    assert turn["response"]["redirect_to_ask"] is True


def test_a_contract_with_no_queries_has_no_conversation_but_has_its_brief(make_client):
    c = make_client()
    detail = c.get(f"/contracts/{upload(c)}").json()
    assert detail["conversations"] == []
    assert detail["brief"] is not None


def test_a_failed_first_query_leaves_no_conversation_behind(make_client):
    class Failing(ConversationLLM):
        def generate_contract_answer(self, *a, **k):
            raise RuntimeError("gemini 503")

    c = make_client(llm=Failing())
    cid = upload(c)
    events = ask(c, cid)
    assert events[-1][0] == "error"
    assert events[-1][1]["stage"] == "generation"
    assert "conversation" not in [e for e, _ in events]
    assert conversations(c, cid) == []


def test_a_cancelled_first_query_leaves_no_conversation_behind(make_client):
    release = threading.Event()

    class Stuck(ConversationLLM):
        def classify_contract_query(self, query, history):
            release.wait(5)  # still checking when the client leaves
            return super().classify_contract_query(query, history)

    llm = Stuck()
    c = make_client(llm=llm)
    cid = upload(c)
    sent = post_then_leave(
        c.app,
        f"/contracts/{cid}/ask/stream",
        json.dumps({"query": ASK}).encode(),
        "application/json",
        after=b"scope_check",
        on_left=release.set,
    )
    assert b"scope_check" in sent and b"event: answer" not in sent
    assert llm.generations == 0  # the work stopped too
    assert conversations(c, cid) == []


def test_a_first_query_that_cannot_be_saved_leaves_no_conversation_behind(make_client):
    c = make_client()
    cid = upload(c)
    # The conversation row can be written, but not its first Query and answer.
    with connect() as conn:
        conn.execute(
            "CREATE FUNCTION refuse() RETURNS trigger LANGUAGE plpgsql AS "
            "$$ BEGIN RAISE EXCEPTION 'refused'; END $$"
        )
        conn.execute(
            "CREATE TRIGGER refuse BEFORE INSERT ON contract_messages "
            "FOR EACH ROW EXECUTE FUNCTION refuse()"
        )
    try:
        events = ask(c, cid)
    finally:
        with connect() as conn:
            conn.execute("DROP FUNCTION refuse() CASCADE")
    assert events[-1][0] == "error"
    assert conversations(c, cid) == []


def test_generation_sees_only_the_open_conversations_turns(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm)
    id_a = upload(c)
    id_b = upload(c, "1. Fee\nThe fee is Rs. 5.\n2. Term\nOne year.")
    first = conversation_of(ask(c, id_a, "What is the deposit?"))
    second = conversation_of(ask(c, id_a, "What is the notice period?"))
    assert llm.histories[-1] == []  # a new conversation knows nothing of the other
    ask(c, id_a, "And the rent?", first)
    # What the scope check and generation were given: that conversation's turn and no more,
    # neither the other conversation's nor the brief.
    for history in llm.histories[-2:]:
        assert [t.query for t in history] == ["What is the deposit?"]
    assert llm.histories[-1][0].response.answer == (
        "Plain answer to: What is the deposit?"
    )
    ask(c, id_a, "And after that?", second)
    assert [t.query for t in llm.histories[-1]] == ["What is the notice period?"]
    ask(c, id_b, "What is the fee?")
    assert llm.histories[-1] == []


def test_only_the_last_ten_turns_are_given(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm)
    cid = upload(c)
    conversation = conversation_of(ask(c, cid, "Question 0?"))
    for i in range(1, 12):
        ask(c, cid, f"Question {i}?", conversation)
    # The last Query (Question 11) is given the ten turns before it.
    assert [t.query for t in llm.histories[-1]] == [
        f"Question {i}?" for i in range(1, 11)
    ]


def test_the_same_query_twice_is_answered_twice_with_no_cache(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm, cache=AnswerCache())
    cid = upload(c)
    ask(c, cid)
    ask(c, cid)
    assert llm.generations == 2


# --- privacy and access ----------------------------------------------------------------------


def test_the_fallbacks_web_query_never_contains_clause_text(make_client):
    fb = RecordingFallback(results=[WEB])
    llm = ConversationLLM(score=0.0)
    c = make_client(llm=llm, fallback=fb)
    ask(c, upload(c), "deposit")
    assert fb.queries == ["rewritten: deposit"]
    assert llm.rewritten == ["deposit"]  # the rewrite was given the Query alone
    assert not any("Rs. 1,00,000" in q or "Tenant" in q for q in fb.queries)


def test_another_users_contract_is_404_and_nothing_is_done(make_client):
    llm = ConversationLLM()
    a, b = make_client("user_a", llm=llm), make_client("user_b", llm=llm)
    cid = upload(a)
    r = b.post(f"/contracts/{cid}/ask/stream", json={"query": ASK})
    assert r.status_code == 404
    assert llm.histories == [] and llm.generations == 0
    assert conversations(a, cid) == []
    assert (
        b.post(f"/contracts/{ID_NEVER}/ask/stream", json={"query": ASK}).status_code
        == 404
    )
    assert (
        b.post("/contracts/not-a-uuid/ask/stream", json={"query": ASK}).status_code
        == 404
    )


def reach(client, contract, conversation) -> list[int]:
    """The statuses of asking in, reading and deleting a conversation."""
    path = f"/contracts/{contract}/conversations/{conversation}"
    body = {"query": ASK, "conversation_id": conversation}
    return [
        client.post(f"/contracts/{contract}/ask/stream", json=body).status_code,
        client.get(path).status_code,
        client.delete(path).status_code,
    ]


def test_a_conversation_is_404_outside_its_own_contract_and_user(make_client):
    llm = ConversationLLM()
    a, b = make_client("user_a", llm=llm), make_client("user_b", llm=llm)
    cid, other = upload(a), upload(a)
    conversation = conversation_of(ask(a, cid))
    theirs = upload(b)
    asked = llm.generations
    for client, contract, wanted in [
        (a, other, conversation),  # another Contract of the same user
        (b, cid, conversation),  # another user, naming the Contract it is on
        (b, theirs, conversation),  # another user, naming their own Contract
        (a, cid, ID_NEVER),
        (a, cid, "not-a-uuid"),
        (a, "not-a-uuid", conversation),
    ]:
        assert reach(client, contract, wanted) == [404, 404, 404], (contract, wanted)
    assert llm.generations == asked  # nothing was done
    assert len(turns(a, cid, conversation)) == 1  # and nothing changed
    assert conversations(a, other) == [] and conversations(b, theirs) == []


def test_deleting_a_conversation_leaves_the_contract_and_its_others(make_client):
    c = make_client()
    cid = upload(c)
    gone = conversation_of(ask(c, cid, "What is the deposit?"))
    kept = conversation_of(ask(c, cid, "What is the rent?"))
    r = c.delete(f"/contracts/{cid}/conversations/{gone}")
    assert r.status_code == 204 and r.content == b""
    assert reach(c, cid, gone) == [404, 404, 404]
    assert [x["id"] for x in conversations(c, cid)] == [kept]
    assert [t["query"] for t in turns(c, cid, kept)] == ["What is the rent?"]
    assert c.get(f"/contracts/{cid}").json()["brief"] is not None
    with connect() as conn:
        assert conn.execute(
            "SELECT count(*) FROM contract_messages WHERE conversation_id = %s", (gone,)
        ).fetchone() == (0,)


def test_deleting_a_contract_removes_all_its_conversations(make_client):
    c = make_client()
    cid = upload(c)
    first = conversation_of(ask(c, cid, "What is the deposit?"))
    second = conversation_of(ask(c, cid, "What is the rent?"))
    assert c.delete(f"/contracts/{cid}").status_code == 204
    for conversation in (first, second):
        assert (
            c.get(f"/contracts/{cid}/conversations/{conversation}").status_code == 404
        )
    with connect() as conn:
        for table in ["contract_conversations", "contract_messages"]:
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)


def test_a_conversation_deleted_while_answering_is_an_error_and_saves_nothing(
    make_client,
):
    class DeletesIt(ConversationLLM):
        def classify_contract_query(self, query, history):
            if history:
                with connect() as conn:
                    conn.execute("DELETE FROM contract_conversations")
            return super().classify_contract_query(query, history)

    c = make_client(llm=DeletesIt())
    cid = upload(c)
    conversation = conversation_of(ask(c, cid))
    events = ask(c, cid, "And the rent?", conversation)
    assert events[-1][0] == "error"
    assert conversations(c, cid) == []


@pytest.mark.parametrize(
    ("query", "title"),
    [
        ("What is\nthe   deposit?", "What is the deposit?"),
        ("a" * 60, "a" * 60),
        (
            "What happens to my security deposit if I leave the flat before the year ends?",
            "What happens to my security deposit if I leave the flat…",
        ),
        ("x" * 75, "x" * 59 + "…"),  # one long word has no boundary to cut at
        (
            "क्या मकान मालिक मेरी जमा राशि पूरी तरह रोक सकता है अगर मैं साल पूरा होने से पहले घर छोड़ूँ?",
            "क्या मकान मालिक मेरी जमा राशि पूरी तरह रोक सकता है अगर मैं…",
        ),
    ],
)
def test_a_long_first_query_is_shortened_at_a_word_boundary_for_the_title(
    make_client, query, title
):
    c = make_client()
    cid = upload(c)
    events = ask(c, cid, query)
    assert events[-2][1]["title"] == title
    [listed] = conversations(c, cid)
    assert listed["title"] == title
    assert turns(c, cid, listed["id"])[0]["query"] == query  # the Query stays whole


def test_asking_needs_sign_in(make_client):
    c = make_client()
    cid = upload(c)
    anon = TestClient(c.app)
    assert (
        anon.post(f"/contracts/{cid}/ask/stream", json={"query": ASK}).status_code
        == 401
    )


def test_a_blank_query_is_422(make_client):
    c = make_client()
    r = c.post(f"/contracts/{upload(c)}/ask/stream", json={"query": "   "})
    assert r.status_code == 422


def test_the_request_log_has_neither_the_query_nor_the_contract(make_client, caplog):
    c = make_client()
    cid = upload(c)
    with caplog.at_level(logging.INFO, logger="legallens.request"):
        ask(c, cid, "What is the deposit of Rs. 1,00,000 for Ravi Kumar?")
    lines = [json.loads(m) for m in caplog.messages if '"event": "request"' in m]
    record = [r for r in lines if r["endpoint"] == "contract_ask_stream"][-1]
    assert record["outcome"] == "answer"
    assert record["trust_label"] == "contract_and_corpus"
    assert "clause_grader_score" in record and "grader_score" in record
    assert "Ravi" not in caplog.text and "1,00,000" not in caplog.text


# --- found in review ----------------------------------------------------------------------------


def test_a_clause_the_model_was_not_shown_cannot_be_quoted(make_client):
    # Clause 1 exists in the Contract, but the Grader set every Clause aside, so none is shown.
    gen = ContractGeneration(answer="Per Clause 1.", citations=[], clause_numbers=["1"])
    llm = ConversationLLM(clause_score=0.0, score=0.0, answers=[gen])
    fb = RecordingFallback(results=[WEB])
    c = make_client(llm=llm, fallback=fb)
    answer = final(ask(c, upload(c)))
    assert answer["clause_references"] == []
    assert answer["trust_label"] == "fallback"


def test_the_trust_label_counts_a_clause_only_if_it_is_quoted(make_client):
    gen = ContractGeneration(answer="Vaguely.", citations=[], clause_numbers=[])
    c = make_client(llm=ConversationLLM(score=0.0, answers=[gen]))
    answer = final(ask(c, upload(c)))
    assert answer["clause_references"] == []
    assert answer["trust_label"] == "none"


def test_a_reader_who_left_during_the_last_stage_saves_nothing():
    import asyncio
    from threading import Event

    from legallens.answering import Cancelled
    from legallens.contract_answering import ContractAnswerer
    from legallens.db import ClauseHit

    saved = []

    class Store:
        async def search_clauses(self, *a, **k):
            return [ClauseHit("1", "", "1. Rent", 0)]

        async def get_clauses(self, *a):
            return {"1": "1. Rent"}

        async def recent_turns(self, *a):
            return []

        async def add_turn(self, *a):
            saved.append(a)  # the only thing that could start a conversation

    class Corp:
        def search(self, q, k):
            return []

        def get(self, *a):
            return None

    gone = Event()
    llm = ConversationLLM()
    answerer = ContractAnswerer(
        corpus=Corp(),
        llm=llm,
        fallback=RecordingFallback(results=[]),
        store=Store(),
        embedder=Embedder1024(),
    )

    def on_stage(stage):
        if stage.id == "generation":
            gone.set()  # the reader leaves; no later Stage starts, but the answer is finished

    with pytest.raises(Cancelled):
        asyncio.run(
            answerer.answer("u", "c", ASK, endpoint="t", on_stage=on_stage, cancel=gone)
        )
    assert saved == []
