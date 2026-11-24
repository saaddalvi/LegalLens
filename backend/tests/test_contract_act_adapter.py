"""Indian Contract Act text (Legislative Department print) -> section records, on excerpts of
real pypdf output."""

from legallens.ingestion.pdf_text import contract_act_sections

RULE = " " * 59  # the blank line of spaces that precedes a page's footnotes
FURNITURE = "This Bare Act is a government source available in the public domain. It is being used strictly for educational purposes only."

# The contents list comes first; its "1. Short title." has no text and must not yield a section.
TOC = f"""1
THE INDIAN CONTRACT ACT, 1872
ARRANGEMENT OF SECTIONS
PRELIMINARY
1. Short title.
Extent.
2. Interpretation-clause.
CHAPTER II
OF CONTRACTS, VOIDABLE CONTRACTS AND VOID
AGREEMENTS
26. Agreement in restraint of marriage, void.
27. Agreement in restraint of trade, void.
{FURNITURE}
"""

PAGE_START = f"""10

THE INDIAN CONTRACT ACT, 1872
ACT NO. 9 OF 18721
 [25th April, 1872.]
Preamble—WHEREAS it is expedient to define and amend certain parts of the law relating to
contracts;
It is hereby enacted as follows:—
PRELIMINARY
1. Short title.—This Act may be called the Indian Contract Act, 1872.
Extent, Commencement.—It extends to the whole of India 2[ 3***]; and it shall come into force on
the first day of September, 1872.
Saving—4*** Nothing herein contained shall affect the provisions of any Statute.
2. Interpretation-clause.—In this Act the following words and expressions are used in the following
senses, unless a contrary intention appears from the context:—
{RULE}
1. For the Statement of Objects and Reasons for the Bill, see Gazette of India, 1867.
2. Subs. by the A.O. 1950, for "and Burma".
"""

# Page furniture (page number, footer), a footnote block under a line of spaces, an
# amendment-marked section, glued footnote digits ("arbitration4."), a deleted-paragraph line
# ("3*****") and a heading with no space after the number ("28.Agreements").
PAGE_RESTRAINT = f"""18

26. Agreement in restraint of marriage, void.—Every agreement in restraint of the marriage of any
person, other than a minor, is void.
27. Agreement in restraint of trade, void.—Every agreement by which any one is restrained from
exercising a lawful profession, trade or business of any kind, is to that extent void.
Exception 1.—Saving of agreement not to carry on business of which good-will is sold.—One
who sells the good-will of a business may agree with the buyer to refrain from carrying on a similar
business, within specified local limits.
1*    *    *    *  *.
28.Agreements in restraint of legal proceedings, void.—2[Every agreement,—
(a) by which any party thereto is restricted absolutely from enforcing his rights; or
(b) which extinguishes the rights of any party thereto,
is void to the extent.]
Exception 1.—Saving of contract to refer to arbitration dispute that may arise.—This section
shall not render illegal a contract, by which two or more persons agree to refer.
3*****
Exception 2.—Nor shall this section affect any provision of any law as to references to arbitration4.
{RULE}
1. Exceptions 2 and 3 rep. by Act 9 of 1932, s. 73 and the Second Schedule.
2. Subs. by Act 1 of 1997, s. 2, for certain words (w.e.f. 8-1-1997).
{FURNITURE}
"""

# A title that wraps onto a second line, and a heading marked as an amendment.
PAGE_WRAPPED = f"""19

19. Voidability of agreements without free consent.—When consent is caused by coercion, the
agreement is a contract voidable at the option of the party.
2[19A. Power to set aside contract induced by undue influence.—When consent to an agreement is
caused by undue influence, the agreement is a contract voidable at the option of the party.]
25. Agreement without consideration, void, unless it is in writing and registered, or is a
promise to compensate for something done.—An agreement made without consideration is void.
1[Exception 3.—Saving of a guarantee agreement of a bank.—This section shall not render illegal.
Explanation.—(i) In Exception 3, the expression “bank” means—
(a) a “banking company”.]
{FURNITURE}
"""

# s.74 with its amendment brackets, then the repealed Chapter VII, whose entries have no text and
# whose last entry wraps onto a line that must not leak into the section before it.
PAGE_PENALTY = f"""41

CHAPTER VI
OF THE CONSEQUENCES OF BREACH OF CONTRACT
73. Compensation for loss or damage caused by breach of contract.—When a contract has been broken,
the party who suffers by such breach is entitled to receive compensation.
74. Compensation for breach of contract where penalty stipulated for.—1[When a contract has
been broken, if a sum is named in the contract as the amount to be paid in case of such breach, or if the
contract contains any other stipulation by way of penalty, the party complaining of the breach is entitled,
whether or not actual damage or loss is proved to have been caused thereby, to receive from the party who
has broken the contract reasonable compensation not exceeding the amount so named or, as the case may
be, the penalty stipulated for.
Explanation.—A stipulation for increased interest from the date of default may be a stipulation by
way of penalty.]
Exception.—When any person enters into any bail-bond, recognizance or other instrument of the
same nature, he is liable for the whole sum.
Illustrations
(a) A contracts to pay B Rs. 1,000 on 1st January.
75. Party rightfully rescinding contract, entitled to compensation.—A person who rightfully rescinds a
contract is entitled to compensation.
[CHAPTER VII.—SALES OF GOODS.] Rep.by the Indian Sale of Goods Act, 1930 (3 of 1930), s. 65.
76.[‘Goods’ of defined.] Rep. by s. 65,ibid.
77.[‘Sale defined.] Rep. by s. 65,ibid.
123. [Effect of use, by seller, of pretended biddings to raise price.] Rep. by s.
65,ibid.
CHAPTER VIII
OF INDEMNITY AND GUARANTEE
124.“Contract of indemnity” defined.—A contract by which one party promises to save the other
from loss, is called a “contract of indemnity”.
{FURNITURE}
"""

PAGE_END = """53

265. [Right of partners to apply for winding-up after termination of partnership.] Rep. by s. 73 and
the Second Schedule, ibid.
SCHEDULE.—[Enactments repealed.] Rep. by the Repealing and Amending Act, 1914 (10 of 1914),
s. 3 and the Second Schedule.
"""


def _sections(*pages: str) -> dict[str, dict]:
    return {r["section"]: r for r in contract_act_sections(list(pages), gap=500)}


def test_contents_list_yields_no_sections():
    sections = _sections(TOC, PAGE_START)
    assert sections["1"]["text"].startswith("This Act may be called")


def test_section_one_keeps_its_unnumbered_paragraphs_without_footnote_marks():
    s1 = _sections(TOC, PAGE_START)["1"]
    assert "Extent, Commencement.—It extends to the whole of India" in s1["text"]
    assert "Saving—" in s1["text"]
    assert "***" not in s1["text"] and "[" not in s1["text"]
    assert (
        "Statement of Objects" not in _sections(TOC, PAGE_START)["2"]["text"]
    )  # a footnote
    assert s1["chapter"] == "Preliminary"
    assert s1["title"] == "Short title"


def test_section_27_has_its_number_title_and_text_without_page_furniture():
    sections = _sections(TOC, PAGE_START, PAGE_RESTRAINT)
    s27 = sections["27"]
    assert s27["title"] == "Agreement in restraint of trade, void"
    assert s27["text"].startswith(
        "Every agreement by which any one is restrained from\nexercising a lawful profession"
    )
    assert "Exception 1.—Saving of agreement not to carry on business" in s27["text"]
    assert "Bare Act" not in s27["text"]
    assert "restraint of marriage" not in s27["text"]  # s.26 ends before it
    assert "Exceptions 2 and 3 rep." not in sections["28"]["text"]  # a footnote
    assert "Subs. by Act 1 of 1997" not in sections["28"]["text"]
    assert not s27["text"].rstrip().endswith("*")  # a deleted-paragraph line


def test_a_heading_without_a_space_after_the_number_still_starts_a_section():
    s28 = _sections(TOC, PAGE_START, PAGE_RESTRAINT)["28"]
    assert s28["title"] == "Agreements in restraint of legal proceedings, void"
    assert s28["text"].startswith(
        "Every agreement,—"
    )  # the amendment mark "2[" is gone
    assert "is void to the extent." in s28["text"]
    assert "references to arbitration." in s28["text"]  # glued footnote digit gone
    assert "3*****" not in s28["text"]


def test_a_title_wrapping_onto_a_second_line_and_a_lettered_section():
    sections = _sections(TOC, PAGE_START, PAGE_WRAPPED)
    s25 = sections["25"]
    assert s25["title"].endswith("or is a promise to compensate for something done")
    assert s25["text"].startswith("An agreement made without consideration is void.")
    assert "Exception 3.—Saving of a guarantee agreement of a bank." in s25["text"]
    assert (
        sections["19A"]["title"]
        == "Power to set aside contract induced by undue influence"
    )


def test_section_74_is_whole_and_repealed_entries_are_not_sections():
    sections = _sections(TOC, PAGE_START, PAGE_WRAPPED, PAGE_RESTRAINT, PAGE_PENALTY)
    s74 = sections["74"]
    assert (
        s74["title"]
        == "Compensation for breach of contract where penalty stipulated for"
    )
    assert s74["text"].startswith("When a contract has\nbeen broken, if a sum is named")
    assert (
        "penalty stipulated for.\nExplanation.—A stipulation for increased interest"
        in s74["text"]
    )
    assert "Exception.—When any person enters into any bail-bond" in s74["text"]
    assert "(a) A contracts to pay B Rs. 1,000" in s74["text"]
    assert "]" not in s74["text"]
    assert "rightfully rescinds" not in s74["text"]  # that is s.75
    for repealed in ("76", "77", "123"):
        assert repealed not in sections
    assert (
        "Rep." not in sections["75"]["text"]
    )  # the repealed chapter line stays out of s.75
    assert sections["124"]["chapter"] == "Chapter VIII"
    assert (
        sections["74"]["chapter"] == "Chapter VI"
    )  # its title line is not part of the name


def test_the_repealed_schedule_ends_the_act():
    sections = _sections(TOC, PAGE_START, PAGE_END)
    assert "265" not in sections
    assert set(sections) == {"1", "2"}


def test_a_footnote_mark_glued_to_the_section_number_is_dropped():
    page = """55

150.Bailor’s duty to disclose faults in goods bailed.—The bailor is bound to disclose faults.
1151. Care to be taken by bailee.—In all cases of bailment the bailee is bound to take care.
152.Bailee when not liable for loss, etc., of thing bailed.—The bailee is not responsible.
"""
    sections = _sections(TOC, PAGE_START, page)
    assert [s for s in sections if s not in ("1", "2")] == ["150", "151", "152"]
    assert sections["151"]["title"] == "Care to be taken by bailee"
