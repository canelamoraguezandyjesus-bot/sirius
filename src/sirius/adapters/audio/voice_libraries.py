"""Las bibliotecas de la voz del robot: cómo se importan y con qué oye y habla.

ADR-242 y ADR-243. Son del extra ``voz`` y se importan al cargar el oído o la voz, no al
importar Sirius, y todas por ``import_voice_library``: sin el extra, o si una biblioteca
nativa no carga, Sirius se importa igual y lo que se cargue levanta ``VoiceUnavailable``
diciendo qué falta.

Con qué oye y habla no está en otra lista: son los módulos que importan los cargadores
del oído y de la voz, y ``voice_tools`` lo lee de ellos (PA-R03-08).
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any

from sirius.ports.local_voice import VoiceUnavailable

#: Silero, dentro de Pipecat: si hay voz.
VOICE_ACTIVITY = "pipecat.audio.vad.silero"
#: Smart Turn v3, dentro de Pipecat: si el turno ha acabado.
END_OF_TURN = "pipecat.audio.turn.smart_turn.local_smart_turn_v3"
#: faster-whisper: lo dicho, en texto.
SPEECH_TO_TEXT = "faster_whisper"
#: Piper: lo escrito, en voz.
TEXT_TO_SPEECH = "piper"
#: La APM de WebRTC de livekit: lo que vuelve del altavoz, fuera de lo que capta el micro
#: (pieza E, ADR-245). No es una herramienta con que oye o habla: sin ella oye y habla
#: igual, pero no se le puede cortar.
ECHO_CANCELLATION = "livekit.rtc"
#: Chatterbox multilingüe, del extra ``personaje``: la voz de personaje de la prueba a
#: ciegas (pieza F, ADR-246). Tampoco es una herramienta del plan con que habla: lo es
#: Piper, y esta habla solo si él la elige.
CHARACTER_VOICE_LIBRARY = "chatterbox.mtl_tts"


def import_voice_library(module: str) -> Any:
    """Una biblioteca del extra ``voz``; si no carga, falle como falle, ``VoiceUnavailable``.

    Una biblioteca nativa no falla solo con ``ImportError``: con ``OSError`` si carga su
    DLL con ctypes, y con lo que quiera su ``__init__`` (H-242). Solo dice qué pasa. Si
    la orden de instalar lo arreglaría no se adivina desde aquí: lo dice lo que falta en
    el ordenador, que se mira antes de cargar nada (``VoiceInstallation.missing``, ronda 7
    de Codex sobre la PR #687).
    """
    try:
        return importlib.import_module(module)
    except Exception as error:
        raise VoiceUnavailable(f"{module} no carga ({error})") from error


#: Lo que pone a Hugging Face sin conexión: lo lee huggingface_hub, y transformers con él.
OFFLINE_VARIABLES = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")


def hugging_face_offline() -> None:
    """Pone a Hugging Face sin conexión en este proceso (ADR-246).

    faster-whisper y Chatterbox traen huggingface_hub, y Chatterbox le pide un fichero al
    cargar aunque hable español: sin conexión, esa petición falla sin salir del ordenador
    (PA-R03-08). huggingface_hub lee las variables al importarse; si ya estaba importado,
    se le apaga la constante, que su versión 1.33 mira en cada petición
    (``constants.is_offline_mode``). Si después de eso no dice que está sin conexión, o no
    se puede saber, ``VoiceUnavailable``: cargar así podría salir.
    """
    for variable in OFFLINE_VARIABLES:
        os.environ[variable] = "1"
    constants: Any = sys.modules.get("huggingface_hub.constants")
    if constants is None:
        return
    constants.HF_HUB_OFFLINE = True
    offline = getattr(constants, "is_offline_mode", None)
    if not callable(offline) or offline() is not True:
        msg = "no puedo poner a Hugging Face sin conexión en este proceso"
        raise VoiceUnavailable(msg)


def voice_tools() -> dict[str, str]:
    """Con qué oye y habla: «voz», «fin de turno», «texto» y «habla», por su nombre."""
    return {
        "voz": _tool(VOICE_ACTIVITY),
        "fin de turno": _tool(END_OF_TURN),
        "texto": _tool(SPEECH_TO_TEXT),
        "habla": _tool(TEXT_TO_SPEECH),
    }


def _tool(module: str) -> str:
    """El nombre de la herramienta de ``module``: la de dentro de Pipecat, o la biblioteca.

    ``pipecat.audio.vad.silero`` es «silero»; ``pipecat.audio.turn.smart_turn.…``,
    «smart-turn»; ``faster_whisper``, «faster-whisper».
    """
    parts = module.split(".")
    name = parts[3] if parts[0] == "pipecat" else parts[0]
    return name.replace("_", "-")
