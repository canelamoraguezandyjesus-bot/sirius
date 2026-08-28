"""Orquesta la voz de Model Studio: escuchar, transcribir, hablar.

Es el único sitio donde vive la política de la voz —qué se sintetiza, qué se
bloquea por presupuesto, cuándo se borra un temporal—, y no conoce ni Qt ni
OpenAI: solo los cuatro puertos de audio. Cambiar de proveedor de voz o de
biblioteca de sonido se hace escribiendo otro adaptador, sin tocar esto ni la
interfaz.

Es **síncrono a propósito**. Las llamadas que tardan —transcribir y sintetizar—
las envuelve la presentación en el patrón ``QThreadPool``/señales que Sirius ya
usa para enviar mensajes, igual que ``SendMessageUseCase``. Aquí no hay hilos.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Protocol

from sirius.application.prepare_speech_text import prepare_speech_text
from sirius.domain.conversation import MessageStatus
from sirius.ports.audio_capture import (
    AudioCapture,
    AudioCaptureError,
    AudioCaptureErrorKind,
    CaptureLimits,
)
from sirius.ports.audio_playback import AudioPlayback, PlaybackError
from sirius.ports.speech_to_text import (
    SpeechToText,
    Transcription,
    TranscriptionError,
    TranscriptionErrorKind,
)
from sirius.ports.text_to_speech import (
    SpeechError,
    SpeechErrorKind,
    SpeechRequest,
    SynthesizedSpeech,
    TextToSpeech,
)


class VoiceSpendGuard(Protocol):
    """Lo mínimo que esta vertical necesita del presupuesto mensual.

    La aplicación no puede importar ``sirius.adapters``
    (``test_application_boundaries.py``), así que no depende de
    ``BudgetTracker``, que lo cumple estructuralmente. La raíz de composición
    conecta el mismo contador que ya usa el proveedor de texto, de modo que la
    voz y el texto gastan del mismo bolsillo y el tope mensual sigue siendo uno.
    """

    def has_remaining_budget(self) -> bool:
        """El AVISO de cortesía (p. ej. antes de abrir el micrófono): dejar
        hablar un minuto para luego decir que no hay saldo es la peor forma de
        avisar. La ADMISIÓN real es `reserva` (H-30)."""
        ...

    def reserva(self, estimado_usd: float) -> AbstractContextManager[object | None]:
        """H-30: la admisión atómica. Dentro del ``with`` se hace la llamada y
        se apunta el coste real con ``record_*``; la salida suelta la reserva."""
        ...

    def costo_transcripcion_usd(self, audio_seconds: float) -> float: ...

    def costo_sintesis_usd(self, character_count: int) -> float: ...

    def record_transcription(self, audio_seconds: float) -> None: ...

    def record_speech(self, character_count: int) -> None: ...


DEFAULT_LANGUAGE = "es"

DEFAULT_VOICE_INSTRUCTIONS = (
    "Habla en español de España, con voz masculina, cercana, directa y serena. "
    "Ritmo natural de conversación, sin entonación de locutor ni de anuncio."
)
"""Cómo suena, no quién es.

La identidad de Sirius vive en la memoria y en el contexto, no aquí: esto es
una instrucción efímera de tono para el sintetizador y no puede alterarla.
"""


@dataclass(frozen=True, slots=True)
class VoiceSettings:
    """Configuración de la voz. Todo dato, nada codificado en el flujo."""

    voice: str
    language: str = DEFAULT_LANGUAGE
    instructions: str = DEFAULT_VOICE_INSTRUCTIONS
    limits: CaptureLimits = field(default_factory=CaptureLimits)


@dataclass(frozen=True, slots=True)
class ListeningStarted:
    """El micrófono está abierto y el usuario lo está viendo."""


@dataclass(frozen=True, slots=True)
class TranscriptReady:
    """Hay texto para que el usuario lo revise antes de enviarlo.

    ``stopped_by_limit`` avisa de que la captura se cerró sola al llegar al
    tope, para poder decírselo en lenguaje claro.
    """

    text: str
    stopped_by_limit: bool = False


@dataclass(frozen=True, slots=True)
class VoiceFailure:
    """Un fallo de voz, ya traducido a algo que se le puede decir a una persona.

    ``recoverable`` distingue "vuelve a intentarlo" de "esto no se va a
    arreglar solo". En ninguno de los dos casos se toca el chat escrito.
    """

    message: str
    recoverable: bool = True


@dataclass(frozen=True, slots=True)
class SpeechStarted:
    """Sirius ha empezado a hablar."""


@dataclass(frozen=True, slots=True)
class NothingToSay:
    """La respuesta no tenía nada pronunciable, por ejemplo solo código.

    No es un fallo: el contenido está en pantalla y no hace falta leerlo.
    """


ListenOutcome = ListeningStarted | VoiceFailure
TranscribeOutcome = TranscriptReady | VoiceFailure
SpeakOutcome = SpeechStarted | NothingToSay | VoiceFailure


_CAPTURE_MESSAGES: dict[AudioCaptureErrorKind, str] = {
    AudioCaptureErrorKind.NO_DEVICE: "No encuentro ningún micrófono disponible.",
    AudioCaptureErrorKind.PERMISSION: "Windows no me deja usar el micrófono.",
    AudioCaptureErrorKind.DEVICE_BUSY: "El micrófono lo está usando otra cosa.",
    AudioCaptureErrorKind.NOT_CAPTURING: "No había ninguna captura en curso.",
    AudioCaptureErrorKind.EMPTY: "No he captado nada. Prueba a hablar más cerca.",
    AudioCaptureErrorKind.UNKNOWN: "No he podido usar el micrófono.",
}

_TRANSCRIPTION_MESSAGES: dict[TranscriptionErrorKind, str] = {
    TranscriptionErrorKind.AUTHENTICATION: "La clave del proveedor no es válida.",
    TranscriptionErrorKind.PERMISSION: "La clave no tiene permiso para transcribir.",
    TranscriptionErrorKind.RATE_LIMITED: "El proveedor va saturado. Inténtalo en un momento.",
    TranscriptionErrorKind.CONNECTION: "No he podido conectar para transcribir.",
    TranscriptionErrorKind.TIMEOUT: "La transcripción ha tardado demasiado.",
    TranscriptionErrorKind.INVALID_AUDIO: "El audio no se ha podido interpretar.",
    TranscriptionErrorKind.BUDGET_EXCEEDED: "Se ha agotado el presupuesto de este mes.",
    TranscriptionErrorKind.CONFIGURATION: "Falta configurar el proveedor de voz.",
    TranscriptionErrorKind.UNKNOWN: "No he podido transcribir lo que has dicho.",
}

_SPEECH_MESSAGES: dict[SpeechErrorKind, str] = {
    SpeechErrorKind.AUTHENTICATION: "La clave del proveedor no es válida.",
    SpeechErrorKind.PERMISSION: "La clave no tiene permiso para sintetizar voz.",
    SpeechErrorKind.RATE_LIMITED: "El proveedor va saturado. Inténtalo en un momento.",
    SpeechErrorKind.CONNECTION: "No he podido conectar para hablar.",
    SpeechErrorKind.TIMEOUT: "La síntesis ha tardado demasiado.",
    SpeechErrorKind.INVALID_VOICE: "Esa voz no existe en el proveedor.",
    SpeechErrorKind.BUDGET_EXCEEDED: "Se ha agotado el presupuesto de este mes.",
    SpeechErrorKind.CONFIGURATION: "Falta configurar el proveedor de voz.",
    SpeechErrorKind.UNKNOWN: "No he podido generar la voz.",
}

_UNRECOVERABLE_TRANSCRIPTION = frozenset(
    {
        TranscriptionErrorKind.AUTHENTICATION,
        TranscriptionErrorKind.PERMISSION,
        TranscriptionErrorKind.CONFIGURATION,
        TranscriptionErrorKind.BUDGET_EXCEEDED,
    }
)

_UNRECOVERABLE_SPEECH = frozenset(
    {
        SpeechErrorKind.AUTHENTICATION,
        SpeechErrorKind.PERMISSION,
        SpeechErrorKind.CONFIGURATION,
        SpeechErrorKind.INVALID_VOICE,
        SpeechErrorKind.BUDGET_EXCEEDED,
    }
)

BUDGET_EXHAUSTED_MESSAGE = "Se ha agotado el presupuesto de este mes."


class StudioVoiceUseCase:
    """Escuchar, transcribir y hablar, sin conocer proveedor ni dispositivo."""

    def __init__(
        self,
        audio_capture: AudioCapture,
        speech_to_text: SpeechToText,
        text_to_speech: TextToSpeech,
        audio_playback: AudioPlayback,
        settings: VoiceSettings,
        budget_guard: VoiceSpendGuard | None = None,
    ) -> None:
        self._capture = audio_capture
        self._speech_to_text = speech_to_text
        self._text_to_speech = text_to_speech
        self._playback = audio_playback
        self._settings = settings
        self._budget = budget_guard
        self._spoken_audio: Path | None = None
        self._speech_finished: Callable[[], None] | None = None

    def set_speech_finished_callback(self, callback: Callable[[], None] | None) -> None:
        """Avisa cuando la voz termina **sola**, no cuando se la detiene.

        Sin esto la interfaz se queda en ``HABLANDO`` para siempre: sabe cuándo
        empieza a sonar porque lo pidió ella, pero el final solo lo conoce el
        reproductor. Quien detiene a propósito ya sabe que ha detenido y ajusta
        su estado sin que nadie se lo diga.

        Se invoca en el hilo del reproductor, que es el de la interfaz.
        """
        self._speech_finished = callback

    # --- Escuchar --------------------------------------------------------

    def start_listening(self) -> ListenOutcome:
        """Abre el micrófono tras una acción explícita del usuario.

        Se comprueba el presupuesto ANTES de abrirlo: dejar hablar un minuto
        para luego decir que no hay saldo es la peor forma de avisar.
        """
        if not self._has_budget():
            return VoiceFailure(BUDGET_EXHAUSTED_MESSAGE, recoverable=False)
        error = self._capture.start(self._settings.limits)
        if error is not None:
            return self._capture_failure(error)
        return ListeningStarted()

    def cancel_listening(self) -> None:
        """Aborta la captura y borra el temporal. Idempotente."""
        self._capture.cancel()

    @property
    def is_listening(self) -> bool:
        return self._capture.is_capturing()

    def stop_and_transcribe(self) -> TranscribeOutcome:
        """Cierra el micrófono y devuelve el texto para que el usuario lo revise.

        El temporal se borra pase lo que pase: ni un WAV sobrevive a esta
        llamada, ni cuando va bien ni cuando falla.
        """
        captured = self._capture.stop()
        if isinstance(captured, AudioCaptureError):
            return self._capture_failure(captured)

        try:
            # El estimado es el TECHO de la captura (maximum_seconds): la
            # duración real solo se conoce después, y una cota superior honesta
            # es exactamente lo que una reserva necesita. El coste real lo
            # apunta record_transcription dentro del with.
            estimado = (
                0.0
                if self._budget is None
                else self._budget.costo_transcripcion_usd(self._settings.limits.maximum_seconds)
            )
            with self._reserva(estimado) as admitida:
                if admitida is None:
                    return VoiceFailure(BUDGET_EXHAUSTED_MESSAGE, recoverable=False)

                result = self._speech_to_text.transcribe(
                    captured.audio_path, self._settings.language
                )
                if isinstance(result, TranscriptionError):
                    return VoiceFailure(
                        _TRANSCRIPTION_MESSAGES[result.kind],
                        recoverable=result.kind not in _UNRECOVERABLE_TRANSCRIPTION,
                    )

                self._record_transcription(result)
                if not result.text.strip():
                    return VoiceFailure(
                        _CAPTURE_MESSAGES[AudioCaptureErrorKind.EMPTY], recoverable=True
                    )
                return TranscriptReady(result.text.strip(), captured.stopped_by_limit)
        finally:
            self._capture.discard(captured.audio_path)

    # --- Hablar ----------------------------------------------------------

    def speak(self, text: str, status: MessageStatus, *, read_code: bool = False) -> SpeakOutcome:
        """Sintetiza y reproduce una respuesta.

        Solo se habla lo que Sirius terminó de decir de verdad. Una respuesta
        cancelada o fallida contiene texto a medias, y leerlo en voz alta lo
        presentaría como una respuesta completa.

        ``read_code`` lee también los bloques de código, que normalmente se
        resumen en «te dejo el código en pantalla». Es lo que hace «Leer todo».
        """
        if status is not MessageStatus.COMPLETED:
            return NothingToSay()

        pronounceable = prepare_speech_text(text, read_code=read_code)
        if not pronounceable:
            return NothingToSay()

        # Aquí el estimado es casi exacto: los caracteres se conocen ANTES.
        estimado = (
            0.0 if self._budget is None else self._budget.costo_sintesis_usd(len(pronounceable))
        )
        with self._reserva(estimado) as admitida:
            if admitida is None:
                return VoiceFailure(BUDGET_EXHAUSTED_MESSAGE, recoverable=False)

            synthesized = self._text_to_speech.synthesize(
                SpeechRequest(
                    text=pronounceable,
                    voice=self._settings.voice,
                    instructions=self._settings.instructions,
                )
            )
            if isinstance(synthesized, SpeechError):
                return VoiceFailure(
                    _SPEECH_MESSAGES[synthesized.kind],
                    recoverable=synthesized.kind not in _UNRECOVERABLE_SPEECH,
                )

            self._record_speech(synthesized)
        return self._play(synthesized)

    def stop_speaking(self) -> None:
        """Detiene la reproducción y limpia el temporal. Idempotente."""
        self._playback.stop()
        self._discard_spoken_audio()

    def set_muted(self, muted: bool) -> None:
        """Silencia o reactiva la salida hablada. Idempotente."""
        self._playback.set_muted(muted)

    def available_voices(self) -> tuple[str, ...]:
        """Voces entre las que se puede elegir en este proveedor."""
        return self._text_to_speech.available_voices()

    @property
    def voice(self) -> str:
        return self._settings.voice

    def set_voice(self, voice: str) -> None:
        """Cambia la voz. Una que el proveedor no tenga se ignora.

        Elegir una voz inexistente convertiría cada respuesta siguiente en un
        error, y por una lista desplegable no se puede romper la voz entera.
        """
        if voice not in self.available_voices():
            return
        self._settings = replace(self._settings, voice=voice)

    @property
    def is_muted(self) -> bool:
        return self._playback.is_muted

    @property
    def is_speaking(self) -> bool:
        return self._playback.is_playing()

    # --- Interior --------------------------------------------------------

    def _play(self, synthesized: SynthesizedSpeech) -> SpeakOutcome:
        # Una reproducción nueva sustituye a la anterior: nunca dos voces a la
        # vez, y el temporal de la anterior se va con ella.
        self._playback.stop()
        self._discard_spoken_audio()
        self._spoken_audio = synthesized.audio_path

        error = self._playback.play(synthesized.audio_path, self._on_playback_finished)
        if isinstance(error, PlaybackError):
            self._discard_spoken_audio()
            return VoiceFailure(
                "No he podido reproducir la voz, pero la respuesta está en pantalla."
            )
        return SpeechStarted()

    def _on_playback_finished(self) -> None:
        self._discard_spoken_audio()
        if self._speech_finished is not None:
            self._speech_finished()

    def _discard_spoken_audio(self) -> None:
        if self._spoken_audio is None:
            return
        self._capture.discard(self._spoken_audio)
        self._spoken_audio = None

    def _has_budget(self) -> bool:
        """La cortesía previa al micrófono; la admisión es `_reserva`."""
        return self._budget is None or self._budget.has_remaining_budget()

    def _reserva(self, estimado_usd: float) -> AbstractContextManager[object | None]:
        """La admisión de H-30, o paso libre si no hay presupuesto configurado.

        `nullcontext(True)` mantiene la forma: el llamador siempre escribe
        `with self._reserva(est) as admitida:` y pregunta por `None`.
        """
        if self._budget is None:
            return nullcontext(True)
        return self._budget.reserva(estimado_usd)

    def _record_transcription(self, transcription: Transcription) -> None:
        if self._budget is not None:
            self._budget.record_transcription(transcription.audio_seconds)

    def _record_speech(self, synthesized: SynthesizedSpeech) -> None:
        if self._budget is not None:
            self._budget.record_speech(synthesized.character_count)

    def _capture_failure(self, error: AudioCaptureError) -> VoiceFailure:
        return VoiceFailure(
            _CAPTURE_MESSAGES[error.kind],
            recoverable=error.kind is not AudioCaptureErrorKind.PERMISSION,
        )
