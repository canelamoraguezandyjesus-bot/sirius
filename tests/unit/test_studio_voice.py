"""Flujo de voz de Model Studio: escuchar, transcribir, revisar y hablar.

Cubre las pruebas SV de #126 que no exigen hardware ni proveedor real. Todo va
con adaptadores simulados: ni micrófono, ni altavoces, ni red.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.audio.fake import (
    FakeAudioCapture,
    FakeAudioPlayback,
    FakeSpeechToText,
    FakeTextToSpeech,
)
from sirius.adapters.llm.budget import BudgetPolicy, BudgetTracker
from sirius.application.studio_voice import (
    ListeningStarted,
    NothingToSay,
    SpeechStarted,
    StudioVoiceUseCase,
    TranscriptReady,
    VoiceFailure,
    VoiceSettings,
)
from sirius.domain.conversation import MessageStatus
from sirius.ports.audio_capture import AudioCaptureError, AudioCaptureErrorKind
from sirius.ports.audio_playback import PlaybackError, PlaybackErrorKind
from sirius.ports.speech_to_text import TranscriptionError, TranscriptionErrorKind
from sirius.ports.text_to_speech import SpeechError, SpeechErrorKind


@pytest.fixture
def temporary_audio(tmp_path: Path) -> Path:
    directory = tmp_path / "audio"
    directory.mkdir()
    return directory


def _use_case(
    temporary_audio: Path,
    *,
    capture: FakeAudioCapture | None = None,
    speech_to_text: FakeSpeechToText | None = None,
    text_to_speech: FakeTextToSpeech | None = None,
    playback: FakeAudioPlayback | None = None,
    budget: BudgetTracker | None = None,
) -> StudioVoiceUseCase:
    return StudioVoiceUseCase(
        audio_capture=capture or FakeAudioCapture(temporary_audio),
        speech_to_text=speech_to_text or FakeSpeechToText(),
        text_to_speech=text_to_speech or FakeTextToSpeech(temporary_audio),
        audio_playback=playback or FakeAudioPlayback(),
        settings=VoiceSettings(voice="onyx"),
        budget_guard=budget,
    )


# --- SV-002: la captura cubre el intervalo que el usuario ve -------------


def test_listening_opens_and_closes_only_on_explicit_actions(temporary_audio: Path) -> None:
    """Se inicia y se detiene con acciones concretas; no hay escucha permanente."""
    capture = FakeAudioCapture(temporary_audio)
    use_case = _use_case(temporary_audio, capture=capture)

    assert not use_case.is_listening
    assert isinstance(use_case.start_listening(), ListeningStarted)
    assert use_case.is_listening

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, TranscriptReady)
    assert not use_case.is_listening


def test_starting_twice_does_not_open_a_second_capture(temporary_audio: Path) -> None:
    use_case = _use_case(temporary_audio)
    use_case.start_listening()

    second = use_case.start_listening()

    assert isinstance(second, VoiceFailure)
    assert "otra cosa" in second.message


def test_reaching_the_limit_is_reported_without_losing_the_audio(
    temporary_audio: Path,
) -> None:
    """El tope de 60 s cierra la captura sola, pero lo capturado se aprovecha."""
    capture = FakeAudioCapture(temporary_audio, stopped_by_limit=True)
    use_case = _use_case(temporary_audio, capture=capture)
    use_case.start_listening()

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, TranscriptReady)
    assert outcome.stopped_by_limit
    assert outcome.text


# --- SV-003 y SV-004: revisión antes de persistir -----------------------


def test_transcription_comes_back_for_review_and_persists_nothing(
    temporary_audio: Path,
) -> None:
    """El caso de uso devuelve texto; no toca la conversación ni la memoria."""
    use_case = _use_case(temporary_audio, speech_to_text=FakeSpeechToText("enciende el led"))
    use_case.start_listening()

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, TranscriptReady)
    assert outcome.text == "enciende el led"


def test_cancelling_discards_the_capture(temporary_audio: Path) -> None:
    capture = FakeAudioCapture(temporary_audio)
    use_case = _use_case(temporary_audio, capture=capture)
    use_case.start_listening()

    use_case.cancel_listening()

    assert not use_case.is_listening
    assert capture.cancelled == 1
    assert not list(temporary_audio.glob("captura-*.wav"))


def test_cancelling_twice_is_safe(temporary_audio: Path) -> None:
    use_case = _use_case(temporary_audio)
    use_case.start_listening()

    use_case.cancel_listening()
    use_case.cancel_listening()

    assert not use_case.is_listening


def test_silence_is_reported_in_plain_language(temporary_audio: Path) -> None:
    use_case = _use_case(temporary_audio, speech_to_text=FakeSpeechToText("   "))
    use_case.start_listening()

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, VoiceFailure)
    assert outcome.recoverable
    assert "hablar más cerca" in outcome.message


# --- SV-012: no sobreviven temporales -----------------------------------


def test_no_temporary_audio_survives_a_successful_turn(temporary_audio: Path) -> None:
    capture = FakeAudioCapture(temporary_audio)
    use_case = _use_case(temporary_audio, capture=capture)
    use_case.start_listening()

    use_case.stop_and_transcribe()

    assert capture.discarded, "el WAV de la captura no se borró"
    assert not list(temporary_audio.glob("captura-*.wav"))


def test_no_temporary_audio_survives_a_failed_transcription(temporary_audio: Path) -> None:
    """Falle lo que falle, el audio no se queda en el disco."""
    capture = FakeAudioCapture(temporary_audio)
    use_case = _use_case(
        temporary_audio,
        capture=capture,
        speech_to_text=FakeSpeechToText(
            error=TranscriptionError(TranscriptionErrorKind.CONNECTION, "sin red")
        ),
    )
    use_case.start_listening()

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, VoiceFailure)
    assert not list(temporary_audio.glob("captura-*.wav"))


def test_spoken_audio_is_discarded_when_playback_finishes(temporary_audio: Path) -> None:
    playback = FakeAudioPlayback()
    use_case = _use_case(temporary_audio, playback=playback)
    use_case.speak("Hola, dime.", MessageStatus.COMPLETED)

    playback.finish()

    assert not list(temporary_audio.glob("voz-*.wav"))


# --- SV-006 y SV-007: solo se habla lo que se completó -------------------


def test_a_completed_answer_is_spoken_once(temporary_audio: Path) -> None:
    playback = FakeAudioPlayback()
    text_to_speech = FakeTextToSpeech(temporary_audio)
    use_case = _use_case(temporary_audio, text_to_speech=text_to_speech, playback=playback)

    outcome = use_case.speak("Monta el Uno y carga el Blink.", MessageStatus.COMPLETED)

    assert isinstance(outcome, SpeechStarted)
    assert len(text_to_speech.requests) == 1
    assert len(playback.played) == 1
    assert use_case.is_speaking


@pytest.mark.parametrize(
    "status",
    [MessageStatus.CANCELLED, MessageStatus.FAILED, MessageStatus.REDACTED],
)
def test_an_incomplete_answer_is_never_spoken(temporary_audio: Path, status: MessageStatus) -> None:
    """Leer en voz alta un texto a medias lo presentaría como respuesta completa."""
    text_to_speech = FakeTextToSpeech(temporary_audio)
    use_case = _use_case(temporary_audio, text_to_speech=text_to_speech)

    outcome = use_case.speak("Estaba diciendo que", status)

    assert isinstance(outcome, NothingToSay)
    assert text_to_speech.requests == []


def test_an_answer_with_nothing_pronounceable_is_not_an_error(temporary_audio: Path) -> None:
    text_to_speech = FakeTextToSpeech(temporary_audio)
    use_case = _use_case(temporary_audio, text_to_speech=text_to_speech)

    outcome = use_case.speak("```python\nprint('hola')\n```", MessageStatus.COMPLETED)

    assert isinstance(outcome, SpeechStarted | NothingToSay)


def test_the_voice_and_the_tone_are_configuration_not_code(temporary_audio: Path) -> None:
    """La voz se pide, no se presupone: MS-A09 dejó `cedar` sin verificar."""
    text_to_speech = FakeTextToSpeech(temporary_audio)
    use_case = StudioVoiceUseCase(
        audio_capture=FakeAudioCapture(temporary_audio),
        speech_to_text=FakeSpeechToText(),
        text_to_speech=text_to_speech,
        audio_playback=FakeAudioPlayback(),
        settings=VoiceSettings(voice="echo", instructions="tono de prueba"),
    )

    use_case.speak("Hola.", MessageStatus.COMPLETED)

    assert text_to_speech.requests[0].voice == "echo"
    assert text_to_speech.requests[0].instructions == "tono de prueba"


# --- SV-008: detener, repetir y silenciar son idempotentes ---------------


def test_stopping_speech_is_idempotent(temporary_audio: Path) -> None:
    playback = FakeAudioPlayback()
    use_case = _use_case(temporary_audio, playback=playback)
    use_case.speak("Hola.", MessageStatus.COMPLETED)

    use_case.stop_speaking()
    use_case.stop_speaking()

    assert not use_case.is_speaking
    assert not list(temporary_audio.glob("voz-*.wav"))


def test_muting_is_idempotent(temporary_audio: Path) -> None:
    use_case = _use_case(temporary_audio)

    use_case.set_muted(True)
    use_case.set_muted(True)
    assert use_case.is_muted

    use_case.set_muted(False)
    assert not use_case.is_muted


def test_speaking_again_replaces_the_previous_audio(temporary_audio: Path) -> None:
    """Nunca dos voces a la vez, y el temporal anterior se va con ella."""
    playback = FakeAudioPlayback()
    use_case = _use_case(temporary_audio, playback=playback)

    use_case.speak("Primera.", MessageStatus.COMPLETED)
    use_case.speak("Segunda.", MessageStatus.COMPLETED)

    assert playback.stops >= 1
    assert len(list(temporary_audio.glob("voz-*.wav"))) == 1


# --- SV-009 y SV-010: los fallos no rompen nada -------------------------


def test_a_missing_microphone_is_explained_and_recoverable(temporary_audio: Path) -> None:
    capture = FakeAudioCapture(
        temporary_audio,
        start_error=AudioCaptureError(AudioCaptureErrorKind.NO_DEVICE, "sin dispositivo"),
    )
    use_case = _use_case(temporary_audio, capture=capture)

    outcome = use_case.start_listening()

    assert isinstance(outcome, VoiceFailure)
    assert outcome.recoverable
    assert "micrófono" in outcome.message


def test_a_denied_microphone_is_not_presented_as_retryable(temporary_audio: Path) -> None:
    capture = FakeAudioCapture(
        temporary_audio,
        start_error=AudioCaptureError(AudioCaptureErrorKind.PERMISSION, "denegado"),
    )
    use_case = _use_case(temporary_audio, capture=capture)

    outcome = use_case.start_listening()

    assert isinstance(outcome, VoiceFailure)
    assert not outcome.recoverable


def test_a_network_failure_can_be_retried(temporary_audio: Path) -> None:
    use_case = _use_case(
        temporary_audio,
        speech_to_text=FakeSpeechToText(
            error=TranscriptionError(TranscriptionErrorKind.CONNECTION, "sin red")
        ),
    )
    use_case.start_listening()

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, VoiceFailure)
    assert outcome.recoverable


def test_a_bad_key_is_not_presented_as_retryable(temporary_audio: Path) -> None:
    use_case = _use_case(
        temporary_audio,
        speech_to_text=FakeSpeechToText(
            error=TranscriptionError(TranscriptionErrorKind.AUTHENTICATION, "clave")
        ),
    )
    use_case.start_listening()

    outcome = use_case.stop_and_transcribe()

    assert isinstance(outcome, VoiceFailure)
    assert not outcome.recoverable


def test_a_playback_failure_says_the_answer_is_still_on_screen(
    temporary_audio: Path,
) -> None:
    playback = FakeAudioPlayback(error=PlaybackError(PlaybackErrorKind.NO_DEVICE, "sin altavoces"))
    use_case = _use_case(temporary_audio, playback=playback)

    outcome = use_case.speak("Hola.", MessageStatus.COMPLETED)

    assert isinstance(outcome, VoiceFailure)
    assert "en pantalla" in outcome.message
    assert not list(temporary_audio.glob("voz-*.wav"))


def test_a_synthesis_failure_is_explained(temporary_audio: Path) -> None:
    use_case = _use_case(
        temporary_audio,
        text_to_speech=FakeTextToSpeech(
            temporary_audio, error=SpeechError(SpeechErrorKind.RATE_LIMITED, "saturado")
        ),
    )

    outcome = use_case.speak("Hola.", MessageStatus.COMPLETED)

    assert isinstance(outcome, VoiceFailure)
    assert outcome.recoverable


# --- SV-011: el presupuesto bloquea ANTES de llamar ---------------------


def test_an_exhausted_budget_blocks_before_opening_the_microphone(
    temporary_audio: Path,
) -> None:
    """Dejar hablar un minuto para luego decir que no hay saldo es lo peor."""
    tracker = BudgetTracker(BudgetPolicy(monthly_limit_usd=0.0))
    capture = FakeAudioCapture(temporary_audio)
    use_case = _use_case(temporary_audio, capture=capture, budget=tracker)

    outcome = use_case.start_listening()

    assert isinstance(outcome, VoiceFailure)
    assert not outcome.recoverable
    assert not capture.is_capturing()


def test_an_exhausted_budget_blocks_before_synthesizing(temporary_audio: Path) -> None:
    tracker = BudgetTracker(BudgetPolicy(monthly_limit_usd=0.0))
    text_to_speech = FakeTextToSpeech(temporary_audio)
    use_case = _use_case(temporary_audio, text_to_speech=text_to_speech, budget=tracker)

    outcome = use_case.speak("Hola.", MessageStatus.COMPLETED)

    assert isinstance(outcome, VoiceFailure)
    assert text_to_speech.requests == []


def test_voice_spends_from_the_same_monthly_pocket_as_text(temporary_audio: Path) -> None:
    """Un turno de voz mueve el mismo contador que el chat escrito (MS-A04)."""
    tracker = BudgetTracker()
    use_case = _use_case(temporary_audio, budget=tracker)

    use_case.start_listening()
    use_case.stop_and_transcribe()
    spent_after_transcription = tracker.spent_usd
    use_case.speak("Una respuesta cualquiera para sintetizar.", MessageStatus.COMPLETED)

    assert spent_after_transcription > 0.0
    assert tracker.spent_usd > spent_after_transcription


# --- El final de la voz: sin aviso, la interfaz se queda en HABLANDO -----


def test_the_end_of_the_speech_is_announced(temporary_audio: Path) -> None:
    """Empezar a hablar lo sabe quien lo pide; terminar, solo el reproductor.

    Sin este aviso la superficie se queda anunciando «HABLANDO» para siempre,
    aunque haga rato que dejó de sonar.
    """
    playback = FakeAudioPlayback()
    use_case = _use_case(temporary_audio, playback=playback)
    endings: list[None] = []
    use_case.set_speech_finished_callback(lambda: endings.append(None))

    use_case.speak("Hola.", MessageStatus.COMPLETED)
    assert endings == []

    playback.finish()

    assert endings == [None]
    assert not list(temporary_audio.glob("voz-*.wav"))


def test_stopping_on_purpose_does_not_announce_an_ending(temporary_audio: Path) -> None:
    """Quien detiene ya sabe que ha detenido y ajusta su estado él mismo."""
    playback = FakeAudioPlayback()
    use_case = _use_case(temporary_audio, playback=playback)
    endings: list[None] = []
    use_case.set_speech_finished_callback(lambda: endings.append(None))

    use_case.speak("Hola.", MessageStatus.COMPLETED)
    use_case.stop_speaking()

    assert endings == []


def test_without_a_callback_the_ending_still_cleans_the_temporary(temporary_audio: Path) -> None:
    """Avisar es opcional; borrar el temporal, nunca."""
    playback = FakeAudioPlayback()
    use_case = _use_case(temporary_audio, playback=playback)

    use_case.speak("Hola.", MessageStatus.COMPLETED)
    playback.finish()

    assert not list(temporary_audio.glob("voz-*.wav"))
