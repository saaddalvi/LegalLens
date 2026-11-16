"""Transfer of Property Act Chapter V (leases) from the ILA text -> section records.

Excerpts are real pypdf output with its quirks kept: page furniture, footnotes dropped into the
middle of a section, a footnote number glued onto a section number ("2107."), amendment
markers ("1[114A."), and sub-headings run into the body.
"""

from legallens.ingestion.pdf_text import tpa_lease_sections

PAGE_A = """© International Insolvency Institute – www.iiiglobal.org
CHAPTER IV
OF MORTGAGES
104. Power to make rules
The High Court may, from time to time, make rules.
CHAPTER V
OF LEASES OF IMMOVEABLE PROPERTY
105. Lease defined
A lease of immoveable property is a transfer of a right to enjoy such property, made for a
certain time, express or implied, or in perpetuity, in consideration of a price paid or promised.
1 Subs. by Act 20 of 1929, sec. 52, for ¡§Where the person or agent to whom such tender
should be made cannot be found within the said district¡¨
2 Ins. by Act 20 of 1929, sec. 53.
Lessor, lessee, premium and rent defined
The transferor is called the lessor, the transferee is called the lessee.
106. Duration of certain leases in absence of written contract or local usage
In the absence of a contract or local law or usage to the contrary, a lease of immoveable
property for any other purpose shall be deemed to be a lease from month to month.
"""

PAGE_B = """© International Insolvency Institute – www.iiiglobal.org
Every notice under this section must be in writing, and 1[either be sent by post to the party
who is intended to be bound by it], or affixed to a conspicuous part of the property.
2107. Leasees how made
A lease of immoveable property from year to year can be made only by a registered instrument.
3[All other leases of immoveable property may be made either by a registered instrument or by
oral agreement accompanied by delivery of possession.
Provided that the State Government may 5[***] from time to time, by notification, direct
otherwise.]
1 Subs. by Act 20 of 1929, sec. 54, for ¡§tendered or delivered either personally to the party
who is intended to be bound by it¡¨.
2 As to limitation to the territorial operation of section 107, see sec. 1, supra, section 107
extends to every cantonment; see section 287 of the Cantonments Act, 1924 (2 of 1924).
108. Rights and liabilities of lessor and lessee
(a) The lessor is bound to disclose to the lessee any material defect in the property.
1 The words ¡§with the previous sanction of the Governor General in Council¡¨ omitted by the
A.O. 1937.
110. Exclusion of day on which term commences
Where the time limited by a lease is expressed as commencing from a particular day, such day shall be excluded.
Duration of lease for a year
Where the time so limited is a year, the lease shall last during the whole anniversary.
Illustrations
(a) A lets a house to B for five years.
111. Determination of lease  
A lease of immoveable property determines by efflux of the time limited thereby.  
112. Waiver of forfeiture  
A forfeiture is waived by acceptance of rent.  
113. Waiver of notice to quit  
A notice to quit is waived by any act showing an intention to treat the lease as subsisting.  
114. Relief against forfeiture for non-payment of rent
Where a lease has determined by forfeiture, the Court may pass an order relieving the lessee.
1[114A. Relief against forfeiture in certain other cases
Where a lease of immoveable property has determined by forfeiture, no suit shall lie unless the lessor has served notice in writing -
(a) specifying the particular breach complained of; and
Nothing in this section shall apply to an express condition against assigning.]
117. Exemption of leases for agricultural purposes
None of the provisions of this Chapter apply to leases for agricultural purposes.
CHAPTER VI
OF EXCHANGES
118. "Exchange" defined
When two persons mutually transfer the ownership of one thing, the transaction is called an "exchange".
"""


def by_number():
    return {r["section"]: r for r in tpa_lease_sections([PAGE_A, PAGE_B])}


def test_only_chapter_v_sections_are_returned_in_order():
    recs = tpa_lease_sections([PAGE_A, PAGE_B])
    assert [r["section"] for r in recs] == [
        "105",
        "106",
        "107",
        "108",
        "110",
        "111",
        "112",
        "113",
        "114",
        "114A",
        "117",
    ]
    assert {r["chapter"] for r in recs} == {"Chapter V"}


def test_text_follows_the_heading_without_the_title():
    text = by_number()["105"]["text"]
    assert text.startswith("A lease of immoveable property is a transfer of a right")
    assert "Lease defined" not in text


def test_footnotes_in_the_middle_of_a_section_are_dropped_with_their_wrapped_lines():
    recs = by_number()
    assert "Subs. by Act" not in recs["105"]["text"]
    assert "should be made cannot be found" not in recs["105"]["text"]
    assert recs["105"]["text"].endswith(
        "or promised.\nThe transferor is called the lessor, the transferee is called the lessee."
    )
    assert "Cantonments Act" not in recs["107"]["text"]
    assert "A.O. 1937" not in recs["108"]["text"]


def test_footnote_number_glued_to_a_section_number_is_removed():
    recs = by_number()
    assert "107" in recs and "2107" not in recs
    assert recs["107"]["text"].startswith(
        "A lease of immoveable property from year to year"
    )


def test_section_text_continues_across_a_page_break():
    text = by_number()["106"]["text"]
    assert text.endswith("affixed to a conspicuous part of the property.")
    assert "International Insolvency" not in text


def test_amendment_markers_are_removed_but_the_text_kept():
    recs = by_number()
    assert (
        "1[" not in recs["106"]["text"]
        and "either be sent by post" in recs["106"]["text"]
    )
    assert "[" not in recs["107"]["text"] and "]" not in recs["107"]["text"]
    assert "***" not in recs["107"]["text"]
    assert recs["107"]["text"].endswith("otherwise.")


def test_lettered_insertion_with_a_leading_amendment_marker_is_its_own_section():
    recs = by_number()
    assert recs["114A"]["text"].startswith(
        "Where a lease of immoveable property has determined by forfeiture, no suit"
    )
    assert recs["114A"]["text"].endswith("against assigning.")
    assert "[" not in recs["114A"]["text"]


def test_sub_headings_are_dropped_but_illustrations_are_kept():
    recs = by_number()
    assert "Lessor, lessee, premium and rent defined" not in recs["105"]["text"]
    assert "Duration of lease for a year" not in recs["110"]["text"]
    assert "Illustrations" in recs["110"]["text"]
    assert "(a) A lets a house to B for five years." in recs["110"]["text"]
