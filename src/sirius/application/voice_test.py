"""Caso de uso de la prueba de voces: elegir su voz a ciegas (pieza F de ADR-241, ADR-246).

Carga cada voz del catálogo, le pide las cinco frases, prepara la hoja barajada y sin
nombres, pone por el altavoz la muestra que él quiera escuchar y, cuando elige, deja esa
voz para hablar desde el turno siguiente. Elegir no pasa nunca sin él: ``choose`` solo lo
llama la ventana cuando el propietario pulsa.

Las muestras viven en la hoja, en memoria: no se escribe ningún audio (PA-R03-05). Y
mientras suena una muestra el micro está cerrado, para que Sirius no la tome por algo que
le dicen: lo cierra ``listen``, que es por donde pasa toda muestra que suena.
"""

from __future__ import annotations

import random
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sirius.config.local_voice import SpeakingVoice
from sirius.domain.voice_test import (
    VOICE_TEST_PHRASES,
    VoiceTestError,
    VoiceTestSheet,
    prepare_voice_test,
)
from sirius.ports.local_voice import SpeakingEngines, VoiceUnavailable

__all__ = ["VoiceTestUseCase", "VoiceTestView"]

#: Lo que explica la hoja, arriba: sin el nombre de ninguna voz ni de quién la hace.
VOICE_TEST_INTRO = (
    "Escucha cada frase con cada voz, por tu altavoz, sin saber cuál es cuál. Elige la "
    "que más te suene a Sirius."
)
#: Lo que dice el botón de elegir cada voz.
CHOOSE_CAPTION = "Elegir la {label}"


@dataclass(frozen=True, slots=True)
class VoiceTestView:
    """Lo que se ve en la hoja, en orden: la explicación, cada frase con un botón por voz
    para escucharla, y un botón por voz para elegirla. La ventana lo pinta tal cual."""

    intro: str
    rows: tuple[tuple[str, tuple[str, ...]], ...]
    choices: tuple[tuple[str, str], ...]

    def lines(self) -> tuple[str, ...]:
        """Todo el texto de la hoja, botones incluidos, línea a línea."""
        lines = [self.intro]
        for phrase, buttons in self.rows:
            lines.append(phrase)
            lines.extend(buttons)
        lines.extend(caption for _label, caption in self.choices)
        return tuple(lines)


class VoiceTestUseCase:
    """Prepara la hoja de voces, pone sus muestras y deja la voz elegida para hablar."""

    def __init__(
        self,
        *,
        load_voice: Callable[[SpeakingVoice], SpeakingEngines[Any]],
        choose_voice: Callable[[SpeakingVoice], None],
        missing: Callable[[], tuple[str, ...]],
        pause_listening: Callable[[], None],
        rng: random.Random | None = None,
    ) -> None:
        """``load_voice`` carga una voz con su altavoz; ``choose_voice`` la guarda en los
        ajustes y se la da al oído; ``missing`` dice qué voces faltan en este ordenador,
        con la orden que las instala; ``pause_listening`` cierra el micro."""
        self._load_voice = load_voice
        self._choose_voice = choose_voice
        self._missing = missing
        self._pause_listening = pause_listening
        self._rng = rng or random.Random()
        #: Las voces cargadas para la hoja, hasta ``close``; las toca el hilo que prepara la
        #: hoja y el de la ventana, con el cerrojo.
        self._lock = threading.Lock()
        self._engines: dict[SpeakingVoice, SpeakingEngines[Any]] = {}
        #: Cuántas veces se ha cerrado: lo que cargue una hoja cerrada a medias no se queda.
        self._closings = 0

    def phrases(self) -> tuple[str, ...]:
        return VOICE_TEST_PHRASES

    def voices(self) -> tuple[SpeakingVoice, ...]:
        """Las candidatas: todas las del catálogo, en su orden."""
        return tuple(SpeakingVoice)

    def missing(self) -> tuple[str, ...]:
        """Lo que falta instalar para la prueba, dicho para él; vacío si no falta nada."""
        return self._missing()

    def prepare(
        self,
        *,
        on_progress: Callable[[int, int], None] | None = None,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> VoiceTestSheet[SpeakingVoice, Any]:
        """Pide a cada voz las cinco frases y baraja las voces.

        Cada voz se carga la primera vez y queda cargada hasta ``close``. ``should_stop``
        se mira antes de cada frase: si él cierra la hoja a medias, no se piden más.
        """
        missing = self.missing()
        if missing:
            raise VoiceTestError(" ".join(missing))
        with self._lock:
            closings = self._closings
        phrases = self.phrases()
        voices = self.voices()
        total = len(voices) * len(phrases)
        done = 0
        samples: dict[SpeakingVoice, dict[str, Any]] = {}
        for voice in voices:
            engines = self._engines_of(voice, closings)
            samples[voice] = {}
            for phrase in phrases:
                if should_stop():
                    msg = "La prueba de voces se canceló."
                    raise VoiceTestError(msg)
                samples[voice][phrase] = engines.voice.say(phrase)
                done += 1
                if on_progress is not None:
                    on_progress(done, total)
        return prepare_voice_test(phrases, samples, self._rng)

    def view(self, sheet: VoiceTestSheet[SpeakingVoice, Any]) -> VoiceTestView:
        """Lo que se ve de la hoja: etiquetas y frases, ningún nombre de voz."""
        labels = tuple(candidate.label for candidate in sheet.candidates)
        return VoiceTestView(
            intro=VOICE_TEST_INTRO,
            rows=tuple((phrase, labels) for phrase in sheet.phrases),
            choices=tuple((label, CHOOSE_CAPTION.format(label=label)) for label in labels),
        )

    def listen(self, sheet: VoiceTestSheet[SpeakingVoice, Any], label: str, phrase: str) -> None:
        """Pone por el altavoz la muestra de ``phrase`` con la voz de ``label``.

        Antes cierra el micro, y calla la muestra que sonara: suena una cada vez.
        """
        voice = sheet.voice_behind(label)
        sample = sheet.sample(label, phrase)
        with self._lock:
            engines = self._engines.get(voice)
            loaded = tuple(self._engines.values())
        if engines is None:
            msg = "La hoja ya está cerrada."
            raise VoiceTestError(msg)
        self._pause_listening()
        for other in loaded:
            other.speaker.stop()
        engines.speaker.play(sample)

    def choose(self, sheet: VoiceTestSheet[SpeakingVoice, Any], label: str) -> SpeakingVoice:
        """Deja la voz de ``label`` para hablar. Solo cuando el propietario lo confirma."""
        voice = sheet.voice_behind(label)
        self._choose_voice(voice)
        return voice

    def close(self) -> None:
        """Calla y suelta las voces cargadas para la hoja; si se estaba preparando, lo que
        cargue después tampoco se queda. No falla."""
        with self._lock:
            self._closings += 1
            engines, self._engines = self._engines, {}
        for loaded in engines.values():
            loaded.speaker.close()

    def _engines_of(self, voice: SpeakingVoice, closings: int) -> SpeakingEngines[Any]:
        """La voz cargada, o cargada ahora; si la hoja se cerró mientras, la suelta y lo dice."""
        with self._lock:
            engines = self._engines.get(voice)
        if engines is not None:
            return engines
        try:
            engines = self._load_voice(voice)
        except VoiceUnavailable as error:
            msg = f"No puedo preparar la prueba de voces: {error.reason}."
            raise VoiceTestError(msg) from error
        with self._lock:
            if self._closings == closings:
                self._engines[voice] = engines
                return engines
        engines.speaker.close()
        msg = "La prueba de voces se canceló."
        raise VoiceTestError(msg)
