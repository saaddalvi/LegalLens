"""Indian Kanoon IPC text -> section records, on excerpts of real pypdf output.

The Kanoon PDF is unofficial and its text layer is damaged: "€" for a dash, "‚" and "ƒ" for
quotation marks, "„" for an apostrophe, and "□" or "−" where a hyphenated word broke across a
line. The adapter repairs those and the tests pin each repair.
"""

import pytest

from legallens.ingestion.pdf_text import kanoon_ipc_sections, repair_kanoon

START = """The Indian Penal Code, 1860
UNION OF INDIA
India
[This is the version of this document at 7 February 2022.]• 
The Indian Penal CodeAct No. 45 of 1860[6th October, 1860]WHEREAS it is expedient to provide a
general Penal Code for India;It is enacted as follows:--
Chapter 1
Introduction
1. Title and extent of operation of the Code.—
This Act shall be called the Indian Penal Code, and shall extend to the whole of India except the
State of Jammu and Kashmir.
2. Punishment of offences committed within India.—
Every person shall be liable to punishment under this Code and not otherwise for every act or
omission contrary to the provisions thereof, of which he shall be guilty within India.
3. Punishment of offences committed beyond, but which by law may be tried
within, India.—
Any person liable, by any Indian law to be tried for an offence committed beyond India shall be dealt
with according to the provisions of this Code.
Indian Kanoon - http://indiankanoon.org/doc/137539806/ 1
"""

PAGE_2 = """4. Extension of Code to extra-territorial offences. —
The provi□sions of this Code apply also to any offence committed by€(1)any citizen of India in any
place without and beyond India;(2)any person on any ship or aircraft registered in India wher□ever
it may be.Explanation .€ In this section€(a)the word ‚offenceƒ includes every act committed outside
India.IllustrationA, who is a citizen of India, commits a murder in Uganda.
5. Certain laws not to be affected by this Act.—
Nothing in this Act shall affect the provisions of any special or local law.
Chapter II
General Explanations
6. Definitions in the Code to be understood subject to excep−tions.—
Throughout this Code every definition of an offence shall be understood subject to the exceptions.
The Indian Penal Code, 1860
Indian Kanoon - http://indiankanoon.org/doc/137539806/ 2
"""

# Repealed sections are one-line "[Title.] Rep. by ..." entries with no dash.
PAGE_REPEALED = """7. Sense of expression once explained.—
Every expression which is explained in any part of this Code is used in conformity.
8. Gender.—
The pronoun “he” and its derivatives are used of any person.
9. Number.—
Unless the contrary appears from the context, words importing the singular number include the plural.
10. “Man”. “Woman”.—
The word ‚manƒ denotes a male human being of any age.
11. “Person”.—
The word ‚personƒ includes any Company or Association.
12. “Public”.—
The word ‚publicƒ includes any class of the public, or any community.
13. [Definition of “Queen”.] Omitted by the A. O. 1950
14. “Servant of Government”.—
The words ‚servant of Governmentƒ denote any officer or servant continued.
15. [Definition of “British India”.] Rep. by the A. O. 1937
16. [Definition of “Government of India”.] Rep., ibid
17. “Government”.—
The word ‚Governmentƒ denotes the Central Government or the Government of a State.
"""

# Headings with no dash at all (376AB, 376D) and one that wraps onto a second line (376A).
PAGE_376 = """376. Punishment for rape.—
(1) Whoever, except in the cases provided for in sub-section (2), commits rape, shall be punished with
rigorous imprisonment of either description for a term which shall not be less than ten years.
The Indian Penal Code, 1860
Indian Kanoon - http://indiankanoon.org/doc/137539806/ 100
376A. Punishment for causing death or resulting in persistent vegetative
state of victim.—
Whoever commits an offence punishable under sub-section (1) or sub-section (2) of section 376 and
in the course of such commission inflicts an injury, shall be punished.
376AB. Punishment for rape on woman under twelve years of age
Whoever, commits rape on a woman under twelve years of age shall be punished with rigorous
imprisonment for a term which shall not be less than twenty years, but which may extend to
imprisonment for life, or with death.
376B. Sexual intercourse by husband upon his wife during separation.—
Whoever has sexual intercourse with his own wife, who is living separately, shall be punished.
"""

LAST = """510. Misconduct in public by a drunken person.—
Whoever, in a state of intoxication, appears in any public place, shall be punished.
Chapter XXIII
Of Attempts to Commit Offences
The Indian Penal Code, 1860
Indian Kanoon - http://indiankanoon.org/doc/137539806/ 139

511. Punishment for attempting to commit offences punishable with
imprisonment for life or other imprisonment.—
Whoever attempts to commit an offence punishable by this Code shall be punished.
The Indian Penal Code, 1860
Indian Kanoon - http://indiankanoon.org/doc/137539806/ 140"""


def sections(pages, after=None):
    return {r["section"]: r for r in kanoon_ipc_sections(pages, after=after)}


def test_each_damaged_character_is_repaired():
    assert repair_kanoon("by€(1)any") == "by—(1) any"
    assert repair_kanoon("the word ‚offenceƒ includes") == "the word “offence” includes"
    assert repair_kanoon("Z„s door") == "Z’s door"
    assert repair_kanoon("the provi□sions, excep−tions") == "the provisions, exceptions"
    assert repair_kanoon("(a)†begging„ means") == "(a) “begging” means"


def test_words_the_pdf_split_or_ran_together_are_repaired():
    assert repair_kanoon("a term of imprisonment of either de\nscription") == (
        "a term of imprisonment of either description"
    )
    assert repair_kanoon("with impris onment for life") == "with imprisonment for life"
    assert (
        repair_kanoon("or fabri-\ncates false evidence")
        == "or fabricates false evidence"
    )
    assert repair_kanoon("of imprison-ment, sec tion 5") == "of imprisonment, section 5"
    assert repair_kanoon("(a)by a mer chant") == "(a) by a merchant"
    assert repair_kanoon("by force;orwith intent") == "by force;or with intent"
    assert repair_kanoon("or Secondly—orSecondly") == "or Secondly—or Secondly"
    assert repair_kanoon("the Act ofIndian origin") == "the Act of Indian origin"
    assert repair_kanoon("counterfeiting 1Indian coin, 2nd and 5th times") == (
        "counterfeiting Indian coin, 2nd and 5th times"
    )
    assert (
        repair_kanoon("a person, orange orchard") == "a person, orange orchard"
    )  # untouched
    assert repair_kanoon("a sub-section of the Act, non-cognizable") == (
        "a sub-section of the Act, non-cognizable"
    )


def test_run_together_subclauses_and_headings_are_spaced():
    assert (
        repair_kanoon("(2)any person on any ship;(3)any person")
        == "(2) any person on any ship;(3) any person"
    )
    assert (
        repair_kanoon("both.Illustrations(a)A sits") == "both. Illustrations (a) A sits"
    )
    assert (
        repair_kanoon("or with bothIllustrationA, a coiner")
        == "or with both Illustration A, a coiner"
    )
    assert repair_kanoon("Illustration(a)A sits") == "Illustration (a) A sits"
    assert repair_kanoon("it.Explanation .— In") == "it. Explanation .— In"
    assert repair_kanoon("section 2(a) of the Act") == "section 2(a) of the Act"


def test_sections_chapters_and_repairs():
    by = sections([START, PAGE_2])
    assert list(by) == ["1", "2", "3", "4", "5", "6"]
    assert by["1"]["chapter"] == "Chapter I" and by["6"]["chapter"] == "Chapter II"
    assert by["1"]["title"] == "Title and extent of operation of the Code."
    assert by["1"]["text"].startswith("This Act shall be called the Indian Penal Code")
    assert "provisions of this Code" in by["4"]["text"]
    assert "—(1) any citizen" in by["4"]["text"]
    assert "“offence” includes" in by["4"]["text"]
    assert (
        by["6"]["title"]
        == "Definitions in the Code to be understood subject to exceptions."
    )


def test_preamble_page_furniture_and_chapter_titles_are_not_text():
    by = sections([START, PAGE_2])
    for r in by.values():
        for junk in (
            "Kanoon",
            "The Indian Penal Code, 1860",
            "General Explanations",
            "Introduction",
        ):
            assert junk not in r["text"], (r["section"], junk)
    assert "WHEREAS" not in by["1"]["text"]


def test_a_title_wrapping_onto_a_second_line_is_joined():
    by = sections([START, PAGE_2])
    assert by["3"]["title"] == (
        "Punishment of offences committed beyond, but which by law may be tried within, India."
    )
    assert by["3"]["text"].startswith("Any person liable")


def test_repealed_and_omitted_sections_are_kept_as_one_line_entries():
    by = sections([PAGE_REPEALED], after=(6, ""))
    assert list(by) == [str(n) for n in range(7, 18)]
    assert by["13"]["title"] == ""
    assert by["13"]["text"] == "[Definition of “Queen”.] Omitted by the A. O. 1950"
    assert by["16"]["text"] == "[Definition of “Government of India”.] Rep., ibid"
    assert by["14"]["title"] == "“Servant of Government”."
    assert by["15"]["text"].endswith("Rep. by the A. O. 1937")


def test_headings_without_a_dash_and_lettered_sections():
    by = sections([PAGE_376], after=(375, ""))
    assert list(by) == ["376", "376A", "376AB", "376B"]
    assert by["376A"]["title"] == (
        "Punishment for causing death or resulting in persistent vegetative state of victim."
    )
    assert (
        by["376AB"]["title"] == "Punishment for rape on woman under twelve years of age"
    )
    assert by["376AB"]["text"].startswith(
        "Whoever, commits rape on a woman under twelve"
    )
    assert by["376B"]["title"].startswith("Sexual intercourse by husband")
    assert "page" not in by["376"]["text"] and "Kanoon" not in by["376"]["text"]


def test_a_chapter_heading_ahead_of_the_page_furniture_belongs_to_the_next_section():
    by = sections([LAST], after=(509, ""))
    assert (
        by["510"]["chapter"] == ""
    )  # no chapter heading has been seen in this excerpt
    assert by["511"]["chapter"] == "Chapter XXIII"
    assert "Attempts" not in by["510"]["text"]
    assert (
        by["511"]["text"]
        == "Whoever attempts to commit an offence punishable by this Code shall be punished."
    )


# Indian Kanoon drops section 333 and prints 334 twice (real text, shortened).
PAGE_333 = """332. Voluntarily causing hurt to deter public servant from his duty.—
Whoever voluntarily causes hurt to any public servant shall be punished.
334. Voluntarily causing hurt on provocation.—
Whoever voluntarily causes hurt on grave and sudden provocation shall be punished.
334. Voluntarily causing hurt on provocation.—
Whoever voluntarily causes hurt on grave and sudden provocation shall be punished.
335. Voluntarily causing grievous hurt on provocation.—
Whoever voluntarily causes grievous hurt on grave and sudden provocation shall be punished.
"""


def test_a_missing_section_is_skipped_and_a_repeated_one_is_not_doubled():
    recs = kanoon_ipc_sections([PAGE_333], after=(331, ""))
    assert [r["section"] for r in recs] == ["332", "334", "335"]
    assert recs[1]["text"] == (
        "Whoever voluntarily causes hurt on grave and sudden provocation shall be punished."
    )


def test_a_numbered_line_far_ahead_of_the_section_before_it_is_not_a_heading():
    pages = [
        "1. Title.—\nBody of one.\n9. A list item that is not a section.\nMore of one."
    ]
    recs = kanoon_ipc_sections(pages)
    assert [r["section"] for r in recs] == ["1"]
    assert "9. A list item" in recs[0]["text"]


# Kanoon's own "Part N" sub-division headings, and case-law notes it appends to a few sections.
PAGE_NOTES = """357. Assault or criminal force in attempt wrongfully to confine a person.—
Whoever assaults any person shall be punished.
358. Assault or criminal force on grave provocation.—
Whoever assaults or uses criminal force to any person on grave and sudden provocation shall be punished
with fine.
Part 5 – Of Kidnapping, Abduction, Slavery and Forced Labour
359. Kidnapping.—
Kidnapping is of two kinds.
360. Kidnapping from India.—
Whoever conveys any person beyond the limits of India shall be said to kidnap.[In Navtej Singh Johar v.
Union of India 2018, the apex Court read down Section 377 of the IPC. It applies to all citizens.
(https:privacylibrary.ccgnlud.org/case/navtej, https:indiankanoon.org/doc/168671544/)]
361. Kidnapping from lawful guardianship.—
Whoever [takes or entices] any minor out of the keeping of the lawful guardian shall be said to kidnap.
362. Abduction.—
Whoever by force compels any person to go from any place is said to abduct.[[Mithu v. State of Punjab :
In 1983, Section 303 was struck down.
(https:indiankanoon.org/doc/590378/)]]
"""


def test_part_headings_and_editorial_notes_are_not_statute_text():
    by = sections([PAGE_NOTES], after=(356, ""))
    assert (
        "Part 5" not in by["358"]["text"]
        and "Kidnapping, Abduction" not in by["358"]["text"]
    )
    assert (
        by["360"]["text"]
        == "Whoever conveys any person beyond the limits of India shall be said to kidnap."
    )
    assert (
        by["362"]["text"]
        == "Whoever by force compels any person to go from any place is said to abduct."
    )
    assert by["361"]["text"].startswith(
        "Whoever [takes or entices] any minor"
    )  # a real amendment


def test_a_page_without_any_section_is_an_error():
    with pytest.raises(ValueError):
        kanoon_ipc_sections(["nothing here"])
