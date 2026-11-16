"""NCRB BSA-IEA corresponding table -> mappings, on excerpts of real pypdf output."""

from legallens.ingestion.mapping_tables import parse_bsa_table

NEW, OLD = "Bharatiya Sakshya Adhiniyam", "Indian Evidence Act"

# Rows with "2. Repealed" ahead of BSA 2, whose old sections 3 and 4 equal the next BSA number.
PAGE_START = """P a g e  | 9 
 
                            HomePage 
Corresponding Section Table of BSA with Repealed Act 
 
BHARATIYA SAKSHYA 
ADHINIYAM, 2023 
INDIAN EVIDENCE ACT, 1872 
PART I 
CHAPTER I 
PRELIMINARY 
 
1. Short title, application and 
commencement. 
 
1. Short title. Extent. Commencement 
of Act. 
 2. Repealed 
2. Definitions. 
 
 
 
3. Interpretation-clause. 
4. ― May Presume. 
―Shall presume. 
―Conclusive proof. 
3. Evidence may be given of facts in 
issue and relevant facts. 
5. Evidence may be given of facts in 
issue and relevant facts. 
Closely connected facts  
4. Relevancy of facts forming part of 
same transaction. 
6. Relevancy of facts forming part of 
same transaction. 
"""

# Provisos, sub-section rows, a deleted old section and an old section equal to the next BSA number.
PAGE_CONFESSIONS = """20. When oral admissions as to 
contents of documents are relevant. 
22. When oral admissions as to 
contents of documents are relevant. 
DELETED 22A. When oral admission as to 
contents of electronic records are 
relevant. 
21. Admissions in civil cases when 
relevant. 
23. Admissions in civil cases when 
relevant. 
22. Confession caused by inducement, 
threat, coercion or promise, when 
irrelevant in criminal proceeding. 
24. Confession caused by inducement, 
threat or promise, when irrelevant in 
criminal proceeding. 
22. Proviso 1 28. Confession made after removal of 
impression caused by inducement, 
threat or promise, relevant. 
22. Proviso 2 29. Confession otherwise relevant not 
to become irrelevant because of 
promise of secrecy, etc. 
23. Confession to police officer. 
23(1) 
25. Confession to police-officer not to 
be proved. 
23(2) 26. Confession by accused while in 
custody of Police not to be proved 
against him. 
23. Proviso 27. How much of information received 
from accused may be proved. 
24. Consideration of proved 
confession affecting person making 
it and others jointly under trial for 
30. Consideration of proved 
confession affecting person making it 
"""

PAGE_EXPERTS = """39. Opinions of experts. 
39(1)  
 
45. Opinions of experts. 
39(2)  45A. Opinion of Examiner of Electronic 
Evidence. 
40. Facts bearing upon opinions of 
experts. 
46. Facts hearing upon opinions of 
experts. 
"""

PAGE_NEW_AND_SUBS = """60. Cases in which secondary 
evidence relating to documents may 
be given. 
65. Cases in which secondary evidence 
relating to documents may be given. 
61. Electronic or digital record. New Section 
62. Special provisions as to evidence 
relating to electronic record. 
65A. Special provisions as to evidence 
relating to electronic record. 
"""

PAGE_PUBLIC = """74. Public and private documents. 
74(1). 
 
74. Public documents. 
74(2). 75. Private documents. 
75. Certified copies of public 
documents. 
76. Certified copies of public 
documents. 
"""

PAGE_GAZETTES = """80. Presumption as to Gazettes, 
newspapers, and other documents. 
 
 
Explanation 
81. Presumption as to Gazettes, 
newspapers, private Acts of 
Parliament and other documents. 
 
Explanation of S. 90 
81. Presumption as to Gazettes in 
electronic or digital record. 
 
Explanation 
81A. Presumption as to Gazettes in 
electronic forms. 
 
Explanation of S. 90A 
DELETED 82. Presumption as to document 
admissible in England without 
proof of seal or signature. 
82. Presumption as to maps or plans 
made by authority of Government. 
83. Presumption as to maps or plans 
made by authority of Government. 
"""

PAGE_LEADING = """146. Leading questions. 
146(1). 
 
141. Leading questions. 
146(2), 146(3). 142. When they must not be asked. 
146(4). 143. When they may be asked. 
147. Evidence as to matters in 
writing. 
144. Evidence as to matters in 
writing. 
"""

PAGE_LAST = """170. Repeal and savings. New Section 
 
 
Note: For Reference only. 
"""

END_PAGE = "Chapters and Sections\nCHAPTER I\n1. Short title.—text"
HEADING = "INDIAN EVIDENCE ACT, 1872\n"


def table(body, first):
    return parse_bsa_table([HEADING + body, END_PAGE], NEW, OLD, first=first)


def pairs(body, first):
    return {(m["new_number"], m["old_number"]) for m in table(body, first).mappings}


def test_plain_rows_and_old_sections_equal_to_the_next_bsa_number():
    p = pairs(PAGE_START, 1)
    assert {("1", "1"), ("2", "3"), ("2", "4"), ("3", "5"), ("4", "6")} <= p


def test_repealed_old_section_has_no_counterpart():
    assert ("2", "2") not in pairs(PAGE_START, 1)
    assert "2" in table(PAGE_START, 1).deleted


def test_deleted_marker_names_an_old_section_without_new_counterpart():
    t = table(PAGE_CONFESSIONS, 20)
    assert t.deleted == ["22A"]
    assert "22A" not in {m["old_number"] for m in t.mappings}
    assert ("21", "23") in pairs(PAGE_CONFESSIONS, 20)
    assert "82" in table(PAGE_GAZETTES, 80).deleted


def test_provisos_and_sub_section_rows_collapse_to_whole_section_pairs():
    p = pairs(PAGE_CONFESSIONS, 20)
    assert {("22", "24"), ("22", "28"), ("22", "29")} <= p
    assert {("23", "25"), ("23", "26"), ("23", "27")} <= p
    assert ("24", "30") in p
    assert {("39", "45"), ("39", "45A"), ("40", "46")} <= pairs(PAGE_EXPERTS, 39)


def test_old_section_after_a_sub_section_marker_is_not_the_next_row():
    assert {("74", "74"), ("74", "75"), ("75", "76")} <= pairs(PAGE_PUBLIC, 74)
    p = pairs(PAGE_LEADING, 146)
    assert {("146", "141"), ("146", "142"), ("146", "143"), ("147", "144")} <= p


def test_old_section_equal_to_the_next_bsa_number_with_an_explanation_between():
    p = pairs(PAGE_GAZETTES, 80)
    assert {("80", "81"), ("81", "81A"), ("82", "83")} <= p


def test_new_sections_are_listed_and_have_no_pairs():
    t = table(PAGE_NEW_AND_SUBS, 60)
    assert t.new == ["61"] and table(PAGE_LAST, 170).new == ["170"]
    assert "61" not in {n for n, _ in pairs(PAGE_NEW_AND_SUBS, 60)}
    assert ("62", "65A") in pairs(PAGE_NEW_AND_SUBS, 60)


def test_missing_table_heading_is_an_error():
    import pytest

    with pytest.raises(ValueError):
        parse_bsa_table(["nothing here"], NEW, OLD)
