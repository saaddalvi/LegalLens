import json

import pytest
from fastapi.testclient import TestClient
from test_ask import (
    ART_21,
    IPC_302,
    AlwaysHallucinatingLLM,
    FakeEmbedder,
    FakeLLM,
    HallucinatingThenValidLLM,
)
from test_crag import QUERY, RecordingFallback

from legallens.corpus import Corpus
from legallens.llm import ScopeDecision
from legallens.main import create_app

HINDI_QUERY = "क्या मुझे जीवन और स्वतंत्रता का अधिकार है?"


def make_client(tmp_path, llm, fallback=None):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add([ART_21, IPC_302])
    return TestClient(
        create_app(corpus=corpus, llm=llm, fallback=fallback or RecordingFallback())
    )


def parse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def stream(client, query=QUERY):
    r = client.post("/ask/stream", json={"query": query})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse(r.text)


def stage_ids(events):
    return [d["id"] for name, d in events if name == "stage"]


class OutOfScopeLLM(FakeLLM):
    def classify(self, query):
        return ScopeDecision(category="personal_advice", reason="Not for me.")


class BrokenLLM(FakeLLM):
    def grade(self, query, provisions):
        raise RuntimeError("gemini down")


CASES = {
    "correct": (lambda: FakeLLM(score=0.9), None,
        ["scope_check", "retrieval", "grading", "generation", "citation_check"]),
    "ambiguous": (lambda: FakeLLM(score=0.5), None,
        ["scope_check", "retrieval", "grading", "fallback", "generation", "citation_check"]),
    "incorrect": (lambda: FakeLLM(score=0.1), None,
        ["scope_check", "retrieval", "grading", "fallback", "generation"]),
    "failed_fallback": (lambda: FakeLLM(score=0.1), RecordingFallback(fail=True),
        ["scope_check", "retrieval", "grading", "fallback"]),
    "recheck": (HallucinatingThenValidLLM, None,
        ["scope_check", "retrieval", "grading", "generation", "citation_check", "citation_recheck"]),
    "blocked": (AlwaysHallucinatingLLM, None,
        ["scope_check", "retrieval", "grading", "generation", "citation_check", "citation_recheck"]),
    "out_of_scope": (OutOfScopeLLM, None, ["scope_check"]),
}


@pytest.mark.parametrize("case", CASES)
def test_stage_sequence_and_answer_equals_ask(tmp_path, case):
    make_llm, fb, expected = CASES[case]
    events = stream(make_client(tmp_path, make_llm(), fb))
    assert stage_ids(events) == expected
    assert [n for n, _ in events][-1] == "answer"
    assert [n for n, _ in events].count("answer") == 1
    fresh = make_client(tmp_path / "again", make_llm(), fb)
    assert events[-1][1] == fresh.post("/ask", json={"query": QUERY}).json()


def test_hindi_query_gets_hindi_labels(tmp_path):
    events = stream(make_client(tmp_path, FakeLLM(score=0.9)), HINDI_QUERY)
    labels = [d["label"] for n, d in events if n == "stage"]
    assert labels
    assert all(any("ऀ" <= ch <= "ॿ" for ch in label) for label in labels)


def test_labels_never_show_verdict_words(tmp_path):
    for make_llm, fb, _ in CASES.values():
        events = stream(make_client(tmp_path / str(id(make_llm)), make_llm(), fb))
        for n, d in events:
            if n == "stage":
                assert not {"correct", "ambiguous", "incorrect", "verdict"} & set(
                    d["label"].lower().split()
                )


def test_exception_emits_error_naming_the_running_stage(tmp_path):
    events = stream(make_client(tmp_path, BrokenLLM()))
    assert events[-1][0] == "error"
    assert events[-1][1]["stage"] == "grading"
    assert "unavailable" in events[-1][1]["message"]
    assert "answer" not in [n for n, _ in events]
