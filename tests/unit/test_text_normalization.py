import pytest

from sirius.domain.text_normalization import normalize_whitespace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a  b", "a b"),
        ("  a b  ", "a b"),
        ("a\t\tb", "a b"),
        ("a\n\nb", "a b"),
        ("a \t\n b", "a b"),
        ("already normal", "already normal"),
        ("single", "single"),
        ("", ""),
        ("   ", ""),
        ("\t\n", ""),
    ],
)
def test_normalize_whitespace_collapses_and_trims(text: str, expected: str) -> None:
    assert normalize_whitespace(text) == expected


def test_normalize_whitespace_is_deterministic() -> None:
    text = "  Sirius   0.1  \t is\ncool  "
    assert normalize_whitespace(text) == normalize_whitespace(text)
    assert normalize_whitespace(text) == "Sirius 0.1 is cool"
