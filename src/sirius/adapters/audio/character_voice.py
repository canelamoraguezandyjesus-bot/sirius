"""La voz de personaje: Chatterbox multilingüe con su voz de serie (pieza F, ADR-246).

Como Piper (ADR-243): la biblioteca es de un extra, ``personaje``, se importa al cargar la
voz y por ``import_voice_library``, y cargarla no tumba a Sirius, falle como falle. Carga
solo de su carpeta, la que deja la orden de instalar, con ``from_local``: aquí no se nombra
ninguna función que baje nada, eso vive solo en la orden de instalar.

Chatterbox, al cargar, le pide a Hugging Face un fichero del chino aunque hable español
(``MTLTokenizer``, dentro de un ``try``). Por eso se carga sin conexión
(``hugging_face_offline``): cada petición suya falla sin salir del ordenador, y si
huggingface_hub ya estaba importado con conexión, no carga (PA-R03-08). Los procesos que
oyen y hablan lo ponen al arrancar.

Y solo recibe texto. Chatterbox imita la voz de un audio si se le da
(``audio_prompt_path``, ``prepare_conditionals``); aquí nunca se le da, así que habla
siempre con la suya, la de ``conds.pt``, que no es el audio de nadie (PA-R03-10).

Al cargar, Chatterbox y sus bibliotecas pintan en la consola avisos que no le dicen nada
al propietario ni cambian nada, y mientras carga se callan (ADR-252). Son tres: que
``pkg_resources`` está en desuso, porque lo importa la marca de agua de Perth; que
``LoRACompatibleLinear`` de diffusers lo está, porque lo usa Chatterbox; y lo que su
tokenizador no carga para el chino, que aquí no se habla. Fuera de la carga, avisan como
siempre, y cualquier otro aviso sale también al cargar.
"""

from __future__ import annotations

import logging
import warnings
from array import array
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sirius.adapters.audio.voice_libraries import (
    CHARACTER_VOICE_LIBRARY,
    hugging_face_offline,
    import_voice_library,
)
from sirius.ports.local_voice import VoiceUnavailable

#: En qué idioma habla: Chatterbox no distingue el español de España del de América.
LANGUAGE = "es"

#: El registrador del tokenizador de Chatterbox: al cargar avisa de que no tiene lo del
#: chino, el fichero que pide a Hugging Face sin conexión y pkuseg.
_TOKENIZER_LOGGER = "chatterbox.models.tokenizers.tokenizer"


def load_character_voice(folder: Path) -> CharacterSpeech:
    """La voz de personaje de ``folder``, sin conexión y en la gráfica si torch la ve.

    Falla con ``VoiceUnavailable`` si falta el extra ``personaje``, si no puede cargar sin
    conexión o si la voz no carga, falle como falle.
    """
    hugging_face_offline()
    with _quiet_load():
        torch = import_voice_library("torch")
        multilingual = import_voice_library(CHARACTER_VOICE_LIBRARY)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            model = multilingual.ChatterboxMultilingualTTS.from_local(folder, device)
        except Exception as error:
            msg = f"la voz de personaje no carga ({error})"
            raise VoiceUnavailable(msg) from error
    return CharacterSpeech(model)


@contextmanager
def _quiet_load() -> Iterator[None]:
    """Calla, mientras dura, los tres avisos de cargar Chatterbox, y nada más."""
    tokenizer = logging.getLogger(_TOKENIZER_LOGGER)
    level = tokenizer.level
    tokenizer.setLevel(logging.ERROR)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "pkg_resources is deprecated", UserWarning)
            warnings.filterwarnings("ignore", ".*LoRACompatibleLinear", FutureWarning)
            yield
    finally:
        tokenizer.setLevel(level)


class CharacterSpeech:
    """Chatterbox ya cargado: cada frase, en muestras de 16 bits a su frecuencia, como las
    da Piper, para el mismo altavoz."""

    def __init__(self, model: Any) -> None:
        self._model = model

    @property
    def sample_rate(self) -> int:
        return int(self._model.sr)

    def say(self, text: str) -> bytes:
        # Solo el texto y el idioma: ningún audio, que es como imita una voz.
        wav = self._model.generate(text, language_id=LANGUAGE)
        samples = wav.squeeze(0).tolist()
        return array("h", (round(max(-1.0, min(1.0, s)) * 32767) for s in samples)).tobytes()
