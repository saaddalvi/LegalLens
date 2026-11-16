"""NCRB BNS-IPC corresponding table -> mappings, on excerpts of real pypdf output."""

from legallens.ingestion.mapping_tables import parse_bns_table

NEW, OLD = "Bharatiya Nyaya Sanhita", "Indian Penal Code"
END = "Chapters and Sections\nCHAPTER I\n1. Short title.—text"
HEAD = "Indian Penal Code, 1860\n"

# BNS 1 and 2: sub-section rows, each with its own IPC section; "New Section" and "Deleted" rows.
PAGE_START = """CHAPTER I – PRELIMINARY CHAPTER I – INTRODUCTION 
1. Short title, commencement and 
application 
1(1) 
 
1. Title and extent of operation of the 
Code. 
1(2) New Section 
1(3) 2. Punishment of offences committed 
within India. 
1(4) 
 
3. Punishment of offences committed 
beyond, but which by law may be 
tried within, India. 
1(5) 4. Extension of Code to extra-
territorial offences. 
1(6) 5. Certain laws not to be affected by 
this Act. 
2. Definitions.  
2(1) ‘act’ 33. “Act”. “Omission” 
2(2) ‘animal’ 47. “Animal”. 
2(3) ‘child’ New Sub-Section 
2(4) ‘counterfeit’ 28. “Counterfeit”. 
Deleted 29A. “Electronic record”. 
2(9) ’fraudulently’ 25. “Fraudulently” 
Deleted 14- “Servant of Government”. 
2(28) ‘public servant’ 21. “Public servant”. 
2(39) New Sub-Section 
3. General explanations  
3(1) 
 
6. Definitions in the Code to be 
understood subject to exceptions. 
3(2) 7. Sense of expression once 
explained. 
"""

# One IPC section per BNS section, lettered IPC sections, a new sub-section row and new sections.
PAGE_HOMICIDE = """100. Culpable homicide. 299. Culpable homicide 
101. Murder.  300. Murder. 
102. Culpable homicide by causing 
death of person other than person 
whose death was intended.  
301. Culpable homicide by causing 
death of person other than person 
whose death was intended. 
103. Punishment for murder.  302. Punishment for murder. 
104. Punishment for murder by life-
convict.  
303. Punishment for murder by life-
convict. 
105. Punishment for culpable 
homicide not amounting to murder.  
304. Punishment for culpable 
homicide not amounting to murder. 
106. Causing death by negligence. 304A. Causing death by negligence. 
106(2) Hit & Run New Sub-Section 
107. Abetment of suicide of child or 
person of unsound mind.  
305. Abetment of suicide of child or 
insane person. 
108. Abetment of suicide.  306. Abetment of suicide. 
109. Attempt to murder.  307. Attempt to murder. 
110. Attempt to commit culpable 
homicide.  
308. Attempt to commit culpable 
homicide. 
111. Organised crime New Section 
112. Petty organised crime.  New Section 
113. Terrorist act.  New Section 
Of hurt Of Hurt 
114. Hurt.  319. Hurt 
115. Voluntarily causing hurt.   
115(1) 
 
321. Voluntarily causing hurt. 
115(2) 323. Punishment for voluntarily 
causing hurt. 
116. Grievous hurt.  320. Grievous hurt. 
"""


def table(body, first):
    return parse_bns_table([HEAD + body, END], NEW, OLD, first=first)


def pairs(body, first):
    return {(m["new_number"], m["old_number"]) for m in table(body, first).mappings}


def test_sub_section_rows_each_carry_their_own_ipc_section():
    p = pairs(PAGE_START, 1)
    assert {("1", "1"), ("1", "2"), ("1", "3"), ("1", "4"), ("1", "5")} <= p
    assert {("2", "33"), ("2", "47"), ("2", "28"), ("2", "25"), ("2", "21")} <= p
    assert {("3", "6"), ("3", "7")} <= p


def test_ipc_section_numbers_equal_to_the_next_bns_number_are_still_old_sections():
    # "1(3) 2. Punishment..." and "1(4) 3. Punishment...": the old sections 2 and 3 follow a marker.
    assert {("1", "2"), ("1", "3")} <= pairs(PAGE_START, 1)


def test_deleted_rows_and_new_sub_sections():
    t = table(PAGE_START, 1)
    assert t.deleted == ["14", "29A"]
    assert (
        t.new == []
    )  # "New Section" on 1(2) and "New Sub-Section" rows do not make BNS 1 or 2 new
    assert ("2", "14") not in pairs(PAGE_START, 1)


def test_whole_section_rows_and_lettered_ipc_sections():
    p = pairs(PAGE_HOMICIDE, 100)
    assert {("100", "299"), ("101", "300"), ("102", "301"), ("103", "302")} <= p
    assert ("106", "304A") in p and ("107", "305") in p
    assert {("114", "319"), ("115", "321"), ("115", "323"), ("116", "320")} <= p


def test_new_sections_have_no_ipc_counterpart():
    t = table(PAGE_HOMICIDE, 100)
    assert t.new == ["111", "112", "113"]
    assert not {"111", "112", "113"} & {n for n, _ in pairs(PAGE_HOMICIDE, 100)}


# An old sub-section printed with a space and no dot ("228A (3)"), then the next row.
PAGE_SUBCLAUSE = """72. Disclosure of identity of  victim of 
certain offences, etc. 
228A. Disclosure of identity of the 
victim of certain offences, etc. 
73. Printing or publishing of any 
matter relating to Court proceedings 
without permission. 
228A (3) 
Of criminal force and assault 
74. Assault or use of criminal force to 
woman with intent to outrage her 
modesty.  
354. Assault or criminal force to 
woman with intent to outrage her 
modesty. 
75. Sexual harassment. 354A. Sexual harassment and 
punishment for sexual harassment. 
"""


def test_an_old_sub_section_without_a_dot_still_closes_the_row():
    p = pairs(PAGE_SUBCLAUSE, 72)
    assert {("72", "228A"), ("73", "228A"), ("74", "354"), ("75", "354A")} <= p


def test_a_hyphenated_lettered_ipc_section_is_stored_without_the_hyphen():
    page = (
        "176. Illegal payments in connection \nwith an election.  \n171H. Illegal payments.\n"
        "177. Failure to keep election \naccounts. \n171-I. Failure to keep election \naccounts. \n"
        "CHAPTER X \nOF OFFENCES\n"
        "178. Counterfeiting coin. \n231. Counterfeiting coin. \n"
    )
    p = pairs(page, 176)
    assert {("176", "171H"), ("177", "171I"), ("178", "231")} <= p


def test_no_space_after_the_dot_of_an_ipc_section():
    page = (
        "253. Harbouring offender who has \nescaped from custody.  \n216. Harbouring offender who has \nescaped from custody. \n"
        "254. Penalty for harbouring robbers or \ndacoits.  \n216A.Penalty for harbouring robbers \nor dacoits. \n"
        "255. Public servant disobeying \ndirection of law.  \n217. Public servant disobeying \ndirection of law. \n"
    )
    assert {("253", "216"), ("254", "216A"), ("255", "217")} <= pairs(page, 253)


def test_a_bns_sub_section_printed_with_a_space_belongs_to_its_own_row():
    page = (
        "178. Counterfeiting coin, Government stamps. \n231. Counterfeiting coin. \n255. Counterfeiting Government \nstamp. \n"
        "Explanation  \n178 (1) Explanation to 489A \n178 (2) 230. \u201cCoin\u201d defined. \n"
        "179. Using as genuine, forged or counterfeit coin. \n237. Import or export of counterfeit \ncoin. \n"
    )
    p = pairs(page, 178)
    assert {("178", "231"), ("178", "255"), ("178", "230"), ("179", "237")} <= p
    assert ("178", "178") not in p


def test_a_row_whose_only_bns_marker_is_a_sub_section():
    # BNS 319 has no "319." heading in the table, only "319(1)" and "319(2)".
    page = (
        "318. Cheating.  \n318 (1) \n \n415. Cheating. \n318 (2) 417. Punishment for cheating. \n"
        "Cheating by personation \n319(1)  \n \n416. Cheating by personation. \n"
        "319(2) 419. Punishment of cheating by \npersonation. \n"
        "320. Dishonest or fraudulent removal \nof property.\n421. Dishonest or fraudulent removal \nof property. \n"
    )
    p = pairs(page, 318)
    assert {
        ("318", "415"),
        ("318", "417"),
        ("319", "416"),
        ("319", "419"),
        ("320", "421"),
    } <= p
