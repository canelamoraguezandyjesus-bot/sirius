"""Port for a deterministic, local token-cost estimate (B6c; SIRIUS-ARQ-0.1
S6.2/S6.3; ATD-007).

S6.2's token budget is "una barrera con margen" against a section growing
unbounded, not an exact provider count — Sirius 0.1 adds no tokenizer
dependency (no ``tiktoken``) and never calls a provider just to size a
budget. A deterministic local estimate is sufficient and keeps every budget
computation offline and reproducible; ``sirius.application.context_budget``
depends only on this Protocol, never on a concrete estimator.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["TokenCounter"]


class TokenCounter(Protocol):
    """Estimates the token cost of a piece of text."""

    def count_tokens(self, text: str) -> int:
        """Return a deterministic, non-negative estimate of ``text``'s token
        cost. Never calls a network or an external provider, and never
        varies between calls for the same ``text``."""
        ...
