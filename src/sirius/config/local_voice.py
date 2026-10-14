"""Los ajustes de la voz del robot (ADR-242).

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


@dataclass(frozen=True, slots=True)
class LocalVoiceSettings:
    """Con qué oye el robot. La pieza C le añadirá con qué habla."""

    listening_model: ListeningModel = ListeningModel.SMALL
