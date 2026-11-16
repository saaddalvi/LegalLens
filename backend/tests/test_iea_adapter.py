"""India Code Indian Evidence Act text -> section records, on excerpts of real pypdf output."""

from legallens.ingestion.pdf_text import iea_sections

# The contents list comes first and must not yield sections (its "1. Short title." lacks the text).
TOC_AND_START = """1 
THE INDIAN EVIDENCE ACT, 1872 
Last updated:-13-3-2020 
ARRANGEMENT OF SECTIONS 
Preamble.                                                               PART I 
RELEVANCY OF FACTS 
CHAPTER  I. ––  PRELIMINARY  
SECTIONS 
1. Short title. 
Extent. 
2. [ Repealed .] 
3. Interpretation-clause. 
4.   “May Presume.” 
CHAPTER  II. ––OF THE  RELEVANCY  OF  FACTS  
5. Evidence may be given of facts in issue and relevant facts. 
[15 th March , 1872.] 
Preamble.—WHEREAS it is expedient to consolidate, define and amend the law of Evidence; It is 
hereby enacted as follows: — 
PART I 
RELEVANCY OF FACTS 
CHAPTER  I.––PRELIMINARY  
1. Short title.  ––This Act may be called the Indian Evidence Act, 1872. 
Extent. ––It extends to the whole of India 2[ 3***] and applies to all judicial proceedings. 
2.  [Repeal of enactments .].–– Rep. by the Repealing Act , 1938 (1 of  1938), s. 2 and Schedule . 
3. Interpretation-clause .––In this Act the following words and expressions are used in the following 
senses, unless a contrary intention appears from the context: –– 
“Court”.––“Court” includes all Judges 9 and Magistrates 10 , and all persons. 
"""

# Footnotes sit under a line of spaces; "3. Ins. by" there is not section 4. Page numbers stand alone.
PAGE_2 = """“Fact”.––“Fact” means and includes––(1) anything, state of things. 
Illustrations 
(a) That there are certain objects arranged in a certain order in a certain place, is a fact. 
                                                      
1. The Act has been extended to Goa, Daman and Diu by Reg. 11 of 1963. 
3. Ins. by Act 18 of 1919, s. 2 and the First Schedule. 
4. Ins. by Act 35 of 1934, s. 2 and the Schedule. 
"""

PAGE_2B = """10 
4. “May presume”.––Whenever it is provided by this Act that the Court may presume a fact. 
CHAPTER  II. –– OF THE  RELEVANCY  OF  FACTS  
5. Evidence may be given of facts in issue and relevant facts.  ––Evidence may be given in any suit 
or proceeding of the existence of non-existence of every fact in issue. 
Illustrations  
(a) A is tried for the murder of B by beating him with a club. 
"""

# A lettered section, a PART heading with a subtitle ahead of
# its chapter, and the end of the Act (a schedule of repealed enactments).
PAGE_3 = """6. When oral admissions as to contents of documents are relevant.  ––Oral admissions as to the 
contents of a document are not relevant. 
1[6A. When oral admission as to contents of electronic records are relevant.—Oral admissions as to 
the contents of electronic records are not relevant.] 
7. Admissions in civil cases, when relevant.  ––In civil cases no admission is relevant. 
PART II 
ON PROOF 
CHAPTER  III.––FACTS  WHICH NEED NOT BE PROVED 
8. Fact judicially noticeable need not be proved. ––No fact of which the Court will take judicial 
notice need be proved. 
"""

PAGE_LAST = """CHAPTER  XI–– OF IMPROPER  ADMISSION  AND  REJECTION  OF  EVIDENCE  
9. No new trial for improper admission or rejection of evidence.  –– The improper admission or 
rejection of evidence shall not be ground of itself for a new trial. 
THE SCHEDULE.  –– [Enactments repealed. ] Rep. by the Repealing Act , 1938 (1 of 1938), s.  2 and 
the Schedule .
"""


def by_number():
    recs = iea_sections([TOC_AND_START, PAGE_2, PAGE_2B, PAGE_3, PAGE_LAST])
    return recs, {r["section"]: r for r in recs}


def test_contents_list_is_skipped_and_sections_come_in_order():
    recs, _ = by_number()
    assert [r["section"] for r in recs] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "6A",
        "7",
        "8",
        "9",
    ]


def test_title_and_text_are_split_at_the_dash():
    _, by = by_number()
    assert by["1"]["title"] == "Short title."
    assert by["1"]["text"].startswith(
        "This Act may be called the Indian Evidence Act, 1872."
    )
    assert "Extent. ––It extends" in by["1"]["text"]


def test_repealed_section_is_kept():
    _, by = by_number()
    assert by["2"]["title"] == "[Repeal of enactments .]."
    assert "Rep. by the Repealing Act" in by["2"]["text"]


def test_footnotes_and_page_numbers_are_dropped():
    _, by = by_number()
    assert "Ins. by Act" not in by["3"]["text"] and "Goa" not in by["3"]["text"]
    assert not any(line.strip() == "10" for line in by["3"]["text"].splitlines())
    assert by["3"]["text"].count("“Fact”.––") == 1


def test_a_section_defined_inside_another_is_its_own_section():
    _, by = by_number()
    assert by["4"]["title"] == "“May presume”."
    assert "“Fact”" not in by["4"]["text"]


def test_chapter_is_tracked_and_part_headings_are_dropped():
    _, by = by_number()
    assert by["1"]["chapter"] == "Chapter I"
    assert by["5"]["chapter"] == "Chapter II"
    assert by["8"]["chapter"] == "Chapter III"
    assert "PART II" not in by["7"]["text"] and "ON PROOF" not in by["7"]["text"]


def test_lettered_section_and_amendment_markers():
    _, by = by_number()
    assert " ".join(by["6A"]["text"].split()).startswith(
        "Oral admissions as to the contents of electronic records"
    )
    assert "[" not in by["6A"]["text"] and "]" not in by["6A"]["text"]
    assert by["6"]["text"].endswith("are not relevant.")


def test_wrapped_title_is_joined():
    recs = iea_sections(
        [
            TOC_AND_START,
            PAGE_2,
            PAGE_2B,
            "6. Relevancy of facts forming part of same\ntransaction.––Facts which form part.",
        ]
    )
    assert recs[-1]["section"] == "6"
    assert recs[-1]["title"] == "Relevancy of facts forming part of same transaction."


def test_heading_with_no_dash_after_its_title():
    # Section 86 of the PDF has two spaces where the dash should be.
    recs = iea_sections(
        [
            TOC_AND_START,
            PAGE_2,
            PAGE_2B,
            (
                "6. Presumption as to certified copies of foreign judicial records.  "
                "The Court may presume that\nany document purporting to be a certified copy is genuine."
            ),
        ]
    )
    assert recs[-1]["section"] == "6"
    assert (
        recs[-1]["title"]
        == "Presumption as to certified copies of foreign judicial records."
    )
    assert recs[-1]["text"].startswith("The Court may presume that")


def test_footnote_digit_glued_to_the_section_number():
    # "1145." is a footnote marker 1 against section 145.
    recs = iea_sections(
        [
            TOC_AND_START,
            PAGE_2,
            PAGE_2B,
            "16. Cross-examination as to previous statements in writing.  –– A witness may be\ncross-examined as to previous statements.",
        ]
    )
    assert recs[-1]["section"] == "6"
    assert (
        recs[-1]["title"] == "Cross-examination as to previous statements in writing."
    )


def test_schedule_ends_the_act():
    _, by = by_number()
    assert (
        "SCHEDULE" not in by["9"]["text"]
        and "Enactments repealed" not in by["9"]["text"]
    )
