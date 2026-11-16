"""Layout quirks of the CPA 2019 and the Labour Codes' Gazette PDFs, on real pypdf excerpts.

They share the BNS Gazette adapter; these cover where their prints differ from it: the
"SEC. 1] THE GAZETTE ..." footer on odd pages, the assent block coming before the Hindi-font
cover on page 1, and an Act-citation note run onto the last line of the Act.
"""

from legallens.ingestion.pdf_text import gazette_sections

# CPA page 1: the assent block sits above the Hindi-font cover block, after the side-heading.
PAGE_1 = """THE CONSUMER PROTECTION ACT, 2019
NO. 35 OF  2019
[9th August, 2019.]
BE it enacted by Parliament in the Seventieth Year of the Republic of India as follows:—
CHAPTER I
PRELIMINARY
1. (1) This Act may be called the Consumer Protection Act, 2019.
(4) Save as otherwise expressly provided by the Central Government, by notification,
this Act shall apply to all goods and services.
MINISTRY OF LAW AND JUSTICE
(Legislative Department)
New Delhi, the 9th August, 2019/Shravana 18, 1941  (Saka)
The following Act of Parliament received the assent of the President on the
9th August, 2019, and is hereby published for general information:—
jftLVªh lañ Mhñ ,yñ —(,u)04@0007@2003—19
vlk/kkj.k
EXTRAORDINARY
Hkkx  II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED  BY  AUTHORITY
No. 54]  NEW DELHI, FRIDAY, AUGUST 9, 2019/SHRAVANA 18, 1941 (SAKA)
Separate paging is given to this Part in order that it may be filed as a separate compilation.
REGISTERED NO. DL—(N)04/0007/2003—19"""

# An odd page: the running head "SEC. 1] THE GAZETTE OF INDIA EXTRAORDINARY 3" is on top.
PAGE_3 = """SEC. 1] THE GAZETTE OF INDIA EXTRAORDINARY 3
(2) "appropriate laboratory" means a laboratory recognised by the Central Government;
3. The Central Government shall establish a Council.
(1) The Council shall consist of a Chairperson."""

# The Act's last page: an Act-citation note ("10 of 1897.") runs onto the final line.
LAST_PAGE = """4. Nothing in this Code affects the repeal of the enactments.
(2) Without prejudice to sub-section (2), the provisions of section 6 of
the General Clauses Act, 1897 shall apply to the repeal of such enactments.10 of 1897."""

SECTION_2 = """2. In this Act, unless the context otherwise requires,—
(1) "advertisement" means any publicity;"""


def records():
    return gazette_sections(
        [
            PAGE_1,
            "2 THE GAZETTE OF INDIA EXTRAORDINARY [PART II—\n" + SECTION_2,
            PAGE_3,
            LAST_PAGE,
        ]
    )


def by_number():
    return {r["section"]: r for r in records()}


def test_assent_block_after_section_one_is_dropped():
    text = by_number()["1"]["text"]
    assert text.endswith("this Act shall apply to all goods and services.")
    assert "MINISTRY" not in text and "jftLV" not in text and "REGISTERED" not in text


def test_sec_prefixed_running_head_on_odd_pages_is_dropped():
    recs = by_number()
    assert recs["3"]["text"].endswith("shall consist of a Chairperson.")
    assert "GAZETTE" not in recs["2"]["text"]


def test_act_citation_note_run_onto_the_last_line_is_removed():
    assert by_number()["4"]["text"].endswith("repeal of such enactments.")


# The CPA's last page: a short final body line sits above the "10 of 1897." note and the
# rule that ends the Act, and must not be mistaken for a side-heading.
CPA_END_PAGE = """(3) The mention of particular matters in sub-section (2) shall not be held to prejudice
or affect the general application of section 6 of the General Clauses Act, 1897 with regard to
the effect of repeal.
10 of 1897.
40 THE GAZETTE OF INDIA EXTRAORDINARY [PART II—SEC. 1]
————
DR. G.  NARAYANA  RAJU,
Secretary to the Govt. of India."""


def test_short_last_line_of_the_act_is_kept():
    recs = gazette_sections([PAGE_1, CPA_END_PAGE])
    assert recs[-1]["text"].endswith("with regard to\nthe effect of repeal.")
