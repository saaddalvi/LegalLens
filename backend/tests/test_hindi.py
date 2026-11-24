import pytest

from legallens.language import detect_language


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", "en"),
        ("12345 ?", "en"),
        ("What is Article 21?", "en"),
        ("अनुच्छेद 21 क्या है", "hi"),
    ],
)
def test_detect_language(query, expected):
    assert detect_language(query) == expected
