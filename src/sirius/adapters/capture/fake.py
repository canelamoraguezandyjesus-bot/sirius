"""Sistema de captura simulado, determinista y sin red ni programas externos.

Es el que usan CI y todas las pruebas automáticas: no abre ningún puerto, no
lanza OBS y no graba nada. #127 lo exige así — *"CI y pruebas automáticas no
usarán cámaras reales, red externa ni credenciales reales"*.

Puede fingir cualquier desenlace, incluido el peor de todos: que la orden salga
y la confirmación no llegue. Ese es justo el caso en el que sería fácil dar por
hecho que se está grabando, y el que más falta hace poder probar.
"""

from __future__ import annotations

from sirius.domain.model_studio import StudioCaptureState
from sirius.ports.capture_backend import (
    BackendScene,
    CaptureError,
    CaptureErrorKind,
    CaptureOutcome,
    CaptureStatus,
)


class FakeCaptureBackend:
    """Sistema de captura de mentira con estado interno coherente."""

    def __init__(
        self,
        scene_names: tuple[str, ...] = ("Pantalla", "Cámara frontal", "Cámara cenital"),
        *,
        connect_error: CaptureError | None = None,
        status_error: CaptureError | None = None,
        command_error: CaptureError | None = None,
        supports_pause: bool = True,
        output_path: str = "C:/grabaciones/sesion-001.mkv",
    ) -> None:
        self._scene_names = scene_names
        self._connect_error = connect_error
        self._status_error = status_error
        self._command_error = command_error
        self._supports_pause = supports_pause
        self._output_path = output_path
        self._connected = False
        self._state = StudioCaptureState.PREPARADO
        self._active_scene = scene_names[0] if scene_names else None
        self._recording_seconds = 0.0
        self.commands: list[str] = []

    # --- Conexión --------------------------------------------------------

    def connect(self) -> CaptureError | None:
        self.commands.append("connect")
        if self._connect_error is not None:
            return self._connect_error
        self._connected = True
        return None

    def disconnect(self) -> None:
        self.commands.append("disconnect")
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def simulate_shutdown(self) -> None:
        """Como si alguien hubiera cerrado el programa de captura sin avisar.

        No es lo mismo que ``disconnect()``: ahí se va Sirius, aquí se va el
        otro. Después de esto ni siquiera se puede volver a conectar, que es
        justo lo que hace un OBS cerrado.
        """
        self._connected = False
        self._connect_error = CaptureError(
            CaptureErrorKind.NOT_CONNECTED, "el sistema de captura no está abierto"
        )

    def simulate_reopening(self) -> None:
        """Como si lo hubieran vuelto a abrir. Conectar vuelve a funcionar."""
        self._connect_error = None

    # --- Estado ----------------------------------------------------------

    def get_status(self) -> CaptureOutcome:
        self.commands.append("get_status")
        if self._status_error is not None:
            return self._status_error
        if not self._connected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        return self._snapshot()

    def _snapshot(self) -> CaptureStatus:
        recording = self._state in (StudioCaptureState.GRABANDO, StudioCaptureState.PAUSADO)
        return CaptureStatus(
            state=self._state,
            active_scene_name=self._active_scene,
            recording_seconds=self._recording_seconds if recording else None,
            output_path=self._output_path if recording else None,
        )

    # --- Grabación -------------------------------------------------------

    def start_recording(self) -> CaptureOutcome:
        self.commands.append("start_recording")
        if (error := self._reject()) is not None:
            return error
        self._state = StudioCaptureState.GRABANDO
        self._recording_seconds = 0.0
        return self._snapshot()

    def pause_recording(self) -> CaptureOutcome:
        self.commands.append("pause_recording")
        if (error := self._reject()) is not None:
            return error
        if not self._supports_pause:
            return CaptureError(
                CaptureErrorKind.UNSUPPORTED_OPERATION, "este formato no admite pausa"
            )
        self._state = StudioCaptureState.PAUSADO
        return self._snapshot()

    def resume_recording(self) -> CaptureOutcome:
        self.commands.append("resume_recording")
        if (error := self._reject()) is not None:
            return error
        self._state = StudioCaptureState.GRABANDO
        return self._snapshot()

    def stop_recording(self) -> CaptureOutcome:
        self.commands.append("stop_recording")
        if (error := self._reject()) is not None:
            return error
        stopped = CaptureStatus(
            state=StudioCaptureState.PREPARADO,
            active_scene_name=self._active_scene,
            output_path=self._output_path,
        )
        self._state = StudioCaptureState.PREPARADO
        self._recording_seconds = 0.0
        return stopped

    # --- Escenas ---------------------------------------------------------

    def list_scenes(self) -> list[BackendScene] | CaptureError:
        self.commands.append("list_scenes")
        if (error := self._reject()) is not None:
            return error
        return [BackendScene(name, name == self._active_scene) for name in self._scene_names]

    def switch_scene(self, backend_name: str) -> CaptureOutcome:
        self.commands.append(f"switch_scene:{backend_name}")
        if (error := self._reject()) is not None:
            return error
        if backend_name not in self._scene_names:
            return CaptureError(CaptureErrorKind.REJECTED, "esa escena no existe")
        self._active_scene = backend_name
        return self._snapshot()

    # --- Ayudas para las pruebas -----------------------------------------

    def advance(self, seconds: float) -> None:
        """Avanza el cronómetro de grabación sin usar el reloj real."""
        if self._state is StudioCaptureState.GRABANDO:
            self._recording_seconds += seconds

    def simulate_manual_recording(self) -> None:
        """Alguien pulsó grabar en el propio programa, no desde Sirius."""
        self._state = StudioCaptureState.GRABANDO

    def _reject(self) -> CaptureError | None:
        if not self._connected:
            return CaptureError(CaptureErrorKind.NOT_CONNECTED, "sin conexión")
        return self._command_error


class FakeCaptureJournal:
    """Registro de mentira: guarda en memoria lo que se le pida anotar."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str, str]] = []
        self.marks: list[tuple[str, float]] = []
        self.takes_started = 0
        self.takes_ended: list[str | None] = []

    def record(self, command: str, result: str, detail: str = "") -> None:
        self.entries.append((command, result, detail))

    def record_mark(self, label: str, elapsed_seconds: float) -> None:
        self.marks.append((label, elapsed_seconds))

    def begin_take(self) -> None:
        self.takes_started += 1

    def end_take(self, output_path: str | None) -> None:
        self.takes_ended.append(output_path)
