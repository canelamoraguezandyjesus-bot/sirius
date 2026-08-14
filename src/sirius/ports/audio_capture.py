"""Contrato de captura de audio, neutral respecto del dispositivo.

Igual que ``LLMProvider``, este puerto no expone ningún tipo, excepción ni
detalle del SDK o del sistema de audio que haya debajo: quien lo use ve rutas,
segundos y bytes. Cambiar QtMultimedia por otra cosa no puede llegar hasta la
aplicación ni hasta la interfaz.

El micrófono solo puede abrirse tras una acción explícita y visible del
usuario, y ``stop()`` o ``cancel()`` lo cierran siempre. No existe escucha
permanente ni palabra de activación.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

DEFAULT_MAXIMUM_SECONDS = 60.0
DEFAULT_MAXIMUM_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class CaptureLimits:
    """Techo de una intervención. El adaptador cierra la captura al alcanzarlo.

    Es el adaptador quien los aplica, y no quien llama, porque la captura ocurre
    en tiempo real: comprobarlos al terminar dejaría grabar sin límite y avisar
    después, que es justo lo que no se quiere.
    """

    maximum_seconds: float = DEFAULT_MAXIMUM_SECONDS
    maximum_bytes: int = DEFAULT_MAXIMUM_BYTES


@dataclass(frozen=True, slots=True)
class AudioCaptureResult:
    """Una intervención capturada, en un archivo temporal propiedad de quien llama.

    ``stopped_by_limit`` distingue "el usuario decidió parar" de "se alcanzó el
    tope": el audio sirve igual, pero al usuario hay que decírselo.
    """

    audio_path: Path
    duration_seconds: float
    size_bytes: int
    stopped_by_limit: bool = False


class AudioCaptureErrorKind(StrEnum):
    """Clasificación segura y neutral de un fallo de captura."""

    NO_DEVICE = "no_device"
    PERMISSION = "permission"
    DEVICE_BUSY = "device_busy"
    NOT_CAPTURING = "not_capturing"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AudioCaptureError:
    """Fallo de captura. ``message`` es corto, seguro y sin detalle interno."""

    kind: AudioCaptureErrorKind
    message: str


class AudioCapture(Protocol):
    """Captura el intervalo entre una orden de inicio y una de parada.

    El usuario inicia con una acción explícita y detiene con otra: no se exige
    mantener nada pulsado (decisión del usuario del 7 de agosto de 2026).
    """

    def start(self, limits: CaptureLimits) -> AudioCaptureError | None:
        """Abre el micrófono. Devuelve el error si no pudo, o ``None`` si va.

        Llamarlo mientras ya se captura devuelve ``DEVICE_BUSY`` y no abre una
        segunda captura.
        """
        ...

    def stop(self) -> AudioCaptureResult | AudioCaptureError:
        """Cierra el micrófono y devuelve lo capturado.

        Sin captura en curso devuelve ``NOT_CAPTURING``; con captura vacía,
        ``EMPTY``. Nunca lanza.
        """
        ...

    def cancel(self) -> None:
        """Aborta la captura y borra el temporal. Idempotente."""
        ...

    def is_capturing(self) -> bool:
        """Si el micrófono está abierto ahora mismo."""
        ...

    def discard(self, audio_path: Path) -> None:
        """Borra un temporal ya entregado. Idempotente.

        Que el borrado viva en el puerto permite limpiar huérfanos sin que la
        aplicación tenga que saber dónde ni cómo se guardan.
        """
        ...
