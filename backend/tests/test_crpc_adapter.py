"""India Code CrPC text -> section records, on short excerpts of real pypdf output."""

from legallens.ingestion.pdf_text import crpc_sections

TOC_AND_START = """ 
1 
THE CODE OF CRIMINAL PROCEDURE, 1973 
________ 
ARRANGEMENT OF SECTIONS 
CHAPTER I 
PRELIMINARY 
SECTIONS 
1. Short title, extent and commencement.  
2. Definitions. 
CHAPTER II 
CONSTITUTION OF CRIMINAL COURTS AND OFFICES 
12. Chief Judicial Magistrate and Additional Chief Judicial Magistrate, etc. 
"""

PAGE_BODY_1 = """CHAPTER I 
PRELIMINARY 
1. Short title, extent and commencement.—(1) This Act may be called the Code of Criminal 
Procedure, 1973. 
(2) It extends to the whole of India except 1[the State of Nagaland]. 
2. Definitions.—In this Code, unless the context otherwise requires,— 
(a) “bailable offence” means an offence which is shown as bailable in the First Schedule; 
                                                 
1. Subs. by Act 22 of 2018, s. 11, for “Jammu and Kashmir” (w.e.f. 21-4-2019). 
"""

# A wrapped title, a "Chapter" with a letter suffix, a state amendment (ended by its [Vide ..]
# line) and the next section's heading following it.
PAGE_BODY_2 = """<<ignored>>
12. Chief Judicial Magistrate and Additional Chief Judicial Magistrate,
etc.—(1) In every district, the High Court shall appoint a Judicial Magistrate.
2[(3) The High Court may empower a Special Judicial Magistrate.] 
 
STATE AMENDMENT 
Assam 
In section 12, in sub-section (3), add the following:— 
13. This state-inserted paragraph looks like a heading but is not.—(4) text. 
[Vide Assam Act 13 of 1964, s. 2.] 
13. Special Judicial Magistrates.—(1) The High Court may confer powers. 
79 
CHAPTER VIIA 
QUESTIONS OF PRIVILEGE 
14. Local jurisdiction.—(1) The High Court may define local limits. 
THE FIRST SCHEDULE.–CLASSIFICATION OF OFFENCES. 
1. Offences under the Indian Penal Code.—not a section. 
"""


def records():
    return crpc_sections(
        [TOC_AND_START, PAGE_BODY_1, PAGE_BODY_2.replace("<<ignored>>\n", "")]
    )


def by_number():
    return {r["section"]: r for r in records()}


def test_table_of_contents_is_skipped_and_schedules_end_the_body():
    assert [r["section"] for r in records()] == ["1", "2", "12", "13", "14"]


def test_text_is_after_the_title_and_amendment_markers_are_removed():
    recs = by_number()
    assert recs["1"]["text"].startswith("(1) This Act may be called")
    assert recs["1"]["title"] == "Short title, extent and commencement"
    assert "the State of Nagaland." in recs["1"]["text"]
    assert "1[" not in recs["1"]["text"] and "]" not in recs["1"]["text"]


def test_footnote_block_below_the_separator_is_dropped():
    assert "Subs. by Act 22" not in by_number()["2"]["text"]
    assert by_number()["2"]["text"].endswith("bailable in the First Schedule;")


def test_wrapped_title_and_chapters():
    recs = by_number()
    assert (
        recs["12"]["title"]
        == "Chief Judicial Magistrate and Additional Chief Judicial Magistrate, etc"
    )
    assert recs["12"]["text"].startswith("(1) In every district")
    assert [recs[n]["chapter"] for n in ("1", "2", "12", "13", "14")] == [
        "Chapter I",
        "Chapter I",
        "Chapter I",
        "Chapter I",
        "Chapter VIIA",
    ]


def test_state_amendment_blocks_are_not_section_text():
    text = by_number()["12"]["text"]
    assert (
        "STATE AMENDMENT" not in text
        and "Assam" not in text
        and "state-inserted" not in text
    )
    assert "Vide" not in text
    assert by_number()["13"]["text"] == "(1) The High Court may confer powers."


def test_page_numbers_are_dropped():
    assert not any(l.strip() == "79" for r in records() for l in r["text"].splitlines())


SUBSTITUTED_AND_SUBHEADED = """68. Service on witness.—(1) Text of sixty-eight.
1[69. Service of summons on witness by post.—(1) Notwithstanding anything, a Court may direct.]
STATE AMENDMENTS
Andaman and Nicobar Islands U.T.
In section 69, in sub-section (1), after the words “registered post” insert words.
[Vide Andaman and Nicobar Islands U.T. Act 6 of 1977, s. 2.]
B.—Warrant of arrest
70. Form of warrant of arrest.—(1) Every warrant shall be in writing.
2[71. Power to direct security.—(1) Any Court may direct.]"""


def test_section_wrapped_whole_in_an_amendment_marker_and_a_sub_heading_after_a_state_block():
    pages = [
        "\n".join(f"{n}. Section {n}.—Text {n}." for n in range(1, 68)),
        SUBSTITUTED_AND_SUBHEADED,
    ]
    recs = {r["section"]: r["text"] for r in crpc_sections(pages)}
    assert list(recs)[-4:] == ["68", "69", "70", "71"]
    assert recs["69"] == "(1) Notwithstanding anything, a Court may direct."
    assert recs["70"] == "(1) Every warrant shall be in writing."


def test_hyphenated_section_numbers_are_normalised():
    pages = [
        "\n".join(f"{n}. Section {n}.—Text {n}." for n in range(1, 105))
        + "\n105H. Forfeiture.—(1) Text.\n105-I. Fine in lieu of forfeiture.—(1) Where the Court makes a declaration.\n105J. Certain transfers.—(1) Text."
    ]
    assert [r["section"] for r in crpc_sections(pages)][-3:] == ["105H", "105I", "105J"]
