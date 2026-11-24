from urllib.parse import quote

import pytest
from conftest import ART_21, IPC_302, FakeEmbedder, FakeFallback, FakeLLM
from fastapi.testclient import TestClient

from legallens.corpus import Corpus
from legallens.main import create_app
from legallens.models import Provision
from legallens.rate_limit import RateLimiter

CONSTITUTION = "Constitution of India"
OSH = "Occupational Safety, Health and Working Conditions Code"


def article(number, text="Some article text."):
    return Provision(
        act=CONSTITUTION,
        chapter="Part III",
        number=number,
        status="in_force",
        text=text,
    )


BNS_103 = Provision(
    act="Bharatiya Nyaya Sanhita",
    chapter="Chapter VI",
    number="103",
    status="in_force",
    text="(1) Whoever commits murder shall be punished with death.",
    supersedes="Indian Penal Code 302",
)
IPC_302_WITH_SUCCESSOR = IPC_302.model_copy(
    update={"superseded_by": "Bharatiya Nyaya Sanhita 103"}
)
OSH_1 = Provision(
    act=OSH, chapter="Chapter I", number="1", status="in_force", text="Short title."
)
LONG = ("x" * 400 + "\n") * 3 + "end"  # over 800 characters: stored as several pieces


@pytest.fixture
def corpus(tmp_path):
    c = Corpus(tmp_path / "chroma", FakeEmbedder())
    c.add(
        [
            # Added out of order on purpose; a long text is stored as several pieces.
            article("100"),
            ART_21,
            article("21A"),
            article("9"),
            article("14", LONG),
            IPC_302_WITH_SUCCESSOR,
            BNS_103,
            OSH_1,
        ]
    )
    return c


@pytest.fixture
def client(corpus):
    return TestClient(create_app(corpus=corpus, llm=FakeLLM(), fallback=FakeFallback()))


def test_an_acts_provisions_come_back_in_statute_order_once_each(corpus):
    numbers = [p.number for p in corpus.list_act(CONSTITUTION)]
    assert numbers == ["9", "14", "21", "21A", "100"]  # 21A after 21, 100 last


def test_an_unknown_act_has_no_provisions(corpus):
    assert corpus.list_act("Nonexistent Act") == []


def test_acts_lists_each_act_with_its_provision_count(client):
    body = client.get("/acts").json()
    assert body == [
        {"act": "Bharatiya Nyaya Sanhita", "provisions": 1},
        {"act": CONSTITUTION, "provisions": 5},
        {"act": "Indian Penal Code", "provisions": 1},
        {"act": OSH, "provisions": 1},
    ]


def test_an_act_lists_its_provisions_with_a_short_first_line(client):
    body = client.get(f"/acts/{quote(CONSTITUTION)}").json()
    assert body["act"] == CONSTITUTION
    assert [p["number"] for p in body["provisions"]] == ["9", "14", "21", "21A", "100"]
    fourteen = next(p for p in body["provisions"] if p["number"] == "14")
    assert fourteen["chapter"] == "Part III" and fourteen["status"] == "in_force"
    assert len(fourteen["snippet"]) == 160 and fourteen["snippet"].endswith("…")
    nine = next(p for p in body["provisions"] if p["number"] == "9")
    assert nine["snippet"] == "Some article text."
    assert "text" not in nine  # the full text is for the Provision itself


def test_an_act_name_with_a_comma_works_in_the_address(client):
    body = client.get(f"/acts/{quote(OSH)}").json()
    assert [p["number"] for p in body["provisions"]] == ["1"]


def test_an_unknown_act_is_404(client):
    assert client.get("/acts/Nonexistent%20Act").status_code == 404


def test_a_provision_comes_back_whole(client):
    r = client.get(f"/provision/{quote(CONSTITUTION)}/21")
    assert r.status_code == 200
    assert r.json() == ART_21.model_dump(mode="json")


def test_a_long_provision_comes_back_whole_not_as_a_piece(client):
    assert client.get(f"/provision/{quote(CONSTITUTION)}/14").json()["text"] == LONG


def test_a_repealed_provision_names_what_replaced_it_and_back(client):
    old = client.get("/provision/Indian%20Penal%20Code/302").json()
    assert old["status"] == "repealed"
    assert old["superseded_by"] == "Bharatiya Nyaya Sanhita 103"
    new = client.get("/provision/Bharatiya%20Nyaya%20Sanhita/103").json()
    assert new["supersedes"] == "Indian Penal Code 302"


def test_the_letter_in_a_number_may_be_typed_in_either_case(client):
    r = client.get(f"/provision/{quote(CONSTITUTION)}/21a")
    assert r.status_code == 200 and r.json()["number"] == "21A"


@pytest.mark.parametrize(
    "path",
    [
        f"/provision/{quote(CONSTITUTION)}/999",
        "/provision/Nonexistent%20Act/1",
    ],
)
def test_a_missing_provision_is_404(client, path):
    assert client.get(path).status_code == 404


def test_browsing_is_not_rate_limited_because_it_costs_no_gemini_calls(corpus):
    client = TestClient(
        create_app(
            corpus=corpus,
            llm=FakeLLM(),
            fallback=FakeFallback(),
            rate_limiter=RateLimiter(per_minute=1, per_day=1),
        )
    )
    for _ in range(5):
        assert client.get("/acts").status_code == 200
        assert client.get(f"/provision/{quote(CONSTITUTION)}/21").status_code == 200
