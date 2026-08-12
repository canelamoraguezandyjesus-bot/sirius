"""Cliente WebSocket mínimo sobre la biblioteca estándar.

Existe para hablar con el sistema de captura local sin añadir ninguna
dependencia, que es lo que #127 exige. Se escribió a mano en vez de usar
``QWebSocket`` por una razón práctica: este cliente es **síncrono y bloqueante**,
así que funciona desde cualquier hilo del ``QThreadPool`` sin necesitar un bucle
de eventos propio, y se puede probar de verdad contra un servidor de mentira.

Alcance deliberadamente estrecho. Solo implementa lo que hace falta para hablar
con un programa local:

- solo cliente, solo ``ws://`` sin cifrar y solo contra la máquina local;
- solo mensajes de texto, con tope de tamaño;
- responde a ``ping`` y entiende el cierre; ignora todo lo demás.

No es un cliente WebSocket de propósito general y no debe usarse como tal.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import socket
import struct
from typing import Any

_HANDSHAKE_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
"""Constante del protocolo: el servidor la usa para demostrar que entendió."""

_OPCODE_TEXT = 0x1
_OPCODE_BINARY = 0x2
_OPCODE_CLOSE = 0x8
_OPCODE_PING = 0x9
_OPCODE_PONG = 0xA

MAXIMUM_MESSAGE_BYTES = 4 * 1024 * 1024
"""Tope de un mensaje entrante. Un programa local no manda nada mayor, y sin
tope un servidor que se comportara mal podría agotar la memoria."""

_HANDSHAKE_RESPONSE_LIMIT = 16 * 1024


class WebSocketError(RuntimeError):
    """Fallo de transporte o de protocolo. El mensaje nunca lleva secretos."""


class TimeoutWebSocketError(WebSocketError):
    """El servidor no contestó dentro del plazo."""


class WebSocketClient:
    """Conexión de texto contra un servidor WebSocket local."""

    def __init__(self, host: str, port: int, timeout_seconds: float = 5.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout_seconds
        self._socket: socket.socket | None = None
        self._buffer = bytearray()

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    # --- Conexión --------------------------------------------------------

    def connect(self) -> None:
        """Abre la conexión y completa el saludo. Idempotente."""
        if self._socket is not None:
            return
        try:
            connection = socket.create_connection((self._host, self._port), timeout=self._timeout)
        except TimeoutError as exc:
            raise TimeoutWebSocketError("el servidor no respondió a tiempo") from exc
        except OSError as exc:
            raise WebSocketError("no se pudo abrir la conexión") from exc

        connection.settimeout(self._timeout)
        self._socket = connection
        self._buffer = bytearray()
        try:
            self._handshake()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Cierra la conexión. Idempotente y nunca lanza."""
        connection, self._socket = self._socket, None
        self._buffer = bytearray()
        if connection is None:
            return
        # Si el otro lado ya se fue, da igual: cerrar es lo único que importa.
        with contextlib.suppress(OSError):
            connection.sendall(self._build_frame(_OPCODE_CLOSE, b""))
        with contextlib.suppress(OSError):
            connection.close()

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        ).encode("ascii")
        self._send_all(request)

        header = self._read_until(b"\r\n\r\n", _HANDSHAKE_RESPONSE_LIMIT)
        text = header.decode("latin-1")
        status_line = text.split("\r\n", 1)[0]
        if "101" not in status_line:
            raise WebSocketError("el servidor rechazó la conexión")

        expected = base64.b64encode(
            hashlib.sha1((key + _HANDSHAKE_GUID).encode("ascii")).digest()
        ).decode("ascii")
        # SHA-1 aquí no protege nada: el protocolo lo fija como prueba de que el
        # servidor entendió la petición, no como medida de seguridad.
        if expected.lower() not in text.lower():
            raise WebSocketError("el servidor no completó el saludo")

    # --- Mensajes --------------------------------------------------------

    def send_json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_all(self._build_frame(_OPCODE_TEXT, data))

    def receive_json(self) -> dict[str, Any]:
        """Devuelve el siguiente mensaje de texto, ya interpretado.

        Contesta a los ``ping`` por el camino y descarta lo binario, que este
        protocolo no usa.
        """
        while True:
            opcode, payload = self._read_frame()
            if opcode == _OPCODE_TEXT:
                try:
                    message = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise WebSocketError("el servidor mandó algo ilegible") from exc
                if not isinstance(message, dict):
                    raise WebSocketError("el servidor mandó algo inesperado")
                return message
            if opcode == _OPCODE_PING:
                self._send_all(self._build_frame(_OPCODE_PONG, payload))
                continue
            if opcode in (_OPCODE_PONG, _OPCODE_BINARY):
                continue
            if opcode == _OPCODE_CLOSE:
                raise WebSocketError("el servidor cerró la conexión")
            raise WebSocketError("el servidor usó una operación desconocida")

    # --- Marcos ----------------------------------------------------------

    @staticmethod
    def _build_frame(opcode: int, payload: bytes) -> bytes:
        # Un cliente SIEMPRE enmascara lo que envía: el protocolo lo exige y
        # los servidores cierran la conexión si no se hace.
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        length = len(payload)

        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        return bytes(header) + mask + masked

    def _read_frame(self) -> tuple[int, bytes]:
        first, second = self._read_exactly(2)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F

        if length == 126:
            (length,) = struct.unpack("!H", self._read_exactly(2))
        elif length == 127:
            (length,) = struct.unpack("!Q", self._read_exactly(8))

        if length > MAXIMUM_MESSAGE_BYTES:
            raise WebSocketError("el servidor mandó un mensaje demasiado grande")

        mask = self._read_exactly(4) if masked else b""
        payload = self._read_exactly(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    # --- Transporte ------------------------------------------------------

    def _send_all(self, data: bytes) -> None:
        if self._socket is None:
            raise WebSocketError("no hay conexión abierta")
        try:
            self._socket.sendall(data)
        except TimeoutError as exc:
            raise TimeoutWebSocketError("el envío tardó demasiado") from exc
        except OSError as exc:
            raise WebSocketError("se perdió la conexión al enviar") from exc

    def _read_exactly(self, count: int) -> bytes:
        while len(self._buffer) < count:
            self._buffer.extend(self._read_chunk())
        chunk = bytes(self._buffer[:count])
        del self._buffer[:count]
        return chunk

    def _read_until(self, terminator: bytes, limit: int) -> bytes:
        while terminator not in self._buffer:
            if len(self._buffer) > limit:
                raise WebSocketError("la respuesta del servidor es demasiado larga")
            self._buffer.extend(self._read_chunk())
        index = self._buffer.index(terminator) + len(terminator)
        chunk = bytes(self._buffer[:index])
        del self._buffer[:index]
        return chunk

    def _read_chunk(self) -> bytes:
        if self._socket is None:
            raise WebSocketError("no hay conexión abierta")
        try:
            chunk = self._socket.recv(4096)
        except TimeoutError as exc:
            raise TimeoutWebSocketError("el servidor no respondió a tiempo") from exc
        except OSError as exc:
            raise WebSocketError("se perdió la conexión al leer") from exc
        if not chunk:
            raise WebSocketError("el servidor cerró la conexión")
        return chunk
