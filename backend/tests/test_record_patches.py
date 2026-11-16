"""Recorded fixes to a source's section records (the IPC from Indian Kanoon needs a few)."""

import pytest

from legallens.ingestion.record_patches import apply_record_patches

RECORDS = [
    {
        "section": "331",
        "chapter": "Chapter XVI",
        "title": "T331.",
        "text": "Whoever shall he punished.",
    },
    {
        "section": "332",
        "chapter": "Chapter XVI",
        "title": "T332.",
        "text": "Under 21 Regulation VII.",
    },
    {"section": "334", "chapter": "Chapter XVI", "title": "T334.", "text": "Hurt."},
]


def spec(**kw):
    return {"replacements": [], "insertions": [], **kw}


def test_a_replacement_is_applied_once_to_the_named_section():
    out = apply_record_patches(
        RECORDS,
        spec(
            replacements=[
                {
                    "section": "331",
                    "find": "shall he punished",
                    "replace": "shall be punished",
                }
            ]
        ),
    )
    assert out[0]["text"] == "Whoever shall be punished."
    assert RECORDS[0]["text"] == "Whoever shall he punished."  # the input is untouched


def test_a_replacement_matches_across_a_line_break():
    recs = [
        {
            "section": "1",
            "chapter": "",
            "title": "",
            "text": "Whoever shall\nhe punished.",
        }
    ]
    out = apply_record_patches(
        recs,
        spec(
            replacements=[
                {
                    "section": "1",
                    "find": "shall he punished",
                    "replace": "shall be punished",
                }
            ]
        ),
    )
    assert out[0]["text"] == "Whoever shall be punished."


def test_a_replacement_that_matches_nothing_or_twice_is_an_error():
    with pytest.raises(ValueError, match="331"):
        apply_record_patches(
            RECORDS,
            spec(replacements=[{"section": "331", "find": "absent", "replace": "x"}]),
        )
    with pytest.raises(ValueError, match="2 times"):
        apply_record_patches(
            [{"section": "1", "chapter": "", "title": "", "text": "a b a"}],
            spec(replacements=[{"section": "1", "find": "a", "replace": "x"}]),
        )


def test_a_replacement_for_a_missing_section_is_an_error():
    with pytest.raises(ValueError, match="999"):
        apply_record_patches(
            RECORDS,
            spec(replacements=[{"section": "999", "find": "a", "replace": "b"}]),
        )


def test_a_missing_section_is_inserted_in_order():
    ins = {
        "section": "333",
        "after": "332",
        "chapter": "Chapter XVI",
        "title": "T333.",
        "text": "Hurt to a servant.",
    }
    out = apply_record_patches(RECORDS, spec(insertions=[ins]))
    assert [r["section"] for r in out] == ["331", "332", "333", "334"]
    assert out[2] == {
        "section": "333",
        "chapter": "Chapter XVI",
        "title": "T333.",
        "text": "Hurt to a servant.",
    }


def test_inserting_a_section_that_exists_is_an_error():
    ins = {"section": "332", "after": "331", "chapter": "", "title": "", "text": "x"}
    with pytest.raises(ValueError, match="332"):
        apply_record_patches(RECORDS, spec(insertions=[ins]))


def test_text_is_filled_in_only_where_the_source_has_none():
    recs = [
        {
            "section": "58",
            "chapter": "",
            "title": "",
            "text": "[Offenders.] Rep. by Act 26.",
        },
        {"section": "59", "chapter": "", "title": "Transportation.", "text": ""},
    ]
    out = apply_record_patches(
        recs, spec(texts=[{"section": "59", "text": "Rep. by Act 26."}])
    )
    assert out[1]["text"] == "Rep. by Act 26."
    with pytest.raises(ValueError, match="58"):
        apply_record_patches(recs, spec(texts=[{"section": "58", "text": "other"}]))
