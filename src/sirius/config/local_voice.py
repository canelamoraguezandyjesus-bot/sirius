"""Los ajustes de la voz del robot (ADR-242, ADR-243, ADR-246).

Todo ocurre en este ordenador. Ningún ajuste es texto libre, así que no hay dónde poner
un servidor, una dirección, una clave ni la ruta de un audio: cada uno es una elección
cerrada de lo que la orden de instalar deja aquí. PA-R03-08 lo comprueba leyendo este
modelo, y un campo de texto aparecería allí como otro destino posible del audio; y
PA-R03-10, que no haya por dónde darle a la voz el audio de alguien para imitarlo.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

#: Dónde guardan los ajustes la voz que él eligió a ciegas (pieza F, ADR-246).
SPEAKING_VOICE_SETTING = "local_speaking_voice"


class ListeningModel(StrEnum):
    """El modelo de faster-whisper con que oye. Hoy uno: el que baja la orden de instalar."""

    SMALL = "small"


class SpeakingVoice(StrEnum):
    """Las voces con que puede hablar: las candidatas de la prueba a ciegas (ADR-246).

    Cuatro de Piper, las masculinas en español de España de ADR-241, como las nombra
    Piper, y la de personaje: la voz de serie de Chatterbox, que no es el audio de nadie.
    Hasta que él elija, habla con la de davefx.
    """

    DAVEFX = "es_ES-davefx-medium"
    SHARVARD = "es_ES-sharvard-medium"
    CARLFM = "es_ES-carlfm-x_low"
    MLS = "es_ES-mls_10246-low"
    CHARACTER = "chatterbox-multilingual"

    @property
    def is_character(self) -> bool:
        """Si es la de personaje, con Chatterbox; las demás son de Piper."""
        return self is SpeakingVoice.CHARACTER

    @property
    def piper_speaker(self) -> str | None:
        """El locutor que se le pide a Piper, en las voces que traen más de uno.

        La de sharvard trae un hombre y una mujer, y Piper habla por defecto con el
        primero de su lista: se pide el hombre por su nombre, y si la voz no lo trae, no
        carga, en vez de hablar con otro.
        """
        return "M" if self is SpeakingVoice.SHARVARD else None


@dataclass(frozen=True, slots=True)
class LocalVoiceSettings:
    """Con qué oye y con qué habla el robot."""

    listening_model: ListeningModel = ListeningModel.SMALL
    speaking_voice: SpeakingVoice = SpeakingVoice.DAVEFX


def local_voice_settings(saved: Mapping[str, object]) -> LocalVoiceSettings:
    """Los ajustes de la voz con la voz que él eligió, si es una de las de la prueba.

    Sin elegir, o con algo que no es una de ellas, la de siempre: un ajuste que no se
    entiende no deja a Sirius sin voz.
    """
    value = saved.get(SPEAKING_VOICE_SETTING)
    voices = {voice.value: voice for voice in SpeakingVoice}
    voice = voices.get(value) if isinstance(value, str) else None
    return LocalVoiceSettings(speaking_voice=voice or SpeakingVoice.DAVEFX)
