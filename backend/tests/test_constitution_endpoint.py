import json
from pathlib import Path

from conftest import FakeEmbedder, FakeFallback, FakeLLM, FakeVerifier, signed_in

from legallens.build_corpus import build
from legallens.corpus import Corpus
from legallens.main import create_app

RAW = json.loads(
    (Path(__file__).parent / "fixtures" / "constitution_raw.json").read_text()
)


def test_constitutional_query_against_built_corpus_cites_expected_article(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    build(corpus, RAW, patches=[])
    client = signed_in(
        create_app(
            verifier=FakeVerifier(),
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
        )
    )

    body = client.post(
        "/ask",
        json={
            "query": "free and compulsory education for children aged six to fourteen"
        },
    ).json()

    cite = body["citations"][0]
    assert (cite["act"], cite["number"]) == ("Constitution of India", "21A")
    assert cite["chapter"] == "Part III"
    assert cite["status"] == "in_force"
    assert cite["text"].startswith(
        "The State shall provide free and compulsory education"
    )


def test_repealed_article_is_cited_with_repealed_status(tmp_path):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    build(corpus, RAW, patches=[])
    client = signed_in(
        create_app(
            verifier=FakeVerifier(),
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
        )
    )

    body = client.post(
        "/ask",
        json={"query": "Compulsory acquisition of property Forty-fourth Amendment"},
    ).json()

    assert (body["citations"][0]["number"], body["citations"][0]["status"]) == (
        "31",
        "repealed",
    )
