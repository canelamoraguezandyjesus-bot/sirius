"""Las órdenes de memoria del propietario (pieza G de ADR-233, ADR-239).

El paso 6 de la memoria: «Por voz o por texto: "eso no es así", "olvida eso" y
"¿qué sabes de mí?". Olvidar borra de verdad, también de los resúmenes».

Aquí solo se reconocen, en el texto llano (sin tildes ni mayúsculas), y se
recorta lo que dijo con sus palabras. Las atiende ``MemoryCommandService`` antes
de montar el contexto: ni el modelo de la charla ni el de huellas las ven.

Se reconocen solo si el mensaje entero es la orden: «olvida eso» sí, «no olvides
eso que te dije» no. Lo que no es una orden va a la charla como siempre.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from sirius.domain.plain_text import nfc, plain

__all__ = ["MemoryCommand", "MemoryCommandKind", "detect_memory_command"]


class MemoryCommandKind(StrEnum):
    FORGET_LAST = "olvida eso"
    FORGET_ABOUT = "olvida lo de"
    CORRECT = "eso no es así"
    ABOUT_ME = "qué sabes de mí"
    ABOUT_PERSON = "qué sabes de alguien"
    YES = "sí"
    NO = "no"


@dataclass(frozen=True, slots=True)
class MemoryCommand:
    """Una orden y lo que lleva: el tema a olvidar, lo que es en realidad o la persona."""

    kind: MemoryCommandKind
    argument: str = ""


# Lo que rodea a la orden y no cambia nada: signos, «Sirius,» delante y «por favor».
_PREFIX = re.compile(r"[\s¿¡\"'«(]*(?:sirius\s*,?\s+)?")
_SUFFIX = re.compile(r"(?:\s*,?\s*por favor)?[\s?!.,;:\"'»)…]*$")

_FORGET_LAST = re.compile(
    r"(?:olvida(?:te de)?|borra|olvidalo|borralo)"
    r"(?:\s+(?:eso|esto|lo ultimo|lo que te (?:acabo de decir|he dicho)))?"
)
_FORGET_ABOUT = re.compile(
    r"(?:olvida(?:te de)?|borra)\s+(?:todo\s+)?lo\s+"
    r"(?:de|del|que te (?:dije|conte) de)\s+(?P<rest>.+)"
)
_CORRECT = re.compile(r"eso no es (?:asi|verdad|cierto)(?P<rest>.*)")
_ABOUT = re.compile(r"(?:y\s+)?que (?:sabes|recuerdas) de (?P<rest>.+)")
_YES = re.compile(r"(?:si|vale|venga|claro|cambialo|si,? cambialo|correcto|eso es)")
_NO = re.compile(r"(?:no|dejalo|da igual|no lo cambies)")

_MIN_TOPIC_LETTERS = 3


def _core(text: str) -> tuple[str, str]:
    """El mensaje sin lo que rodea a la orden: en llano y con sus palabras, alineados."""
    original = nfc(text).strip()
    flat = plain(original)
    prefix = _PREFIX.match(flat)
    start = prefix.end() if prefix is not None else 0
    suffix = _SUFFIX.search(flat, start)
    end = suffix.start() if suffix is not None else len(flat)
    return flat[start:end], original[start:end]


def detect_memory_command(text: str) -> MemoryCommand | None:
    """La orden de memoria que es ``text`` entero, o ``None`` si no es ninguna."""
    flat, original = _core(text)
    if not flat:
        return None
    if _FORGET_LAST.fullmatch(flat):
        return MemoryCommand(MemoryCommandKind.FORGET_LAST)
    if match := _FORGET_ABOUT.fullmatch(flat):
        topic = original[match.start("rest") :].strip(" ,.;:")
        letters = sum(char.isalpha() for char in topic)
        if letters >= _MIN_TOPIC_LETTERS:
            return MemoryCommand(MemoryCommandKind.FORGET_ABOUT, topic)
        return None
    if match := _CORRECT.fullmatch(flat):
        rest = original[match.start("rest") :].strip(" ,.;:-—")
        return MemoryCommand(MemoryCommandKind.CORRECT, rest)
    if match := _ABOUT.fullmatch(flat):
        who = original[match.start("rest") :].strip(" ,.;:")
        if plain(who) in {"mi", "mi mismo", "mi misma"}:
            return MemoryCommand(MemoryCommandKind.ABOUT_ME)
        return MemoryCommand(MemoryCommandKind.ABOUT_PERSON, who)
    if _YES.fullmatch(flat):
        return MemoryCommand(MemoryCommandKind.YES)
    if _NO.fullmatch(flat):
        return MemoryCommand(MemoryCommandKind.NO)
    return None
