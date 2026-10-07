"""Las dos marcas de cada respuesta de Sirius (pieza D de ADR-233, PA-R02-06).

El paso 5 de la personalidad en la 0.2 del plan del robot: dos botones en cada
respuesta, «eso es Sirius» y «eso no». Sirven ya como ejemplos y después para
entrenarle (0.5). No hay una tercera marca a propósito: se marca si es Sirius,
no si gusta. Premiar lo que agrada volvió pelota a ChatGPT en abril de 2025, y
una marca «me gusta» que no existe no se puede usar para entrenarle mal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReplyMark(StrEnum):
    ES_SIRIUS = "eso es Sirius"
    NO_ES_SIRIUS = "eso no"


@dataclass(frozen=True, slots=True)
class MarkedReply:
    """Una respuesta marcada: cuál, con qué marca, con qué modelo y con qué identidad."""

    message_id: int
    sequence: int
    mark: ReplyMark
    model: str | None
    identity_version: int | None
