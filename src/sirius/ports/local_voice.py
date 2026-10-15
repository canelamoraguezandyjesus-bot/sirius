"""Puertos del oído y de la voz locales del robot (piezas B y C de ADR-241; ADR-242, ADR-243).

El micro, el detector de turno y el transcriptor, y la voz y el altavoz, sin tipos de
ninguna biblioteca: los de verdad (``sounddevice``, Silero y Smart Turn de Pipecat,
faster-whisper y Piper) viven en ``sirius.adapters.audio`` y se cargan solo si están
instalados, y las pruebas ponen dobles. Lo que pasa de uno a otro es audio que Sirius no
abre: un trozo, que solo saben leer el micro que lo dio, el detector y el transcriptor;
o un sonido, que solo saben leer la voz que lo hizo y el altavoz.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class TurnSignal(Enum):
    """Lo que dice el detector de cada trozo que le enseñan."""

    #: No hay voz en este trozo.
    QUIET = "quiet"
    #: Hay voz: el turno empieza o sigue.
    VOICE = "voice"
    #: Con este trozo, el turno ha acabado.
    ENDED = "ended"


class VoiceUnavailable(RuntimeError):
    """El oído o la voz no pueden arrancar en este ordenador: algo que está no carga o no
    se abre.

    No dice si lo arregla la orden de instalar, y a propósito: adivinarlo salió mal seis
    veces (rondas 2, 4, 5, 6, 7 y 8 de Codex sobre la PR #687). Quien avisa aconseja la
    orden para lo que ella toca y dice lo que hace, que es siempre lo mismo.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Captured[Chunk]:
    """Un trozo del micro y cuánto llevaba esperando a que lo leyeran (ADR-244).

    El micro capta sin parar, y lo captado espera en su cola mientras el oído transcribe o
    contesta. Con ``age``, en segundos, el oído sabe cuándo sonó de verdad y no cuándo lo
    leyó: no hace falta que los dos lleven el mismo reloj. Cero, si se lee en el acto.
    """

    chunk: Chunk
    age: float = 0.0


class Microphone[Chunk](Protocol):
    """El micrófono, trozo a trozo."""

    def open(self) -> None:
        """Empieza a captar. Falla con ``VoiceUnavailable`` si no hay micrófono."""
        ...

    def close(self) -> None:
        """Deja de dar audio a Sirius y tira lo captado que nadie ha leído.

        No falla: pase lo que pase con el hardware, después de cerrar no llega ningún
        trozo más, y lo que no se haya podido cerrar se apunta en el diario.
        """
        ...

    def read(self) -> Captured[Chunk] | None:
        """El siguiente trozo captado, con cuánto llevaba esperando, o ``None`` si no ha
        llegado ninguno. No espera."""
        ...


class TurnDetector[Chunk](Protocol):
    """Silero y Smart Turn: si hay voz y si el turno ha acabado.

    Hay que enseñarle cada trozo, en orden y una sola vez: lleva la cuenta de los
    silencios y de la voz del turno.
    """

    def listen(self, chunk: Chunk) -> TurnSignal: ...

    def reset(self) -> None:
        """Olvida el turno que llevaba: lo siguiente que oiga empieza de cero.

        Si no puede, falla y se queda como estaba.
        """
        ...


class Transcriber[Chunk](Protocol):
    """faster-whisper: lo dicho en los trozos de un turno, en texto."""

    def transcribe(self, chunks: Sequence[Chunk]) -> str: ...


@dataclass(frozen=True, slots=True)
class ListeningEngines[Chunk]:
    """Las tres piezas del oído, ya cargadas."""

    microphone: Microphone[Chunk]
    detector: TurnDetector[Chunk]
    transcriber: Transcriber[Chunk]


class Voice[Sound](Protocol):
    """Piper, con la voz que dicen los ajustes: una frase en sonido."""

    def say(self, text: str) -> Sound:
        """El sonido de ``text`` dicho con esta voz."""
        ...


class Speaker[Sound](Protocol):
    """El altavoz: suena lo que le dan, en orden, y dice si aún suena."""

    def play(self, sound: Sound) -> None:
        """Lo pone a sonar detrás de lo que ya suene, y vuelve sin esperar a que acabe."""
        ...

    @property
    def playing(self) -> bool:
        """Si aún suena algo de lo que le dieron, lo que espera en cola incluido."""
        ...

    @property
    def latency(self) -> float:
        """Cuánto tarda en sonar, como mucho, lo que se le da cuando no suena nada, en
        segundos."""
        ...

    def stop(self) -> None:
        """Tira lo que esperaba y no da nada más. Lo que ya estaba saliendo acaba en lo que
        tarda en sonar, y hasta entonces sigue sonando (``playing``). No falla."""
        ...


@dataclass(frozen=True, slots=True)
class SpeakingEngines[Sound]:
    """La voz y el altavoz, ya cargados."""

    voice: Voice[Sound]
    speaker: Speaker[Sound]


class VoiceInstallation(Protocol):
    """Lo instalado en este ordenador para oír y hablar, y la orden que lo instala."""

    @property
    def install_command(self) -> str:
        """La orden que el propietario ejecuta para instalar la voz."""
        ...

    def missing(self) -> tuple[str, ...]:
        """Lo que falta para oír y hablar, dicho para el propietario; vacío si no falta nada."""
        ...
