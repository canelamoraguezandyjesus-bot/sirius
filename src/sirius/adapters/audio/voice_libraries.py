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
