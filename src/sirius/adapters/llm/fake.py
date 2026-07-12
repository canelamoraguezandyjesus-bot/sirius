"""Deterministic provider for tests and offline development."""

from __future__ import annotations

from collections.abc import Iterable

from sirius.ports.llm import LLMChunk, LLMRequest


class FakeLLMProvider:
    """Small deterministic adapter; it never accesses the network."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMChunk]:
        del request
        yield LLMChunk(text="Respuesta simulada de Sirius.")

    def cancel(self, operation_id: str) -> None:
        del operation_id
