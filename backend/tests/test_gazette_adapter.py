"""Gazette PDF text -> section records, on short excerpts of real pypdf output (quirks kept)."""

from legallens.ingestion.pdf_text import gazette_sections

# Page 1 of the BNS Gazette: section 1 runs into the marginal heading, then the Hindi-font
# cover block (garbled), which pypdf interleaves into the page.
PAGE_1 = """THE BHARATIYA NYAYA SANHITA, 2023
NO. 45 OF 2023
[25th December, 2023.]
An  Act  to consolidate and amend the provisions relating to offences and  for
matters connected therewith or incidental thereto.
BE it enacted by Parliament in the Seventy-fourth Year of the Republic of India as
follows:––
CHAPTER I
PRELIMINARY
1. (1) This Act may be called the Bharatiya Nyaya Sanhita, 2023.
(2) It shall come into force on such date as the Central Government may, by notification
in the Official Gazette, appoint.
Short title,
commencement
and
application.
vlk/kkj.k
EXTRAORDINARY
Hkkx  II — [k.M 1
PART II — Section 1
izkf/kdkj ls izdkf'kr
PUBLISHED  BY  AUTHORITY
lañ   53] ubZ fnYyh] lkseokj] fnlEcj 25] 2023@ikS"k 4] 1945 ¼'kd½
No. 53] NEW DELHI, MONDAY, DECEMBER 25, 2023/PAUSHA 4, 1945 (SAKA)
bl Hkkx esa fHkUu i`"B la[;k nh tkrh gS ftlls fd ;g vyx ladyu ds :i esa j[kk tk ldsA
Separate paging is given to this Part in order that it may be filed as a separate compilation.
xxxGIDHxxx
xxxGIDExxx
jftLVªh lañ Mhñ ,yñ—(,u)04@0007@2003—23 REGISTERED NO. DL—(N)04/0007/2003—23
MINISTRY OF LAW AND JUSTICE
(Legislative Department)
New Delhi, the 25th December, 2023/Pausha 4, 1945  (Saka)
The following Act of Parliament received the assent of the President on the
25th December, 2023 and is hereby published for general information:—
सी.जी.-डी.एल.-अ.-25122023-250883
CG-DL-E-25122023-250883"""

# Page 2 (even page): number first, footer last; the marginal heading "Definitions." sits
# between the body and the footer; a word is split across lines mid-token by the PDF.
PAGE_2 = """2
(3) Every person shall be liable to punishment under this Sanhita and not otherwise.
2. In this Sanhita, unless the context otherwise requires,––
(1) “act” denotes as well a series of acts as a single act;
(8) “document” means any matter expressed or described upon any substance
by means of letters, figures or marks, and includes
electronic and digital record.
Definitions.
2
THE GAZETTE OF INDIA EXTRAORDINARY
[Part II—
____________________________________________________________
_____________________________________________________________"""

# Page 3 (odd page): act-citation margin notes ("40 of 2019.") then "Sec. 1]" and the footer.
PAGE_3 = """3
(10) “gender”.—The pronoun “he” and its derivatives are used of any person.
Explanation.–– “transgender” shall have the meaning assigned to it in clause (k)
of section 2 of the Transgender Persons (Protection of Rights) Act, 2019;
40 of 2019.
Sec. 1]
THE GAZETTE OF INDIA EXTRAORDINARY
3
____________________________________________________________"""

# Chapter change on a page whose tail holds a multi-line marginal heading.
PAGE_4 = """4
(4) The last sub-section of section 2 ends here.
CHAPTER II
OF PUNISHMENTS
3. The punishments to which offenders are liable under the provisions of this Sanhita
are—
(a) death;
(b) imprisonment for life;
Punishments.
Buying child
for purposes of
prostitution,
etc.
4
THE GAZETTE OF INDIA EXTRAORDINARY
[Part II—
____________________________________________________________"""


def records():
    return gazette_sections([PAGE_1, PAGE_2, PAGE_3, PAGE_4])


def by_number():
    return {r["section"]: r for r in records()}


def test_one_record_per_section_in_order():
    assert [r["section"] for r in records()] == ["1", "2", "3"]


def test_chapter_comes_from_the_heading_and_its_title_is_not_body_text():
    recs = by_number()
    assert recs["1"]["chapter"] == "Chapter I"
    assert recs["2"]["chapter"] == "Chapter I"
    assert recs["3"]["chapter"] == "Chapter II"
    assert "PRELIMINARY" not in recs["1"]["text"]
    assert "OF PUNISHMENTS" not in recs["3"]["text"]


def test_text_drops_the_section_number_and_spans_pages():
    text = by_number()["1"]["text"]
    assert text.startswith(
        "(1) This Act may be called the Bharatiya Nyaya Sanhita, 2023."
    )
    assert "Official Gazette, appoint." in text
    s2 = by_number()["2"]["text"]
    assert s2.startswith("In this Sanhita, unless the context otherwise requires")
    assert "(10) “gender”" in s2  # continues across pages 2 and 3
    assert "Transgender Persons (Protection of Rights) Act, 2019;" in s2


def test_hindi_font_cover_block_and_page_furniture_are_stripped():
    joined = "\n".join(r["text"] for r in records())
    for junk in (
        "vlk/kkj.k",
        "xxxGIDHxxx",
        "Hkkx",
        "EXTRAORDINARY",
        "सी.जी.",
        "CG-DL-E",
        "REGISTERED NO.",
        "THE GAZETTE OF INDIA",
        "Sec. 1]",
        "[Part II",
        "_____",
    ):
        assert junk not in joined, junk


def test_marginal_headings_and_act_citation_notes_are_stripped():
    recs = by_number()
    assert not recs["1"]["text"].endswith("application.")
    assert "Short title" not in recs["1"]["text"]
    assert "Definitions." not in recs["2"]["text"]
    assert "40 of 2019" not in recs["2"]["text"]
    assert "Buying child" not in recs["3"]["text"]
    assert "Punishments." not in recs["3"]["text"]
    assert "prostitution" not in recs["3"]["text"]


def test_full_width_body_lines_at_a_page_end_are_kept():
    assert by_number()["3"]["text"].endswith("(b) imprisonment for life;")
    assert by_number()["2"]["text"].count("electronic and digital record.") == 1


def test_page_numbers_are_not_body_text():
    assert not any(
        line.strip() == "2" for r in records() for line in r["text"].splitlines()
    )


# BNS prints sub-headings ("Of  hurt") between sections, and can put a section number alone
# on its line; BNSS prints "A.—Summons" style sub-headings.
SUBHEADINGS = """124. (1) Whoever causes permanent damage shall be punished.
125. Whoever does any act so rashly or negligently as to endanger human life
shall be punished.
Of  wrongful restraint and wrongful confinement
126.
 (1) Whoever voluntarily obstructs any person so as to prevent that person
from proceeding is said wrongfully to restrain that person.
A.—Summons
127. (1) Whoever wrongfully restrains any person shall be punished."""


def test_number_alone_on_its_line_and_sub_headings():
    recs = {
        r["section"]: r["text"]
        for r in gazette_sections(
            [
                "1. x\n"
                + SUBHEADINGS.replace("124", "2", 1)
                .replace("125", "3", 1)
                .replace("126", "4", 1)
                .replace("127", "5", 1)
            ]
        )
    }
    assert list(recs) == ["1", "2", "3", "4", "5"]
    assert recs["4"].startswith("(1) Whoever voluntarily obstructs")
    assert "wrongful confinement" not in recs["3"]
    assert "Summons" not in recs["4"]


def test_missing_space_after_the_number_and_decimals_in_body():
    pages = [
        "1. First section.\n2.Whoever fines up to\n2.5 lakh rupees shall be punished.\n3. Third."
    ]
    recs = {r["section"]: r["text"] for r in gazette_sections(pages)}
    assert list(recs) == ["1", "2", "3"]
    assert recs["2"] == "Whoever fines up to\n2.5 lakh rupees shall be punished."


LAST_PAGE = """102 THE GAZETTE OF INDIA EXTRAORDINARY [PART II—SEC. 1]
Of  breach of  contract to attend on and supply wants of  helpless person
357. Whoever does the last thing shall be punished.
358. (1) The Indian Penal Code is hereby repealed.
Breach of
contract to
attend on and
Repeal and
savings.
45 of 1860.
—————
DIWAKAR SINGH,
Joint Secretary & Legislative Counsel to the Govt. of  India.
MGIPMRND—531GI(S3)—25-12-2023."""

SCHEDULE_PAGE = """248
531. (1) The Code of Criminal Procedure, 1973 is hereby repealed.
THE FIRST SCHEDULE
CLASSIFICATION OF OFFENCES
1. Offences under the Bharatiya Nyaya Sanhita, 2023."""


def test_the_last_section_stops_at_the_end_rule_or_the_first_schedule():
    prefix = "\n".join(f"{n}. Section {n}." for n in range(1, 357))
    last = gazette_sections([prefix, LAST_PAGE])[-1]
    assert last["section"] == "358"
    assert last["text"] == "(1) The Indian Penal Code is hereby repealed."
    prefix = "\n".join(f"{n}. Section {n}." for n in range(1, 531))
    sched = gazette_sections([prefix, SCHEDULE_PAGE])[-1]
    assert (
        sched["text"] == "(1) The Code of Criminal Procedure, 1973 is hereby repealed."
    )


MID_PAGE_MARGINALS = """340. (3) Whoever possesses any seal, plate or other instrument knowing the same to be
counterfeit, shall be punished with imprisonment of either description for a term which may
extend to three years, and shall also be liable to fine.
Forgery of
record of
Court or of
public register,
etc.
Having
possession of
document
21 of 2000.
(4) Whoever fraudulently or dishonestly uses as genuine any seal, plate or other
instrument knowing it to be counterfeit shall be punished."""


def test_a_marginal_block_followed_by_more_body_is_stripped():
    pages = ["\n".join(f"{n}. Section {n}." for n in range(1, 340)), MID_PAGE_MARGINALS]
    text = gazette_sections(pages)[-1]["text"]
    assert (
        "Forgery of" not in text
        and "public register" not in text
        and "21 of 2000" not in text
    )
    assert "to be counterfeit shall be punished." in text
    assert "and shall also be liable to fine.\n(4) Whoever" in text


def test_marginal_blocks_ending_in_a_short_word_or_a_section_number_are_stripped():
    page = """1. (1) First sub-section of the first section, long enough to be body text here.
Procedure on
order being
made absolute
and
consequences
of
2. (1) If the Magistrate considers the charge against the accused to be groundless, he
shall discharge the accused, and record his reasons for so doing.
Compliance
with section
230.
Sec. 1]
THE GAZETTE OF INDIA EXTRAORDINARY
62"""
    recs = {r["section"]: r["text"] for r in gazette_sections([page])}
    assert (
        recs["1"]
        == "(1) First sub-section of the first section, long enough to be body text here."
    )
    assert recs["2"].endswith("reasons for so doing.")


def test_a_section_number_alone_at_a_page_end_is_still_a_heading():
    pages = [
        "1. First section text, long enough to be a body line of the page.\n2.\nTHE GAZETTE OF INDIA EXTRAORDINARY\n",
        "3\n(1) Text of the second section, which began on the previous page.",
    ]
    recs = {r["section"]: r["text"] for r in gazette_sections(pages)}
    assert (
        recs["2"] == "(1) Text of the second section, which began on the previous page."
    )


def test_short_limbs_ending_a_page_are_not_mistaken_for_side_headings():
    page = """1. Text of the first section that is long enough to be a line.
(a) the first limb of the test;
(b) the second limb of the test; and
Sec. 1]
THE GAZETTE OF INDIA EXTRAORDINARY
5"""
    assert gazette_sections([page])[0]["text"].endswith(
        "(b) the second limb of the test; and"
    )
