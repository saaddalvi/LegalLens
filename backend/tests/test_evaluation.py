from test_ask import ART_21, IPC_302, FakeEmbedder, FakeLLM

from legallens.corpus import Corpus
from legallens.evaluation import GoldenCase, render_report, run_evaluation
from legallens.llm import Generation, ProvisionRef, ScopeDecision
from legallens.models import FallbackSource

WEB = FallbackSource(
    title="Explainer", url="https://example.org/x", snippet="Web snippet."
)


class StubFallback:
    def search(self, query):
        return [WEB]


class EvalLLM(FakeLLM):
    """Refuses 'should I sue' Queries, grades 'obscure' Queries as poorly retrieved,
    and answers from the web alone when it is given no Provisions."""

    def classify(self, query):
        if "should i sue" in query.lower():
            return ScopeDecision(category="personal_advice")
        return ScopeDecision(category="in_scope")

    def grade(self, query, provisions):
        return 0.1 if "obscure" in query else 0.9

    def generate(self, query, provisions, sources=(), language="en"):
        if "ghost" in query:
            return Generation(
                answer="ghost",
                citations=[ProvisionRef(act="Indian Penal Code", number="420")],
            )
        if sources and not provisions:
            return Generation(answer="web-answer", citations=[])
        return super().generate(query, provisions, sources, language)


class ReferenceJudge:
    """Accurate when the answer mentions the case's reference text."""

    def is_accurate(self, case, response):
        return case.reference.lower() in response.answer.lower()


CASES = [
    GoldenCase(
        id="en-liberty",
        category="english",
        query="Can I be deprived of personal liberty?",
        expected_provisions=[ProvisionRef(act=ART_21.act, number="21")],
        reference="Constitution of India 21",
    ),
    GoldenCase(
        id="en-miss",
        category="english",
        query="Can I be deprived of personal liberty? ghost",
        expected_provisions=[ProvisionRef(act=IPC_302.act, number="302")],
        reference="never matches",
    ),
    GoldenCase(
        id="oos-sue",
        category="out_of_scope",
        query="Should I sue my landlord?",
        expect_refusal=True,
    ),
    GoldenCase(
        id="poor-obscure",
        category="poor_retrieval",
        query="obscure question about liberty",
        reference="web-answer",
    ),
]


def run(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return run_evaluation(
        CASES,
        corpus=corpus,
        llm=EvalLLM(),
        fallback=StubFallback(),
        judge=ReferenceJudge(),
    )


def test_crag_beats_plain_rag_on_poor_retrieval_and_both_refuse_out_of_scope(tmp_path):
    result = run(tmp_path)
    plain, crag = result.modes["plain"], result.modes["crag"]
    # Retrieval hit-rate counts only cases with expected Provisions (en-liberty hits, en-miss does not).
    assert plain.retrieval_hit_rate == crag.retrieval_hit_rate == 0.5
    # Accuracy: en-liberty and oos-sue are right in both modes; only CRAG answers poor-obscure from the web.
    assert plain.answer_accuracy == 0.5
    assert crag.answer_accuracy == 0.75
    assert crag.by_category["poor_retrieval"].answer_accuracy == 1.0
    assert plain.by_category["poor_retrieval"].answer_accuracy == 0.0
    assert plain.by_category["out_of_scope"].answer_accuracy == 1.0


def test_citation_validity_is_reported_per_mode(tmp_path):
    result = run(tmp_path)
    for mode in result.modes.values():
        assert (
            mode.citation_validity == 1.0
        )  # the endpoint never lets a hallucination through


def test_report_shows_plain_versus_crag_on_every_metric(tmp_path):
    report = render_report(run(tmp_path))
    for metric in ("Retrieval hit-rate", "Answer accuracy", "Citation validity"):
        row = next(line for line in report.splitlines() if metric in line)
        assert "Plain RAG" not in row and row.count("%") >= 2
    assert "Plain RAG" in report and "CRAG" in report
    assert "poor_retrieval" in report


def test_report_shows_case_counts_per_mode_when_modes_error_on_different_cases(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("time.sleep", lambda s: None)

    class GraderDown(EvalLLM):
        def grade(self, query, provisions):  # only CRAG calls the Grader
            if "liberty?" in query and "ghost" not in query:
                raise RuntimeError("503")
            return super().grade(query, provisions)

    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    result = run_evaluation(
        CASES,
        corpus=corpus,
        llm=GraderDown(),
        fallback=StubFallback(),
        judge=ReferenceJudge(),
    )
    assert result.modes["plain"].cases == 4
    assert result.modes["crag"].cases == 3
    report = render_report(result)
    overall = next(line for line in report.splitlines() if line.startswith("## Overall"))
    assert "Plain RAG: 4" in overall and "CRAG: 3" in overall


def test_report_shows_hallucinated_citation_rate_before_the_endpoint_blocks_them(
    tmp_path,
):
    result = run(tmp_path)
    plain, crag = result.modes["plain"], result.modes["crag"]
    # en-miss ("ghost") hallucinates on both attempts and is blocked. Plain RAG checks three
    # generations (en-liberty, en-miss, poor-obscure); CRAG answers poor-obscure from the web
    # alone, where no Citations are checked, so it checks two.
    assert plain.hallucinated_before_block_rate == 1 / 3
    assert crag.hallucinated_before_block_rate == 0.5
    assert plain.citation_validity == crag.citation_validity == 1.0
    report = render_report(result)
    row = next(l for l in report.splitlines() if "Hallucinated citations before" in l)
    assert "33%" in row and "50%" in row
