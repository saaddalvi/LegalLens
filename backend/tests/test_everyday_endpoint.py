"""Everyday-law Queries answered with Citations to consumer, tenancy and labour Provisions."""

import json
from pathlib import Path

import pytest
from conftest import FakeEmbedder, FakeFallback, FakeLLM, FakeVerifier, signed_in

from legallens.build_corpus import build
from legallens.corpus import Corpus
from legallens.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"
EVERYDAY = json.loads((FIXTURES / "everyday_acts_raw.json").read_text())
CONSTITUTION = json.loads((FIXTURES / "constitution_raw.json").read_text())


class WideEmbedder(FakeEmbedder):
    """The shared hashing embedder, widened and length-normalised so a long Provision does not
    outrank a short, closer one on word collisions alone."""

    dim = 4096

    def embed(self, texts, *, is_query):
        out = []
        for v in super().embed(texts, is_query=is_query):
            norm = sum(x * x for x in v) ** 0.5 or 1.0
            out.append([x / norm for x in v])
        return out


@pytest.fixture
def client(tmp_path):
    corpus = Corpus(tmp_path / "chroma", WideEmbedder())
    build(corpus, CONSTITUTION, patches=[], everyday_acts=EVERYDAY)
    return signed_in(
        create_app(
            verifier=FakeVerifier(),
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
        )
    )


def first_citation(client, query):
    body = client.post("/ask", json={"query": query}).json()
    assert body["response_type"] == "answer"
    return body["citations"][0]


def test_informal_tenancy_query_cites_the_lease_provisions(client):
    c = first_citation(
        client,
        "I have only an oral lease and no written contract. How much notice must my "
        "landlord give to end a month to month lease?",
    )
    assert c["act"] == "Transfer of Property Act"
    assert c["number"] == "106"
    assert c["status"] == "in_force"
    assert "fifteen days' notice" in c["text"]


def test_rental_deposit_query_cites_the_model_tenancy_act(client):
    c = first_citation(
        client,
        "My landlord will not refund my security deposit after I vacated. How many "
        "months rent can a security deposit be and when must it be refunded?",
    )
    assert c["act"] == "Model Tenancy Act"
    assert c["number"] == "11"
    assert c["status"] == "model"
    assert "refunded to the tenant on the date of" in c["text"]


def test_model_act_provision_reaches_the_llm_with_its_status(tmp_path):
    corpus = Corpus(tmp_path / "chroma", WideEmbedder())
    build(corpus, CONSTITUTION, patches=[], everyday_acts=EVERYDAY)
    llm = FakeLLM()
    app_client = signed_in(
        create_app(
            verifier=FakeVerifier(), corpus=corpus, llm=llm, fallback=FakeFallback()
        )
    )
    first_citation(
        app_client,
        "How many months rent can a security deposit be and when must it be refunded?",
    )
    assert llm.seen[0].act == "Model Tenancy Act"
    assert llm.seen[0].status == "model"


def test_consumer_query_cites_the_consumer_protection_act(client):
    c = first_citation(
        client,
        "The shop sold me defective goods and gave poor service. How do I file a "
        "complaint as a consumer with the District Commission?",
    )
    assert c["act"] == "Consumer Protection Act"
    assert c["number"] in {"35", "39"}  # filing a complaint; defects and remedies
    assert c["chapter"] == "Chapter IV"


def test_labour_query_cites_the_code_on_wages(client):
    c = first_citation(
        client,
        "By when must the employer pay wages to employees engaged on a monthly basis?",
    )
    assert c["act"] == "Code on Wages"
    assert c["number"] == "17"


def test_named_everyday_section_is_found_directly(client):
    c = first_citation(
        client,
        "What does section 53 of the Code on Social Security say about gratuity?",
    )
    assert (c["act"], c["number"]) == ("Code on Social Security", "53")
