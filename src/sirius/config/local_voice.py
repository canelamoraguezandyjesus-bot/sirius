"""Los ajustes de la voz del robot (ADR-242, ADR-243).

Todo ocurre en este ordenador. Ningún ajuste es texto libre, así que no hay dónde poner
un servidor, una dirección ni una clave: cada uno es una elección cerrada de lo que la
orden de instalar deja aquí. PA-R03-08 lo comprueba leyendo este modelo, y un campo de
texto aparecería allí como otro destino posible del audio.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ListeningModel(StrEnum):
    """El modelo de faster-whisper con que oye. Hoy uno: el que baja la orden de instalar."""

    SMALL = "small"


class SpeakingVoice(StrEnum):
    """La voz de Piper con que habla, como la nombra Piper. Hoy una: la que baja la orden
    de instalar, de las cuatro masculinas en español de España de ADR-241. Él elige la
    suya a ciegas en la pieza F."""

    DAVEFX = "es_ES-davefx-medium"


@dataclass(frozen=True, slots=True)
class LocalVoiceSettings:
    """Con qué oye y con qué habla el robot."""

    listening_model: ListeningModel = ListeningModel.SMALL
    speaking_voice: SpeakingVoice = SpeakingVoice.DAVEFX
