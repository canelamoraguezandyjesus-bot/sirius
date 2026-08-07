"""Sistema de captura real: OBS Studio por su servidor WebSocket local.

Traduce el protocolo de OBS al puerto de captura. Nada del protocolo —códigos
de operación, nombres de petición, formas del JSON— sale de este archivo, así
que sustituir OBS por otro programa es escribir otro adaptador al lado.

Autenticación: OBS manda una sal y un desafío, y espera de vuelta un resumen
SHA-256 encadenado. Se calcula con la biblioteca estándar y **la contraseña
nunca se registra ni aparece en ningún mensaje de error**.

> ## Sin verificar contra OBS real
>
> Este adaptador se ha escrito a partir de la descripción del protocolo, no de
> una sesión real: el entorno donde se programó no tiene ni internet ni Windows
> ni OBS. Lo que sí está probado es el cliente WebSocket que hay debajo, contra
> un servidor de mentira.
>
> #127 exige *"no afirmar que OBS, una API, una cámara o un protocolo funcionan
> sin prueba real"*. Hasta que se ejecute el plan de verificación de
> `SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md`, **este archivo es una
> hipótesis ejecutable, no una función demostrada**. Es previsible que los
> nombres exactos de alguna petición haya que ajustarlos con OBS delante.
"""

from __future__ import annotations

import base64
import hashlib
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

_MAXIMUM_HANDSHAKE_MESSAGES = 8
"""Cuántos mensajes se aceptan antes de rendirse en el saludo: evita quedarse
esperando para siempre si el servidor manda eventos y nunca se identifica."""


def _authentication_response(password: str, salt: str, challenge: str) -> str:
    """Respuesta al desafío de OBS. La contraseña no sale de aquí."""
    secret = base64.b64encode(hashlib.sha256((password + salt).encode("utf-8")).digest())
    return base64.b64encode(hashlib.sha256(secret + challenge.encode("utf-8")).digest()).decode(
        "ascii"
    )


def _state_from(record_status: dict[str, Any]) -> StudioCaptureState:
    """Traduce lo que OBS dice a un estado de Model Studio.

    Solo ``outputActive`` puede llevar a ``GRABANDO``. Ninguna otra señal vale:
    ese es el requisito duro de #127.
    """
    if not record_status.get("outputActive", False):
        return StudioCaptureState.PREPARADO
    if record_status.get("outputPaused", False):
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
    ) -> None:
        self._password = password
        self._client = WebSocketClient(host, port, timeout_seconds)
        self._identified = False

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

    def _status(self) -> CaptureStatus:
        record = self._request("GetRecordStatus")
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
        return self._guarded("StartRecord")

    def pause_recording(self) -> CaptureOutcome:
        outcome = self._guarded("PauseRecord")
        if isinstance(outcome, CaptureError) and outcome.kind is CaptureErrorKind.REJECTED:
            # OBS rechaza pausar cuando el formato de salida no lo admite. No es
            # una avería, y #127 acepta declararlo explícitamente (MS-007).
            return CaptureError(
                CaptureErrorKind.UNSUPPORTED_OPERATION,
                "el formato de grabación no admite pausa",
            )
        return outcome

    def resume_recording(self) -> CaptureOutcome:
        return self._guarded("ResumeRecord")

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
        status = self.get_status()
        if isinstance(status, CaptureError):
            return status
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
