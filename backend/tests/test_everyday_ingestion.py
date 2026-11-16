"""Ingestion of the consumer, tenancy and labour Acts, on real section text kept as fixtures.

The fixtures hold real records from each adapter's output (CPA, TPA Chapter V, and the four
Labour Codes), so each Act's source format reaches the parser.
"""

import json
from pathlib import Path

import pytest

from legallens.ingestion import (
    EVERYDAY_ACTS,
    build_report,
    parse_everyday_act,
)

RAW = json.loads(
    (Path(__file__).parent / "fixtures" / "everyday_acts_raw.json").read_text()
)


def provisions(key):
    return parse_everyday_act(key, RAW[key])


@pytest.mark.parametrize("key", sorted(EVERYDAY_ACTS))
def test_each_act_yields_one_in_force_chunk_per_section(key):
    chunks = provisions(key)
    assert [c.number for c in chunks] == [r["section"] for r in RAW[key]]
    assert {c.act for c in chunks} == {EVERYDAY_ACTS[key].name}
    assert {c.status for c in chunks} == {"model" if key == "mta" else "in_force"}
    assert all(c.text and c.chapter.startswith("Chapter ") for c in chunks)
    assert all(c.superseded_by is None and c.supersedes is None for c in chunks)


def test_chunk_text_is_the_verbatim_section_text():
    by_number = {c.number: c for c in provisions("tpa")}
    assert by_number["106"].text.startswith(
        "In the absence of a contract or local law or usage to the contrary"
    )
    assert "fifteen days' notice" in by_number["106"].text


def test_chapters_are_taken_from_the_source():
    chapters = {c.number: c.chapter for c in provisions("cpa")}
    assert chapters == {"1": "Chapter I", "35": "Chapter IV", "39": "Chapter IV"}


def test_duplicate_section_numbers_are_an_error():
    with pytest.raises(ValueError, match="duplicate"):
        parse_everyday_act("wages", RAW["wages"] + RAW["wages"][:1])


def test_report_flags_an_act_with_the_wrong_count():
    report = build_report(provisions("cpa"))  # 3 of 107
    assert any(
        "Consumer Protection Act: 3 Chunks, expected 107-107" in w
        for w in report.warnings
    )


def test_every_act_has_an_exact_expected_count():
    assert {k: v.expected_count for k, v in EVERYDAY_ACTS.items()} == {
        "cpa": (107, 107),
        "tpa": (14, 14),
        "mta": (47, 47),
        "wages": (69, 69),
        "ir": (104, 104),
        "ss": (164, 164),
        "osh": (143, 143),
    }
