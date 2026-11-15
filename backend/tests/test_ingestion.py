import json
from pathlib import Path

from legallens.ingestion import build_report, parse_constitution
from legallens.models import Provision

RAW = json.loads(
    (Path(__file__).parent / "fixtures" / "constitution_raw.json").read_text()
)


def by_number():
    return {p.number: p for p in parse_constitution(RAW)}


def test_one_chunk_per_article_and_preamble_is_not_a_provision():
    provisions = parse_constitution(RAW)
    assert [p.number for p in provisions] == [
        "12",
        "21",
        "21A",
        "31",
        "238",
        "239AA",
        "243ZT",
        "370",
    ]


def test_chunk_metadata_for_in_force_article():
    p = by_number()["21"]
    assert p.act == "Constitution of India"
    assert p.chapter == "Part III"
    assert p.status == "in_force"
    assert p.superseded_by is None
    assert (
        p.text
        == "No person shall be deprived of his life or personal liberty except according to procedure established by law."
    )


def test_lettered_and_malformed_numbers_are_normalised():
    numbers = by_number()
    assert numbers["21A"].chapter == "Part III"
    assert numbers["239AA"].chapter == "Part VIII"  # source spells it "239 A A"
    assert numbers["243ZT"].chapter == "Part IXB"


def test_repealed_and_omitted_articles_have_repealed_status():
    numbers = by_number()
    assert numbers["31"].status == "repealed"
    assert numbers["238"].status == "repealed"
    assert numbers["21A"].status == "in_force"


def test_text_whitespace_is_normalised_but_paragraphs_are_kept():
    assert (
        by_number()["239AA"].text.splitlines()[1]
        == "(2) There shall be a Legislative Assembly."
    )
    assert by_number()["370"].text == (
        "(1) Notwithstanding anything in this Constitution, —\n(a) the provisions of article 238 shall not apply."
    )


def test_report_counts_per_act_and_flags_suspicious_count():
    report = build_report(parse_constitution(RAW))
    assert report.counts == {"Constitution of India": 8}
    assert any("Constitution of India" in w and "8" in w for w in report.warnings)


def test_report_is_clean_when_count_is_plausible():
    provisions = [
        Provision(
            act="Constitution of India",
            chapter="Part I",
            number=str(i),
            status="in_force",
            text="x",
        )
        for i in range(1, 500)
    ]
    report = build_report(provisions)
    assert report.counts == {"Constitution of India": 499}
    assert report.warnings == []


def test_report_flags_duplicate_numbers_and_empty_text():
    p = Provision(
        act="Constitution of India",
        chapter="Part I",
        number="1",
        status="in_force",
        text="x",
    )
    report = build_report([p, p, p.model_copy(update={"number": "2", "text": ""})])
    assert any("duplicate" in w and "1" in w for w in report.warnings)
    assert any("empty" in w and "2" in w for w in report.warnings)


def test_patch_adds_missing_article_in_order_with_derived_part_and_status():
    patches = [
        {
            "op": "add",
            "number": "320",
            "text": "It shall be the duty of the Union and the State Public Service Commissions to conduct examinations.",
            "reason": "missing from source",
        },
        {
            "op": "add",
            "number": "242",
            "text": "[Coorg.] Omitted by the Constitution (Seventh Amendment) Act, 1956.",
            "reason": "missing from source",
        },
    ]
    numbers = [p.number for p in parse_constitution(RAW, patches=patches)]
    assert numbers == [
        "12",
        "21",
        "21A",
        "31",
        "238",
        "239AA",
        "242",
        "243ZT",
        "320",
        "370",
    ]
    patched = {p.number: p for p in parse_constitution(RAW, patches=patches)}
    assert patched["320"].chapter == "Part XIV" and patched["320"].status == "in_force"
    assert patched["242"].chapter == "Part VIII" and patched["242"].status == "repealed"


def test_patch_replaces_text_of_existing_article():
    patches = [
        {
            "op": "replace",
            "number": "21",
            "text": "Corrected text.",
            "reason": "typo in source",
        }
    ]
    assert {p.number: p for p in parse_constitution(RAW, patches=patches)}[
        "21"
    ].text == "Corrected text."


def test_patch_for_unknown_article_or_duplicate_add_is_an_error():
    import pytest

    with pytest.raises(ValueError):
        parse_constitution(
            RAW,
            patches=[{"op": "replace", "number": "999", "text": "x", "reason": "r"}],
        )
    with pytest.raises(ValueError):
        parse_constitution(
            RAW, patches=[{"op": "add", "number": "21", "text": "x", "reason": "r"}]
        )


def test_duplicate_article_numbers_in_source_are_an_error():
    import pytest

    dup = RAW + [
        {"article": 21, "title": "Again", "description": "A second Article 21."}
    ]
    with pytest.raises(ValueError, match="duplicate"):
        parse_constitution(dup)


def test_preamble_is_skipped_however_the_source_spells_zero():
    records = [
        {"article": "0", "title": "Preamble", "description": "WE, THE PEOPLE"}
    ] + RAW[1:]
    assert "0" not in {p.number for p in parse_constitution(records)}
