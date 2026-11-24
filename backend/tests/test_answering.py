"""The Answerer's interface: a Query in, an answer out, with its Stages, Decisions and
failures. The real Corpus and the real corrective loop run; only the LLM and the Fallback are fakes."""

import re
import threading

import pytest
from conftest import (
    ART_21,
    HINDI_QUERY,
    IPC_302,
    QUERY,
    WEB,
    AlwaysHallucinatingLLM,
    BrokenLLM,
    FakeEmbedder,
    FakeFallback,
    FakeLLM,
    GenerationFailsLLM,
    HallucinatingThenValidLLM,
    OutOfScopeLLM,
    RecordingFallback,
    RewritingLLM,
    ScopeFailsLLM,
)

from legallens.answer_cache import AnswerCache
from legallens.answering import Answered, Cancelled, StageFailed
from legallens.llm import Generation, ProvisionRef, ScopeDecision
from legallens.models import Provision
from legallens.pipeline import TOP_K

HINDI_LIBERTY = "क्या मुझे व्यक्तिगत स्वतंत्रता से वंचित किया जा सकता है?"
HINDI_ANSWER = "अनुच्छेद 21 के अनुसार, कानून की प्रक्रिया के बिना किसी को जीवन या स्वतंत्रता से वंचित नहीं किया जा सकता।"


def devanagari(text) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text))


def ask(answerer, query=QUERY, **kw) -> Answered:
    return answerer.answer(query, endpoint="ask", **kw)


def staged(answerer, query=QUERY):
    """The Stages the Answerer reports for a Query, and its result."""
    seen = []
    answered = ask(answerer, query, on_stage=seen.append)
    return seen, answered


# ── Verdict routing ────────────────────────────────────────────────────────


def test_a_correct_verdict_answers_from_the_corpus_alone(make_answerer):
    fb = RecordingFallback()
    answered = ask(make_answerer(FakeLLM(score=0.9), fb))
    r = answered.response
    assert r.trust_label == "corpus"
    assert r.fallback_sources == []
    assert r.citations
    assert r.citations[0].text == ART_21.text  # verbatim, from the Corpus
    assert fb.queries == []
    d = answered.decisions
    assert (d.grader_score, d.verdict, d.fallback_sources) == (0.9, "correct", None)
    assert d.citation_recheck is False and d.citation_blocked is False


def test_an_incorrect_verdict_answers_from_the_fallback_with_a_rewritten_query(
    make_answerer,
):
    fb = RecordingFallback()
    llm = RewritingLLM(score=0.1)
    answered = ask(make_answerer(llm, fb))
    r = answered.response
    assert fb.queries == [f"rewritten: {QUERY}"]
    assert r.trust_label == "fallback"
    assert r.fallback_sources == [WEB]
    assert r.citations == []
    assert list(llm.sources_seen) == [WEB]
    d = answered.decisions
    assert (d.grader_score, d.verdict, d.fallback_sources) == (0.1, "incorrect", 1)
    assert d.citation_recheck is None  # no Provision was cited, so none was checked


def test_an_ambiguous_verdict_combines_the_corpus_and_the_fallback(make_answerer):
    fb = RecordingFallback()
    answered = ask(make_answerer(RewritingLLM(score=0.5), fb))
    r = answered.response
    assert fb.queries == [f"rewritten: {QUERY}"]
    assert r.trust_label == "corpus_and_fallback"
    assert r.fallback_sources == [WEB]
    assert r.citations
    d = answered.decisions
    assert (d.verdict, d.fallback_sources) == ("ambiguous", 1)


@pytest.mark.parametrize(
    "fb", [RecordingFallback(fail=True), RecordingFallback(results=())]
)
def test_ambiguous_with_a_failed_or_empty_fallback_degrades_to_the_corpus_alone(
    make_answerer, fb
):
    answered = ask(make_answerer(FakeLLM(score=0.5), fb))
    r = answered.response
    assert r.trust_label == "corpus"
    assert r.fallback_sources == []
    assert r.citations
    assert answered.decisions.fallback_sources == 0


@pytest.mark.parametrize(
    "fb", [RecordingFallback(fail=True), RecordingFallback(results=())]
)
def test_incorrect_with_a_failed_or_empty_fallback_says_it_cannot_answer(
    make_answerer, fb
):
    r = ask(make_answerer(FakeLLM(score=0.1), fb)).response
    assert "cannot answer" in r.answer.lower()
    assert r.trust_label == "none"  # neither the Corpus nor the Fallback supports it
    assert r.citations == []
    assert r.fallback_sources == []


def test_a_fallback_only_answer_never_returns_citations_even_if_the_model_cites(
    make_answerer,
):
    class CitingLLM(FakeLLM):
        def generate(self, query, provisions, sources=(), language="en"):
            return Generation(
                answer="x", citations=[ProvisionRef(act=ART_21.act, number="21")]
            )

    r = ask(make_answerer(CitingLLM(score=0.1), RecordingFallback())).response
    assert r.citations == []


def test_a_failed_rewrite_degrades_like_a_failed_fallback(make_answerer):
    class BrokenRewriteLLM(FakeLLM):
        def rewrite(self, query):
            raise RuntimeError("quota")

    r = ask(make_answerer(BrokenRewriteLLM(score=0.5), RecordingFallback())).response
    assert r.trust_label == "corpus"


def test_plain_rag_never_grades_or_falls_back(make_answerer):
    fb = RecordingFallback()
    answered = ask(make_answerer(FakeLLM(score=0.0), fb, crag=False))
    assert fb.queries == []
    assert answered.response.trust_label == "corpus"
    assert answered.response.citations
    d = answered.decisions
    assert (d.grader_score, d.verdict, d.fallback_sources) == (None, None, None)


def test_the_llm_sees_the_ten_best_matches(make_answerer):
    wages = [
        Provision(
            act="Code on Wages",
            chapter="Chapter II",
            number=str(n),
            status="in_force",
            text=f"employer pays wages {n}",
        )
        for n in range(1, 11)
    ]
    llm = FakeLLM()
    ask(make_answerer(llm, provisions=wages), "employer pays wages")
    assert len(llm.seen) == TOP_K == 10


def test_a_repealed_provision_is_cited_with_its_status(make_answerer):
    r = ask(
        make_answerer(FakeLLM()), "punishment for murder death imprisonment"
    ).response
    assert r.citations[0].status == "repealed"


def test_a_long_provision_is_cited_whole_when_a_query_matches_one_part(make_answerer):
    filler = " ".join(["registers records authority prescribed notice period"] * 14)
    key = "(7) Whoever dishonestly takes a movable phone commits theft."
    long = Provision(
        act="Test Code",
        chapter="Chapter I",
        number="303",
        status="in_force",
        text="\n".join([filler] * 3 + [key] + [filler] * 3),
    )
    decoys = [
        Provision(
            act="Test Code",
            chapter="Chapter II",
            number=str(400 + i),
            status="in_force",
            text=f"A short note on phone theft, item {i}.",
        )
        for i in range(12)
    ]

    class Wide(FakeEmbedder):
        dim = 4096

    answerer = make_answerer(FakeLLM(), provisions=[long, *decoys], embedder=Wide())
    c = ask(
        answerer, "Whoever dishonestly takes a movable phone commits theft"
    ).response.citations[0]
    assert (c.act, c.number) == ("Test Code", "303")
    assert c.text == long.text


# ── Stages ─────────────────────────────────────────────────────────────────

GRADED = ["scope_check", "retrieval", "grading"]
CHECKED = ["generation", "citation_check"]

STAGE_CASES = {
    "correct": (lambda: FakeLLM(score=0.9), None, GRADED + CHECKED),
    "ambiguous": (lambda: FakeLLM(score=0.5), None, GRADED + ["fallback"] + CHECKED),
    "incorrect": (
        lambda: FakeLLM(score=0.1),
        None,
        GRADED + ["fallback", "generation"],
    ),
    "failed_fallback": (
        lambda: FakeLLM(score=0.1),
        RecordingFallback(fail=True),
        GRADED + ["fallback"],
    ),
    "recheck": (
        HallucinatingThenValidLLM,
        None,
        GRADED + CHECKED + ["citation_recheck"],
    ),
    "blocked": (AlwaysHallucinatingLLM, None, GRADED + CHECKED + ["citation_recheck"]),
    "out_of_scope": (OutOfScopeLLM, None, ["scope_check"]),
}


@pytest.mark.parametrize("case", STAGE_CASES)
def test_stages_are_reported_in_order_for_every_path(make_answerer, case):
    make_llm, fb, expected = STAGE_CASES[case]
    seen, _ = staged(make_answerer(make_llm(), fb))
    assert [s.id for s in seen] == expected


def test_stage_labels_are_plain_language_never_verdict_words(make_answerer):
    for make_llm, fb, _ in STAGE_CASES.values():
        seen, _ = staged(make_answerer(make_llm(), fb))
        for stage in seen:
            words = set(re.findall(r"\w+", stage.label.lower()))
            assert (
                stage.label
                and not {"correct", "ambiguous", "incorrect", "verdict"} & words
            )


def test_english_stage_labels_are_english(make_answerer):
    seen, _ = staged(make_answerer(FakeLLM()))
    assert seen[0].label == "Checking your question"
    assert not any(devanagari(s.label) for s in seen)


def test_a_hindi_query_gets_hindi_stage_labels(make_answerer):
    seen, _ = staged(make_answerer(FakeLLM()), HINDI_QUERY)
    assert seen
    assert all(devanagari(s.label) for s in seen)


# ── Refusal ────────────────────────────────────────────────────────────────


class ScopedLLM(FakeLLM):
    def __init__(self, decision: ScopeDecision):
        super().__init__()
        self.decision = decision
        self.generated = False

    def classify(self, query):
        return self.decision

    def generate(self, query, provisions, sources=(), language="en"):
        self.generated = True
        return super().generate(query, provisions, sources, language)


def test_a_non_indian_law_query_is_refused_with_a_reason_and_a_reformulation(
    make_answerer,
):
    decision = ScopeDecision(
        category="not_indian_law",
        reason="This question is about US law, which LegalLens does not cover.",
        suggested_reformulation="Ask what Indian law says about the same situation.",
    )
    llm = ScopedLLM(decision)
    answered = ask(make_answerer(llm), "What is the US tax code?")
    r = answered.response
    assert r.response_type == "refusal"
    assert r.refusal_reason == decision.reason
    assert r.suggested_reformulation == decision.suggested_reformulation
    assert r.citations == []
    assert r.trust_label == "none"  # no source supports a refusal
    assert not llm.generated
    assert answered.decisions.grader_score is None  # refused before retrieval


@pytest.mark.parametrize("category", ["personal_advice", "not_indian_law"])
def test_a_refusal_without_a_reason_gets_a_default_reason_and_reformulation(
    make_answerer, category
):
    llm = ScopedLLM(ScopeDecision(category=category))
    r = ask(make_answerer(llm), "Best pizza in Rome?").response
    assert r.response_type == "refusal"
    assert r.refusal_reason
    assert r.suggested_reformulation
    assert not llm.generated


def test_an_in_scope_query_is_not_refused(make_answerer):
    llm = ScopedLLM(ScopeDecision(category="in_scope"))
    r = ask(make_answerer(llm)).response
    assert r.response_type == "answer"
    assert r.refusal_reason is None
    assert r.citations
    assert llm.generated


# ── Hindi ──────────────────────────────────────────────────────────────────

HINDI_TO_ENGLISH = {"स्वतंत्रता": "liberty", "व्यक्तिगत": "personal", "वंचित": "deprived"}


class MultilingualFakeEmbedder(FakeEmbedder):
    """Stands in for a multilingual model: Hindi words land where their English ones do."""

    def embed(self, texts, *, is_query):
        def translate(t):
            for hi, en in HINDI_TO_ENGLISH.items():
                t = t.replace(hi, en)
            return t

        return super().embed([translate(t) for t in texts], is_query=is_query)


class LanguageAwareLLM(FakeLLM):
    """Answers in the language it is asked for, citing the top Provision."""

    def generate(self, query, provisions, sources=(), language="en"):
        top = provisions[0]
        answer = (
            HINDI_ANSWER if language == "hi" else f"Summary of {top.act} {top.number}."
        )
        return Generation(
            answer=answer, citations=[ProvisionRef(act=top.act, number=top.number)]
        )


@pytest.fixture
def hindi_answerer(make_answerer):
    def make(llm=None, **kw):
        return make_answerer(
            llm or LanguageAwareLLM(),
            provisions=[ART_21, IPC_302],
            embedder=MultilingualFakeEmbedder(),
            **kw,
        )

    return make


def test_a_hindi_query_retrieves_the_article_and_is_answered_in_hindi(hindi_answerer):
    r = ask(hindi_answerer(), HINDI_LIBERTY).response
    top = r.citations[0]
    assert (top.act, top.number) == ("Constitution of India", "21")
    assert top.text == ART_21.text  # the citation stays the English Provision
    assert r.answer_language == "hi"
    assert devanagari(r.answer)


def test_an_english_query_is_answered_in_english(hindi_answerer):
    r = ask(hindi_answerer()).response
    assert r.answer_language == "en"
    assert not devanagari(r.answer)


def test_a_mixed_script_query_that_is_mostly_hindi_is_hindi(hindi_answerer):
    r = ask(hindi_answerer(), "Article 21 क्या है और स्वतंत्रता का अधिकार क्या है?").response
    assert r.answer_language == "hi"


def test_a_hindi_refusal_is_in_hindi(hindi_answerer):
    class Refusing(LanguageAwareLLM):
        def classify(self, query):
            return ScopeDecision(category="personal_advice")

    r = ask(hindi_answerer(Refusing()), "क्या मुझे मुकदमा करना चाहिए?").response
    assert (r.response_type, r.answer_language) == ("refusal", "hi")
    assert devanagari(r.refusal_reason) and devanagari(r.suggested_reformulation)


def test_a_hindi_refusal_keeps_the_reason_the_llm_gave(hindi_answerer):
    class Refusing(LanguageAwareLLM):
        def classify(self, query):
            return ScopeDecision(
                category="personal_advice", reason="मैं सलाह नहीं दे सकता।"
            )

    r = ask(hindi_answerer(Refusing()), "क्या मुझे मुकदमा करना चाहिए?").response
    assert r.refusal_reason == "मैं सलाह नहीं दे सकता।"


def test_a_hindi_cannot_answer_message_is_in_hindi(hindi_answerer):
    r = ask(
        hindi_answerer(LanguageAwareLLM(score=0.0), fallback=FakeFallback()),
        HINDI_LIBERTY,
    ).response
    assert r.trust_label == "none"
    assert r.answer_language == "hi" and devanagari(r.answer)


def test_a_hindi_unreliable_citations_message_is_in_hindi(hindi_answerer):
    r = ask(hindi_answerer(AlwaysHallucinatingLLM()), HINDI_LIBERTY).response
    assert r.answer_language == "hi" and devanagari(r.answer)


# ── Citation recheck and block ─────────────────────────────────────────────


def test_a_hallucinated_citation_triggers_one_regeneration(make_answerer):
    llm = HallucinatingThenValidLLM()
    answered = ask(make_answerer(llm, provisions=[ART_21]))
    refs = [(c.act, c.number) for c in answered.response.citations]
    assert llm.calls == 2
    assert ("Indian Penal Code", "420") not in refs
    assert ("Constitution of India", "21") in refs
    assert answered.decisions.citation_recheck is True
    assert answered.decisions.citation_blocked is False


def test_a_citation_still_hallucinated_after_the_rewrite_is_blocked(make_answerer):
    llm = AlwaysHallucinatingLLM()
    answered = ask(make_answerer(llm, provisions=[ART_21]))
    assert llm.calls == 2
    assert answered.response.citations == []
    assert answered.response.trust_label == "none"
    assert "cannot answer reliably" in answered.response.answer.lower()
    assert answered.decisions.citation_recheck is True
    assert answered.decisions.citation_blocked is True


# ── Cache ──────────────────────────────────────────────────────────────────


class CountingLLM(FakeLLM):
    """Counts scope checks: one per question that reaches the corrective loop."""

    def __init__(self, score=1.0):
        super().__init__(score)
        self.questions = 0

    def classify(self, query):
        self.questions += 1
        return super().classify(query)


def test_a_repeated_query_is_served_from_the_cache_with_no_stages(make_answerer):
    llm = CountingLLM()
    answerer = make_answerer(llm, cache=AnswerCache())
    first = ask(answerer)
    seen, second = staged(answerer, "  can I be DEPRIVED of   personal liberty? ")
    assert second.response == first.response
    assert seen == []
    assert llm.questions == 1


def test_a_different_query_is_not_served_from_the_cache(make_answerer):
    llm = CountingLLM()
    answerer = make_answerer(llm, cache=AnswerCache())
    ask(answerer)
    ask(answerer, "What is the punishment for murder?")
    assert llm.questions == 2


def test_a_cannot_answer_message_is_not_cached(make_answerer):
    llm = CountingLLM(score=0.0)  # the Fallback finds nothing
    answerer = make_answerer(llm, FakeFallback(), cache=AnswerCache())
    assert ask(answerer).response.trust_label == "none"
    ask(answerer)
    assert llm.questions == 2


def test_a_refusal_is_cached(make_answerer):
    class CountingOutOfScope(OutOfScopeLLM):
        questions = 0

        def classify(self, query):
            self.questions += 1
            return super().classify(query)

    llm = CountingOutOfScope()
    answerer = make_answerer(llm, cache=AnswerCache())
    first = ask(answerer, "What is the US tax code?").response
    assert first.response_type == "refusal"
    assert ask(answerer, "What is the US tax code?").response == first
    assert llm.questions == 1


def test_no_cache_means_every_question_runs(make_answerer):
    llm = CountingLLM()
    answerer = make_answerer(llm)
    ask(answerer)
    ask(answerer)
    assert llm.questions == 2


def test_a_cache_hit_has_no_decisions_to_report(make_answerer):
    answerer = make_answerer(FakeLLM(score=0.9), cache=AnswerCache())
    ask(answerer)
    d = ask(answerer).decisions
    assert (d.grader_score, d.verdict, d.fallback_sources) == (None, None, None)


# ── Cancellation ───────────────────────────────────────────────────────────


def test_a_cancel_set_before_the_first_stage_stops_the_work_at_once(make_answerer):
    llm = CountingLLM()
    cancel = threading.Event()
    cancel.set()
    seen = []
    with pytest.raises(Cancelled):
        ask(make_answerer(llm), cancel=cancel, on_stage=seen.append)
    assert seen == [] and llm.questions == 0


def test_a_cancel_is_noticed_at_the_next_stage_boundary(make_answerer):
    cancel = threading.Event()
    llm = FakeLLM(score=0.9)
    seen = []

    def on_stage(stage):
        seen.append(stage.id)
        if stage.id == "retrieval":
            cancel.set()

    with pytest.raises(Cancelled):
        ask(make_answerer(llm), cancel=cancel, on_stage=on_stage)
    assert seen == ["scope_check", "retrieval"]  # grading never started
    assert llm.seen == []  # nothing was generated


def test_a_cancel_during_the_fallback_stage_is_not_swallowed(make_answerer):
    cancel = threading.Event()

    class CancellingFallback:
        def search(self, query):
            cancel.set()  # the client leaves while the web search runs
            raise RuntimeError("provider down")  # the pipeline degrades past this

    llm = FakeLLM(score=0.5)
    with pytest.raises(Cancelled):
        ask(make_answerer(llm, CancellingFallback()), cancel=cancel)
    assert llm.seen == []  # the generation Stage never started


def test_a_cancel_that_arrives_when_the_answer_is_done_still_returns_it(make_answerer):
    cancel = threading.Event()
    answered = ask(
        make_answerer(FakeLLM(score=0.9)),
        cancel=cancel,
        on_stage=lambda s: s.id == "citation_check" and cancel.set(),
    )
    assert answered.response.citations  # no Stage followed, so nothing to cancel


# ── Failures ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("llm", "stage"),
    [
        (ScopeFailsLLM(), "scope_check"),
        (BrokenLLM(), "grading"),
        (GenerationFailsLLM(score=0.9), "generation"),
    ],
)
def test_a_failure_raises_one_typed_error_naming_the_stage(make_answerer, llm, stage):
    with pytest.raises(StageFailed) as caught:
        ask(make_answerer(llm))
    assert caught.value.stage == stage


def test_a_failed_answer_is_not_cached(make_answerer):
    cache = AnswerCache()
    with pytest.raises(StageFailed):
        ask(make_answerer(GenerationFailsLLM(score=0.9), cache=cache))
    assert cache.get(QUERY) is None
