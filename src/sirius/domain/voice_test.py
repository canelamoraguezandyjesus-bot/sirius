"""La prueba a ciegas para elegir su voz (pieza F de ADR-241, ADR-246; PA-R03-10).

El plan del robot, «Lo que se hace», 7: cinco frases típicas suyas con cuatro a seis
voces, a ciegas, por el altavoz. Aquí vive lo que no depende de cómo suena cada voz: las
frases, las etiquetas sin nombre y el barajado. La hoja guarda aparte, en ``key``, qué voz
hay tras cada etiqueta; lo que ve el propietario son las etiquetas y las frases.

Como la prueba a ciegas del modelo de la charla (pieza C de ADR-233), pero al revés: allí
cambia la respuesta y aquí la voz, así que las frases son las mismas para todas.
"""

from __future__ import annotations

import random
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass

#: Las cinco frases: un saludo, una broma, una pregunta y una frase larga, que son
#: respuestas que él escribió para la semilla de Sirius (ADR-235), y una con un número y
#: una fecha, que es lo que más cambia de una voz a otra. Ninguna cambia al prepararla
#: para hablar (``prepare_speech_text``): suenan como sonarían en la charla.
VOICE_TEST_PHRASES: tuple[str, ...] = (
    "Buenos días, jefe.",
    "Joder, macho, por lo menos pide todo de una vez.",
    "¿Qué tal, Marta? ¿Y dónde conociste a este energúmeno?",
    "Bueno, yo te escucho, pero otra cosa es que te entienda. Recuerda que cuando me "
    "creaste me limitaste a ser tu compañero, no tu empleado.",
    "Apuntado: el 23 de diciembre, a las 8 y media, cena para 12.",
)

#: Las etiquetas con las que ve cada voz, sin su nombre: tantas como voces, en este orden.
VOICE_TEST_LABELS: tuple[str, ...] = ("Voz A", "Voz B", "Voz C", "Voz D", "Voz E", "Voz F")

#: Cuántas voces admite la prueba: el plan dice de cuatro a seis.
MIN_VOICES = 4
MAX_VOICES = 6


class VoiceTestError(ValueError):
    """La prueba de voces no se puede preparar, escuchar o elegir tal como se ha pedido."""


@dataclass(frozen=True, slots=True)
class VoiceCandidate[Sound]:
    """Una voz de la hoja: su etiqueta y su muestra de cada frase."""

    label: str
    samples: Mapping[str, Sound]


@dataclass(frozen=True, slots=True)
class VoiceTestSheet[Voice: Hashable, Sound]:
    """La hoja: las frases, las voces barajadas con su etiqueta y, aparte, qué voz es cada
    una (``key``, etiqueta a voz). Las muestras viven aquí, en memoria."""

    phrases: tuple[str, ...]
    candidates: tuple[VoiceCandidate[Sound], ...]
    key: Mapping[str, Voice]

    def voice_behind(self, label: str) -> Voice:
        """La voz de verdad tras ``label``; ``VoiceTestError`` si la hoja no la tiene."""
        if label not in self.key:
            msg = f"La hoja no tiene la etiqueta {label!r}."
            raise VoiceTestError(msg)
        return self.key[label]

    def sample(self, label: str, phrase: str) -> Sound:
        """La muestra de ``phrase`` con la voz de ``label``."""
        for candidate in self.candidates:
            if candidate.label == label:
                if phrase not in candidate.samples:
                    msg = f"La hoja no tiene la frase {phrase!r}."
                    raise VoiceTestError(msg)
                return candidate.samples[phrase]
        msg = f"La hoja no tiene la etiqueta {label!r}."
        raise VoiceTestError(msg)


def prepare_voice_test[Voice: Hashable, Sound](
    phrases: Sequence[str],
    samples: Mapping[Voice, Mapping[str, Sound]],
    rng: random.Random,
) -> VoiceTestSheet[Voice, Sound]:
    """Baraja las voces y les pone etiqueta.

    ``samples[voz][frase]`` es la muestra que dio ``voz`` de ``frase``. Cada hoja baraja
    otra vez: la etiqueta no dice nada de la voz que hay detrás.
    """
    voices = tuple(samples)
    if not MIN_VOICES <= len(voices) <= MAX_VOICES:
        msg = f"La prueba de voces es entre {MIN_VOICES} y {MAX_VOICES} voces."
        raise VoiceTestError(msg)
    if len(set(phrases)) != len(phrases) or not all(phrase.strip() for phrase in phrases):
        msg = "Las frases de la prueba de voces tienen que ser distintas y no vacías."
        raise VoiceTestError(msg)
    for voice in voices:
        if set(samples[voice]) != set(phrases):
            msg = "Falta alguna muestra de una voz."
            raise VoiceTestError(msg)
    order = rng.sample(voices, k=len(voices))
    labels = VOICE_TEST_LABELS[: len(order)]
    candidates = tuple(
        VoiceCandidate(label=label, samples={phrase: samples[voice][phrase] for phrase in phrases})
        for label, voice in zip(labels, order, strict=True)
    )
    key = dict(zip(labels, order, strict=True))
    return VoiceTestSheet(phrases=tuple(phrases), candidates=candidates, key=key)
