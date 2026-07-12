"""Provider-neutral LLM contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Provider-neutral input for a language model."""

    operation_id: str
    instructions: str
    input_text: str


@dataclass(frozen=True, slots=True)
class LLMChunk:
    """A normalized streaming fragment."""

    text: str


class LLMProvider(Protocol):
    """Contract implemented by real and simulated model providers."""

    def health_check(self) -> bool:
        """Return whether the provider is currently usable."""
        ...

    def stream_response(self, request: LLMRequest) -> Iterable[LLMChunk]:
        """Yield normalized response fragments."""
        ...

    def cancel(self, operation_id: str) -> None:
        """Cancel an in-flight operation when supported."""
        ...
