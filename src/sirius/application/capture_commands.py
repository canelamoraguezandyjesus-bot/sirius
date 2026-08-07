"""Entiende órdenes de captura dichas o escritas, sin preguntarle al modelo.

MS-017 de #127: la voz, la interfaz y los futuros botones físicos tienen que
producir **el mismo comando interno**. Este módulo es el que lo consigue para
la voz y para el texto escrito: convierte una frase en un comando tipado, o en
nada.

**No interviene ningún modelo.** Es una decisión de seguridad, no de coste.
#127 prohíbe el «texto libre ejecutable» y exige que el controlador solo acepte
comandos tipados y escenas de la lista blanca. Si fuera un modelo quien
decidiera qué orden es cada frase, podría inventarse una que nadie dijo, y la
peor de todas —parar una grabación a mitad— no admite equivocaciones. Aquí lo
que no está escrito literalmente, no se ejecuta.

Regla que evita el accidente más probable: **la frase entera tiene que ser la
orden**. «Para» es parar; «¿para qué sirve esta resistencia?» es una pregunta y
se manda a la conversación como cualquier otra. Mencionar una cámara hablando
no cambia de plano.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from sirius.domain.capture import SceneRegistry, normalize_alias


class CaptureCommand(StrEnum):
    """Contrato cerrado de órdenes. No hay ninguna más."""

    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    PAUSE_RECORDING = "pause_recording"
    RESUME_RECORDING = "resume_recording"
    MARK_MOMENT = "mark_moment"
    SWITCH_SCENE = "switch_scene"
    EMERGENCY_STOP = "emergency_stop"
    GET_STATUS = "get_status"


@dataclass(frozen=True, slots=True)
class CaptureIntent:
    """Una orden reconocida, ya resuelta contra la lista blanca."""

    command: CaptureCommand
    scene_id: str | None = None
    label: str | None = None


# Frases que son la orden entera. Se comparan sin acentos ni mayúsculas.
_EXACT_PHRASES: dict[str, CaptureCommand] = {
    # Empezar
    "graba": CaptureCommand.START_RECORDING,
    "grabar": CaptureCommand.START_RECORDING,
    "empieza a grabar": CaptureCommand.START_RECORDING,
    "empieza la grabacion": CaptureCommand.START_RECORDING,
    "comienza a grabar": CaptureCommand.START_RECORDING,
    "dale a grabar": CaptureCommand.START_RECORDING,
    "ponte a grabar": CaptureCommand.START_RECORDING,
    # Parar
    "para": CaptureCommand.STOP_RECORDING,
    "parar": CaptureCommand.STOP_RECORDING,
    "detente": CaptureCommand.STOP_RECORDING,
    "deten la grabacion": CaptureCommand.STOP_RECORDING,
    "deja de grabar": CaptureCommand.STOP_RECORDING,
    "para de grabar": CaptureCommand.STOP_RECORDING,
    "para la grabacion": CaptureCommand.STOP_RECORDING,
    "corta": CaptureCommand.STOP_RECORDING,
    "corta la grabacion": CaptureCommand.STOP_RECORDING,
    # Pausar
    "pausa": CaptureCommand.PAUSE_RECORDING,
    "pausar": CaptureCommand.PAUSE_RECORDING,
    "haz una pausa": CaptureCommand.PAUSE_RECORDING,
    "pausa la grabacion": CaptureCommand.PAUSE_RECORDING,
    # Reanudar
    "sigue": CaptureCommand.RESUME_RECORDING,
    "seguimos": CaptureCommand.RESUME_RECORDING,
    "continua": CaptureCommand.RESUME_RECORDING,
    "continuamos": CaptureCommand.RESUME_RECORDING,
    "reanuda": CaptureCommand.RESUME_RECORDING,
    "reanudar": CaptureCommand.RESUME_RECORDING,
    "sigue grabando": CaptureCommand.RESUME_RECORDING,
    # Marcar
    "marca": CaptureCommand.MARK_MOMENT,
    "marca esto": CaptureCommand.MARK_MOMENT,
    "marca este momento": CaptureCommand.MARK_MOMENT,
    "apunta esto": CaptureCommand.MARK_MOMENT,
    "toma nota de esto": CaptureCommand.MARK_MOMENT,
    # Emergencia
    "parada de emergencia": CaptureCommand.EMERGENCY_STOP,
    "para ya": CaptureCommand.EMERGENCY_STOP,
    "corta ya": CaptureCommand.EMERGENCY_STOP,
    "emergencia": CaptureCommand.EMERGENCY_STOP,
    # Estado
    "estas grabando": CaptureCommand.GET_STATUS,
    "estamos grabando": CaptureCommand.GET_STATUS,
    "se esta grabando": CaptureCommand.GET_STATUS,
    "que estas grabando": CaptureCommand.GET_STATUS,
    "estado de la grabacion": CaptureCommand.GET_STATUS,
    "como va la grabacion": CaptureCommand.GET_STATUS,
}

_SCENE_PREFIXES: tuple[str, ...] = (
    "cambia a la camara",
    "cambia a la escena",
    "cambia a la",
    "cambia a",
    "cambiate a la camara",
    "cambiate a la",
    "cambiate a",
    "pasa a la camara",
    "pasa a la",
    "pasa a",
    "ponme la camara",
    "ponme la",
    "ponme",
    "pon la camara",
    "pon la",
    "pon",
    "activa la camara",
    "activa la escena",
    "activa la",
    "activa",
    "ve a la",
    "ve a",
    "vete a la",
    "vete a",
    "saca la camara",
    "saca la",
    "muestra la camara",
    "muestra la",
    "quiero la camara",
    "quiero la",
    "dame la camara",
    "dame la",
)
"""Ordenados de más largo a más corto al usarlos: «cambia a la camara X» tiene
que ganarle a «cambia a», o el nombre de la escena se quedaría con un «la
camara» delante que no resolvería."""

_MARK_PREFIXES: tuple[str, ...] = (
    "marca esto como",
    "marca este momento como",
    "marca el momento como",
    "apunta esto como",
    "marca como",
)
"""Todos exigen «como» o «esto». Un «marca» suelto seguido de palabras **no**
vale: en español «marca» es también un sustantivo, y «marca de la placa que
compré» acabaría marcando un momento que nadie pidió marcar. Para marcar sin
etiqueta ya está la frase exacta «marca»."""

_TRAILING_PUNCTUATION = re.compile(r"^[¿¡\s]+|[?!.,;:\s]+$")
_INNER_SPACES = re.compile(r"\s+")

MAXIMUM_LABEL_LENGTH = 60
"""Una marca es una etiqueta corta para reencontrar el momento, no una nota."""


def _normalize(text: str) -> str:
    """Forma canónica: sin acentos, sin mayúsculas y sin signos alrededor."""
    stripped = _TRAILING_PUNCTUATION.sub("", text)
    collapsed = _INNER_SPACES.sub(" ", stripped)
    return normalize_alias(collapsed)


def interpret(text: str, scenes: SceneRegistry) -> CaptureIntent | None:
    """Devuelve la orden que la frase **es**, o ``None`` si no es una orden.

    ``None`` significa «esto va a la conversación». Ante la duda siempre se
    devuelve ``None``: dejar pasar una orden a la conversación es una molestia
    menor; ejecutar una orden que nadie dio, mientras se graba, no lo es.
    """
    normalized = _normalize(text)
    if not normalized:
        return None

    exact = _EXACT_PHRASES.get(normalized)
    if exact is not None:
        return CaptureIntent(exact)

    scene_intent = _interpret_scene(normalized, scenes)
    if scene_intent is not None:
        return scene_intent

    return _interpret_mark(normalized)


def _interpret_scene(normalized: str, scenes: SceneRegistry) -> CaptureIntent | None:
    """Cambio de plano, solo si lo que sigue al verbo es una escena autorizada.

    Se prueban los prefijos de más largo a más corto para que «cambia a la
    camara cenital» no deje «la camara cenital» como nombre de escena.
    """
    for prefix in sorted(_SCENE_PREFIXES, key=len, reverse=True):
        if not normalized.startswith(f"{prefix} "):
            continue
        remainder = normalized[len(prefix) :].strip()
        if not remainder:
            continue
        scene = scenes.resolve(remainder)
        # Sin coincidencia exacta no se cambia de plano y no se adivina: la
        # frase se manda a la conversación tal cual.
        if scene is not None:
            return CaptureIntent(CaptureCommand.SWITCH_SCENE, scene_id=scene.scene_id)
    return None


def _interpret_mark(normalized: str) -> CaptureIntent | None:
    """Marca con etiqueta: «marca esto como el primer led»."""
    for prefix in sorted(_MARK_PREFIXES, key=len, reverse=True):
        if not normalized.startswith(f"{prefix} "):
            continue
        label = normalized[len(prefix) :].strip()
        if not label or len(label) > MAXIMUM_LABEL_LENGTH:
            continue
        return CaptureIntent(CaptureCommand.MARK_MOMENT, label=label)
    return None
