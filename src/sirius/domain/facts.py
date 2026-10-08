"""Los hechos de la 0.2 del robot (pieza G de ADR-233, ADR-239).

El paso 3 de la memoria: «Hechos con fecha de inicio y de fin, quién lo dijo y
con qué seguridad. Lo que dice Sirius nunca cuenta como hecho del propietario».

Un hecho es un recuerdo con persona y tema (``Memory.person``, ``Memory.topic``),
y cada revisión suya es un tramo: desde cuándo valió, hasta cuándo, quién lo
dijo y con qué seguridad. Un hecho que cambia es una revisión nueva que cierra la
anterior con su fecha, así que la charla solo ve el vigente y la historia los
guarda todos. Lo demás lo hace ya la memoria: corregir, borrar, buscar.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sirius.domain.memory import Memory, MemoryRevision
from sirius.domain.plain_text import plain

__all__ = [
    "OWNER",
    "SIRIUS",
    "Certainty",
    "FactSpan",
    "ProposedFact",
    "fact_line",
    "fact_lines",
    "fact_note",
    "is_owner",
    "is_sirius",
    "memory_note",
    "mentioned_people",
    "person_key",
    "same_person",
    "span_of",
]

#: Quién es el propietario en los hechos: la persona de lo que se sabe de él, y
#: quién lo dijo cuando lo dijo él.
OWNER = "propietario"

#: Lo que dice Sirius nunca es un hecho del propietario: nadie puede apuntar un
#: hecho con este «quién lo dijo».
SIRIUS = "Sirius"

_WORD = re.compile(r"[^\W_]+")


class Certainty(StrEnum):
    """Con qué seguridad se sabe un hecho."""

    SURE = "segura"
    DOUBTFUL = "dudosa"


@dataclass(frozen=True, slots=True)
class ProposedFact:
    """Un hecho que alguien propone apuntar: el sueño, o el propietario al confirmarlo.

    Nada propuesto es un hecho hasta que él dice que sí.
    """

    person: str
    topic: str | None
    text: str
    since: date | None = None
    said_by: str = OWNER
    certainty: Certainty = Certainty.SURE


@dataclass(frozen=True, slots=True)
class FactSpan:
    """Un hecho mientras estuvo vigente: un tramo de su historia."""

    text: str
    since: date
    until: date | None
    said_by: str
    certainty: Certainty


def person_key(name: str) -> str:
    """El nombre para compararlo: en llano y con un espacio entre palabras."""
    return " ".join(_WORD.findall(plain(name)))


def same_person(first: str, second: str) -> bool:
    return person_key(first) == person_key(second)


def is_owner(person: str | None) -> bool:
    return person is not None and same_person(person, OWNER)


def is_sirius(person: str | None) -> bool:
    return person is not None and same_person(person, SIRIUS)


def mentioned_people(text: str, people: Iterable[str]) -> list[str]:
    """Las personas de ``people`` que nombra ``text``, palabra por palabra.

    «¿Qué tal estará Lucía?» nombra a Lucía; «Luciano» no. El propietario no se
    nombra: lo suyo va siempre.
    """
    words = _WORD.findall(plain(text))
    found: list[str] = []
    for person in people:
        if is_owner(person):
            continue
        name = person_key(person).split()
        if name and any(words[i : i + len(name)] == name for i in range(len(words))):
            found.append(person)
    return found


def span_of(revision: MemoryRevision) -> FactSpan:
    """El tramo que es una revisión de un hecho."""
    return FactSpan(
        text=revision.content or "",
        since=revision.valid_from or revision.created_at.date(),
        until=revision.valid_to,
        said_by=revision.said_by or OWNER,
        certainty=Certainty(revision.certainty or Certainty.SURE),
    )


def fact_note(said_by: str | None, certainty: str | None) -> str:
    """Lo que hay que saber de dónde sale un hecho, o nada si lo dijo él y es seguro."""
    parts: list[str] = []
    if said_by is not None and not is_owner(said_by):
        parts.append(f"lo dijo {said_by}")
    if certainty == Certainty.DOUBTFUL:
        parts.append("no es seguro")
    return f" ({'; '.join(parts)})" if parts else ""


def fact_line(memory: Memory) -> str:
    """Un hecho vigente como va en la petición: el texto, desde cuándo y de dónde sale."""
    revision = memory.current_revision
    since = revision.valid_from
    when = f" (desde el {since:%d-%m-%Y})" if since is not None else ""
    return f"- {revision.content}{when}{fact_note(revision.said_by, revision.certainty)}"


def fact_lines(memories: Sequence[Memory]) -> list[str]:
    return [fact_line(memory) for memory in memories if memory.current_revision.content]


def memory_note(memory: Memory) -> str:
    """Lo que hay que saber de un hecho que trae la búsqueda: de quién es y de dónde sale."""
    if not memory.is_fact:
        return ""
    revision = memory.current_revision
    parts: list[str] = []
    if memory.person is not None and not is_owner(memory.person):
        parts.append(f"de {memory.person}")
    if revision.said_by is not None and not is_owner(revision.said_by):
        parts.append(f"lo dijo {revision.said_by}")
    if revision.certainty == Certainty.DOUBTFUL:
        parts.append("no es seguro")
    return f" ({'; '.join(parts)})" if parts else ""
