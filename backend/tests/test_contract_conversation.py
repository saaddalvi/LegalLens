"""Follow-up Queries in a Contract conversation, through `POST /contracts/{id}/ask/stream`.

These need a Postgres with pgvector (see the README) and skip without one. The model, the
Corpus and the web Fallback are fakes; what is asserted is the HTTP status, the SSE events and
what a reopened Contract shows."""

import json
import logging

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


def ask(client, cid, query=ASK):
    r = client.post(f"/contracts/{cid}/ask/stream", json={"query": query})
    assert r.status_code == 200, r.text
    return parse_sse(r.text)


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
    assert "/ask" in refusal["refusal_reason"]


def test_a_refusal_with_no_reason_from_the_model_still_explains_itself(make_client):
    c = make_client(llm=ConversationLLM(scope=ContractScope(category="unrelated")))
    refusal = final(ask(c, upload(c), "Tell me a joke"))
    assert "/ask" in refusal["refusal_reason"]
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


def test_each_query_and_answer_is_saved_and_a_reopened_contract_shows_them_in_order(
    make_client,
):
    c = make_client()
    cid = upload(c)
    ask(c, cid, "What is the deposit?")
    ask(c, cid, "What is the rent?")
    detail = c.get(f"/contracts/{cid}").json()
    assert [t["query"] for t in detail["conversation"]] == [
        "What is the deposit?",
        "What is the rent?",
    ]
    first = detail["conversation"][0]["response"]
    assert first["answer"] == "Plain answer to: What is the deposit?"
    assert first["clause_references"][0]["number"] == "3"
    assert first["trust_label"] == "contract_and_corpus"
    assert detail["brief"] is not None  # the brief is still the first message


def test_a_refusal_is_part_of_the_saved_conversation(make_client):
    c = make_client(llm=ConversationLLM(scope=ContractScope(category="unrelated")))
    cid = upload(c)
    ask(c, cid, "Tell me a joke")
    turn = c.get(f"/contracts/{cid}").json()["conversation"][0]
    assert turn["query"] == "Tell me a joke"
    assert turn["response"]["response_type"] == "refusal"
    assert turn["response"]["redirect_to_ask"] is True


def test_a_contract_with_no_queries_has_an_empty_conversation(make_client):
    c = make_client()
    assert c.get(f"/contracts/{upload(c)}").json()["conversation"] == []


def test_an_answer_that_failed_is_not_saved(make_client):
    class Failing(ConversationLLM):
        def generate_contract_answer(self, *a, **k):
            raise RuntimeError("gemini 503")

    c = make_client(llm=Failing())
    cid = upload(c)
    events = ask(c, cid)
    assert events[-1][0] == "error"
    assert events[-1][1]["stage"] == "generation"
    assert c.get(f"/contracts/{cid}").json()["conversation"] == []


def test_previous_turns_reach_the_model_and_other_contracts_turns_never_do(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm)
    id_a = upload(c)
    id_b = upload(c, "1. Fee\nThe fee is Rs. 5.\n2. Term\nOne year.")
    ask(c, id_a, "What is the deposit?")
    ask(c, id_a, "And the rent?")
    history = llm.histories[-1]  # what generation for the second Query was given
    assert [t.query for t in history] == ["What is the deposit?"]
    assert history[0].response.answer == "Plain answer to: What is the deposit?"
    # A Query in the other Contract starts with none of Contract A's turns.
    ask(c, id_b, "What is the fee?")
    assert llm.histories[-1] == []
    assert all("deposit" not in t.query for h in llm.histories[-2:] for t in h)


def test_only_the_last_few_turns_are_given(make_client):
    llm = ConversationLLM()
    c = make_client(llm=llm)
    cid = upload(c)
    for i in range(7):
        ask(c, cid, f"Question {i}?")
    # The last Query (Question 6) is given the three turns before it.
    assert [t.query for t in llm.histories[-1]] == [
        "Question 3?",
        "Question 4?",
        "Question 5?",
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
    assert a.get(f"/contracts/{cid}").json()["conversation"] == []
    assert (
        b.post(f"/contracts/{ID_NEVER}/ask/stream", json={"query": ASK}).status_code
        == 404
    )
    assert (
        b.post("/contracts/not-a-uuid/ask/stream", json={"query": ASK}).status_code
        == 404
    )


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
            saved.append(a)

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
