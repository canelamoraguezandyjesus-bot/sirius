"""Olvidar de verdad (pieza G de ADR-233, ADR-239)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

__all__ = ["ForgetReport", "Forgetter"]


@dataclass(frozen=True, slots=True)
class ForgetReport:
    """Cuánto se borró al olvidar, para decírselo al propietario."""

    messages: int = 0
    memories: int = 0
    suggestions: int = 0
    summaries: int = 0

    @property
    def anything(self) -> bool:
        return bool(self.messages or self.memories or self.suggestions or self.summaries)


class Forgetter(Protocol):
    def forget_message(self, message_id: int) -> ForgetReport:
        """Olvida un mensaje del propietario, la respuesta que le dio Sirius y lo que salió de él.

        Lo que salió de él: los recuerdos y las sugerencias que se guardaron desde
        ese mensaje o que lo repiten, y los resúmenes que ya lo cubrían.
        """
        ...

    def forget_phrase(self, phrase: str) -> ForgetReport:
        """Olvida todo lo que contiene ``phrase``, sin mirar tildes ni mayúsculas.

        Mensajes de los dos, recuerdos y hechos, sugerencias, y las frases de los
        resúmenes que la nombran.
        """
        ...
