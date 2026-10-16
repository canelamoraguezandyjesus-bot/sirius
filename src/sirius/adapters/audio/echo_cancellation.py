"""La cancelación de eco de verdad: la APM de WebRTC que trae ``livekit`` (pieza E, ADR-245).

Como el oído y la voz (ADR-242, ADR-243): la biblioteca es del extra ``voz`` y se importa
al cargar la voz, por ``import_voice_library``. Si no está o no carga, no hay cancelador, y
el oído cierra el micro mientras habla, como en la pieza C: no se le puede cortar, pero
oye y habla igual. Aquí solo se crea la APM: no se abre ninguna sala ni ninguna conexión.

La APM pide tramas de 10 ms, lo que suena (``process_reverse_stream``) y lo captado
(``process_stream``), intercaladas como pasaron. El oído lee el micro tarde, mientras
transcribe o contesta, así que no se le dan en el momento: el altavoz apunta lo que suena
con la hora a la que se oye (``played``), y al limpiar cada trozo, con la hora a la que se
captó (``clean``), se le da antes todo lo que sonó hasta entonces. Así quedan intercaladas
en orden aunque se procesen tarde.

El altavoz suena siempre, silencio incluido, y con el micro cerrado nadie limpia: de lo que
suena se guardan los últimos ``RENDER_KEPT_SECONDS``, y lo que acabó de sonar más de
``ECHO_REACH_SECONDS`` antes de lo captado se tira sin dárselo a la APM. Si no, tras una
hora callado, el primer trozo esperaría a que la APM tragara la hora entera.
"""

from __future__ import annotations

import threading
import time
from array import array
from collections import deque
from collections.abc import Callable
from typing import Any

from sirius.adapters.audio.local_listening import BLOCK_SAMPLES, SAMPLE_RATE
from sirius.adapters.audio.voice_libraries import ECHO_CANCELLATION, import_voice_library
from sirius.infrastructure.logging import get_logger
from sirius.ports.local_voice import Captured, Cleaned, VoiceUnavailable

_logger = get_logger(__name__)

#: Las muestras de cada trama que pide la APM: 10 ms a la frecuencia del micro.
FRAME_SAMPLES = SAMPLE_RATE // 100
#: Lo que la voz de Sirius sigue en la habitación después de su última muestra: hasta
#: entonces, lo que capta el micro aún lleva su eco.
ECHO_TAIL_SECONDS = 0.25
#: Lo que se guarda de lo que suena hasta que el oído limpie lo que el micro captó a la
#: vez: lo que puede tardar en leerlo, mientras transcribe o la charla piensa, con holgura.
RENDER_KEPT_SECONDS = 120.0
#: Hasta dónde llega el eco de lo que suena: lo que acabó de sonar antes no hace falta para
#: limpiar lo captado después.
ECHO_REACH_SECONDS = 1.0
#: Por encima de esto, en valor absoluto, una muestra de lo que suena no es silencio.
_SILENCE = 64
#: Lo que se le dice a la APM que tarda el eco en llegar al micro, más allá de lo que ya
#: alinean las horas: lo que tarda el micro en dar lo captado. Su estimador de retraso
#: afina el resto.
_STREAM_DELAY_MS = 30


def load_echo_canceller(render_rate: int) -> WebRtcEchoCanceller | None:
    """La APM de WebRTC con la cancelación de eco puesta, para lo que suena a
    ``render_rate``; ``None`` si ``livekit`` no está o no carga, falle como falle."""
    try:
        rtc = import_voice_library(ECHO_CANCELLATION)
        apm = rtc.AudioProcessingModule(echo_cancellation=True, high_pass_filter=True)
    except VoiceUnavailable as error:
        _logger.info("Sin cancelación de eco: %s", error.reason)
        return None
    except Exception as error:
        _logger.info("Sin cancelación de eco: la APM no arranca (%s)", type(error).__name__)
        return None
    return WebRtcEchoCanceller(apm, rtc.AudioFrame, render_rate=render_rate)


class WebRtcEchoCanceller:
    """Aparta de lo que capta el micro lo que vuelve del altavoz, con la APM de WebRTC.

    ``played`` lo llama el altavoz desde el hilo de PortAudio, con cada bloque que le da y
    la hora a la que se oye; ``clean``, el oído, con cada trozo del micro, en orden. Lo que
    suena se pasa a la frecuencia del micro antes de dárselo a la APM. Lo limpio sale con
    10 ms de retraso como mucho: lo que sobra de una trama espera a la siguiente, y la
    salida empieza con una trama de silencio para que cada trozo salga entero.
    """

    def __init__(
        self,
        apm: Any,
        frame: Callable[..., Any],
        *,
        render_rate: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._apm = apm
        self._frame = frame
        self._render_rate = render_rate
        self._clock = clock
        self._lock = threading.Lock()
        #: Lo que ha sonado y aún no se le ha dado a la APM: (hora a la que se oye, bloque).
        self._played: deque[tuple[float, bytes]] = deque()
        self._resampler = _Resampler(render_rate, SAMPLE_RATE)
        #: Lo que sonó, ya a la frecuencia del micro, a la espera de completar una trama.
        self._render = bytearray()
        #: Lo captado a la espera de completar una trama, y lo limpio que aún no ha salido.
        self._capture = bytearray()
        self._clean = bytearray(FRAME_SAMPLES * 2)
        #: Hasta cuándo se oye lo último que sonó con voz.
        self._sounding_until = float("-inf")

    def played(self, block: bytes, at: float) -> None:
        """El altavoz da ``block`` a PortAudio, y se oirá a la hora ``at``. No espera, y de
        lo que nadie ha limpiado guarda solo lo de los últimos ``RENDER_KEPT_SECONDS``."""
        with self._lock:
            self._played.append((at, block))
            while self._played[0][0] < at - RENDER_KEPT_SECONDS:
                self._played.popleft()

    def clean(self, captured: Captured[bytes]) -> Cleaned[bytes]:
        captured_at = self._clock() - captured.age
        self._feed_render(until=captured_at)
        echoing = captured_at < self._sounding_until + ECHO_TAIL_SECONDS
        self._apm.set_stream_delay_ms(_STREAM_DELAY_MS)
        self._capture.extend(captured.chunk)
        size = FRAME_SAMPLES * 2
        while len(self._capture) >= size:
            frame = self._frame(bytearray(self._capture[:size]), SAMPLE_RATE, 1, FRAME_SAMPLES)
            del self._capture[:size]
            self._apm.process_stream(frame)
            self._clean.extend(bytes(frame.data))
        out = len(captured.chunk)
        chunk = bytes(self._clean[:out])
        del self._clean[:out]
        return Cleaned(chunk, echoing=echoing)

    def _feed_render(self, until: float) -> None:
        """Le da a la APM lo que sonó hasta ``until``, a la frecuencia del micro y en
        tramas de 10 ms, menos lo que acabó de sonar mucho antes, cuyo eco ya no llega."""
        with self._lock:
            ready = []
            while self._played and self._played[0][0] <= until:
                ready.append(self._played.popleft())
        size = FRAME_SAMPLES * 2
        for at, block in ready:
            seconds = len(block) / 2 / self._render_rate
            if at + seconds < until - ECHO_REACH_SECONDS:
                continue
            if _has_sound(block):
                self._sounding_until = max(self._sounding_until, at + seconds)
            self._render.extend(self._resampler.push(block))
            while len(self._render) >= size:
                frame = self._frame(bytearray(self._render[:size]), SAMPLE_RATE, 1, FRAME_SAMPLES)
                del self._render[:size]
                self._apm.process_reverse_stream(frame)


def _has_sound(block: bytes) -> bool:
    """Si ``block``, muestras de 16 bits, lleva algo más que silencio."""
    samples = memoryview(block).cast("h")
    return any(abs(sample) > _SILENCE for sample in samples)


class _Resampler:
    """Pasa lo que suena, muestras de 16 bits a ``rate``, a ``target``, por interpolación
    lineal y sin cortes entre bloques: guarda dónde cae la siguiente muestra y lo que hace
    falta del bloque anterior para calcularla. Sin numpy, que Quality no instala: son unas
    pocas centenas de muestras por bloque."""

    def __init__(self, rate: int, target: int) -> None:
        self._step = rate / target
        self._same = rate == target
        #: Dónde cae la siguiente muestra de salida, en muestras de ``_pending``.
        self._position = 0.0
        self._pending: list[int] = []

    def push(self, block: bytes) -> bytes:
        if self._same:
            return block
        pending = self._pending + list(memoryview(block).cast("h"))
        last = len(pending) - 1
        out = array("h")
        position = self._position
        while position <= last:
            index = int(position)
            fraction = position - index
            if index < last:
                value = pending[index] + (pending[index + 1] - pending[index]) * fraction
            elif fraction == 0:
                value = pending[index]
            else:
                break
            out.append(round(value))
            position += self._step
        keep = max(0, min(int(position), last))
        self._pending = pending[keep:]
        self._position = position - keep
        return out.tobytes()


__all__ = [
    "BLOCK_SAMPLES",
    "ECHO_REACH_SECONDS",
    "FRAME_SAMPLES",
    "RENDER_KEPT_SECONDS",
    "WebRtcEchoCanceller",
    "load_echo_canceller",
]
