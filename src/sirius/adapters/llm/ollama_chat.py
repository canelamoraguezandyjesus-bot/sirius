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
- **Una respuesta que acaba.** Sin tope, Ollama puede escribir sin fin, y como
  no deja de llegar texto, el tope de lectura no salta nunca. Se pide uno,
  ``num_predict``, el «Máximo de tokens de salida» de los ajustes, 4.096 si no
  dicen otro (ADR-248). Una respuesta cortada por él acaba como cualquier otra.
- **Cortar es al momento.** Mientras Ollama lee la pregunta no envía nada, y
  un corte que esperara al siguiente trozo esperaría a que acabara de leerla.
  ``cancel`` cuelga la conexión de esa petición, y Ollama deja de trabajar en
  ella en cuanto ve que se ha ido: un turno de voz no espera a la nota del juez
  (ADR-252). Por eso cada petición abre su conexión y la cierra al acabar.
- **El juez no piensa antes de contestar.** Una petición que no deja pensar
  (``may_think``) apaga ``think``. Si Ollama la rechazara por eso, se repite
  una vez sin apagarlo, y ese modelo ya no lo apaga más (ADR-252).
- **Ni el razonamiento interno ni la sugerencia de recuerdo llegan al
  propietario.** Los modelos que «piensan» escriben ``<think>…</think>`` antes
  de contestar, y ``render_instructions()`` pide la sugerencia detrás de un
  delimitador. Las dos cosas se quitan antes de que exista un solo
  ``LLMTextDelta``, aunque lleguen partidas entre trozos.
- **El diario no lleva nada de lo que dijo Ollama.** Al fallar apunta el código
  HTTP, la clase del fallo de red o una categoría de una lista cerrada, nunca
  su texto: lo que repite de la charla puede venir en cualquier forma, y
  tacharlo no era un límite seguro (ronda 2 de Codex de ADR-248).
"""

from __future__ import annotations

import contextlib
import json
import socket
import threading
from collections.abc import Callable, Iterable, Iterator
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
    "DEFAULT_NUM_PREDICT",
    "OLLAMA_CHAT_URL",
    "OLLAMA_SHOW_URL",
    "OLLAMA_TAGS_URL",
    "OllamaChatProvider",
    "OllamaNotAvailableError",
    "list_installed_models",
    "model_capabilities",
]

_logger = get_logger(__name__)

#: La única dirección a la que puede ir la charla.
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

#: Dónde dice Ollama qué modelos tiene instalados.
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

#: Dónde dice Ollama qué sabe hacer un modelo (ADR-247).
OLLAMA_SHOW_URL = "http://localhost:11434/api/show"

#: Contexto que se pide al modelo si los ajustes no dicen otro.
DEFAULT_NUM_CTX = 8192

#: Cuánto puede escribir como mucho si no le dicen otro: el «Máximo de tokens de salida»
#: de serie de los ajustes (ADR-248).
DEFAULT_NUM_PREDICT = 4096

#: Lo único que el diario dice de lo que contestó Ollama al fallar: la categoría de la
#: primera de estas firmas que aparezca en su texto, sin distinguir mayúsculas. Cada firma
#: son trozos que tienen que salir todos. Del texto no se copia nada (ronda 2 de Codex de
#: ADR-248). La memoria va antes que el proceso caído: dice por qué se cayó.
_ERROR_CATEGORIES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("memory",), "sin memoria"),
    (("cuda",), "sin memoria"),
    (("does not support thinking",), "no admite think"),
    (("not found",), "modelo no encontrado"),
    (("context canceled",), "cancelado"),
    (("runner process", "terminated"), "el proceso del modelo se cayó"),
    (("no longer running",), "el proceso del modelo se cayó"),
)

#: La categoría de un error que no encaja en ninguna firma.
_OTHER_ERROR = "otro"

#: Cuánto tiempo deja Ollama el modelo cargado después de cada respuesta. Con
#: el valor por defecto, cinco minutos, la primera frase tras una pausa
#: esperaría a que el modelo se cargara otra vez.
_KEEP_ALIVE = "30m"

#: Cargar un modelo de varios gigas puede llevar más de un minuto en un disco
#: lento, y Ollama no envía nada hasta tener la primera palabra.
_TIMEOUT = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)

#: Decir qué sabe hacer un modelo no lo carga: si en diez segundos Ollama no lo dice, ese
#: modelo se queda fuera de la prueba a ciegas, y la ventana no espera más.
_SHOW_TIMEOUT = httpx.Timeout(10.0)

#: Cada petición abre su conexión y la cierra al acabar: así se sabe cuál colgar al
#: cortarla (ADR-252). A este ordenador, abrir una cuesta nada.
_ONE_CONNECTION_PER_REQUEST = httpx.Limits(max_keepalive_connections=0)

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


def _category(text: str) -> str:
    """La categoría con que el diario apunta un error de Ollama: de la lista, nunca su texto."""
    folded = text.casefold()
    for signature, category in _ERROR_CATEGORIES:
        if all(part in folded for part in signature):
            return category
    return _OTHER_ERROR


def _what_ollama_said(response: httpx.Response) -> str:
    """El texto del error con que contestó Ollama, o el cuerpo tal cual si no es su JSON:
    solo para sacar su categoría, nunca para el diario."""
    try:
        raw = response.read().decode("utf-8", errors="replace")
    except httpx.HTTPError:
        return ""
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, str) else raw


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

    #: Solo va a ``localhost``, una dirección que no se puede cambiar
    #: (``sirius.ports.llm.runs_on_this_computer``).
    runs_on_this_computer = True

    def __init__(
        self,
        model: str,
        *,
        num_ctx: int = DEFAULT_NUM_CTX,
        num_predict: int = DEFAULT_NUM_PREDICT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        self._num_ctx = num_ctx
        self._num_predict = num_predict
        self._client = httpx.Client(
            timeout=_TIMEOUT,
            limits=_ONE_CONNECTION_PER_REQUEST,
            transport=transport,
            trust_env=False,
        )
        self._cancelled_operations: set[str] = set()
        #: La conexión de cada petición en curso, para colgarla si se corta.
        self._connections: dict[str, socket.socket] = {}
        #: Si Ollama rechazó ya que se apagara el pensamiento de este modelo: las
        #: peticiones siguientes ya no lo apagan (ADR-252).
        self._refuses_think = False
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        """El modelo que contesta: queda apuntado con cada respuesta marcada (pieza D)."""
        return self._model

    def health_check(self) -> bool:
        """Solo mira la configuración; nunca sale a la red."""
        return bool(self._model)

    def cancel(self, operation_id: str) -> None:
        """Corta la respuesta en curso, y si ya está con Ollama, cuelga su conexión: no
        espera al siguiente trozo (ADR-252). Se puede llamar más de una vez."""
        with self._lock:
            self._cancelled_operations.add(operation_id)
            connection = self._connections.get(operation_id)
        if connection is not None:
            _hang_up(connection)

    def _note_connection(self, operation_id: str) -> Callable[[str, dict[str, Any]], None]:
        """Apunta la conexión que abre la petición ``operation_id``, para poder colgarla.

        Lo avisa httpx al conectar (su extensión ``trace``). Si la cortaron mientras
        conectaba, la cuelga ya.
        """

        def note(event: str, info: dict[str, Any]) -> None:
            if event != "connection.connect_tcp.complete":
                return
            stream = info.get("return_value")
            get_extra_info = getattr(stream, "get_extra_info", None)
            connection = get_extra_info("socket") if callable(get_extra_info) else None
            if not isinstance(connection, socket.socket):
                return
            with self._lock:
                self._connections[operation_id] = connection
                cancelled = operation_id in self._cancelled_operations
            if cancelled:
                _hang_up(connection)

        return note

    def close(self) -> None:
        self._client.close()

    def _is_cancelled(self, operation_id: str) -> bool:
        with self._lock:
            return operation_id in self._cancelled_operations

    def _body(self, request: LLMRequest) -> dict[str, Any]:
        # Una petición puede pedir menos que el tope de los ajustes, nunca más (ADR-252).
        num_predict = self._num_predict
        if request.max_output_tokens is not None:
            num_predict = min(num_predict, request.max_output_tokens)
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": request.input_text},
            ],
            "stream": True,
            "keep_alive": _KEEP_ALIVE,
            "options": {"num_ctx": self._num_ctx, "num_predict": num_predict},
        }
        if self._turns_off_thinking(request):
            # Solo se apaga, nunca se pide: la charla va como siempre, sin «think».
            body["think"] = False
        return body

    def _turns_off_thinking(self, request: LLMRequest) -> bool:
        with self._lock:
            return not request.may_think and not self._refuses_think

    def _refused_think(self, response: httpx.Response) -> bool:
        """Si Ollama rechazó la petición por apagar el pensamiento: que lo haga con un
        modelo que no piensa no se ha comprobado con ninguna versión, y si lo hace, se
        pregunta otra vez sin apagarlo, y este modelo ya no lo apaga (ADR-252).

        Lo que dice Ollama solo se mira para decidirlo: al diario no va nada de su texto.
        """
        if response.status_code != httpx.codes.BAD_REQUEST:
            return False
        said = _what_ollama_said(response)
        # Sin el nombre del modelo, que podría llevar la palabra: «qwen3:4b-thinking».
        if "think" not in said.lower().replace(self._model.lower(), ""):
            return False
        with self._lock:
            self._refuses_think = True
        _logger.info(
            "Ollama no deja apagar el pensamiento de %s: se pregunta sin apagarlo", self._model
        )
        return True

    def _post(self, request: LLMRequest) -> contextlib.AbstractContextManager[httpx.Response]:
        return self._client.stream(
            "POST",
            OLLAMA_CHAT_URL,
            json=self._body(request),
            extensions={"trace": self._note_connection(request.operation_id)},
        )

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        try:
            if self._is_cancelled(request.operation_id):
                yield LLMCancelled(partial_text="")
                return
            try:
                if self._turns_off_thinking(request):
                    with self._post(request) as r:
                        if not self._refused_think(r):
                            yield from self._answer(request, r)
                            return
                with self._post(request) as r:
                    yield from self._answer(request, r)
            except httpx.ConnectError:
                _logger.error("Operación %s: Ollama no contesta", request.operation_id)
                yield _error(LLMErrorKind.CONNECTION)
            except httpx.TimeoutException:
                _logger.error("Operación %s: Ollama tardó demasiado", request.operation_id)
                yield _error(LLMErrorKind.TIMEOUT)
            except httpx.HTTPError as exc:
                if self._is_cancelled(request.operation_id):
                    # La colgó cancel(): no es un fallo, es el corte que se pidió.
                    yield LLMCancelled(partial_text="")
                    return
                _logger.error(
                    "Operación %s: fallo de red con Ollama (%s)",
                    request.operation_id,
                    type(exc).__name__,
                )
                yield _error(LLMErrorKind.UNKNOWN)
        finally:
            with self._lock:
                self._cancelled_operations.discard(request.operation_id)
                self._connections.pop(request.operation_id, None)

    def _answer(self, request: LLMRequest, r: httpx.Response) -> Iterable[LLMStreamEvent]:
        if r.status_code == httpx.codes.NOT_FOUND:
            _logger.error(
                "Ollama no tiene el modelo de la charla (%s): %s",
                self._model,
                _category(_what_ollama_said(r)),
            )
            yield _error(LLMErrorKind.CONFIGURATION)
            return
        if r.status_code >= httpx.codes.BAD_REQUEST:
            _logger.error(
                "Ollama respondió %s a la charla: %s",
                r.status_code,
                _category(_what_ollama_said(r)),
            )
            yield _error(LLMErrorKind.UNKNOWN)
            return
        yield from self._consume(request, r.iter_lines())

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
                    _logger.error(
                        "Operación %s: Ollama devolvió un error: %s",
                        request.operation_id,
                        _category(str(chunk["error"])),
                    )
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
        except httpx.HTTPError as exc:
            if self._is_cancelled(request.operation_id):
                # La colgó cancel(): no es un fallo, es el corte que se pidió (ADR-252).
                yield LLMCancelled(partial_text=partial())
                return
            # La rama de fuera, en ``stream_response``, no llega a verlo (ronda 1 de ADR-248).
            _logger.error(
                "Operación %s: fallo de red con Ollama a mitad de respuesta (%s)",
                request.operation_id,
                type(exc).__name__,
            )
            timed_out = isinstance(exc, httpx.TimeoutException)
            yield _error(LLMErrorKind.TIMEOUT if timed_out else LLMErrorKind.CONNECTION, partial())
            return
        yield _error(LLMErrorKind.INVALID_RESPONSE, partial())


def _count(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _hang_up(connection: socket.socket) -> None:
    """Cuelga una conexión desde otro hilo: el que lee de ella deja de esperar al
    momento, y Ollama ve que se ha ido. Si ya estaba cerrada, no pasa nada."""
    with contextlib.suppress(OSError):
        connection.shutdown(socket.SHUT_RDWR)


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


def model_capabilities(model: str, transport: httpx.BaseTransport | None = None) -> tuple[str, ...]:
    """Lo que dice el Ollama de este ordenador que sabe hacer ``model``: ``completion`` si
    conversa, ``embedding`` si da huellas.

    Va a la misma dirección fija que la charla y tampoco lee los proxies del sistema. Si
    Ollama no contesta, o contesta sin decir qué sabe hacer, ``OllamaNotAvailableError``
    con el motivo: la prueba a ciegas deja ese modelo fuera y sigue con los demás
    (ADR-247).
    """
    try:
        with httpx.Client(timeout=_SHOW_TIMEOUT, transport=transport, trust_env=False) as client:
            response = client.post(OLLAMA_SHOW_URL, json={"model": model})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        msg = "Ollama no contestó al preguntarle qué sabe hacer"
        raise OllamaNotAvailableError(msg) from exc
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = None
    capabilities = body.get("capabilities") if isinstance(body, dict) else None
    if not isinstance(capabilities, list) or not all(isinstance(c, str) for c in capabilities):
        msg = "Ollama no dijo qué sabe hacer"
        raise OllamaNotAvailableError(msg)
    return tuple(capabilities)
