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
from sirius.adapters.llm.memory_suggestion import MemorySuggestionSplitter, split_delimiter
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

    @property
    def model_name(self) -> str:
        """El modelo que contesta: queda apuntado con cada respuesta (pieza D de ADR-233)."""
        return self._model

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

            # H-30 (auditoría #396): la admisión es una RESERVA atómica, no un
            # comprobar-y-gastar en dos pasos. El estimado es una cota honesta:
            # la entrada por longitud (~4 caracteres/token, la aproximación de
            # tarifado habitual) y la salida por el max_output_tokens ya
            # configurado. El coste real lo apunta record_usage al completar,
            # DENTRO del with; la salida suelta la reserva pase lo que pase.
            entrada_estimada = (len(request.instructions) + len(request.input_text)) // 4
            estimado_usd = self._budget_tracker.costo_texto_usd(
                entrada_estimada, self._max_output_tokens
            )
            with self._budget_tracker.reserva(estimado_usd) as admitida:
                if admitida is None:
                    _logger.warning(
                        "Operación %s bloqueada: presupuesto mensual agotado",
                        request.operation_id,
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
        # §3.2: every raw chunk passes through this splitter before it can
        # ever become an ``LLMTextDelta`` or reach a terminal event's text —
        # the delimiter and the raw proposal after it never leak into either,
        # even split across chunk boundaries or cut short by a cancellation
        # or failure mid-delimiter.
        splitter = MemorySuggestionSplitter()
        try:
            for event in stream:
                if self._is_cancelled(request.operation_id):
                    trailing, _ = splitter.finish(completed=False)
                    if trailing:
                        accumulated.append(trailing)
                    yield LLMCancelled(partial_text="".join(accumulated))
                    return

                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta_text = getattr(event, "delta", "")
                    safe_text = splitter.feed(delta_text)
                    if safe_text:
                        accumulated.append(safe_text)
                        yield LLMTextDelta(text=safe_text)
                elif event_type == "response.completed":
                    trailing, memory_suggestion = splitter.finish(completed=True)
                    if trailing:
                        accumulated.append(trailing)
                        yield LLMTextDelta(text=trailing)
                    completed = self._handle_completed(event, accumulated, memory_suggestion)
                    yield completed
                    return
                elif event_type in ("response.failed", "response.incomplete"):
                    trailing, _ = splitter.finish(completed=False)
                    if trailing:
                        accumulated.append(trailing)
                    _logger.error(
                        "Operación %s: respuesta inválida del proveedor", request.operation_id
                    )
                    yield _build_error(LLMErrorKind.INVALID_RESPONSE, "".join(accumulated))
                    return
                elif event_type == "error":
                    trailing, _ = splitter.finish(completed=False)
                    if trailing:
                        accumulated.append(trailing)
                    _logger.error(
                        "Operación %s: error no clasificado del proveedor", request.operation_id
                    )
                    yield _build_error(LLMErrorKind.UNKNOWN, "".join(accumulated))
                    return
        except Exception as exc:  # translated to a safe, typed event; never re-raised
            trailing, _ = splitter.finish(completed=False)
            if trailing:
                accumulated.append(trailing)
            kind = _classify_exception(exc)
            _logger.error(
                "Operación %s falló durante el streaming (%s)", request.operation_id, kind.value
            )
            yield _build_error(kind, "".join(accumulated))
            return

        # The stream ended without ever reaching a terminal event.
        trailing, _ = splitter.finish(completed=False)
        if trailing:
            accumulated.append(trailing)
        yield _build_error(LLMErrorKind.INVALID_RESPONSE, "".join(accumulated))

    def _handle_completed(
        self, event: object, accumulated: list[str], memory_suggestion: str | None
    ) -> LLMCompleted | LLMError:
        response = event.response  # type: ignore[attr-defined]
        usage = response.usage
        input_tokens = usage.input_tokens if usage is not None else 0
        output_tokens = usage.output_tokens if usage is not None else 0
        if usage is not None:
            self._budget_tracker.record_usage(input_tokens, output_tokens)

        full_text = "".join(accumulated)
        if not full_text:
            # No incremental delta ever arrived (defensive fallback only): the
            # full raw output still goes through the same delimiter contract,
            # so it can never leak here either (§3.2).
            full_text, memory_suggestion = split_delimiter(response.output_text or "")
        if not full_text:
            return _build_error(LLMErrorKind.INVALID_RESPONSE)
        return LLMCompleted(
            text=full_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            memory_suggestion=memory_suggestion,
        )
