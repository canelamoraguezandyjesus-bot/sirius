"""Unit tests for the deterministic local ``TokenCounter`` estimator (B6c).

No network, no dependency: only character arithmetic, so every assertion
here is exact rather than approximate.
"""

from __future__ import annotations

import pytest

from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter


@pytest.fixture
def counter() -> CharacterHeuristicTokenCounter:
    return CharacterHeuristicTokenCounter()


def test_empty_text_costs_zero_tokens(counter: CharacterHeuristicTokenCounter) -> None:
    assert counter.count_tokens("") == 0


@pytest.mark.parametrize(
    "text,expected_tokens",
    [
        ("a", 1),
        ("abcd", 1),
        ("abcde", 2),
        ("a" * 8, 2),
        ("a" * 9, 3),
    ],
)
def test_estimate_rounds_up_from_four_characters_per_token(
    counter: CharacterHeuristicTokenCounter, text: str, expected_tokens: int
) -> None:
    assert counter.count_tokens(text) == expected_tokens


def test_estimate_is_deterministic_across_repeated_calls(
    counter: CharacterHeuristicTokenCounter,
) -> None:
    text = "el mismo texto, siempre el mismo coste estimado"

    assert counter.count_tokens(text) == counter.count_tokens(text)


def test_a_longer_text_never_costs_fewer_tokens_than_a_prefix_of_it(
    counter: CharacterHeuristicTokenCounter,
) -> None:
    prefix = "contexto"
    longer = prefix + " ampliado con más contenido"

    assert counter.count_tokens(longer) >= counter.count_tokens(prefix)
