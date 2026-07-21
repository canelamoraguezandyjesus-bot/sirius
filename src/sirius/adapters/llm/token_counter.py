"""Deterministic local estimator implementing ``TokenCounter`` (B6c).

Uses the common "~4 characters per token" rule of thumb for English-like
text — a coarse, documented heuristic, never a real tokenizer. It exists only
to give S6.2's token budget a barrier with margin, so precision beyond that
is not a goal; no dependency (no ``tiktoken``) and no network call are
involved, matching ``sirius.ports.token_counter.TokenCounter``'s contract.
"""

from __future__ import annotations

import math

__all__ = ["CharacterHeuristicTokenCounter"]

_CHARACTERS_PER_TOKEN = 4


class CharacterHeuristicTokenCounter:
    """Estimates token cost as ``ceil(len(text) / 4)``.

    Rounds up so that any non-empty text costs at least one token; an empty
    (or blank-only) text costs zero. Deterministic and pure: the same text
    always yields the same estimate.
    """

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return math.ceil(len(text) / _CHARACTERS_PER_TOKEN)
