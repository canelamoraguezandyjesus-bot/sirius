"""Orquesta la grabación, las escenas y las marcas de Model Studio.

Concentra las reglas de #127 y no conoce ni OBS ni WebSockets: solo el puerto
de captura y la lista blanca de escenas. Cambiar de programa de grabación es
escribir otro adaptador.

La regla que manda sobre todas las demás: **el estado lo dice el backend, no
Sirius.** Aquí no hay ni una ruta en la que se dé por hecho que se está
grabando. Cuando una orden sale pero aún no hay confirmación, el estado es
``INICIANDO`` o ``DETENIENDO``, nunca ``GRABANDO``. Y si la confirmación no
llega, el estado es ``INCIERTO`` y se pide reconciliación, jamás se supone
éxito.

Es síncrono a propósito: la presentación lo envuelve en el mismo patrón
``QThreadPool``/señales que ya usan el envío de mensajes y la voz.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sirius.domain.capture import Scene, SceneRegistry
from sirius.domain.model_studio import StudioCaptureState
from sirius.ports.capture_backend import (
    CaptureBackend,
    CaptureError,
    CaptureErrorKind,
    CaptureStatus,
)


class CaptureJournal(Protocol):
    """Registro local mínimo de lo que ha pasado.

    Guarda sesión, momento, comando, resultado, escena y error. **Nunca** vídeo,
    audio ni transcripciones: #127 lo prohíbe expresamente y es la razón de que
    este contrato solo acepte texto corto.
    """

    def record(self, command: str, result: str, detail: str = "") -> None: ...

    def record_mark(self, label: str, elapsed_seconds: float) -> None: ...

    def begin_take(self) -> None:
        """Empieza una toma nueva.

        Las marcas sueltas no sirven de nada: hay que poder pegarlas a un vídeo
        concreto, y saber dónde empieza y acaba cada toma es lo único que lo
        permite.
        """
        ...

    def end_take(self, output_path: str | None) -> None:
        """Cierra la toma, con el archivo que el sistema de captura haya dicho.

        ``None`` cuando no lo ha dicho: es información que falta, no un motivo
        para tirar las marcas.
        """
        ...


@dataclass(frozen=True, slots=True)
class MomentMark:
    """Una marca temporal para editar después."""

    label: str
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class CaptureFeedback:
    """Lo que hay que enseñar tras una orden, y si salió bien.

    ``succeeded`` en falso **no** significa que algo se haya roto: también
    cubre una orden rechazada a propósito, como una escena no autorizada.
    """

    state: StudioCaptureState
    message: str = ""
    scene_id: str | None = None
    recording_seconds: float | None = None
    output_path: str | None = None
    succeeded: bool = True


_ERROR_MESSAGES: dict[CaptureErrorKind, str] = {
    CaptureErrorKind.NOT_CONNECTED: "No estoy conectado al sistema de grabación.",
    CaptureErrorKind.AUTHENTICATION: "La contraseña del sistema de grabación no es válida.",
    CaptureErrorKind.UNSUPPORTED_VERSION: "La versión del sistema de grabación no sirve.",
    CaptureErrorKind.TIMEOUT: "El sistema de grabación no ha contestado a tiempo.",
    CaptureErrorKind.REJECTED: "El sistema de grabación ha rechazado la orden.",
    CaptureErrorKind.UNSUPPORTED_OPERATION: "El sistema de grabación no admite eso.",
    CaptureErrorKind.UNKNOWN: "No he podido hablar con el sistema de grabación.",
}

DISABLED_MESSAGE = "Model Studio tiene la grabación desactivada."
NO_SCENES_MESSAGE = "No hay ninguna escena autorizada configurada."
ALREADY_RECORDING_MESSAGE = "Ya estaba grabando; no he abierto una segunda sesión."
NOT_RECORDING_MESSAGE = "No había ninguna grabación en curso."
UNKNOWN_SCENE_MESSAGE = "Esa escena no está autorizada. No he cambiado el plano."
UNCERTAIN_MESSAGE = "No sé si se está grabando. Voy a comprobarlo con el sistema."


class StudioCaptureUseCase:
    """Grabar, cambiar de escena y marcar momentos, sin inventar nunca el estado."""

    def __init__(
        self,
        backend: CaptureBackend,
        scenes: SceneRegistry,
        journal: CaptureJournal | None = None,
        *,
        enabled: bool = False,
    ) -> None:
        self._backend = backend
        self._scenes = scenes
        self._journal = journal
        # Se lleva aparte del estado general porque ese pasa por INICIANDO y
        # DETENIENDO, que son órdenes en vuelo y no tomas.
        self._take_open = False
        # Desactivado por omisión: #127 exige que abrir Sirius no conecte ni
        # grabe nada, y que haga falta encenderlo a propósito.
        self._enabled = enabled
        self._marks: list[MomentMark] = []
        self._last_known_state = StudioCaptureState.DESACTIVADO

    # --- Interruptor general ---------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> CaptureFeedback:
        """Enciende el módulo y se conecta. ``PREPARADO`` solo tras confirmar."""
        if self._scenes.is_empty:
            return self._refuse(StudioCaptureState.DESACTIVADO, NO_SCENES_MESSAGE, "enable")
        self._enabled = True
        error = self._backend.connect()
        if error is not None:
            return self._fail(error, "enable")
        # No se declara PREPARADO por haber conectado: se pregunta.
        return self.refresh_status()

    def disable(self) -> CaptureFeedback:
        """Apaga el módulo y se desconecta, sin tocar lo que se esté grabando."""
        self._enabled = False
        self._backend.disconnect()
        self._last_known_state = StudioCaptureState.DESACTIVADO
        self._log("disable", "ok")
        return CaptureFeedback(StudioCaptureState.DESACTIVADO)

    # --- Estado ----------------------------------------------------------

    @property
    def last_known_state(self) -> StudioCaptureState:
        """Último estado confirmado. No es autoridad: solo memoria de pantalla."""
        return self._last_known_state

    def refresh_status(self) -> CaptureFeedback:
        """Pregunta al backend. Es la reconciliación de #127.

        Se llama al encender, tras un timeout, tras una desconexión y al
        arrancar Sirius si quedó una grabación abierta.
        """
        if not self._enabled:
            return CaptureFeedback(StudioCaptureState.DESACTIVADO)
        outcome = self._backend.get_status()
        if isinstance(outcome, CaptureError):
            return self._fail(outcome, "get_status")
        return self._accept(outcome, "get_status")

    # --- Grabación -------------------------------------------------------

    def start_recording(self) -> CaptureFeedback:
        """Inicia la grabación. Idempotente: no abre una segunda sesión.

        La comprobación se hace preguntando al backend, no mirando lo que
        Sirius recuerda: si alguien pulsó grabar en OBS a mano, aquí se ve.
        """
        guard = self._require_enabled()
        if guard is not None:
            return guard

        current = self._backend.get_status()
        if isinstance(current, CaptureError):
            return self._fail(current, "start_recording")
        if current.state.is_recording_confirmed:
            self._last_known_state = current.state
            self._log("start_recording", "ya-grabando")
            return CaptureFeedback(
                current.state,
                ALREADY_RECORDING_MESSAGE,
                recording_seconds=current.recording_seconds,
                succeeded=True,
            )

        # Orden enviada, sin confirmar: INICIANDO, nunca GRABANDO.
        self._last_known_state = StudioCaptureState.INICIANDO
        outcome = self._backend.start_recording()
        if isinstance(outcome, CaptureError):
            return self._fail(outcome, "start_recording")
        self._marks.clear()
        return self._accept(outcome, "start_recording")

    def pause_recording(self) -> CaptureFeedback:
        guard = self._require_enabled()
        if guard is not None:
            return guard
        outcome = self._backend.pause_recording()
        if isinstance(outcome, CaptureError):
            # Que el backend no sepa pausar no es una avería: se dice y ya.
            return self._fail(outcome, "pause_recording")
        return self._accept(outcome, "pause_recording")

    def resume_recording(self) -> CaptureFeedback:
        guard = self._require_enabled()
        if guard is not None:
            return guard
        outcome = self._backend.resume_recording()
        if isinstance(outcome, CaptureError):
            return self._fail(outcome, "resume_recording")
        return self._accept(outcome, "resume_recording")

    def stop_recording(self) -> CaptureFeedback:
        """Detiene la grabación. Repetirlo es seguro y no destruye nada."""
        guard = self._require_enabled()
        if guard is not None:
            return guard

        current = self._backend.get_status()
        if isinstance(current, CaptureError):
            return self._fail(current, "stop_recording")
        if current.state in (StudioCaptureState.PREPARADO, StudioCaptureState.DESACTIVADO):
            self._last_known_state = current.state
            self._log("stop_recording", "no-habia-grabacion")
            return CaptureFeedback(current.state, NOT_RECORDING_MESSAGE, succeeded=True)

        self._last_known_state = StudioCaptureState.DETENIENDO
        outcome = self._backend.stop_recording()
        if isinstance(outcome, CaptureError):
            return self._fail(outcome, "stop_recording")
        return self._accept(outcome, "stop_recording")

    def emergency_stop(self) -> CaptureFeedback:
        """Cierra la grabación de inmediato y deja constancia.

        No pregunta antes ni comprueba nada: si alguien pulsa esto es porque
        quiere que deje de grabar **ya**. Cualquier comprobación previa es
        tiempo grabando que no se quería grabar.
        """
        self._log("emergency_stop", "solicitado")
        if not self._enabled:
            return CaptureFeedback(StudioCaptureState.DESACTIVADO, DISABLED_MESSAGE)
        outcome = self._backend.stop_recording()
        if isinstance(outcome, CaptureError):
            # Ni siquiera aquí se afirma que se detuvo: si no se pudo, el
            # estado queda incierto y se dice.
            self._last_known_state = StudioCaptureState.INCIERTO
            self._log("emergency_stop", "fallido", outcome.kind.value)
            return CaptureFeedback(
                StudioCaptureState.INCIERTO,
                f"{_ERROR_MESSAGES[outcome.kind]} {UNCERTAIN_MESSAGE}",
                succeeded=False,
            )
        return self._accept(outcome, "emergency_stop")

    # --- Escenas ---------------------------------------------------------

    def authorized_scenes(self) -> tuple[Scene, ...]:
        return self._scenes.scenes

    def switch_scene(self, spoken_or_id: str) -> CaptureFeedback:
        """Cambia de escena, solo si está en la lista blanca.

        Una escena desconocida **no cambia el plano**: se rechaza y se dice.
        Adivinar la escena más parecida sería cambiar de cámara por error en
        mitad de una toma.
        """
        guard = self._require_enabled()
        if guard is not None:
            return guard

        scene = self._scenes.resolve(spoken_or_id)
        if scene is None:
            self._log("switch_scene", "rechazada", "no-autorizada")
            return CaptureFeedback(self._last_known_state, UNKNOWN_SCENE_MESSAGE, succeeded=False)

        previous = self._last_known_state
        self._last_known_state = StudioCaptureState.CAMBIANDO
        outcome = self._backend.switch_scene(scene.backend_name)
        if isinstance(outcome, CaptureError):
            self._last_known_state = previous
            return self._fail(outcome, "switch_scene")
        feedback = self._accept(outcome, "switch_scene")
        return CaptureFeedback(
            feedback.state,
            feedback.message,
            scene_id=scene.scene_id,
            recording_seconds=feedback.recording_seconds,
            output_path=feedback.output_path,
            succeeded=True,
        )

    def fall_back_to_safe_scene(self) -> CaptureFeedback:
        """Vuelve a la escena de reserva cuando una fuente se pierde.

        Nunca finge que la fuente perdida sigue ahí: o se cambia de plano, o se
        informa de la degradación.
        """
        fallback = self._scenes.fallback
        if fallback is None:
            return self._refuse(self._last_known_state, NO_SCENES_MESSAGE, "fallback")
        return self.switch_scene(fallback.scene_id)

    # --- Marcas ----------------------------------------------------------

    @property
    def marks(self) -> tuple[MomentMark, ...]:
        return tuple(self._marks)

    def mark_moment(self, label: str = "") -> CaptureFeedback:
        """Anota un momento con su tiempo relativo, para editar después.

        Solo tiene sentido durante una grabación confirmada: marcar algo que no
        se está grabando produciría una referencia a un vídeo que no existe.
        """
        guard = self._require_enabled()
        if guard is not None:
            return guard

        current = self._backend.get_status()
        if isinstance(current, CaptureError):
            return self._fail(current, "mark_moment")
        if not current.state.is_recording_confirmed:
            self._last_known_state = current.state
            self._log("mark_moment", "rechazada", "sin-grabacion")
            return CaptureFeedback(current.state, NOT_RECORDING_MESSAGE, succeeded=False)

        elapsed = current.recording_seconds or 0.0
        clean_label = label.strip() or f"Marca {len(self._marks) + 1}"
        self._marks.append(MomentMark(clean_label, elapsed))
        if self._journal is not None:
            self._journal.record_mark(clean_label, elapsed)
        self._last_known_state = current.state
        return CaptureFeedback(
            current.state,
            f"Marcado «{clean_label}» en {int(elapsed // 60):02d}:{int(elapsed % 60):02d}.",
            recording_seconds=elapsed,
        )

    # --- Interior --------------------------------------------------------

    def _require_enabled(self) -> CaptureFeedback | None:
        if not self._enabled:
            return CaptureFeedback(
                StudioCaptureState.DESACTIVADO, DISABLED_MESSAGE, succeeded=False
            )
        if not self._backend.is_connected():
            return CaptureFeedback(
                StudioCaptureState.ERROR,
                _ERROR_MESSAGES[CaptureErrorKind.NOT_CONNECTED],
                succeeded=False,
            )
        return None

    _ACTIVE_STATES = frozenset({StudioCaptureState.GRABANDO, StudioCaptureState.PAUSADO})
    """Una toma sigue abierta en pausa: pausar no cierra el archivo."""

    def _announce_take(self, status: CaptureStatus) -> None:
        """Avisa al diario del principio y el final de cada toma.

        Se guía solo por estados confirmados por el backend, nunca por los de
        una orden en vuelo, y es idempotente: repetir la misma confirmación no
        abre ni cierra una toma dos veces.
        """
        if self._journal is None:
            return
        activo = status.state in self._ACTIVE_STATES
        if activo and not self._take_open:
            self._take_open = True
            self._journal.begin_take()
        elif not activo and self._take_open:
            self._take_open = False
            self._journal.end_take(status.output_path)

    def _accept(self, status: CaptureStatus, command: str) -> CaptureFeedback:
        """Adopta el estado que dice el backend. Único camino a ``GRABANDO``."""
        self._last_known_state = status.state
        self._announce_take(status)
        scene = (
            self._scene_id_for(status.active_scene_name)
            if status.active_scene_name is not None
            else None
        )
        self._log(command, status.state.value, scene or "")
        return CaptureFeedback(
            state=status.state,
            scene_id=scene,
            recording_seconds=status.recording_seconds,
            output_path=status.output_path,
        )

    def _scene_id_for(self, backend_name: str) -> str | None:
        for scene in self._scenes.scenes:
            if scene.backend_name == backend_name:
                return scene.scene_id
        return None

    def _fail(self, error: CaptureError, command: str) -> CaptureFeedback:
        # Un timeout o una desconexión dejan el estado INCIERTO, no DETENIDO:
        # no saber no es lo mismo que saber que no.
        uncertain = error.kind in (CaptureErrorKind.TIMEOUT, CaptureErrorKind.NOT_CONNECTED)
        state = StudioCaptureState.INCIERTO if uncertain else StudioCaptureState.ERROR
        self._last_known_state = state
        self._log(command, "error", error.kind.value)
        message = _ERROR_MESSAGES[error.kind]
        if uncertain:
            message = f"{message} {UNCERTAIN_MESSAGE}"
        return CaptureFeedback(state, message, succeeded=False)

    def _refuse(self, state: StudioCaptureState, message: str, command: str) -> CaptureFeedback:
        self._last_known_state = state
        self._log(command, "rechazada", message)
        return CaptureFeedback(state, message, succeeded=False)

    def _log(self, command: str, result: str, detail: str = "") -> None:
        if self._journal is not None:
            self._journal.record(command, result, detail)
