"""Trabajadores de fondo de la voz de Model Studio.

Mismo modelo de hilos que ``SendMessageWorker`` (SIRIUS-ARQ-0.1 S10.2):
transcribir y sintetizar tardan y llaman a la red, así que corren en el
``QThreadPool`` y el resultado vuelve al hilo de la interfaz por señales. Nada
de esto puede congelar la ventana mientras se está grabando en vídeo.

Abrir y cerrar el micrófono no pasa por aquí: son inmediatos y tienen que
responder al instante para que el estado ``ESCUCHANDO`` aparezca sin retraso.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.studio_voice import (
    SpeakOutcome,
    StudioVoiceUseCase,
    TranscribeOutcome,
)
from sirius.domain.conversation import MessageStatus
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class StudioVoiceWorkerSignals(QObject):
    """Un único desenlace, siempre: o ``finished`` o ``crashed``."""

    finished = Signal(object)
    crashed = Signal(str)


class TranscribeWorker(QRunnable):
    """Cierra la captura y transcribe, fuera del hilo de la interfaz."""

    def __init__(self, studio_voice_use_case: StudioVoiceUseCase) -> None:
        super().__init__()
        self._use_case = studio_voice_use_case
        self.signals = StudioVoiceWorkerSignals()

    def run(self) -> None:
        try:
            outcome: TranscribeOutcome = self._use_case.stop_and_transcribe()
        except Exception as exc:  # frontera del trabajador: informa, nunca tumba el hilo
            _logger.error("Transcripción interrumpida (%s)", type(exc).__name__)
            self.signals.crashed.emit(str(exc))
        else:
            self.signals.finished.emit(outcome)


class SpeakWorker(QRunnable):
    """Sintetiza una respuesta y empieza a reproducirla."""

    def __init__(
        self,
        studio_voice_use_case: StudioVoiceUseCase,
        text: str,
        status: MessageStatus,
    ) -> None:
        super().__init__()
        self._use_case = studio_voice_use_case
        self._text = text
        self._status = status
        self.signals = StudioVoiceWorkerSignals()

    def run(self) -> None:
        try:
            outcome: SpeakOutcome = self._use_case.speak(self._text, self._status)
        except Exception as exc:  # frontera del trabajador: informa, nunca tumba el hilo
            _logger.error("Síntesis interrumpida (%s)", type(exc).__name__)
            self.signals.crashed.emit(str(exc))
        else:
            self.signals.finished.emit(outcome)
