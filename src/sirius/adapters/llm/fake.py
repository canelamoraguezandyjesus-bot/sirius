"""Deterministic provider for tests and offline development."""

from __future__ import annotations

import threading
from collections.abc import Iterable

from sirius.ports.llm import LLMCancelled, LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta

_DEFAULT_CHUNKS = ("Respuesta ", "simulada ", "de Sirius.")


class FakeLLMProvider:
    """Small deterministic adapter; it never accesses the network.

    Yields ``chunks`` (a fixed canned response split into pieces by default)
    one ``LLMTextDelta`` at a time, checking cooperative cancellation before
    each one — the same mechanism ``OpenAIResponsesProvider`` uses. Because a
    generator does not run any code until first iterated, calling ``cancel()``
    even before ``stream_response`` starts running is observed correctly on
    its very first check; calling it from an ``on_delta`` callback lets tests
    exercise "cancel mid-stream" deterministically, with no threads or sleeps.
    """

    def __init__(self, chunks: Iterable[str] = _DEFAULT_CHUNKS) -> None:
        self._chunks = tuple(chunks)
        self._cancelled_operations: set[str] = set()
        self._lock = threading.Lock()

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        try:
            accumulated: list[str] = []
            for chunk in self._chunks:
                if self._is_cancelled(request.operation_id):
                    yield LLMCancelled(partial_text="".join(accumulated))
                    return
                accumulated.append(chunk)
                yield LLMTextDelta(text=chunk)

            if self._is_cancelled(request.operation_id):
                yield LLMCancelled(partial_text="".join(accumulated))
                return

            full_text = "".join(accumulated)
            yield LLMCompleted(
                text=full_text,
                input_tokens=len(request.instructions) + len(request.input_text),
                output_tokens=len(full_text),
            )
        finally:
            with self._lock:
                self._cancelled_operations.discard(request.operation_id)

    def cancel(self, operation_id: str) -> None:
        with self._lock:
            self._cancelled_operations.add(operation_id)

    def _is_cancelled(self, operation_id: str) -> bool:
        with self._lock:
            return operation_id in self._cancelled_operations
