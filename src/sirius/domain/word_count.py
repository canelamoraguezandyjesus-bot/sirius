"""Pure word-counting helper used to smoke-test the automation pipeline."""

from __future__ import annotations


def count_words(text: str) -> int:
    """Count whitespace-separated words in ``text``."""
    return len(text.split())
