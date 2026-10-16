"""La voz de verdad: Piper, y el altavoz con sounddevice (ADR-243).

Como el oído de la pieza B (ADR-242): las bibliotecas son del extra ``voz``, se importan
al cargar la voz y todas por ``import_voice_library``, y cargarla no tumba a Sirius, falle
como falle lo de fuera. Ninguna función de aquí importa por su cuenta, y una prueba lo
mira.

Todo es de este ordenador. Piper carga la voz solo de su fichero, con su ``.onnx.json`` al
lado, y pasa el texto a fonemas con el espeak-ng que trae dentro: aquí no se nombra
ninguna función que baje voces, eso vive solo en la orden de instalar. Piper apunta en
DEBUG el texto de cada frase que dice: su registrador se deja en WARNING, para que lo
dicho no acabe en ningún diario aunque alguien encienda los de las bibliotecas.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sirius.adapters.audio.echo_cancellation import WebRtcEchoCanceller, load_echo_canceller
from sirius.adapters.audio.voice_libraries import TEXT_TO_SPEECH, import_voice_library
from sirius.infrastructure.logging import get_logger
from sirius.ports.local_voice import SpeakingEngines, VoiceUnavailable

_logger = get_logger(__name__)

#: Lo que sigue sonando en la habitación después de la última muestra. El altavoz no da
#: por acabado lo que dijo hasta que pasa, y el oído no abre el micro hasta entonces: la
#: cola de su propia voz no entra como un turno.
ECHO_TAIL_SECONDS = 0.25
#: Las muestras que se le dan a PortAudio de cada vez: 23 ms a 22 050 Hz. Fijas, para saber
#: cuánto puede esperar una frase al siguiente bloque (ronda 1 de Codex sobre la PR #688).
BLOCK_FRAMES = 512


def check_speaking_libraries() -> None:
    """Que las bibliotecas de la voz están y cargan; si no, ``VoiceUnavailable``."""
    _libraries()


def _libraries() -> tuple[Any, Any]:
    """Piper y sounddevice."""
    return import_voice_library(TEXT_TO_SPEECH), import_voice_library("sounddevice")


def load_speaking_engines(model: Path) -> SpeakingEngines[bytes]:
    """Carga la voz de Piper de ``model``, abre el altavoz a su frecuencia y, si se puede,
    la cancelación de eco, a la que el altavoz le da lo que suena (pieza E, ADR-245).

    Falla con ``VoiceUnavailable`` si falta Piper o sounddevice, si la voz está pero no
    carga o si el altavoz no se puede abrir. Sin cancelación de eco no falla: habla igual,
    con el micro cerrado mientras habla, como en la pieza C.
    """
    _piper, sounddevice = _libraries()
    logging.getLogger(TEXT_TO_SPEECH).setLevel(logging.WARNING)
    voice = load_speaking_voice(model)
    rate = voice.config.sample_rate
    echo = load_echo_canceller(rate)
    return SpeakingEngines(
        voice=PiperSpeech(voice),
        speaker=SoundDeviceSpeaker(sounddevice, rate, echo=echo),
        echo_canceller=echo,
    )


def load_speaking_voice(model: Path) -> Any:
    """La voz de Piper de ``model``: solo de ahí, con su ``.onnx.json`` al lado, sin bajar
    nada.

    Falla con ``VoiceUnavailable`` si Piper falta o no carga, o si la voz no carga, falle
    como falle: un modelo roto da un error de onnxruntime, que hereda de ``Exception``, y
    una configuración rota, uno de json. Como con el modelo de oír, no se promete que
    volver a bajarla lo arregle (ronda 5 de Codex sobre la PR #687).
    """
    piper = import_voice_library(TEXT_TO_SPEECH)
    try:
        return piper.PiperVoice.load(model)
    except Exception as error:
        msg = f"la voz no carga ({error})"
        raise VoiceUnavailable(msg) from error


class PiperSpeech:
    """Piper con la voz ya cargada: cada frase, en muestras de 16 bits a su frecuencia."""

    def __init__(self, voice: Any) -> None:
        self._voice = voice

    def say(self, text: str) -> bytes:
        return b"".join(chunk.audio_int16_bytes for chunk in self._voice.synthesize(text))


class SoundDeviceSpeaker:
    """El altavoz por defecto del sistema, mono, en 16 bits y a la frecuencia de la voz.

    El flujo se abre al cargar la voz y sigue abierto: abrirlo para cada frase añadiría su
    latencia a cada una. PortAudio pide audio desde su hilo, de bloque en bloque, y se le
    da lo que espera en la cola o, si no hay nada, silencio. Lo dicho sigue sonando
    mientras queda algo en la cola o lo último que se le dio no ha acabado de salir, con la
    latencia del flujo y la cola del eco en la habitación. Callar tira la cola, pero lo que
    PortAudio ya tiene sale igual: hasta que acaba, sigue sonando (ronda 1 de Codex sobre
    la PR #688).

    Cuenta los sonidos que han empezado a salir (``started``): uno empieza cuando PortAudio
    se lleva su primera muestra, y lo que callar tira de la cola no llega a empezar
    (pieza E, ADR-245). Con cancelación de eco, le da cada bloque que sale, silencio
    incluido, con la hora a la que se oye.
    """

    def __init__(
        self,
        sounddevice: Any,
        sample_rate: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        echo: WebRtcEchoCanceller | None = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._clock = clock
        self._echo = echo
        self._lock = threading.Lock()
        self._pending = bytearray()
        self._until = 0.0
        #: Bytes que se le han dado y que PortAudio se ha llevado, desde que se abrió.
        self._given = 0
        self._taken = 0
        #: Dónde empieza, en lo dado, cada sonido que aún no ha empezado a salir.
        self._waiting: deque[int] = deque()
        self._started = 0
        try:
            stream = sounddevice.RawOutputStream(
                samplerate=sample_rate,
                blocksize=BLOCK_FRAMES,
                channels=1,
                dtype="int16",
                callback=self._fill,
            )
        except Exception as error:
            raise _no_speaker(error) from error
        self._latency = float(stream.latency)
        try:
            stream.start()
        except Exception as error:
            _quietly_close(stream)
            raise _no_speaker(error) from error
        self._stream = stream

    def play(self, sound: bytes) -> None:
        with self._lock:
            self._waiting.append(self._given)
            self._given += len(sound)
            self._pending.extend(sound)

    @property
    def playing(self) -> bool:
        with self._lock:
            return bool(self._pending) or self._clock() < self._until

    @property
    def latency(self) -> float:
        """A lo sumo: lo que puede esperar al siguiente bloque y lo que tarda en salir."""
        return BLOCK_FRAMES / self._sample_rate + self._latency

    def stop(self) -> None:
        with self._lock:
            self._pending.clear()
            # Lo que esperaba y se tira no llega a empezar.
            self._given = self._taken
            self._waiting.clear()

    @property
    def started(self) -> int:
        with self._lock:
            return self._started

    def _fill(self, outdata: Any, frames: int, time: Any, status: Any) -> None:
        """Lo llama PortAudio desde su hilo: lo siguiente de la cola y, si falta, silencio."""
        del time, status
        size = len(outdata)
        with self._lock:
            sound = bytes(self._pending[:size])
            del self._pending[:size]
            self._taken += len(sound)
            while self._waiting and self._waiting[0] < self._taken:
                self._waiting.popleft()
                self._started += 1
            if sound:
                self._until = (
                    self._clock() + self._latency + frames / self._sample_rate + ECHO_TAIL_SECONDS
                )
        block = sound + bytes(size - len(sound))
        outdata[:] = block
        if self._echo is not None:
            self._echo.played(block, at=self._clock() + self._latency)


def _no_speaker(error: Exception) -> VoiceUnavailable:
    return VoiceUnavailable(f"no puedo abrir el altavoz ({error})")


def _quietly_close(stream: Any) -> None:
    """Cierra el flujo que no arrancó; si tampoco se deja, lo apunta en el diario."""
    try:
        stream.close()
    except Exception as error:
        _logger.warning("No se ha podido cerrar el altavoz que no arrancó: %s", error)
