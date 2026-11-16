import json
from pathlib import Path

import pytest

from legallens.ingestion import apply_mappings, build_report, parse_criminal_code
from legallens.ingestion.criminal_codes import CRIMINAL_ACTS

FIXTURES = Path(__file__).parent / "fixtures"
RAW = json.loads((FIXTURES / "criminal_codes_raw.json").read_text())
MAPPINGS = json.loads((FIXTURES / "criminal_code_mappings.json").read_text())[
    "mappings"
]


def parsed(key):
    return {p.number: p for p in parse_criminal_code(key, RAW[key])}


@pytest.mark.parametrize(
    ("key", "act", "status", "numbers"),
    [
        ("ipc", "Indian Penal Code", "repealed", ["302", "376", "420", "498A"]),
        ("crpc", "Code of Criminal Procedure", "repealed", ["41A", "154"]),
        ("iea", "Indian Evidence Act", "repealed", ["3", "65B"]),
        ("bns", "Bharatiya Nyaya Sanhita", "in_force", ["64", "85", "103", "318"]),
        ("bnss", "Bharatiya Nagarik Suraksha Sanhita", "in_force", ["35", "173"]),
        ("bsa", "Bharatiya Sakshya Adhiniyam", "in_force", ["2", "63"]),
    ],
)
def test_each_act_parses_to_one_ordered_chunk_per_section(key, act, status, numbers):
    provisions = parse_criminal_code(key, RAW[key])
    assert [p.number for p in provisions] == numbers
    assert {p.act for p in provisions} == {act}
    assert {p.status for p in provisions} == {status}


def test_chunk_metadata_and_text_normalisation():
    p = parsed("ipc")["376"]
    assert p.chapter == "Chapter XVI"
    assert (
        "rigorous imprisonment of either description" in p.text
    )  # double space collapsed
    assert parsed("ipc")["498A"].chapter == "Chapter XXA"


def test_duplicate_section_numbers_are_an_error():
    with pytest.raises(ValueError, match="duplicate"):
        parse_criminal_code("bns", RAW["bns"] + [RAW["bns"][0]])


def test_unparseable_section_number_is_an_error():
    with pytest.raises(ValueError, match="section number"):
        parse_criminal_code("bns", [{"section": "one", "chapter": "x", "text": "t"}])


def test_unknown_act_key_is_an_error():
    with pytest.raises(KeyError):
        parse_criminal_code("nope", [])


def all_provisions():
    return [p for key in RAW for p in parse_criminal_code(key, RAW[key])]


def mapped():
    return {(p.act, p.number): p for p in apply_mappings(all_provisions(), MAPPINGS)}


def test_repealed_to_superseding_mapping_on_known_examples():
    m = mapped()
    assert m["Indian Penal Code", "302"].superseded_by == "Bharatiya Nyaya Sanhita 103"
    assert m["Indian Penal Code", "420"].superseded_by == "Bharatiya Nyaya Sanhita 318"
    assert m["Code of Criminal Procedure", "154"].superseded_by == (
        "Bharatiya Nagarik Suraksha Sanhita 173"
    )
    assert (
        m["Indian Evidence Act", "65B"].superseded_by
        == "Bharatiya Sakshya Adhiniyam 63"
    )


def test_in_force_provision_carries_its_old_equivalent():
    m = mapped()
    assert m["Bharatiya Nyaya Sanhita", "103"].supersedes == "Indian Penal Code 302"
    assert (
        m["Bharatiya Sakshya Adhiniyam", "63"].supersedes == "Indian Evidence Act 65B"
    )
    assert m["Bharatiya Nyaya Sanhita", "103"].superseded_by is None


def test_unmapped_provisions_have_no_references():
    m = mapped()
    assert m["Indian Evidence Act", "3"].superseded_by is None
    assert m["Bharatiya Sakshya Adhiniyam", "2"].supersedes is None


def test_one_to_many_mapping_lists_every_target():
    extra = [
        {
            "old_act": "Indian Penal Code",
            "old_number": "302",
            "new_act": "Bharatiya Nyaya Sanhita",
            "new_number": "64",
        },
    ]
    p = {
        (p.act, p.number): p for p in apply_mappings(all_provisions(), MAPPINGS + extra)
    }
    assert p["Indian Penal Code", "302"].superseded_by == (
        "Bharatiya Nyaya Sanhita 103; Bharatiya Nyaya Sanhita 64"
    )


def test_mapping_to_a_missing_provision_is_an_error():
    bad = [
        {
            "old_act": "Indian Penal Code",
            "old_number": "999",
            "new_act": "Bharatiya Nyaya Sanhita",
            "new_number": "103",
        }
    ]
    with pytest.raises(ValueError, match="999"):
        apply_mappings(all_provisions(), bad)


def test_report_has_a_configured_range_for_every_criminal_act():
    report = build_report(all_provisions())
    assert not any("no expected range" in w for w in report.warnings)
    assert set(report.counts) >= {a.name for a in CRIMINAL_ACTS.values()}
    assert any(
        "Indian Penal Code" in w for w in report.warnings
    )  # fixture counts are tiny
