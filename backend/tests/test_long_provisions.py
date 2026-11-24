"""A long Provision is found by a Query that matches only one part of it."""

from conftest import FakeEmbedder

from legallens.corpus import Corpus
from legallens.models import Provision


class WideEmbedder(FakeEmbedder):
    dim = 4096


FILLER = " ".join(
    ["registers records authority prescribed notice period"] * 14
)  # ~790 chars
KEY = "(7) Whoever dishonestly takes a movable phone commits theft."
LONG = Provision(
    act="Test Code",
    chapter="Chapter I",
    number="303",
    status="in_force",
    text="\n".join([FILLER] * 3 + [KEY] + [FILLER] * 3),
)
DECOYS = [
    Provision(
        act="Test Code",
        chapter="Chapter II",
        number=str(400 + i),
        status="in_force",
        text=f"A short note on phone theft, item {i}.",
    )
    for i in range(12)
]


def test_each_provision_is_counted_once(tmp_path):
    corpus = Corpus(tmp_path / "chroma", WideEmbedder())
    corpus.add([LONG, *DECOYS])
    assert corpus.count() == 1 + len(DECOYS)
    found = corpus.search("dishonestly takes a movable phone", 5)
    assert len({(p.act, p.number) for p in found}) == len(found)


def test_a_corpus_larger_than_one_upsert_batch_is_stored_whole(tmp_path, monkeypatch):
    monkeypatch.setattr("legallens.corpus._UPSERT_BATCH", 5)
    corpus = Corpus(tmp_path / "chroma", WideEmbedder())
    corpus.add([LONG, *DECOYS])  # 19 pieces: four batches
    assert corpus.count() == 1 + len(DECOYS)
    assert corpus.get("Test Code", "303").text == LONG.text
