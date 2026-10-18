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

Y al decir cada frase pinta otras tres cosas, que se callan mientras la dice y por su
texto (#696): la barra «Sampling» de tqdm, que su T3 repinta en cada paso; el aviso de
torch de que ``sdp_kernel`` está en desuso, porque lo usa su perceptor; y el de transformers
de que ``output_attentions`` no vale para generar. Lo demás que pinte sale igual. Los textos
salen del código de las versiones fijadas: chatterbox-tts 0.1.7, torch 2.14.1, tqdm 4.68.4 y
transformers 5.2.0.
"""

from __future__ import annotations

import logging
import sys
import threading
import warnings
from array import array
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

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

#: Cómo empieza la barra de tqdm de Chatterbox cada vez que se repinta: ``\r`` y su nombre.
_SAMPLING_BAR = "Sampling:"
#: El aviso de torch cada vez que el perceptor de Chatterbox usa ``sdp_kernel``.
_SDP_KERNEL = r"`torch\.backends\.cuda\.sdp_kernel\(\)` is deprecated"
#: Dónde y cómo avisa transformers de que ``output_attentions`` no vale para generar.
_GENERATION_FLAGS_LOGGER = "transformers.generation.configuration_utils"
_GENERATION_FLAGS = "The following generation flags are not valid"


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
        # Solo el texto y el idioma: ningún audio, que es como imita una voz. Una frase cada
        # vez: callar lo que pinta toca la consola y los avisos de todo el proceso.
        with _SAYING, _quiet_say():
            wav = self._model.generate(text, language_id=LANGUAGE)
        samples = wav.squeeze(0).tolist()
        return array("h", (round(max(-1.0, min(1.0, s)) * 32767) for s in samples)).tobytes()


#: Una frase de la voz de personaje cada vez, la diga quien la diga (#696). Dos a la vez,
#: en dos hilos, se pisarían al callar lo que pinta Chatterbox: ``warnings.catch_warnings``
#: no es seguro entre hilos, y la consola se envuelve y se devuelve para todo el proceso. Y
#: tampoco se le piden dos frases a la vez al mismo modelo.
_SAYING = threading.Lock()


@contextmanager
def _quiet_say() -> Iterator[None]:
    """Calla, mientras dice una frase, las tres cosas que pinta Chatterbox con cada una, y
    nada más (#696). Con ``_SAYING`` puesto: no se entrelaza con otra."""
    flags = logging.getLogger(_GENERATION_FLAGS_LOGGER)
    without_flags = _WithoutText(_GENERATION_FLAGS)
    flags.addFilter(without_flags)
    stderr = sys.stderr
    # tqdm se queda con la consola que hay al crear la barra.
    sys.stderr = _WithoutSamplingBar(stderr)
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", _SDP_KERNEL, FutureWarning)
            yield
    finally:
        sys.stderr = stderr
        flags.removeFilter(without_flags)


class _WithoutText(logging.Filter):
    """Deja fuera los mensajes que empiezan por ``text``."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.getMessage().startswith(self._text)


class _WithoutSamplingBar:
    """La consola de errores sin la barra «Sampling» de Chatterbox, y lo demás tal cual.

    tqdm repinta la barra escribiendo ``\\r`` y la barra entera, y al cerrarla escribe un
    salto de línea solo: se quitan esos, y nada más.
    """

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._after_bar = False

    def write(self, text: str) -> int:
        if text.lstrip("\r").startswith(_SAMPLING_BAR):
            self._after_bar = True
            return len(text)
        if self._after_bar and text == "\n":
            self._after_bar = False
            return len(text)
        if text:
            self._after_bar = False
        return self._stream.write(text)

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)
