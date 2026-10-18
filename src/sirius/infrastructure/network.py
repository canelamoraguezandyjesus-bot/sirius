"""Las conexiones de red de Sirius, y colgarlas todas al cerrar (ADR-255).

Cada cliente de red de Sirius se construye aquí: ``http_client`` para los de httpx y
``openai_client`` para los del SDK de OpenAI. Así cada conexión que abren queda apuntada
en un registro único del proceso, con la extensión ``trace`` de httpx, la misma con la
que la charla cuelga la suya al cortarla (ADR-252). Al cerrar Sirius, ``hang_up_all``
las cuelga todas a la vez: cada petición en vuelo deja de esperar y falla por el camino
de fallo que ya tiene su trabajador, sea cual sea. Las ventanas no lo llaman: el punto de
composición les da el registro como ``ConnectionCloser`` (ronda 4 de Codex sobre la #698).

Lo que garantiza, y lo que no:

- **Toda petición nueva nace colgable.** Una guarda de la batería falla si un cliente de
  red se construye fuera de aquí (``tests/unit/test_toda_conexion_nace_colgable.py``).
- **Mientras una ventana se cierra, tampoco lo que conecte entonces.** Desde que pide
  cerrarse (``begin_close``) hasta que se cierra de verdad (``end_close``), toda conexión
  que se abra se cuelga en el acto, también la que estaba a medio abrir al pedirlo. Al
  cerrarse de verdad se vuelve a poder abrir: tras cambiar de proyecto se abre otra
  ventana con las mismas dependencias. Es de todo el proceso: si se abriera otra ventana
  con red mientras la primera espera para cerrarse, lo de la nueva también se colgaría.
- **No cuelga lo que aún no ha acabado de abrirse.** Mientras una conexión resuelve el DNS
  o conecta, el transporte aún no la ha devuelto y no hay nada que colgar: se cuelga en
  cuanto se abre. Si el servidor no contesta nunca al conectar, se espera a su tope de
  conexión, 10 s en la validación de la clave y 5 s en los demás clientes de OpenAI; si no
  contesta el DNS, lo que tarde el sistema. Las de Ollama van a 127.0.0.1, y abren o fallan
  en el acto.
- **Al salir, tampoco lo que conecte después.** Con ``final=True`` se cuelga además, en
  el acto, toda conexión que se abra desde entonces, para siempre: solo es para salir del
  proceso.
- **No para al servidor.** Ollama deja de escribir al ver la conexión colgada
  (ADR-252); OpenAI cobra la petición igual.
- **No corta lo que no es red.** Cargar o sintetizar una voz local, o transcribir,
  siguen hasta acabar.
- Colgar en Windows no se ha comprobado (ADR-252): visto en Linux.
"""

from __future__ import annotations

import contextlib
import socket
import threading
import weakref
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import httpx

from sirius.infrastructure.logging import get_logger

if TYPE_CHECKING:
    import openai

__all__ = [
    "ConnectionRegistry",
    "connection_registry",
    "hang_up_all",
    "http_client",
    "openai_client",
]

_logger = get_logger(__name__)

#: Los eventos de httpcore que traen el socket recién abierto: la conexión TCP, y la TLS
#: que la envuelve, que es la que queda viva. Con proxy cambia el prefijo del nombre.
_SOCKET_EVENTS = (".connect_tcp.complete", ".start_tls.complete")

Trace = Callable[[str, dict[str, Any]], None]


class ConnectionRegistry:
    """Las conexiones abiertas por los clientes de Sirius, para colgarlas todas a la vez.

    Las apunta al abrirse, por la extensión ``trace`` de httpx, y las suelta solas al
    desaparecer la conexión: el registro guarda referencias débiles. Es también el
    ``ConnectionCloser`` de las ventanas.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sockets: weakref.WeakSet[socket.socket] = weakref.WeakSet()
        self._final = False
        #: Cuántas ventanas se están cerrando: mientras haya alguna, lo que se abre se
        #: cuelga en el acto.
        self._closing = 0

    def trace(self, event: str, info: dict[str, Any]) -> None:
        """La extensión ``trace`` de httpx: apunta el socket de cada conexión que se abre, y
        si una ventana se está cerrando o ya se salió de Sirius, lo cuelga en el acto."""
        if not event.endswith(_SOCKET_EVENTS):
            return
        stream = info.get("return_value")
        get_extra_info = getattr(stream, "get_extra_info", None)
        connection = get_extra_info("socket") if callable(get_extra_info) else None
        if not isinstance(connection, socket.socket):
            return
        with self._lock:
            self._sockets.add(connection)
            hang_up = self._final or self._closing > 0
        if hang_up:
            _hang_up(connection)

    def hang_up_all(self, *, final: bool = False) -> int:
        """Cuelga todas las conexiones abiertas, y devuelve cuántas.

        Con ``final``, además, toda conexión que se abra desde ahora se cuelga en el acto:
        es para salir del proceso, no para cerrar una ventana.
        """
        with self._lock:
            if final:
                self._final = True
            pending = self._open_connections()
        return _hang_up_each(pending)

    def begin_close(self) -> None:
        """Una ventana pide cerrarse: cuelga lo abierto y, hasta ``end_close``, lo que se
        abra, como lo que estaba a medio abrir, que aún no estaba apuntado."""
        with self._lock:
            self._closing += 1
            pending = self._open_connections()
        _hang_up_each(pending)

    def end_close(self) -> None:
        """La ventana se cerró de verdad: si no queda otra cerrándose, lo que se abra ya no
        se cuelga. Uno de más no deja sin colgar el cierre siguiente."""
        with self._lock:
            self._closing = max(0, self._closing - 1)

    def _open_connections(self) -> list[socket.socket]:
        return [connection for connection in self._sockets if connection.fileno() != -1]

    def note_requests(self, request: httpx.Request) -> None:
        """El gancho de petición de los clientes de la fábrica: añade ``trace`` a cada
        petición sin pisar el que ya traiga, como el de la charla (ADR-252)."""
        previous = request.extensions.get("trace")
        if getattr(previous, "_noted_by", None) is self:
            return

        def both(event: str, info: dict[str, Any]) -> None:
            if previous is not None:
                previous(event, info)
            self.trace(event, info)

        request.extensions["trace"] = _marked(both, self)


#: El registro del proceso: el que usan la fábrica y el cierre de Sirius.
_REGISTRY = ConnectionRegistry()


def http_client(
    *,
    registry: ConnectionRegistry | None = None,
    client_class: type[httpx.Client] | None = None,
    **kwargs: Any,
) -> httpx.Client:
    """Un cliente de httpx cuyas conexiones quedan apuntadas para colgarlas al cerrar.

    Recibe lo mismo que ``httpx.Client``; ``registry`` es para las pruebas.
    """
    noted_by = registry or _REGISTRY
    hooks = dict(kwargs.pop("event_hooks", None) or {})
    hooks["request"] = [noted_by.note_requests, *hooks.get("request", [])]
    return (client_class or httpx.Client)(event_hooks=hooks, **kwargs)


def openai_client(*, registry: ConnectionRegistry | None = None, **kwargs: Any) -> openai.OpenAI:
    """Un cliente del SDK de OpenAI con los ajustes de siempre del SDK y sus conexiones
    apuntadas para colgarlas al cerrar. Recibe lo mismo que ``openai.OpenAI``."""
    import openai

    transport = http_client(registry=registry, client_class=openai.DefaultHttpxClient)
    return openai.OpenAI(http_client=transport, **kwargs)


def hang_up_all(*, final: bool = False) -> int:
    """Cuelga todas las conexiones de Sirius en vuelo; lo llama la salida (ADR-255)."""
    return _REGISTRY.hang_up_all(final=final)


def connection_registry() -> ConnectionRegistry:
    """El registro del proceso, para que el punto de composición se lo dé a las ventanas
    como ``ConnectionCloser``: ellas no importan nada de aquí (ronda 4 de Codex sobre la
    #698)."""
    return _REGISTRY


def _marked(trace: Trace, registry: ConnectionRegistry) -> Trace:
    """``trace`` con la marca de su registro, para no encadenarlo dos veces si httpx
    vuelve a pasar la petición por el gancho, como al seguir una redirección."""
    trace._noted_by = registry  # type: ignore[attr-defined]
    return trace


def _hang_up_each(connections: list[socket.socket]) -> int:
    for connection in connections:
        _hang_up(connection)
    _logger.info("Al cerrar se cuelgan %d conexiones", len(connections))
    return len(connections)


def _hang_up(connection: socket.socket) -> None:
    """Cuelga una conexión desde otro hilo, para que el que lee de ella deje de esperar. Si
    ya estaba cerrada, no pasa nada."""
    with contextlib.suppress(OSError):
        connection.shutdown(socket.SHUT_RDWR)
