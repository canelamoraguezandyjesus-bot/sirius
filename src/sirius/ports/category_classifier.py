"""Port for automatic category classification (D7, SIRIUS-ARQ-0.2 §6.1).

A single-method ``Protocol`` deliberately narrower than ``LLMProvider``: the
paid provider never intervenes in category classification (D7 point 5) —
only a local-model adapter (``OllamaCategoryClassifierAdapter``) implements
this port.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["CategoryClassifierPort"]


class CategoryClassifierPort(Protocol):
    """Classifies a piece of content into the closed category vocabulary.

    Implementations must never propagate an exception: any internal failure
    (model unavailable, connection refused, timeout, a response outside the
    closed vocabulary) is reported as ``None``, exactly like "I could not
    decide" — never as a raised error. Callers (``TagCategoryUseCase``) rely
    on this to fail open without a ``try``/``except`` of their own.
    """

    def classify(self, content: str) -> str | None:
        """Return a category from the closed vocabulary, or ``None`` if no
        confident classification could be made."""
        ...
