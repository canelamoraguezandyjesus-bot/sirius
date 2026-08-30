"""Port for the model-backed relevance filter (D7, SIRIUS-ARQ-0.2 §6.3).

A single-method ``Protocol``, deliberately narrower than ``LLMProvider``:
only a local-model adapter (``OllamaRelevanceFilterAdapter``) implements it,
mirroring ``CategoryClassifierPort``'s split between the paid provider and a
local-only classification model (D7 point 5).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sirius.domain.relevance import RankedKnowledge

__all__ = ["RelevanceFilterPort"]


class RelevanceFilterPort(Protocol):
    """Decides which already-ranked candidates to keep, never to reorder.

    ``filter_candidates`` returns the subset of ``candidates`` to conserve —
    ordering stays exclusively §6.2's (``sirius.domain.relevance``)
    responsibility, never this port's. Implementations must never propagate
    an exception: any internal failure (model not installed, connection
    refused, timed out, a response outside the expected shape) is reported
    by returning ``candidates`` unchanged — fail open, exactly like
    ``CategoryClassifierPort`` reports "I could not decide" as ``None``
    rather than raising. Callers (``ContextBuilder``) rely on this to trust
    the contract without a ``try``/``except`` of their own.
    """

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        """Return the subset of ``candidates`` to keep, in no particular
        order relative to the input — the caller decides how to recombine
        it. Never raises; a fresh, unmodified ``candidates`` is the
        contractual answer to every internal failure."""
        ...
