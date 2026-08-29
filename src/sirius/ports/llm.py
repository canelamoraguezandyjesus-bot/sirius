"""Provider-neutral LLM contract.

``stream_response`` never raises for external/provider failures: it always
yields zero or more ``LLMTextDelta`` events followed by exactly one terminal
event — ``LLMCompleted``, ``LLMCancelled``, or ``LLMError``. This lets
application code handle every outcome uniformly, without exposing any SDK
type or exception from a concrete adapter.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

# SIRIUS-ARQ-0.2 §3.2/§3.6 (M6): the literal token ``render_instructions()``
# asks the provider to append, in the same response, when it has a memory
# worth proposing. Shared between the application layer (which asks for it in
# the instructions) and every concrete ``LLMProvider`` adapter (which must
# strip it — and anything after it — from the raw output before a single
# ``LLMTextDelta`` or terminal event exists, per the same section). Never
# reaches ``LLMTextDelta.text``, ``LLMCompleted.text``,
# ``LLMCancelled.partial_text`` or ``LLMError.partial_text``.
MEMORY_SUGGESTION_DELIMITER = "<<<SIRIUS_MEMORY_SUGGESTION>>>"


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Provider-neutral input for a language model."""

    operation_id: str
    instructions: str
    input_text: str


@dataclass(frozen=True, slots=True)
class LLMTextDelta:
    """A normalized streaming text fragment."""

    text: str


@dataclass(frozen=True, slots=True)
class LLMCompleted:
    """The stream finished successfully with a full, valid response.

    ``memory_suggestion`` (§3.2/§3.6, M6) is the automatic-path proposal the
    concrete adapter already separated from ``text`` using
    ``MEMORY_SUGGESTION_DELIMITER``, or ``None`` when the provider proposed
    nothing this turn. ``text`` never contains the delimiter or the raw
    proposal, regardless of ``memory_suggestion``.
    """

    text: str
    input_tokens: int
    output_tokens: int
    memory_suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class LLMCancelled:
    """The operation was cancelled cooperatively.

    ``partial_text`` may be persisted (SIRIUS-ARQ-0.1 S5.1: "se conserva el
    contenido parcial con estado CANCELADO"), but callers must never treat it
    as a completed response or feed it back into a future context.
    """

    partial_text: str


class LLMErrorKind(StrEnum):
    """Safe, provider-neutral classification of an LLM operation failure."""

    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMITED = "rate_limited"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    BUDGET_EXCEEDED = "budget_exceeded"
    # Provider selected but not usable yet (missing/invalid key or settings).
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LLMError:
    """A terminal error event. ``message`` is short, safe, and never includes
    secrets, headers, or the request/response body.

    ``partial_text`` carries whatever text streamed before the failure (SIRIUS-
    ARQ-0.1 S5.1: "se conserva el contenido parcial con estado... FALLIDO");
    it may be persisted as a FAILED message but never as a completed one.
    """

    kind: LLMErrorKind
    message: str
    partial_text: str = ""


LLMStreamEvent = LLMTextDelta | LLMCompleted | LLMCancelled | LLMError


class LLMProvider(Protocol):
    """Contract implemented by real and simulated model providers."""

    def health_check(self) -> bool:
        """Return whether the provider is currently usable."""
        ...

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        """Yield normalized response fragments, ending in exactly one terminal event."""
        ...

    def cancel(self, operation_id: str) -> None:
        """Request cooperative cancellation of an in-flight operation. Idempotent."""
        ...
