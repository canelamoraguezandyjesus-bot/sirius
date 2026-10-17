"""El oído de verdad: el micro con sounddevice, Silero y Smart Turn de Pipecat y faster-whisper.

ADR-242. Las bibliotecas son del extra ``voz`` y se importan al cargar el oído, no al
importar este módulo, y todas por ``import_voice_library``: sin el extra, o si una
biblioteca nativa no carga, el módulo se importa igual y lo que se cargue levanta
``VoiceUnavailable`` diciendo qué falta. Ninguna función de aquí importa por su cuenta, y
una prueba lo mira.

Cargar el oído no tumba a Sirius, falle como falle lo de fuera. Una biblioteca nativa no
falla solo con ``ImportError``: con ``OSError`` si carga su DLL con ctypes, y con lo que
quiera su ``__init__``; los modelos de Silero y Smart Turn, con las excepciones de
onnxruntime, y el de oír, con las de tokenizers, que heredan directamente de
``Exception``. Por eso los tres sitios donde se carga algo de fuera (importar, cargar el
modelo de oír y arrancar Silero y Smart Turn) atrapan cualquier ``Exception`` (H-242, y
rondas 3 y 4 de Codex sobre la PR #687).

Todo carga de este ordenador. El modelo de faster-whisper, solo de su carpeta y con
``local_files_only``; los de Silero y Smart Turn, de dentro del paquete de Pipecat. Aquí
no se nombra ninguna función que baje modelos: eso vive solo en la orden de instalar.
"""

from __future__ import annotations

import asyncio
import os
import queue
import sys
import time
from collections.abc import Callable, Coroutine, Sequence
from functools import partial
from pathlib import Path
from typing import Any

from sirius.adapters.audio.voice_libraries import (
    END_OF_TURN,
    SPEECH_TO_TEXT,
    VOICE_ACTIVITY,
    import_voice_library,
)
from sirius.application.addressing import NAME
from sirius.infrastructure.logging import get_logger
from sirius.ports.local_voice import Captured, ListeningEngines, TurnSignal, VoiceUnavailable

_logger = get_logger(__name__)

#: A lo que oyen Silero, Smart Turn y faster-whisper: 16 kHz, mono, 16 bits.
SAMPLE_RATE = 16_000
#: Las muestras de cada trozo del micro: 32 ms, lo que Silero analiza de cada vez.
BLOCK_SAMPLES = 512
#: Lo más que creemos que separa dos horas de PortAudio del mismo bloque: más es una hora
#: sin sentido, y se usa la de cuando llega la llamada.
_PORTAUDIO_MAX_SECONDS = 1.0
#: Si está puesta, Smart Turn escribe en disco el audio de cada turno
#: (``LocalSmartTurnAnalyzerV3._write_audio_to_wav``). Sirius no guarda audio: se quita.
_SMART_TURN_AUDIO_LOG = "PIPECAT_SMART_TURN_LOG_DATA"
#: Los estados de Silero en que hay alguien hablando, como los cuenta Pipecat: desde que
#: confirma que empieza hasta que confirma que ha parado.
_SPEAKING = frozenset({"SPEAKING", "STOPPING"})


def portaudio_seconds(later: Any, earlier: Any) -> float | None:
    """Los segundos de ``earlier`` a ``later``, dos horas que da PortAudio en la llamada de
    un bloque (``currentTime``, ``inputBufferAdcTime``, ``outputBufferDacTime``); ``None``
    si no las da, alguna es cero, que es como dice que no la sabe, o no tienen sentido.

    Con ellas, el micro y el altavoz dicen cuándo se captó y cuándo suena de verdad cada
    bloque, no cuándo atendió Python su llamada, que puede llegar antes o después según el
    sistema: es con lo que la cancelación de eco pone en fila lo que suena y lo captado
    (ronda 1 de Codex sobre la PR #690).
    """
    try:
        later_s, earlier_s = float(later), float(earlier)
    except TypeError, ValueError:
        return None
    if later_s <= 0 or earlier_s <= 0:
        return None
    seconds = later_s - earlier_s
    return seconds if 0 <= seconds < _PORTAUDIO_MAX_SECONDS else None


def check_listening_libraries() -> None:
    """Que las bibliotecas del oído están y cargan; si no, ``VoiceUnavailable``.

    La orden de instalar lo mira antes que el modelo: si falla una biblioteca, bajar el
    modelo otra vez no lo arregla.
    """
    _libraries()
    import_voice_library(SPEECH_TO_TEXT)


def _libraries() -> tuple[Any, Any, Any, Any, Any]:
    """numpy, sounddevice, el registrador de loguru y los módulos de Silero y Smart Turn.

    Pipecat escribe con loguru, que por defecto lo saca todo por la consola, y al importarse
    ya pinta su cartel: loguru se deja en los avisos antes de importar Pipecat (ADR-252).
    """
    numpy = import_voice_library("numpy")
    sounddevice = import_voice_library("sounddevice")
    logger = import_voice_library("loguru").logger
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    return (
        numpy,
        sounddevice,
        logger,
        import_voice_library(VOICE_ACTIVITY),
        import_voice_library(END_OF_TURN),
    )


def load_listening_engines(model_dir: Path) -> ListeningEngines[bytes]:
    """Carga el micro, el detector y el transcriptor de verdad, sin abrir el micro.

    Falla con ``VoiceUnavailable`` si falta un módulo del extra ``voz``, que lo arregla la
    orden de instalar, o si una biblioteca o el modelo de ``model_dir`` están pero no
    cargan o Silero y Smart Turn no arrancan, que no lo arregla.
    """
    numpy, sounddevice, _, silero, smart_turn = _libraries()
    os.environ.pop(_SMART_TURN_AUDIO_LOG, None)
    model = load_listening_model(model_dir)
    try:
        detector = PipecatTurnDetector(
            lambda: silero.SileroVADAnalyzer(sample_rate=SAMPLE_RATE),
            lambda: smart_turn.LocalSmartTurnAnalyzerV3(sample_rate=SAMPLE_RATE),
        )
    except Exception as error:
        msg = f"Silero o Smart Turn no arrancan ({error})"
        raise VoiceUnavailable(msg) from error
    return ListeningEngines(
        microphone=SoundDeviceMicrophone(sounddevice),
        detector=detector,
        transcriber=FasterWhisperTranscriber(model, numpy),
    )


def load_listening_model(model_dir: Path) -> Any:
    """El modelo de faster-whisper de ``model_dir``: solo de ahí y sin bajar nada.

    Falla con ``VoiceUnavailable`` si faster-whisper falta o no carga, o si el modelo no
    carga, falle como falle: un ``tokenizer.json`` roto, por ejemplo, da un ``Exception``
    pelado de tokenizers. Un modelo que está y no carga no se promete arreglarlo con la
    orden de instalar: el constructor de faster-whisper arranca CTranslate2, que falla
    igual con un fichero roto que con un ordenador que no puede cargarlo (sin memoria, un
    motor que no admite), y volver a bajarlo solo arregla lo primero (ronda 5 de Codex
    sobre la PR #687).
    """
    whisper = import_voice_library(SPEECH_TO_TEXT)
    try:
        return whisper.WhisperModel(
            str(model_dir), device="cpu", compute_type="int8", local_files_only=True
        )
    except Exception as error:
        msg = f"el modelo de oír no carga ({error})"
        raise VoiceUnavailable(msg) from error


def _quietly(what: str, step: Callable[[], object]) -> None:
    """Hace ``step`` y, si falla, lo apunta en el diario sin propagarlo."""
    try:
        step()
    except Exception as error:
        _logger.warning("No se ha podido %s: %s", what, error)


class SoundDeviceMicrophone:
    """El micrófono por defecto del sistema, a 16 kHz y en trozos de 512 muestras.

    PortAudio entrega cada trozo desde su hilo, y se guardan en una cola hasta que Sirius
    los lee. Cada apertura es una generación: al cerrar se pasa a la siguiente, y cada
    trozo va a la cola con la suya. Quien decide es ``read``, en el hilo de Sirius: lo que
    sea de una generación pasada lo tira, llegue cuando llegue. Así, cerrado el micro, a
    Sirius no le llega audio aunque el hardware siga encendido o el hilo de PortAudio se
    quede a medias entre mirar la generación y encolar (rondas 3 y 4 de Codex sobre la
    PR #687). Cerrar no falla nunca: lo que PortAudio no puede hacer se apunta.

    Cada trozo va a la cola con la hora a la que acabó de captarse, y ``read`` dice cuánto
    hace: mientras Sirius transcribe o contesta, lo que se capta espera, y el oído tiene que
    saber cuándo sonó (ronda 1 de Codex sobre la PR #689). La hora sale de la del ADC que
    da PortAudio para la primera muestra, más lo que dura el trozo; si no la da, es la de
    cuando llega (ronda 1 de Codex sobre la PR #690).
    """

    def __init__(self, sounddevice: Any, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._sounddevice = sounddevice
        self._clock = clock
        self._stream: Any = None
        self._chunks: queue.SimpleQueue[tuple[int, float, bytes]] = queue.SimpleQueue()
        self._generation = 0

    def open(self) -> None:
        if self._stream is not None:
            return
        self._drain()
        self._generation += 1
        error_type = self._sounddevice.PortAudioError
        try:
            stream = self._sounddevice.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SAMPLES,
                channels=1,
                dtype="int16",
                callback=self._receiver(self._generation),
            )
        except error_type as error:
            raise _no_microphone(error) from error
        try:
            stream.start()
        except error_type as error:
            self._generation += 1
            _quietly("cerrar el micrófono que no arrancó", stream.close)
            raise _no_microphone(error) from error
        self._stream = stream

    def close(self) -> None:
        self._generation += 1
        stream, self._stream = self._stream, None
        if stream is not None:
            _quietly("parar el micrófono", stream.stop)
            _quietly("cerrar el micrófono", stream.close)
        self._drain()

    def read(self) -> Captured[bytes] | None:
        while True:
            try:
                generation, captured_at, chunk = self._chunks.get_nowait()
            except queue.Empty:
                return None
            if generation == self._generation:
                return Captured(chunk, age=self._clock() - captured_at)

    def _receiver(self, generation: int) -> Callable[[Any, int, Any, Any], None]:
        def arrived(data: Any, frames: int, time: Any, status: Any) -> None:
            del status
            now = self._clock()
            since = portaudio_seconds(
                getattr(time, "currentTime", None), getattr(time, "inputBufferAdcTime", None)
            )
            captured_at = now if since is None else min(now, now - since + frames / SAMPLE_RATE)
            # Solo para no llenar la cola con lo que ya no vale: quien decide es `read`.
            if generation == self._generation:
                self._chunks.put((generation, captured_at, bytes(data)))

        return arrived

    def _drain(self) -> None:
        while self.read() is not None:
            pass


def _no_microphone(error: Exception) -> VoiceUnavailable:
    return VoiceUnavailable(f"no puedo abrir el micrófono ({error})")


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
        try:
            self.reset()
        except BaseException:
            # Un detector que no arranca no deja su bucle de eventos abierto.
            self._loop.close()
            raise

    def reset(self) -> None:
        """Silero y Smart Turn nuevos; si no se pueden cargar, falla y deja los que tenía."""
        new: list[Any] = []
        try:
            new.append(self._make_vad())
            new.append(self._make_turn())
            for analyzer in new:
                analyzer.set_sample_rate(SAMPLE_RATE)
        except BaseException:
            self._release(new)
            raise
        old = [self._vad, self._turn]
        self._vad, self._turn = new
        self._speaking = False
        self._release(old)

    def _release(self, analyzers: list[Any]) -> None:
        for analyzer in analyzers:
            if analyzer is not None:
                _quietly("soltar un analizador de Pipecat", partial(self._cleanup, analyzer))

    def _cleanup(self, analyzer: Any) -> None:
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
            audio,
            language="es",
            condition_on_previous_text=False,
            # Una pista para que escriba su nombre como es, y no «Sirio» o «serios»: el oído
            # solo lo reconoce exacto (ADR-252).
            hotwords=NAME,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
