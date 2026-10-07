"""«Ponte serio» y «para»: los modos de la charla (pieza D de ADR-233, PA-R02-04).

El paso 4 de la personalidad en la 0.2 del plan del robot: «"Ponte serio" le
cambia de modo. Vacila al entrar y luego va al grano. "Para" corta el pique».
Las palabras del propietario lo fijan: «ponte serio» → «vale, jefe», y serio de
verdad hasta que vuelva el buen rollo.

Las órdenes se reconocen por reglas, no por el modelo: así el modo no depende de
que un modelo pequeño se acuerde de él diez turnos después. El modo dura hasta
que el propietario lo suelta, con palabras («ya puedes volver a ser tú») o con
el botón de la ventana.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum


class ConversationMode(StrEnum):
    NORMAL = "normal"
    SERIO = "serio"
    PARA = "para"


#: Lo que se añade a las instrucciones mientras dura cada modo.
MODE_INSTRUCTIONS: dict[ConversationMode, str] = {
    # El modo normal no añade nada: Sirius es la semilla.
    ConversationMode.NORMAL: "",
    ConversationMode.SERIO: (
        "# Modo serio\n"
        "Te ha pedido que te pongas serio. Al grano y preciso: di qué sabes y qué supones, "
        "sin bromas, hasta que te diga que vuelvas a ser tú. Serio no es estirado: sigues "
        "hablando como hablas."
    ),
    ConversationMode.PARA: (
        "# Sin pique\n"
        "Te ha pedido que pares. Nada de pique ni de pullas hasta que te diga que vuelvas a "
        "ser tú. En lo demás sigues siendo tú."
    ),
}

#: Solo en el turno en que entra el modo serio: el vacile del propietario.
ENTERING_SERIOUS_MODE = (
    "Acaba de pedírtelo en este mensaje: vacílale un segundo, «vale, jefe», y ve al grano."
)


def _plain(text: str) -> str:
    """Minúsculas y sin tildes, para reconocer la orden se escriba como se escriba."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


_SERIO = re.compile(r"\bponte\s+serio\b")
# «Para» solo como orden al empezar el mensaje: «para», «para ya», «para, que…»,
# «para de picarme». «Para mañana…» o «para que lo sepas» no son órdenes.
_PARA = re.compile(r"^\W*para(?:\s*$|\s*[,.!;:]|\s+ya\b|\s+de\b)")
_VUELVE = re.compile(r"\b(?:volver|vuelve|vuelvas)\s+a\s+ser\s+tu\b")


def detect_mode_command(text: str) -> ConversationMode | None:
    """El modo que pide el mensaje, o ``None`` si no pide ninguno.

    Soltar el modo gana a pedirlo si el mismo mensaje hace las dos cosas: «vale,
    ya está, vuelve a ser tú» no puede dejarle serio por una coincidencia.
    """
    plain = _plain(text)
    if _VUELVE.search(plain):
        return ConversationMode.NORMAL
    if _SERIO.search(plain):
        return ConversationMode.SERIO
    if _PARA.search(plain):
        return ConversationMode.PARA
    return None
