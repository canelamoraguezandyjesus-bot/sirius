"""Sistema de captura real: OBS Studio por su servidor WebSocket local.

Traduce el protocolo de OBS al puerto de captura. Nada del protocolo —códigos
de operación, nombres de petición, formas del JSON— sale de este archivo, así
que sustituir OBS por otro programa es escribir otro adaptador al lado.

Autenticación: OBS manda una sal y un desafío, y espera de vuelta un resumen
SHA-256 encadenado. Se calcula con la biblioteca estándar y **la contraseña
nunca se registra ni aparece en ningún mensaje de error**.

> ## Verificado contra OBS real
>
> Se escribió a partir de la descripción del protocolo, sin OBS delante, y por
> eso llevó durante un tiempo la advertencia contraria. El 9 de agosto de 2026
> se ejecutó la verificación contra **OBS Studio 32.2.1 en Windows**: saludo,
> autenticación, lista de escenas, cambio de plano, grabación y parada, con el
> archivo resultante en disco.
>
> Lo que la verificación cambió: OBS acepta la orden y la ejecuta después, así
> que consultar el estado en la línea siguiente devuelve el anterior. Las
> órdenes que cambian el estado ahora esperan a que OBS lo confirme —y si no
> llega la confirmación, se dice lo que OBS diga, no lo que convendría—.
>
> Lo que la verificación **no** cubre: varias cámaras a la vez, sesiones
> largas, ni la reconexión después de cerrar OBS a mitad de una grabación.
"""

from __future__ import annotations

import base64
import hashlib
import time
from collections.abc import Callable
from typing import Any

from sirius.adapters.capture.websocket_client import (
    TimeoutWebSocketError,
    WebSocketClient,
    WebSocketError,
)
from sirius.domain.model_studio import StudioCaptureState
from sirius.infrastructure.logging import get_logger
from sirius.ports.capture_backend import (
    BackendScene,
    CaptureError,
    CaptureErrorKind,
    CaptureOutcome,
    CaptureStatus,
)

_logger = get_logger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455
"""Puerto por omisión del servidor local de OBS. **A verificar** (V-01)."""

_OP_HELLO = 0
_OP_IDENTIFY = 1
_OP_IDENTIFIED = 2
_OP_REQUEST = 6
_OP_REQUEST_RESPONSE = 7

_RPC_VERSION = 1
_REQUEST_ID = "sirius"

SETTLE_TIMEOUT_SECONDS = 5.0
"""Cuánto se espera a que OBS confirme un cambio que ya ha aceptado.

OBS responde «recibido» y ejecuta después: entre las dos cosas inicializa el
codificador y abre el archivo. Preguntar en ese hueco devuelve el estado
anterior, y creérselo es justo el accidente que #127 prohíbe —dar por buena una
grabación que no ha empezado, o darla por parada mientras sigue—.
"""

SETTLE_INTERVAL_SECONDS = 0.1

_MAXIMUM_HANDSHAKE_MESSAGES = 8
"""Cuántos mensajes se aceptan antes de rendirse en el saludo: evita quedarse
esperando para siempre si el servidor manda eventos y nunca se identifica."""


def _authentication_response(password: str, salt: str, challenge: str) -> str:
    """Respuesta al desafío de OBS. La contraseña no sale de aquí."""
    secret = base64.b64encode(hashlib.sha256((password + salt).encode("utf-8")).digest())
    return base64.b64encode(hashlib.sha256(secret + challenge.encode("utf-8")).digest()).decode(
        "ascii"
    )


def _grabando(record_status: dict[str, Any]) -> bool:
    return bool(record_status.get("outputActive", False))


def _pausado(record_status: dict[str, Any]) -> bool:
    return bool(record_status.get("outputPaused", False))


def _state_from(record_status: dict[str, Any]) -> StudioCaptureState:
    """Traduce lo que OBS dice a un estado de Model Studio.

    Solo ``outputActive`` puede llevar a ``GRABANDO``. Ninguna otra señal vale:
    ese es el requisito duro de #127.
    """
    if not _grabando(record_status):
        return StudioCaptureState.PREPARADO
    if _pausado(record_status):
        return StudioCaptureState.PAUSADO
    return StudioCaptureState.GRABANDO


class ObsWebSocketBackend:
    """Gobierna OBS Studio a través de su servidor WebSocket local."""

    def __init__(
        self,
        password: str = "",
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout_seconds: float = 5.0,
        settle_timeout_seconds: float = SETTLE_TIMEOUT_SECONDS,
    ) -> None:
        self._password = password
        self._client = WebSocketClient(host, port, timeout_seconds)
        self._identified = False
        self._settle_timeout = settle_timeout_seconds

    # --- Conexión --------------------------------------------------------

    def connect(self) -> CaptureError | None:
        if self._identified:
            return None
        try:
            self._client.connect()
            self._identify()
        except TimeoutWebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError as exc:
            self.disconnect()
            _logger.warning("no se pudo conectar con el sistema de captura: %s", exc)
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "no se pudo conectar")
        except _AuthenticationRejected:
            self.disconnect()
            return CaptureError(CaptureErrorKind.AUTHENTICATION, "contraseña rechazada")
        except _UnsupportedVersion:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNSUPPORTED_VERSION, "versión incompatible")
        self._identified = True
        return None

    def disconnect(self) -> None:
        self._identified = False
        self._client.close()

    def is_connected(self) -> bool:
        return self._identified and self._client.is_connected

    def _identify(self) -> None:
        hello = self._client.receive_json()
        if hello.get("op") != _OP_HELLO:
            raise WebSocketError("el servidor no saludó como se esperaba")

        data = hello.get("d", {})
        if not isinstance(data, dict):
            raise WebSocketError("el saludo del servidor no es válido")
        if int(data.get("rpcVersion", _RPC_VERSION)) < _RPC_VERSION:
            raise _UnsupportedVersion

        identify: dict[str, Any] = {"rpcVersion": _RPC_VERSION}
        authentication = data.get("authentication")
        if isinstance(authentication, dict):
            if not self._password:
                raise _AuthenticationRejected
            identify["authentication"] = _authentication_response(
                self._password,
                str(authentication.get("salt", "")),
                str(authentication.get("challenge", "")),
            )

        self._client.send_json({"op": _OP_IDENTIFY, "d": identify})
        for _ in range(_MAXIMUM_HANDSHAKE_MESSAGES):
            message = self._client.receive_json()
            if message.get("op") == _OP_IDENTIFIED:
                return
        raise _AuthenticationRejected

    # --- Peticiones ------------------------------------------------------

    def _request(self, request_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.is_connected():
            raise _NotConnected
        self._client.send_json(
            {
                "op": _OP_REQUEST,
                "d": {
                    "requestType": request_type,
                    "requestId": _REQUEST_ID,
                    "requestData": data or {},
                },
            }
        )
        for _ in range(_MAXIMUM_HANDSHAKE_MESSAGES):
            message = self._client.receive_json()
            # Entre la petición y su respuesta llegan eventos: se ignoran.
            if message.get("op") != _OP_REQUEST_RESPONSE:
                continue
            payload = message.get("d", {})
            if not isinstance(payload, dict):
                raise WebSocketError("respuesta ilegible")
            status = payload.get("requestStatus", {})
            if not (isinstance(status, dict) and status.get("result", False)):
                raise _Rejected
            response = payload.get("responseData", {})
            return response if isinstance(response, dict) else {}
        raise TimeoutWebSocketError("el servidor no contestó a la petición")

    def _guarded(self, request_type: str, data: dict[str, Any] | None = None) -> CaptureOutcome:
        """Ejecuta una petición y devuelve el estado, o un error tipado.

        Ninguna excepción del transporte sale de aquí hacia arriba: quien llama
        recibe siempre un resultado que puede enseñar.
        """
        try:
            self._request(request_type, data)
            return self._status()
        except _NotConnected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        except _Rejected:
            return CaptureError(CaptureErrorKind.REJECTED, "orden rechazada")
        except TimeoutWebSocketError:
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNKNOWN, "se perdió la conexión")

    def _settle(self, confirmado: Callable[[dict[str, Any]], bool]) -> CaptureStatus:
        """Pregunta hasta que OBS confirme el cambio, o hasta agotar la espera.

        Al agotarse **no se miente**: se devuelve el estado que OBS diga en ese
        momento, sea el que sea. Quien llama ya sabe distinguir «no ha
        empezado» de «no lo sé», y ninguna de las dos cosas se arregla
        inventando la que interesa.
        """
        limite = time.monotonic() + self._settle_timeout
        while True:
            record = self._request("GetRecordStatus")
            if confirmado(record) or time.monotonic() >= limite:
                return self._status_from(record)
            time.sleep(SETTLE_INTERVAL_SECONDS)

    def _commanded(
        self, request_type: str, confirmado: Callable[[dict[str, Any]], bool]
    ) -> CaptureOutcome:
        """Como ``_guarded``, pero esperando a que el cambio sea real."""
        try:
            self._request(request_type)
            return self._settle(confirmado)
        except _NotConnected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        except _Rejected:
            return CaptureError(CaptureErrorKind.REJECTED, "orden rechazada")
        except TimeoutWebSocketError:
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNKNOWN, "se perdió la conexión")

    def _status(self) -> CaptureStatus:
        return self._status_from(self._request("GetRecordStatus"))

    def _status_from(self, record: dict[str, Any]) -> CaptureStatus:
        scene = self._request("GetCurrentProgramScene")
        active = scene.get("currentProgramSceneName") or scene.get("sceneName")
        seconds = record.get("outputDuration")
        return CaptureStatus(
            state=_state_from(record),
            active_scene_name=str(active) if active else None,
            # OBS informa la duración en milisegundos.
            recording_seconds=float(seconds) / 1000.0 if isinstance(seconds, int | float) else None,
            output_path=str(record["outputPath"]) if record.get("outputPath") else None,
        )

    # --- Puerto ----------------------------------------------------------

    def get_status(self) -> CaptureOutcome:
        try:
            return self._status()
        except _NotConnected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        except _Rejected:
            return CaptureError(CaptureErrorKind.REJECTED, "consulta rechazada")
        except TimeoutWebSocketError:
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNKNOWN, "se perdió la conexión")

    def start_recording(self) -> CaptureOutcome:
        return self._commanded("StartRecord", _grabando)

    def pause_recording(self) -> CaptureOutcome:
        outcome = self._commanded("PauseRecord", _pausado)
        if isinstance(outcome, CaptureError) and outcome.kind is CaptureErrorKind.REJECTED:
            # OBS rechaza pausar cuando el formato de salida no lo admite. No es
            # una avería, y #127 acepta declararlo explícitamente (MS-007).
            return CaptureError(
                CaptureErrorKind.UNSUPPORTED_OPERATION,
                "el formato de grabación no admite pausa",
            )
        return outcome

    def resume_recording(self) -> CaptureOutcome:
        return self._commanded(
            "ResumeRecord", lambda record: _grabando(record) and not _pausado(record)
        )

    def stop_recording(self) -> CaptureOutcome:
        try:
            response = self._request("StopRecord")
        except _NotConnected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        except _Rejected:
            return CaptureError(CaptureErrorKind.REJECTED, "orden rechazada")
        except TimeoutWebSocketError:
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNKNOWN, "se perdió la conexión")

        # El archivo solo lo sabe la respuesta de la parada: si se consultara el
        # estado después, ya no estaría, y la grabación quedaría sin identificar.
        output_path = response.get("outputPath")
        try:
            # Parar tampoco es instantáneo: OBS cierra el archivo después de
            # aceptar la orden.
            status = self._settle(lambda record: not _grabando(record))
        except _NotConnected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        except TimeoutWebSocketError:
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNKNOWN, "se perdió la conexión")
        return CaptureStatus(
            state=status.state,
            active_scene_name=status.active_scene_name,
            recording_seconds=status.recording_seconds,
            output_path=str(output_path) if output_path else status.output_path,
        )

    def list_scenes(self) -> list[BackendScene] | CaptureError:
        try:
            response = self._request("GetSceneList")
        except _NotConnected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        except _Rejected:
            return CaptureError(CaptureErrorKind.REJECTED, "consulta rechazada")
        except TimeoutWebSocketError:
            return CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
        except WebSocketError:
            self.disconnect()
            return CaptureError(CaptureErrorKind.UNKNOWN, "se perdió la conexión")

        current = response.get("currentProgramSceneName")
        scenes = response.get("scenes", [])
        result: list[BackendScene] = []
        if isinstance(scenes, list):
            for entry in scenes:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("sceneName")
                if isinstance(name, str):
                    result.append(BackendScene(name, name == current))
        return result

    def switch_scene(self, backend_name: str) -> CaptureOutcome:
        return self._guarded("SetCurrentProgramScene", {"sceneName": backend_name})


class _NotConnected(Exception):
    """Interno: no hay sesión identificada."""


class _Rejected(Exception):
    """Interno: OBS respondió que no."""


class _AuthenticationRejected(Exception):
    """Interno: contraseña ausente o no aceptada."""


class _UnsupportedVersion(Exception):
    """Interno: la versión del protocolo del servidor no sirve."""
