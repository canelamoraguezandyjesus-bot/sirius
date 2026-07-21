from __future__ import annotations

import pytest

from sirius.domain.text_normalization import normalize_whitespace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello world", "hello world"),
        ("hello   world", "hello world"),
        ("  hello world  ", "hello world"),
        ("hello\tworld", "hello world"),
        ("hello\nworld", "hello world"),
        ("hello \t\n  world", "hello world"),
        ("hello", "hello"),
        ("", ""),
        ("   ", ""),
        ("\t\n  \t", ""),
        ("  multiple   internal    gaps  here  ", "multiple internal gaps here"),
    ],
)
def test_normalize_whitespace(text: str, expected: str) -> None:
    assert normalize_whitespace(text) == expected


def test_normalize_whitespace_is_deterministic() -> None:
    text = "  a\tb\n\nc  "
    assert normalize_whitespace(text) == normalize_whitespace(text)
