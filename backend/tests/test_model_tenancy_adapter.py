"""Model Tenancy Act 2021 (MoHUA text, LiveLaw print) -> section records.

Excerpts are real pypdf output with its quirks kept: page furniture, side-headings that
repeat the table of contents titles (one on the heading line, others wrapped over lines),
and Act-citation notes split over two lines ("41 of" / "2006.").
"""

from legallens.ingestion.pdf_text import model_tenancy_sections

CONTENTS = """Page 1 of 28 
ARRANGEMENT OF CLAUSES 
CHAPTER I 
PRELIMINARY 
Clauses  
1. Short title, extent and commencement. 
2. Definitions. 
CHAPTER III 
RENT 
8. Rent payable. 
11. Security deposit. 
12. Original tenancy agreement to be retained by landlord and tenant. 
CHAPTER V 
EVICTION AND RECOVERY OF POSSESSION OF PREMISES BY THE 
LANDLORD 
24. Refund of advance rent by landlord. 
47. Repeal and savings. 
First Schedule 
WWW.LIVELAW.IN
"""

PAGE_A = """Page 4 of 28 
 THE MODEL TENANCY ACT, 2021  
 BE it enacted by the (State/Union territory Legislature) in the 
Seventy-first Year of the Republic of India as follows:––  
CHAPTER I 
PRELIMINARY 
 1. (1) This Act may be called the (Name of State/Union territory) 
Tenancy Act, 2020.  
(3) It shall come into force on such date as the State 
Government may, by notification in the Official Gazette, appoint. 
Short title, extent 
and 
commencement. 
 2.  In this Act, unless the context otherwise requires,–– Definitions.  
 (a) “landlord” means a person who receives the rent of any premises;  
 
 
43 of 
1995 
41 of 
2006. 
(b) “local authority” means a Village Panchayat or the Cantonment Board, or as the case may be, a civil area committee appointed under section 47 of the Cantonment Act, 2006; 
WWW.LIVELAW.IN
"""

PAGE_B = """Page 10 of 28 
CHAPTER III 
 
RENT 
8. The rent payable in respect of a premises shall be the rent agreed 
upon. 
Rent payable. 
11. (1) The security deposit to be paid by the tenant in advance shall 
be such as may be agreed upon between the landlord and the tenant, which shall –– 
(a)   not exceed two months rent, in case of residential premises; 
and 
(b) not exceed six months rent, in case of non-residential premises. 
(2) The security deposit shall be refunded to the tenant on the date of 
taking over vacant possession of the premises from the tenant, after 
making due deduction of any liability of the tenant. 
 
Security deposit. 
Original tenancy 
agreement to be 
retained by landlord 
and tenant. 
12. (1) The landlord and tenant shall retain the original tenancy 
agreement. 
Original tenancy 
agreement to be 
retained by landlord 
and tenant. 
WWW.LIVELAW.IN
"""

PAGE_C = """Page 24 of 28 
CHAPTER V 
EVICTION AND RECOVERY OF POSSESSION OF PREMISES BY THE 
LANDLORD 
24. (1) Where a landlord exercises the right of recovery of possession, he shall 
refund to the tenant such amount after deducting the rent due. 
Refund of advance 
rent by landlord. 
47. (1) The State Rent Control Act, which is in force 
immediately before the commencement of this Act, is hereby 
repealed. 
Repeal and 
savings.  
WWW.LIVELAW.IN
"""

PAGE_D = """Page 25 of 28 
(2) Notwithstanding such repeal, all cases pending shall be continued. 
WWW.LIVELAW.IN
THE FIRST SCHEDULE 
[See section 4(1)] 
1. Name and address of the landlord 
"""

PAGES = [CONTENTS, PAGE_A, PAGE_B, PAGE_C, PAGE_D]


def by_number():
    return {r["section"]: r for r in model_tenancy_sections(PAGES, gap=50)}


def test_sections_come_from_the_body_not_the_contents_or_the_form():
    recs = model_tenancy_sections(PAGES, gap=50)
    assert [r["section"] for r in recs] == ["1", "2", "8", "11", "12", "24", "47"]
    assert [r["chapter"] for r in recs] == [
        "Chapter I",
        "Chapter I",
        "Chapter III",
        "Chapter III",
        "Chapter III",
        "Chapter V",
        "Chapter V",
    ]


def test_side_headings_are_removed_wherever_they_fall():
    recs = by_number()
    assert recs["1"]["text"].endswith("appoint.")  # three wrapped lines after the body
    assert recs["2"]["text"].startswith(
        "In this Act, unless the context otherwise requires,––\n(a)"
    )
    assert recs["8"]["text"].endswith("upon.")  # after the text, not before
    assert recs["11"]["text"].endswith("liability of the tenant.")
    assert recs["12"]["text"].endswith("agreement.")  # four wrapped lines
    assert recs["24"]["text"].endswith("rent due.")
    assert "Repeal and" not in recs["47"]["text"]


def test_act_citation_notes_split_over_two_lines_are_removed():
    text = by_number()["2"]["text"]
    assert "41 of" not in text and "2006.\n" not in text
    assert "section 47 of the Cantonment Act, 2006;" in text  # in-text citation stays


def test_a_section_continues_across_a_page_and_stops_at_the_schedule():
    text = by_number()["47"]["text"]
    assert "is hereby\nrepealed." in text
    assert text.endswith("shall be continued.")
    assert "Name and address" not in text and "WWW" not in text


def test_security_deposit_text_is_complete():
    text = by_number()["11"]["text"]
    assert "not exceed two months rent, in case of residential premises;" in text
    assert "shall be refunded to the tenant on the date of" in text


def test_side_headings_of_neighbouring_sections_are_removed_too():
    assert "Original tenancy" not in by_number()["11"]["text"]
    assert by_number()["11"]["text"].endswith("liability of the tenant.")


def test_act_citation_with_a_year_lacking_its_full_stop_is_removed():
    assert (
        "43 of" not in by_number()["2"]["text"]
        and "1995" not in by_number()["2"]["text"]
    )
