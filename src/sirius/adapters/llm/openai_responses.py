"""OpenAI Responses API adapter, behind the LLMProvider port.

Real streaming via ``client.responses.create(..., stream=True)``. ``store``
is always ``False`` and no ``previous_response_id`` is ever sent: the only
authoritative conversation state is Sirius's local SQLite database. No
tools, web search, file, or code-execution capabilities are enabled.

Only this module imports the ``openai`` package or knows any of its types or
exceptions; everything above the port sees ``sirius.ports.llm`` events only.
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable, Iterable
from typing import Literal

import openai

from sirius.adapters.llm.budget import BudgetTracker
from sirius.infrastructure.logging import get_logger
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)

_logger = get_logger(__name__)

_MAX_RETRIES = 2
_BASE_BACKOFF_SECONDS = 0.5
_MAX_JITTER_SECONDS = 0.25

# DR-016/DR-017: retry only transient/provider-side failures, never auth,
# permission, malformed requests, or anything the user must act on first.
_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

_SAFE_MESSAGES: dict[LLMErrorKind, str] = {
    LLMErrorKind.AUTHENTICATION: "La credencial del proveedor no es válida.",
    LLMErrorKind.PERMISSION: "La credencial no tiene permiso para esta operación.",
    LLMErrorKind.RATE_LIMITED: (
        "El proveedor está limitando las peticiones; inténtalo de nuevo en un momento."
    ),
    LLMErrorKind.CONNECTION: "No se pudo contactar con el proveedor.",
    LLMErrorKind.TIMEOUT: "El proveedor tardó demasiado en responder.",
    LLMErrorKind.INVALID_RESPONSE: "El proveedor no devolvió una respuesta válida.",
    LLMErrorKind.BUDGET_EXCEEDED: "Se alcanzó el límite mensual de uso del proveedor.",
    LLMErrorKind.CONFIGURATION: "El proveedor de IA no está configurado.",
    LLMErrorKind.UNKNOWN: "No se pudo completar la petición al proveedor.",
}


def _classify_exception(exc: Exception) -> LLMErrorKind:
    """Map an SDK exception to a safe, provider-neutral error kind.

    Never inspects ``str(exc)`` for the user-facing message: the message
    shown to the user always comes from ``_SAFE_MESSAGES``, a fixed table,
    so nothing from the exception (headers, request body, raw provider text)
    can ever reach the interface or a log.
    """
    if isinstance(exc, openai.AuthenticationError):
        return LLMErrorKind.AUTHENTICATION
    if isinstance(exc, openai.PermissionDeniedError):
        return LLMErrorKind.PERMISSION
    if isinstance(exc, openai.RateLimitError):
        return LLMErrorKind.RATE_LIMITED
    if isinstance(exc, openai.APITimeoutError):
        return LLMErrorKind.TIMEOUT
    if isinstance(exc, openai.APIConnectionError | openai.InternalServerError):
        return LLMErrorKind.CONNECTION
    return LLMErrorKind.UNKNOWN


def _build_error(kind: LLMErrorKind, partial_text: str = "") -> LLMError:
    return LLMError(kind=kind, message=_SAFE_MESSAGES[kind], partial_text=partial_text)


class OpenAIResponsesProvider:
    """LLMProvider adapter using OpenAI's Responses API with real streaming."""

    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        *,
        max_output_tokens: int = 4096,
        reasoning_effort: Literal["low", "medium"] = "low",
        budget_tracker: BudgetTracker | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort
        self._budget_tracker = budget_tracker or BudgetTracker()
        self._sleep_fn = sleep_fn
        self._cancelled_operations: set[str] = set()
        self._lock = threading.Lock()

    def health_check(self) -> bool:
        """Configuration-only check; never calls the network."""
        return bool(self._model)

    def cancel(self, operation_id: str) -> None:
        """Request cooperative cancellation. Idempotent: safe to call more than once."""
        with self._lock:
            self._cancelled_operations.add(operation_id)

    def _is_cancelled(self, operation_id: str) -> bool:
        with self._lock:
            return operation_id in self._cancelled_operations

    def _create_stream(self, request: LLMRequest) -> Iterable[object]:
        attempt = 0
        while True:
            try:
                return self._client.responses.create(
                    model=self._model,
                    instructions=request.instructions,
                    input=request.input_text,
                    stream=True,
                    store=False,
                    max_output_tokens=self._max_output_tokens,
                    reasoning={"effort": self._reasoning_effort},
                )
            except _RETRYABLE_EXCEPTIONS:
                attempt += 1
                if attempt > _MAX_RETRIES:
                    raise
                backoff = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                self._sleep_fn(backoff + random.uniform(0, _MAX_JITTER_SECONDS))

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        # A generator runs no code until first iterated, so a cancel() call
        # that arrives before this even starts is still observed correctly
        # by the first cooperative check below; cleanup happens in `finally`
        # rather than at the top, so it is never lost to that race.
        try:
            if self._is_cancelled(request.operation_id):
                # Cancelled before we ever sent anything: no request is made.
                yield LLMCancelled(partial_text="")
                return

            if not self._budget_tracker.has_remaining_budget():
                _logger.warning(
                    "Operación %s bloqueada: presupuesto mensual agotado", request.operation_id
                )
                yield _build_error(LLMErrorKind.BUDGET_EXCEEDED)
                return

            try:
                stream = self._create_stream(request)
            except Exception as exc:  # translated to a safe, typed event; never re-raised
                kind = _classify_exception(exc)
                _logger.error(
                    "Operación %s falló al conectar (%s)", request.operation_id, kind.value
                )
                yield _build_error(kind)
                return

            try:
                yield from self._consume_stream(request, stream)
            finally:
                close = getattr(stream, "close", None)
                if callable(close):
                    close()
        finally:
            with self._lock:
                self._cancelled_operations.discard(request.operation_id)

    def _consume_stream(
        self, request: LLMRequest, stream: Iterable[object]
    ) -> Iterable[LLMStreamEvent]:
        accumulated: list[str] = []
        try:
            for event in stream:
                if self._is_cancelled(request.operation_id):
                    yield LLMCancelled(partial_text="".join(accumulated))
                    return

                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta_text = getattr(event, "delta", "")
                    accumulated.append(delta_text)
                    yield LLMTextDelta(text=delta_text)
                elif event_type == "response.completed":
                    completed = self._handle_completed(event, accumulated)
                    yield completed
                    return
                elif event_type in ("response.failed", "response.incomplete"):
                    _logger.error(
                        "Operación %s: respuesta inválida del proveedor", request.operation_id
                    )
                    yield _build_error(LLMErrorKind.INVALID_RESPONSE, "".join(accumulated))
                    return
                elif event_type == "error":
                    _logger.error(
                        "Operación %s: error no clasificado del proveedor", request.operation_id
                    )
                    yield _build_error(LLMErrorKind.UNKNOWN, "".join(accumulated))
                    return
        except Exception as exc:  # translated to a safe, typed event; never re-raised
            kind = _classify_exception(exc)
            _logger.error(
                "Operación %s falló durante el streaming (%s)", request.operation_id, kind.value
            )
            yield _build_error(kind, "".join(accumulated))
            return

        # The stream ended without ever reaching a terminal event.
        yield _build_error(LLMErrorKind.INVALID_RESPONSE, "".join(accumulated))

    def _handle_completed(self, event: object, accumulated: list[str]) -> LLMCompleted | LLMError:
        response = event.response  # type: ignore[attr-defined]
        usage = response.usage
        input_tokens = usage.input_tokens if usage is not None else 0
        output_tokens = usage.output_tokens if usage is not None else 0
        if usage is not None:
            self._budget_tracker.record_usage(input_tokens, output_tokens)

        full_text = "".join(accumulated) or (response.output_text or "")
        if not full_text:
            return _build_error(LLMErrorKind.INVALID_RESPONSE)
        return LLMCompleted(text=full_text, input_tokens=input_tokens, output_tokens=output_tokens)
