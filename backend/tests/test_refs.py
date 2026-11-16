import pytest

from legallens.refs import find_references, split_refs

IPC = "Indian Penal Code"
BNS = "Bharatiya Nyaya Sanhita"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What is IPC 302?", [(IPC, "302")]),
        ("IPC section 376", [(IPC, "376")]),
        ("section 420 of the IPC", [(IPC, "420")]),
        ("Section 498A IPC", [(IPC, "498A")]),
        ("IPC sections 302", [(IPC, "302")]),
        ("IPC 100 BNS 101", [(IPC, "100"), (BNS, "101")]),
        ("in 2023 BNS 103", [(BNS, "103")]),
        ("what is the punishment for murder", []),
        ("Article 21 of the Constitution", []),
    ],
)
def test_find_references(query, expected):
    assert find_references(query) == expected


def test_split_refs_round_trips_multiple_references():
    assert split_refs(f"{BNS} 103; {BNS} 64") == [(BNS, "103"), (BNS, "64")]
    assert split_refs(None) == []
