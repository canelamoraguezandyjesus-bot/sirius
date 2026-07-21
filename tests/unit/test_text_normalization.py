import pytest

from sirius.domain.text_normalization import normalize_whitespace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello world", "hello world"),
        ("hello    world", "hello world"),
        ("  hello world  ", "hello world"),
        ("hello\t\tworld", "hello world"),
        ("hello\n\nworld", "hello world"),
        ("hello \t\n world", "hello world"),
        ("", ""),
        ("   ", ""),
        ("\t\n", ""),
        ("single", "single"),
    ],
)
def test_normalize_whitespace(text: str, expected: str) -> None:
    assert normalize_whitespace(text) == expected
