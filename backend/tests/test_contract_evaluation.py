"""The Contract evaluation: sample Contracts driven through the app and scored on flags,
Clause references and follow-up answers.

The app, its model and its Corpus are fakes; what is asserted is the scoring and the report.
Like the Contract conversation tests, these need a Postgres with pgvector and skip without one."""

import json
from pathlib import Path

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
)
from fastapi.testclient import TestClient
from test_contract_conversation import ConversationLLM
from test_contracts import RENT, Embedder1024

from legallens.contract_evaluation import (
    ExpectedFlag,
    FollowUp,
    SampleContract,
    keep_contract_section,
    load_samples,
    render_contracts_report,
    run_contract_evaluation,
    unverified_clause_references,
    write_report,
)
from legallens.corpus import Corpus
from legallens.db import Database
from legallens.llm import ContractScope, ProvisionRef
from legallens.main import create_app
from legallens.models import ClauseOut, ClauseReference

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"
USER = "user_eval"


class EvalLLM(ConversationLLM):
    """Refuses 'should I' Queries, as the real scope check does."""

    def classify_contract_query(self, query, history):
        if "should i" in query.lower():
            return ContractScope(
                category="personal_advice",
                reason="I can't say whether you should sign.",
            )
        return super().classify_contract_query(query, history)


class ReferenceJudge:
    """Accurate when the answer mentions the follow-up's reference text."""

    def is_accurate(self, case, response):
        return case.reference.lower() in response.answer.lower()


@pytest.fixture
def llm():
    return EvalLLM()


@pytest.fixture
def client(tmp_path, pg, llm):
    with connect() as conn:
        conn.execute("TRUNCATE users CASCADE")
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    app = create_app(
        corpus=corpus,
        llm=llm,
        fallback=RecordingFallback(results=[]),
        verifier=FakeVerifier(),
        database=Database(TEST_DB, pooled=False),
        embedder=Embedder1024(),
    )
    return TestClient(app, headers=auth_for(USER))


def sample(**kw) -> SampleContract:
    base = {
        "id": "rent",
        "title": "Rent agreement",
        "text": RENT,
        "expected_flags": [
            ExpectedFlag(
                clause="3", provisions=[ProvisionRef(act=ART_21.act, number="21")]
            )
        ],
        "followups": [],
    }
    return SampleContract(**{**base, **kw})


def run(client, s: SampleContract):
    return run_contract_evaluation([s], client=client, judge=ReferenceJudge())


# --- flags ----------------------------------------------------------------------------------


def test_an_expected_flag_that_is_found_counts_for_recall_and_precision(client):
    result = run(client, sample())
    c = result.contracts[0]
    assert c.error is None
    assert (result.flag_recall, result.flag_precision) == (1.0, 1.0)
    assert [(f.clause, f.provisions) for f in c.found_flags] == [
        ("3", [f"{ART_21.act} 21"])
    ]


def test_a_missed_flag_lowers_recall_and_an_unexpected_one_lowers_precision(client):
    s = sample(
        expected_flags=[
            ExpectedFlag(
                clause="2", provisions=[ProvisionRef(act=IPC_302.act, number="302")]
            ),
        ]
    )
    result = run(client, s)
    # The brief flags Clause 3 citing Art. 21; the sample expected Clause 2 citing IPC 302.
    assert (result.flag_recall, result.flag_precision) == (0.0, 0.0)


def test_a_flag_on_the_right_clause_citing_another_provision_is_not_a_match(client):
    s = sample(
        expected_flags=[
            ExpectedFlag(
                clause="3", provisions=[ProvisionRef(act=IPC_302.act, number="302")]
            )
        ]
    )
    assert run(client, s).flag_recall == 0.0


def test_a_flag_on_a_sub_clause_matches_its_parent_clause_number(client):
    s = sample(
        expected_flags=[
            ExpectedFlag(
                clause="3.1", provisions=[ProvisionRef(act=ART_21.act, number="21")]
            )
        ]
    )
    assert run(client, s).flag_recall == 1.0


class DownClient:
    """A client whose every upload fails, as when Gemini is down."""

    def post(self, url, **kw):
        return type("R", (), {"status_code": 503, "text": ""})()


def test_a_contract_that_will_not_upload_is_reported_and_left_out_of_the_scores():
    result = run_contract_evaluation(
        [sample()], client=DownClient(), judge=ReferenceJudge(), sleep=lambda s: None
    )
    assert result.contracts[0].error == "_StreamFailed"
    assert result.flag_recall is None
    assert "could not be uploaded" in render_contracts_report(result)


def test_the_sample_contracts_are_deleted_after_the_run(client):
    run(client, sample())
    assert client.get("/contracts").json() == []


# --- follow-ups -----------------------------------------------------------------------------


def followups(*items: FollowUp) -> SampleContract:
    return sample(followups=list(items))


def test_a_clause_supported_answer_must_quote_one_of_the_expected_clauses(client):
    good = FollowUp(
        kind="clause_supported",
        query="What is the deposit?",
        expected_clauses=["3"],
        reference="Plain answer to: What is the deposit?",
    )
    wrong_clause = good.model_copy(update={"expected_clauses": ["1"]})
    result = run(client, followups(good, wrong_clause))
    assert [f.accurate for f in result.contracts[0].followups] == [True, False]


def test_a_sign_or_not_question_is_correct_only_when_refused(client):
    ok = FollowUp(kind="sign_refusal", query="Should I sign this?")
    answered = FollowUp(kind="sign_refusal", query="What is the deposit?")
    result = run(client, followups(ok, answered))
    outcomes = result.contracts[0].followups
    assert [f.accurate for f in outcomes] == [True, False]
    assert outcomes[0].response_type == "refusal"


def test_a_law_question_must_cite_an_expected_provision(client):
    cites = FollowUp(
        kind="law",
        query="What does the law say about liberty?",
        expected_provisions=[ProvisionRef(act=ART_21.act, number="21")],
        reference="Plain answer to",
    )
    other = cites.model_copy(
        update={"expected_provisions": [ProvisionRef(act=IPC_302.act, number="302")]}
    )
    result = run(client, followups(cites, other))
    assert [f.accurate for f in result.contracts[0].followups] == [True, False]


def test_a_hindi_question_is_correct_only_when_answered_in_hindi(client):
    f = FollowUp(kind="hindi", query=HINDI_QUERY, reference="Plain answer to")
    # The fake model answers in English, so the answer language says "hi" only because the app
    # detected a Hindi Query; the case still has to pass the judge too.
    outcome = run(client, followups(f)).contracts[0].followups[0]
    assert outcome.answer_language == "hi"
    assert outcome.accurate is True


def test_a_contract_silent_answer_is_judged_on_its_reference(client):
    silent = FollowUp(
        kind="contract_silent",
        query="Is a pet allowed?",
        reference="the contract does not say",
    )
    outcome = run(client, followups(silent)).contracts[0].followups[0]
    assert outcome.accurate is False  # the fake answer does not say that


def test_follow_up_accuracy_is_reported_overall_and_by_kind(client):
    ok = FollowUp(kind="sign_refusal", query="Should I sign this?")
    bad = FollowUp(kind="sign_refusal", query="What is the deposit?")
    result = run(client, followups(ok, bad))
    assert result.followup_accuracy == 0.5
    assert result.followup_accuracy_by_kind["sign_refusal"] == 0.5


def test_a_follow_up_case_is_asked_after_its_earlier_queries_in_one_conversation(
    client, llm
):
    case = FollowUp(
        kind="follow_up",
        earlier=["What is the rent?", "What is the deposit?"],
        query="And when is it paid?",
        reference="Plain answer to: And when is it paid?",
    )
    other = FollowUp(kind="sign_refusal", query="Should I sign this?")
    result = run(client, followups(case, other, case))
    outcomes = result.contracts[0].followups
    assert [f.accurate for f in outcomes] == [True, True, True]
    assert outcomes[0].earlier == case.earlier
    # The Query under test saw its own earlier turns, and nothing of the other cases'.
    assert [t.query for t in llm.histories[-1]] == case.earlier
    assert result.followup_accuracy_by_kind["follow_up"] == 1.0
    assert (
        "What is the rent? → What is the deposit? → And when is it paid?"
        in render_contracts_report(result)
    )


# --- Clause references ----------------------------------------------------------------------


def test_no_clause_reference_is_hallucinated_when_the_app_checks_them(client):
    ok = FollowUp(kind="clause_supported", query="What is the deposit?")
    result = run(client, followups(ok))
    assert result.hallucinated_clause_references == 0
    assert result.contracts[0].clause_references_checked > 0


STORED = [
    ClauseOut(number="3", heading="Deposit", text="3. Deposit\nRs. 1,00,000."),
]


def test_a_clause_reference_must_name_a_stored_clause_with_its_verbatim_text():
    refs = [
        ClauseReference(number="3", text="3. Deposit\nRs. 1,00,000."),  # right
        ClauseReference(number="3", text="3. Deposit\nRs. 5,00,000."),  # altered text
        ClauseReference(number="9", text="Anything."),  # no such Clause
    ]
    assert unverified_clause_references(refs, STORED) == refs[1:]


def test_whitespace_differences_do_not_make_a_clause_reference_unverified():
    ref = ClauseReference(number="3", text="3. Deposit  Rs. 1,00,000.")
    assert unverified_clause_references([ref], STORED) == []


# --- report ---------------------------------------------------------------------------------


def test_the_report_lists_expected_against_found_flags_hallucinations_and_follow_ups(
    client,
):
    s = followups(FollowUp(kind="sign_refusal", query="Should I sign this?"))
    report = render_contracts_report(run(client, s))
    assert "## Contract evaluation" in report
    assert "### rent: Rent agreement" in report
    assert f"{ART_21.act} 21" in report  # expected and found
    assert "Hallucinated clause references: 0" in report
    assert "sign_refusal" in report
    assert "Flag recall" in report and "Flag precision" in report


def test_write_report_replaces_only_the_contract_section(tmp_path):
    path = tmp_path / "report.md"
    path.write_text("# LegalLens evaluation\n\nask results\n")
    write_report(path, "## Contract evaluation\n\nfirst\n")
    write_report(path, "## Contract evaluation\n\nsecond\n")
    text = path.read_text()
    assert text.startswith("# LegalLens evaluation\n\nask results\n")
    assert "second" in text and "first" not in text
    assert text.count("## Contract evaluation") == 1


def test_a_fresh_ask_report_keeps_the_contract_section(tmp_path):
    path = tmp_path / "report.md"
    write_report(
        path, "## Contract evaluation\n\nkept\n<!-- end contract evaluation -->\n"
    )
    merged = keep_contract_section(path, "# LegalLens evaluation\n\nnew ask results\n")
    assert merged.startswith("# LegalLens evaluation\n\nnew ask results\n")
    assert "kept" in merged
    assert keep_contract_section(tmp_path / "none.md", "x\n") == "x\n"


# --- the checked-in samples -----------------------------------------------------------------


def test_the_sample_contracts_are_the_three_the_ticket_asks_for():
    samples = load_samples(FIXTURES / "cases.json")
    assert [s.id for s in samples] == ["rent-agreement", "job-offer", "nda"]
    for s in samples:
        assert s.expected_flags
        assert sorted(f.kind for f in s.followups if f.kind != "follow_up") == sorted(
            [
                "clause_supported",
                "contract_silent",
                "law",
                "sign_refusal",
                "hindi",
            ]
        )


def test_at_least_two_sample_cases_follow_up_on_earlier_queries():
    cases = [f for s in load_samples(FIXTURES / "cases.json") for f in s.followups]
    assert len([f for f in cases if f.kind == "follow_up"]) >= 2
    for f in cases:
        assert bool(f.earlier) == (f.kind == "follow_up"), f.query


def test_every_expected_flag_clause_exists_in_its_sample_contract():
    from legallens.clauses import split_clauses

    for s in load_samples(FIXTURES / "cases.json"):
        numbers = {p.number for p in split_clauses(s.text)}
        for flag in s.expected_flags:
            assert flag.clause in numbers, (s.id, flag.clause)
        for f in s.followups:
            for n in f.expected_clauses:
                assert n in numbers, (s.id, n)


def test_the_sample_contracts_hold_no_real_personal_data():
    import re

    for path in FIXTURES.glob("*.txt"):
        text = path.read_text()
        assert "written for testing" in text
        assert not re.search(r"\b\d{10}\b|@|\b\d{4}\s\d{4}\s\d{4}\b", text), path.name
    json.loads((FIXTURES / "cases.json").read_text())


def test_retried_uploads_leave_no_contract_behind(client):
    """Each attempt that stored a Contract before failing must still be cleaned up."""
    first = client.post("/contracts/stream", data={"text": RENT})
    assert first.status_code == 200
    assert len(client.get("/contracts").json()) == 1
    run(client, sample())
    assert client.get("/contracts").json() == []


def test_a_malformed_brief_is_one_errored_contract_not_a_crashed_run(
    client, monkeypatch
):
    import legallens.contract_evaluation as ce

    def broken(*a, **k):
        raise KeyError("clause_reference")

    monkeypatch.setattr(ce, "_score_contract", broken)
    result = run(client, sample())
    assert result.contracts[0].error == "KeyError"
    assert result.contracts[0].found_flags == []
    assert client.get("/contracts").json() == []
