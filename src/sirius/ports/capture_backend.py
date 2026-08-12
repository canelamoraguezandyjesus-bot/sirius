"""Contrato del sistema de captura, neutral respecto del programa que haya debajo.

Hoy detrás vive OBS; mañana podría vivir otra cosa. Este puerto no expone
WebSockets, ni JSON, ni nombres de comandos de ningún programa concreto, de
modo que sustituirlo es escribir otro adaptador y nada más.

**El backend es la autoridad sobre el estado.** ``get_status()`` no devuelve lo
que Sirius cree, sino lo que el sistema de captura dice. Esa es la regla que
manda en #127: ningún modelo puede afirmar que se está grabando; solo puede
repetir lo que el backend confirme.

Nunca lanza por un fallo externo: devuelve un resultado o un error tipado.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sirius.domain.model_studio import StudioCaptureState


@dataclass(frozen=True, slots=True)
class BackendScene:
    """Una escena tal como la conoce el sistema de captura."""

    name: str
    is_active: bool = False


@dataclass(frozen=True, slots=True)
class CaptureStatus:
    """Lo que el backend dice de sí mismo ahora mismo.

    ``output_path`` solo tiene valor cuando el backend informa del archivo
    resultante: #127 exige que la grabación quede identificada y reproducible,
    y un nombre inventado no serviría para encontrarla después.
    """

    state: StudioCaptureState
    active_scene_name: str | None = None
    recording_seconds: float | None = None
    output_path: str | None = None


class CaptureErrorKind(StrEnum):
    """Clasificación segura y neutral de un fallo de captura."""

    NOT_CONNECTED = "not_connected"
    AUTHENTICATION = "authentication"
    UNSUPPORTED_VERSION = "unsupported_version"
    TIMEOUT = "timeout"
    REJECTED = "rejected"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CaptureError:
    """Fallo del sistema de captura. ``message`` es corto, seguro y sin secretos."""

    kind: CaptureErrorKind
    message: str


CaptureOutcome = CaptureStatus | CaptureError


class CaptureBackend(Protocol):
    """Gobierna grabación y escenas en un sistema de captura local."""

    def connect(self) -> CaptureError | None:
        """Se conecta y autentica. Devuelve el error, o ``None`` si va.

        Idempotente: llamarlo estando ya conectado no abre una segunda sesión.
        """
        ...

    def disconnect(self) -> None:
        """Cierra la conexión. Idempotente y sin efectos sobre la grabación.

        Desconectarse **no** detiene lo que se esté grabando: cerrar Sirius no
        puede llevarse por delante una toma en curso.
        """
        ...

    def is_connected(self) -> bool: ...

    def get_status(self) -> CaptureOutcome:
        """Estado real, preguntado al backend. Única fuente de verdad."""
        ...

    def start_recording(self) -> CaptureOutcome:
        """Inicia la grabación y devuelve el estado resultante."""
        ...

    def pause_recording(self) -> CaptureOutcome:
        """Pausa. Devuelve ``UNSUPPORTED_OPERATION`` si el backend no puede."""
        ...

    def resume_recording(self) -> CaptureOutcome: ...

    def stop_recording(self) -> CaptureOutcome:
        """Detiene y, si el backend lo informa, incluye el archivo resultante."""
        ...

    def list_scenes(self) -> list[BackendScene] | CaptureError:
        """Escenas que existen en el backend, estén o no autorizadas."""
        ...

    def switch_scene(self, backend_name: str) -> CaptureOutcome:
        """Activa una escena por su nombre en el backend."""
        ...
