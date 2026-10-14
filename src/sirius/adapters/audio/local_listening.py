"""El oído de verdad: el micro con sounddevice, Silero y Smart Turn de Pipecat y faster-whisper.

ADR-242. Las bibliotecas son del extra ``voz`` y se importan al cargar el oído, no al
importar este módulo: sin el extra instalado, el módulo se importa igual y
``load_listening_engines`` levanta ``VoiceUnavailable`` diciendo qué falta.

Todo carga de este ordenador. El modelo de faster-whisper, solo de su carpeta y con
``local_files_only``; los de Silero y Smart Turn, de dentro del paquete de Pipecat. Aquí
no se nombra ninguna función que baje modelos: eso vive solo en la orden de instalar.
"""

from __future__ import annotations

import asyncio
import os
import queue
import sys
from collections.abc import Callable, Coroutine, Sequence
from pathlib import Path
from typing import Any

from sirius.ports.local_voice import ListeningEngines, TurnSignal, VoiceUnavailable

#: A lo que oyen Silero, Smart Turn y faster-whisper: 16 kHz, mono, 16 bits.
SAMPLE_RATE = 16_000
#: Las muestras de cada trozo del micro: 32 ms, lo que Silero analiza de cada vez.
BLOCK_SAMPLES = 512
#: Si está puesta, Smart Turn escribe en disco el audio de cada turno
#: (``LocalSmartTurnAnalyzerV3._write_audio_to_wav``). Sirius no guarda audio: se quita.
_SMART_TURN_AUDIO_LOG = "PIPECAT_SMART_TURN_LOG_DATA"
#: Los estados de Silero en que hay alguien hablando, como los cuenta Pipecat: desde que
#: confirma que empieza hasta que confirma que ha parado.
_SPEAKING = frozenset({"SPEAKING", "STOPPING"})


def load_listening_engines(model_dir: Path) -> ListeningEngines[bytes]:
    """Carga el micro, el detector y el transcriptor de verdad, sin abrir el micro.

    Falla con ``VoiceUnavailable`` si falta una biblioteca del extra ``voz`` o si el
    modelo de ``model_dir`` no carga; las dos cosas las arregla la orden de instalar.
    """
    try:
        import numpy
        import sounddevice
        from faster_whisper import WhisperModel
        from loguru import logger
        from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
        from pipecat.audio.vad.silero import SileroVADAnalyzer
    except ImportError as error:
        name = error.name or "una biblioteca de la voz"
        raise VoiceUnavailable(f"falta {name}", fixed_by_install=True) from error
    except OSError as error:
        # sounddevice levanta OSError, no ImportError, si no encuentra PortAudio.
        msg = f"una biblioteca de la voz no carga ({error})"
        raise VoiceUnavailable(msg, fixed_by_install=True) from error
    # Pipecat escribe con loguru, que por defecto lo saca todo por la consola.
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    os.environ.pop(_SMART_TURN_AUDIO_LOG, None)
    try:
        model = WhisperModel(
            str(model_dir), device="cpu", compute_type="int8", local_files_only=True
        )
        detector = PipecatTurnDetector(
            lambda: SileroVADAnalyzer(sample_rate=SAMPLE_RATE),
            lambda: LocalSmartTurnAnalyzerV3(sample_rate=SAMPLE_RATE),
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise VoiceUnavailable(f"el oído no carga ({error})", fixed_by_install=True) from error
    return ListeningEngines(
        microphone=SoundDeviceMicrophone(sounddevice),
        detector=detector,
        transcriber=FasterWhisperTranscriber(model, numpy),
    )


class SoundDeviceMicrophone:
    """El micrófono por defecto del sistema, a 16 kHz y en trozos de 512 muestras.

    PortAudio llama a ``_arrived`` desde su hilo con cada trozo; se guardan en una cola
    hasta que Sirius los lee, y al cerrar se tiran los que nadie ha leído.
    """

    def __init__(self, sounddevice: Any) -> None:
        self._sounddevice = sounddevice
        self._stream: Any = None
        self._chunks: queue.SimpleQueue[bytes] = queue.SimpleQueue()

    def open(self) -> None:
        if self._stream is not None:
            return
        try:
            stream = self._sounddevice.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SAMPLES,
                channels=1,
                dtype="int16",
                callback=self._arrived,
            )
            stream.start()
        except self._sounddevice.PortAudioError as error:
            raise VoiceUnavailable(
                f"no puedo abrir el micrófono ({error})", fixed_by_install=False
            ) from error
        self._stream = stream

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        while self.read() is not None:
            pass

    def read(self) -> bytes | None:
        try:
            return self._chunks.get_nowait()
        except queue.Empty:
            return None

    def _arrived(self, data: Any, frames: int, time: Any, status: Any) -> None:
        del frames, time, status
        self._chunks.put(bytes(data))


class PipecatTurnDetector:
    """Silero dice si hay voz y Smart Turn v3 si el turno ha acabado, como en Pipecat.

    Se encadenan como en su estrategia de fin de turno
    (``pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy``): cada trozo pasa
    por Silero y después por Smart Turn, con si hay alguien hablando; cuando Silero deja
    de oír voz, Smart Turn mira el turno entero, y si no lo da por acabado lo acaba el
    silencio largo (``stop_secs``, 3 s). Los dos analizadores son asíncronos: se les
    espera en un bucle de eventos propio.

    Los dos llevan dentro el turno que oyen, y Pipecat no da forma de vaciarlos sin
    tocar sus tripas: reiniciar es cargarlos otra vez con ``make_vad`` y ``make_turn``,
    en unas décimas de segundo, y soltar los viejos.
    """

    def __init__(self, make_vad: Callable[[], Any], make_turn: Callable[[], Any]) -> None:
        self._make_vad = make_vad
        self._make_turn = make_turn
        self._loop = asyncio.new_event_loop()
        self._vad: Any = None
        self._turn: Any = None
        self._speaking = False
        self.reset()

    def reset(self) -> None:
        old = (self._vad, self._turn)
        self._vad = self._make_vad()
        self._turn = self._make_turn()
        self._vad.set_sample_rate(SAMPLE_RATE)
        self._turn.set_sample_rate(SAMPLE_RATE)
        self._speaking = False
        for analyzer in old:
            if analyzer is not None:
                self._wait(analyzer.cleanup())

    def listen(self, chunk: bytes) -> TurnSignal:
        state = self._wait(self._vad.analyze_audio(chunk))
        speaking = state.name in _SPEAKING
        started = speaking and not self._speaking
        stopped = self._speaking and not speaking
        self._speaking = speaking
        if started:
            self._turn.update_vad_start_secs(self._vad.params.start_secs)
        if self._turn.append_audio(chunk, speaking).name == "COMPLETE":
            return TurnSignal.ENDED
        if stopped:
            ended, _metrics = self._wait(self._turn.analyze_end_of_turn())
            if ended.name == "COMPLETE":
                return TurnSignal.ENDED
        return TurnSignal.VOICE if speaking else TurnSignal.QUIET

    def _wait(self, step: Coroutine[Any, Any, Any]) -> Any:
        return self._loop.run_until_complete(step)


class FasterWhisperTranscriber:
    """faster-whisper en español, con el modelo ya cargado."""

    def __init__(self, model: Any, numpy: Any) -> None:
        self._model = model
        self._numpy = numpy

    def transcribe(self, chunks: Sequence[bytes]) -> str:
        np = self._numpy
        samples = np.frombuffer(b"".join(chunks), dtype=np.int16)
        audio = samples.astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(
            audio, language="es", condition_on_previous_text=False
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
