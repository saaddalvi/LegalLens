"""NCRB "Corresponding Section Table" (flattened two-column text) -> section mappings."""

from legallens.ingestion.mapping_tables import parse_corresponding_table

NEW, OLD = "Bharatiya Nagarik Suraksha Sanhita", "Code of Criminal Procedure"

INDEX_PAGE = """P a g e  | 3
 Corresponding Section Table of BNSS with Repealed Act
1. Short title, extent and commencement.
2. Definitions."""

# Real excerpts: wrapped titles in either column, "Deleted" rows (old section only), a number
# that lands on a later line than its title, "New Section" on its own line or trailing.
TABLE_1 = """P a g e  | 20
HomePage
 Corresponding Section Table of BNSS with Repealed Act
Bharatiya Nagarik Suraksha
Sanhita, 2023
Code of Criminal Procedure, 1973
CHAPTER I
PRELIMINARY
CHAPTER I
PRELIMINARY
1.  Short title, extent and
commencement.
1.  Short title, extent and
commencement
2.  Definitions. 2.  Definitions.
4. Trial of offences under Bharatiya
Nyaya Sanhita, 2023 and other laws.
4.  Trial of offences under the Indian
Penal Code and other laws.
7. Territorial divisions. 7. Territorial divisions.
Deleted 8. Metropolitan areas.
8. Court of Session 9.  Court of Session.
Deleted 10. Subordination of Assistant
Sessions Judges.
9.  Courts of Judicial Magistrates.

11.  Courts of Judicial Magistrates.
10.  Chief Judicial Magistrate and
Additional Chief Judicial Magistrate,
etc.

12.  Chief Judicial Magistrate and
Additional Chief Judicial Magistrate,
etc.
11.  Special Judicial Magistrates 13.  Special Judicial Magistrates."""

# Sub-section rows: 35 maps to 41 (and 41A), 43 has a new sub-section, a "–" range.
TABLE_2 = """P a g e  | 21
CHAPTER V
ARREST OF PERSONS
CHAPTER V
ARREST OF PERSONS
35.   When police may arrest without
warrant

35(1)
41.  When police may arrest without
warrant.
35(2) 41(2)
35(3), 35(4) 35(5), 35(6) 41A Notice of appearance before
police officer
 35(7)  New Sub-Section

36.  Procedure of arrest and duties of
officer making arrest.
41B.  Procedure of arrest and duties
of officer making arrest.
43. Arrest how made.   46.  Arrest how made.
43(1) 46(1)
43(2) 46(2)
43(3)  New Sub-Section
43(4) 46(3)
43(5) 46(4)
44.   Search of place entered by
person sought to be arrested
47.   Search of place entered by
person sought to be arrested.
65. Service of summons on corporate
bodies, firms, and societies.
65(1)
63.  Service of summons on
corporate bodies and societies.
65(2)  New Sub-Section
86. Identification and attachment
of property of proclaimed person.
New Section
87. Claims and objections to
attachment.
84.  Claims and objections to
attachment."""

TABLE_3 = """P a g e  | 40
172.  Persons bound to conform
to lawful directions of police.
New Section
Deleted 153. Inspection of weights and
measures.
CHAPTER-XIII INFORMATION TO
THE POLICE AND THEIR POWERS
TO INVESTIGATE
CHAPTER-XII INFORMATION TO
THE POLICE AND THEIR POWERS
175. Police officer’s power to
investigate cognizable case.
175(1)
156.  Police officer’s power to
investigate cognizable case.
175(2) 156(2)
175(3) 156(3)
175(4) New Sub-Section
395. Order to pay compensation.  357. Order to pay compensation.
396. Victim compensation scheme.
396(1) – 396(6) 357A. Victim compensation scheme.
396(7)  357B. Compensation to be in addition
to fine under section 326A or section
376D of Indian Penal Code.
397. Treatment of victims.  357C. Treatment of victims.
398. Witness protection scheme. New Section
399. Compensation to persons
groundlessly arrested.
358. Compensation to persons
groundlessly arrested."""

TAIL = "Chapters and Sections   HomePage\nCHAPTER I\n1. (1) This Act may be called the Bharatiya Nagarik Suraksha Sanhita, 2023."


def table():
    return parse_corresponding_table(
        [INDEX_PAGE, TABLE_1, TABLE_2, TABLE_3, TAIL],
        new_act=NEW,
        old_act=OLD,
        old_title="Code of Criminal Procedure, 1973",
    )


def pairs():
    return {(m["new_number"], m["old_number"]) for m in table().mappings}


def test_plain_and_wrapped_rows_map_one_to_one():
    p = pairs()
    assert {
        ("1", "1"),
        ("2", "2"),
        ("4", "4"),
        ("7", "7"),
        ("8", "9"),
        ("11", "13"),
    } <= p


def test_a_number_on_a_later_line_than_its_title():
    p = pairs()
    assert {("9", "11"), ("10", "12")} <= p


def test_deleted_rows_are_old_sections_with_no_new_counterpart():
    t = table()
    assert t.deleted == ["8", "10", "153"]
    assert not any(m["old_number"] in {"8", "10", "153"} for m in t.mappings)


def test_new_sections_have_no_old_counterpart():
    t = table()
    assert t.new == ["86", "172", "398"]
    assert not any(m["new_number"] in {"86", "172", "398"} for m in t.mappings)


def test_sub_section_rows_collapse_to_their_sections():
    p = pairs()
    assert ("43", "46") in p and ("65", "63") in p and ("175", "156") in p
    assert not any("(" in n for pair in p for n in pair)


def test_one_new_section_maps_to_several_old_sections():
    p = pairs()
    assert {("35", "41"), ("35", "41A"), ("36", "41B")} <= p
    assert {("396", "357A"), ("396", "357B")} <= p


def test_new_sub_sections_and_headings_do_not_leak_in():
    p = pairs()
    assert ("35", "35") not in p and ("43", "43") not in p
    assert ("87", "84") in p and ("399", "358") in p
    assert ("395", "357") in p and ("397", "357C") in p


def test_mappings_carry_act_names_and_the_table_ends_at_the_act_text():
    m = table().mappings[0]
    assert (m["new_act"], m["old_act"]) == (NEW, OLD)
    assert not any(
        m["new_number"] == "1" and m["old_number"] != "1" for m in table().mappings
    )
    assert len(table().mappings) == len(pairs())  # no duplicates


# More real quirks: a hyphenated old number ("105-I."), an old number with no full stop
# ("151 Arrest ..."), and a row whose old side is only sub-sections of other sections.
TABLE_4 = """P a g e  | 30
120.  Fine in lieu of forfeiture.
105-I. Fine in lieu of forfeiture.
121.  Certain transfers to be null and
void.
105J. Certain transfers to be null and
void.
122.  Procedure in respect of letter of
request.
105K. Procedure in respect of letter
of request.
170.  Arrest to prevent commission of
cognizable offences.
151 Arrest to prevent commission of
cognizable offences.
171.  Prevention of injury to public
property.
152.  Prevention of injury to public
property.
283.  Summary trial for imprisonment up to
two years
260 (1). (i) Summary trial for
imprisonment upto two years
283(3) 260(2).
284. Summary trial by Magistrate of
second class.
261. Summary trial by Magistrate of
second class.
285. Procedure for summary trials.  262. Procedure for summary trials."""


def table_4():
    return parse_corresponding_table(
        ["Code of Criminal Procedure, 1973\n" + TABLE_4],
        new_act=NEW,
        old_act=OLD,
        old_title="Code of Criminal Procedure, 1973",
    )


def test_hyphenated_dotless_and_sub_section_only_old_sides():
    p = {(m["new_number"], m["old_number"]) for m in table_4().mappings}
    assert {("120", "105I"), ("121", "105J"), ("122", "105K")} <= p
    assert ("170", "151") in p and ("171", "152") in p
    assert {("283", "260")} <= p
    assert ("284", "261") in p and ("285", "262") in p
    assert ("122", "170") not in p and ("283", "284") not in p
