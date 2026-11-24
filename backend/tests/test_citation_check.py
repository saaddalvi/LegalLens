from conftest import ART_21, FakeEmbedder

from legallens.citation_check import check_citations
from legallens.corpus import Corpus
from legallens.llm import ProvisionRef


def make_corpus(tmp_path, provisions):
    corpus = Corpus(tmp_path / "chroma", FakeEmbedder())
    corpus.add(provisions)
    return corpus


def test_citation_present_in_corpus_is_valid(tmp_path):
    corpus = make_corpus(tmp_path, [ART_21])
    result = check_citations(
        [ProvisionRef(act=ART_21.act, number=ART_21.number)], corpus=corpus
    )
    assert result.hallucinated == []
    assert len(result.valid) == 1
    assert result.valid[0].text == ART_21.text


def test_citation_absent_from_corpus_is_hallucinated(tmp_path):
    corpus = make_corpus(tmp_path, [ART_21])
    ghost = ProvisionRef(act="Indian Penal Code", number="420")
    result = check_citations([ghost], corpus=corpus)
    assert result.valid == []
    assert result.hallucinated == [ghost]


def test_repeated_hallucinated_citation_is_deduped(tmp_path):
    corpus = make_corpus(tmp_path, [ART_21])
    ghost = ProvisionRef(act="Indian Penal Code", number="420")
    result = check_citations([ghost, ghost], corpus=corpus)
    assert result.hallucinated == [ghost]
