"""La charla de Sirius con un modelo de Ollama, en este ordenador (pieza C de ADR-233).

Desde la versión 0.2 del robot la charla va a un modelo local (decisión 4 del
propietario, EV-023). Este adaptador habla con el Ollama de esta máquina por
``/api/chat`` y traduce lo que devuelve a los eventos del puerto
``LLMProvider``. Solo este módulo sabe cómo responde Ollama.

Lo que garantiza por construcción:

- **Solo va a este ordenador.** La dirección es ``http://localhost:11434``,
  absoluta en cada petición, y ningún parámetro ni ajuste la cambia. El
  cliente no lee los proxies del sistema (``trust_env=False``): un proxy
  configurado en Windows podría sacar de la máquina hasta lo que va a
  ``localhost``. Las pruebas enchufan un transporte de mentira, nunca otra
  dirección.
- **Un contexto que quepa.** Lo que no cabe en el contexto del modelo se
  recorta, y el que trae Ollama por defecto puede ser más corto que la
  semilla, sus ejemplos y la charla juntos. Se pide uno explícito,
  ``num_ctx``, de 8.192 tokens salvo que los ajustes digan otro.
- **Ni el razonamiento interno ni la sugerencia de recuerdo llegan al
  propietario.** Los modelos que «piensan» escriben ``<think>…</think>`` antes
  de contestar, y ``render_instructions()`` pide la sugerencia detrás de un
  delimitador. Las dos cosas se quitan antes de que exista un solo
  ``LLMTextDelta``, aunque lleguen partidas entre trozos.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterable, Iterator
from typing import Any

import httpx

from sirius.adapters.llm.memory_suggestion import (
    MemorySuggestionSplitter,
    longest_prefix_as_suffix,
)
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

__all__ = [
    "DEFAULT_NUM_CTX",
    "OLLAMA_CHAT_URL",
    "OLLAMA_TAGS_URL",
    "OllamaChatProvider",
    "OllamaNotAvailableError",
    "list_installed_models",
]

_logger = get_logger(__name__)

#: La única dirección a la que puede ir la charla.
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

#: Dónde dice Ollama qué modelos tiene instalados.
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

#: Contexto que se pide al modelo si los ajustes no dicen otro.
DEFAULT_NUM_CTX = 8192

#: Cuánto tiempo deja Ollama el modelo cargado después de cada respuesta. Con
#: el valor por defecto, cinco minutos, la primera frase tras una pausa
#: esperaría a que el modelo se cargara otra vez.
_KEEP_ALIVE = "30m"

#: Cargar un modelo de varios gigas puede llevar más de un minuto en un disco
#: lento, y Ollama no envía nada hasta tener la primera palabra.
_TIMEOUT = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)

_SAFE_MESSAGES: dict[LLMErrorKind, str] = {
    LLMErrorKind.CONNECTION: "No se pudo contactar con Ollama en este ordenador. ¿Está abierto?",
    LLMErrorKind.TIMEOUT: "El modelo local tardó demasiado en responder.",
    LLMErrorKind.CONFIGURATION: "El modelo de la charla no está instalado en Ollama.",
    LLMErrorKind.INVALID_RESPONSE: "Ollama no devolvió una respuesta válida.",
    LLMErrorKind.UNKNOWN: "No se pudo completar la petición a Ollama.",
    # Un modelo local no tiene clave, permisos, límite de peticiones ni
    # presupuesto: estos tipos no salen de este conector, pero si alguno llegara
    # a usarse, el mensaje sigue siendo cierto.
    LLMErrorKind.AUTHENTICATION: "No se pudo completar la petición a Ollama.",
    LLMErrorKind.PERMISSION: "No se pudo completar la petición a Ollama.",
    LLMErrorKind.RATE_LIMITED: "No se pudo completar la petición a Ollama.",
    LLMErrorKind.BUDGET_EXCEEDED: "No se pudo completar la petición a Ollama.",
}


def _error(kind: LLMErrorKind, partial_text: str = "") -> LLMError:
    return LLMError(kind=kind, message=_SAFE_MESSAGES[kind], partial_text=partial_text)


class _ThinkFilter:
    """Quita los bloques ``<think>…</think>`` de un flujo de texto partido en trozos.

    Como el separador de la sugerencia de recuerdo, retiene como mucho el
    principio de una etiqueta que todavía podría completarse con el trozo
    siguiente, así que una etiqueta partida entre dos trozos también se ve.
    """

    _ABRE = "<think>"
    _CIERRA = "</think>"

    def __init__(self) -> None:
        self._pendiente = ""
        self._dentro = False

    def feed(self, trozo: str) -> str:
        self._pendiente += trozo
        salida: list[str] = []
        while True:
            etiqueta = self._CIERRA if self._dentro else self._ABRE
            indice = self._pendiente.find(etiqueta)
            if indice == -1:
                retenido = longest_prefix_as_suffix(self._pendiente, etiqueta)
                visible = self._pendiente[: len(self._pendiente) - retenido]
                if not self._dentro:
                    salida.append(visible)
                self._pendiente = self._pendiente[len(visible) :]
                return "".join(salida)
            if not self._dentro:
                salida.append(self._pendiente[:indice])
            self._pendiente = self._pendiente[indice + len(etiqueta) :]
            self._dentro = not self._dentro

    def finish(self) -> str:
        """Lo que quedaba retenido: texto normal si no estaba dentro de un bloque."""
        resto, self._pendiente = self._pendiente, ""
        return "" if self._dentro else resto


class OllamaChatProvider:
    """``LLMProvider`` que conversa con un modelo del Ollama de este ordenador."""

    def __init__(
        self,
        model: str,
        *,
        num_ctx: int = DEFAULT_NUM_CTX,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        self._num_ctx = num_ctx
        self._client = httpx.Client(timeout=_TIMEOUT, transport=transport, trust_env=False)
        self._cancelled_operations: set[str] = set()
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        """El modelo que contesta: queda apuntado con cada respuesta marcada (pieza D)."""
        return self._model

    def health_check(self) -> bool:
        """Solo mira la configuración; nunca sale a la red."""
        return bool(self._model)

    def cancel(self, operation_id: str) -> None:
        """Pide cortar la respuesta en curso. Se puede llamar más de una vez."""
        with self._lock:
            self._cancelled_operations.add(operation_id)

    def close(self) -> None:
        self._client.close()

    def _is_cancelled(self, operation_id: str) -> bool:
        with self._lock:
            return operation_id in self._cancelled_operations

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.input_text},
            ],
            "stream": True,
            "keep_alive": _KEEP_ALIVE,
            "options": {"num_ctx": self._num_ctx},
        }

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        try:
            if self._is_cancelled(request.operation_id):
                yield LLMCancelled(partial_text="")
                return
            try:
                with self._client.stream("POST", OLLAMA_CHAT_URL, json=self._body(request)) as r:
                    if r.status_code == httpx.codes.NOT_FOUND:
                        _logger.error("Ollama no tiene el modelo de la charla (%s)", self._model)
                        yield _error(LLMErrorKind.CONFIGURATION)
                        return
                    if r.status_code >= httpx.codes.BAD_REQUEST:
                        _logger.error("Ollama respondió %s a la charla", r.status_code)
                        yield _error(LLMErrorKind.UNKNOWN)
                        return
                    yield from self._consume(request, r.iter_lines())
            except httpx.ConnectError:
                _logger.error("Operación %s: Ollama no contesta", request.operation_id)
                yield _error(LLMErrorKind.CONNECTION)
            except httpx.TimeoutException:
                _logger.error("Operación %s: Ollama tardó demasiado", request.operation_id)
                yield _error(LLMErrorKind.TIMEOUT)
            except httpx.HTTPError:
                _logger.error("Operación %s: fallo de red con Ollama", request.operation_id)
                yield _error(LLMErrorKind.UNKNOWN)
        finally:
            with self._lock:
                self._cancelled_operations.discard(request.operation_id)

    def _consume(self, request: LLMRequest, lines: Iterator[str]) -> Iterable[LLMStreamEvent]:
        accumulated: list[str] = []
        think = _ThinkFilter()
        splitter = MemorySuggestionSplitter()
        started = False

        def visible(texto: str) -> str:
            nonlocal started
            if not started:
                texto = texto.lstrip()
                started = bool(texto)
            return texto

        def partial() -> str:
            trailing, _ = splitter.finish(completed=False)
            return "".join(accumulated) + (visible(trailing) if trailing else "")

        try:
            for line in lines:
                if self._is_cancelled(request.operation_id):
                    yield LLMCancelled(partial_text=partial())
                    return
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    yield _error(LLMErrorKind.INVALID_RESPONSE, partial())
                    return
                if not isinstance(chunk, dict):
                    yield _error(LLMErrorKind.INVALID_RESPONSE, partial())
                    return
                if "error" in chunk:
                    _logger.error("Operación %s: Ollama devolvió un error", request.operation_id)
                    yield _error(LLMErrorKind.UNKNOWN, partial())
                    return
                message = chunk.get("message")
                content = message.get("content", "") if isinstance(message, dict) else ""
                if isinstance(content, str) and content:
                    safe = visible(splitter.feed(think.feed(content)))
                    if safe:
                        accumulated.append(safe)
                        yield LLMTextDelta(text=safe)
                if chunk.get("done") is True:
                    tail = splitter.feed(think.finish())
                    trailing, memory_suggestion = splitter.finish(completed=True)
                    rest = visible(tail + trailing)
                    if rest:
                        accumulated.append(rest)
                        yield LLMTextDelta(text=rest)
                    text = "".join(accumulated)
                    if not text.strip():
                        yield _error(LLMErrorKind.INVALID_RESPONSE)
                        return
                    yield LLMCompleted(
                        text=text,
                        input_tokens=_count(chunk.get("prompt_eval_count")),
                        output_tokens=_count(chunk.get("eval_count")),
                        memory_suggestion=memory_suggestion,
                    )
                    return
        except httpx.TimeoutException:
            yield _error(LLMErrorKind.TIMEOUT, partial())
            return
        except httpx.HTTPError:
            yield _error(LLMErrorKind.CONNECTION, partial())
            return
        yield _error(LLMErrorKind.INVALID_RESPONSE, partial())


def _count(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


class OllamaNotAvailableError(RuntimeError):
    """Ollama no contesta en este ordenador, o contesta algo que no se entiende."""


def list_installed_models(transport: httpx.BaseTransport | None = None) -> tuple[str, ...]:
    """Los modelos que tiene instalados el Ollama de este ordenador, en orden alfabético.

    Va a la misma dirección fija que la charla y tampoco lee los proxies del
    sistema. La prueba a ciegas los ofrece para que el propietario elija entre
    dos y tres.
    """
    try:
        with httpx.Client(timeout=_TIMEOUT, transport=transport, trust_env=False) as client:
            response = client.get(OLLAMA_TAGS_URL)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        msg = "No se pudo preguntar a Ollama qué modelos tiene. ¿Está abierto?"
        raise OllamaNotAvailableError(msg) from exc
    models = body.get("models") if isinstance(body, dict) else None
    if not isinstance(models, list):
        msg = "Ollama no dijo qué modelos tiene."
        raise OllamaNotAvailableError(msg)
    names = {
        model["name"].strip()
        for model in models
        if isinstance(model, dict) and isinstance(model.get("name"), str) and model["name"].strip()
    }
    return tuple(sorted(names))
