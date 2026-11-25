"""Splitting a Contract's text into Clauses: deterministic code, tested on fixture Contracts."""

from legallens.clauses import PIECE_CHARS, count_clauses, split_clauses

NUMBERED = """RENT AGREEMENT
This agreement is made between Asha Rao (Landlord) and Ravi Kumar (Tenant).

1. Term
The tenancy lasts eleven months from 1 April 2025.

2. Rent
The Tenant shall pay Rs. 20,000 each month.

3. Deposit
The Tenant pays a deposit of Rs. 1,00,000.
"""


def numbers(text):
    return [c.number for c in split_clauses(text)]


def test_numbered_contract_gives_recitals_as_clause_zero_then_each_clause():
    clauses = split_clauses(NUMBERED)
    assert [c.number for c in clauses] == ["0", "1", "2", "3"]
    assert clauses[0].text.startswith("RENT AGREEMENT")
    assert "Asha Rao" in clauses[0].text
    assert clauses[2].heading == "Rent"
    assert clauses[2].text == "2. Rent\nThe Tenant shall pay Rs. 20,000 each month."


def test_no_clause_zero_when_the_text_starts_with_clause_one():
    assert numbers("1. A\nfirst.\n2. B\nsecond.") == ["1", "2"]


NESTED = """1. Payments
1.1 Rent is due on the 5th.
1.2 Late rent attracts interest.
7. Termination
7.1 Either party may terminate on notice.
7.2 Notice is two months.
7(a) Notice must be in writing.
(b) Notice must be signed.
7.2.1 Notice by email is not valid.
8. Misc
(a) first thing
(i) sub thing
(ii) another sub thing
(b) second thing
"""


def test_nested_numbering_keeps_the_papers_numbers():
    assert numbers(NESTED) == [
        "1", "1.1", "1.2", "7", "7.1", "7.2", "7(a)", "7(b)", "7.2.1",
        "8", "8(a)", "8(a)(i)", "8(a)(ii)", "8(b)",
    ]  # fmt: skip


def test_a_date_or_amount_at_a_line_start_is_not_a_clause():
    text = "1. Term\nThe lease runs\n12 March 2025 to 11 February 2026.\n2. Rent\n5000 rupees monthly.\n"
    clauses = split_clauses(text)
    assert [c.number for c in clauses] == ["1", "2"]
    assert "12 March 2025" in clauses[0].text


def test_a_repeated_number_stays_inside_the_clause_it_follows():
    text = "1. A\nbody\n2. B\nbody\nSCHEDULE\n1. Item one\n"
    clauses = split_clauses(text)
    assert [c.number for c in clauses] == ["1", "2"]
    assert "Item one" in clauses[1].text


def test_unnumbered_paragraphs_are_numbered_in_order():
    text = "This agreement binds both.\nIt continues here.\n\nThe tenant pays rent.\n\n\nThe landlord repairs.\n"
    clauses = split_clauses(text)
    assert [c.number for c in clauses] == ["1", "2", "3"]
    assert clauses[0].text == "This agreement binds both.\nIt continues here."


def test_a_single_numbered_looking_line_does_not_make_the_contract_numbered():
    text = "1. only one\n\nSecond paragraph.\n"
    assert numbers(text) == ["1", "2"]


def test_blank_text_has_no_clauses():
    assert split_clauses("  \n\n ") == []


def test_a_long_clause_is_split_into_pieces_that_keep_its_number():
    sentence = "The Tenant shall keep the premises clean and in good repair. "
    long_body = sentence * 60  # one unbroken paragraph, several times the piece size
    clauses = split_clauses(f"1. Short\nok.\n2. Long\n{long_body}\n3. End\nok.")
    long = [c for c in clauses if c.number == "2"]
    assert len(long) > 1
    assert [c.piece for c in long] == list(range(len(long)))
    assert all(len(c.text) <= PIECE_CHARS for c in long)
    # The pieces rejoin into the Clause exactly as written.
    assert "".join(c.text for c in long) == f"2. Long\n{long_body.strip()}"
    assert all(c.heading == "Long" for c in long)
    assert [c.number for c in clauses if c.number != "2"] == ["1", "3"]


def test_paragraphs_one_per_line_are_numbered_when_there_are_no_blank_lines():
    assert numbers("The tenant pays rent.\nThe landlord repairs.\n") == ["1", "2"]


def test_the_count_is_of_top_level_numbers_without_the_recitals():
    assert count_clauses(["0", "1", "1.1", "1.2", "2", "2(a)", "2(a)(i)", "10.1"]) == 3
    assert count_clauses(["1.1", "1.2", "2.1"]) == 2  # no parent lines of their own
    assert count_clauses(["1", "1", "2"]) == 2  # the pieces of a long Clause
    assert count_clauses([]) == 0
