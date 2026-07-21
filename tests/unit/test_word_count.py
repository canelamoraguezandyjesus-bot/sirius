"""Unit tests for the pure ``count_words`` helper."""

from sirius.domain.word_count import count_words


def test_empty_string_returns_zero() -> None:
    assert count_words("") == 0


def test_whitespace_only_returns_zero() -> None:
    assert count_words("   \t\n  ") == 0


def test_single_word() -> None:
    assert count_words("hello") == 1


def test_multiple_words_with_mixed_separators() -> None:
    assert count_words("hello \t world\nfoo  bar") == 4


def test_leading_and_trailing_whitespace() -> None:
    assert count_words("  hello world  ") == 2
