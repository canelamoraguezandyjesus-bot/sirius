"""El puerto de lo que recuerda haber visto, como texto (pieza G de la 0.4, ADR-265).

Lo apuntado es un cambio de quién tiene delante: cuándo, qué cambió y quién, su nombre si
dio permiso para que le reconozca o nadie. Nada de la imagen ni nada que distinga a un
desconocido: de dos sin identificar se sabe que vinieron dos.
"""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class Change(enum.StrEnum):
    """Qué cambió: alguien vino, alguien se fue, o ya estaba al abrir los ojos."""

    CAME = "came"
    LEFT = "left"
    THERE = "there"


@dataclass(frozen=True, slots=True)
class SeenChange:
    """Un cambio de quién tiene delante: ``at``, cuándo, en UTC; ``change``, qué cambió; y
    ``who``, su nombre si dio permiso, o ``None``."""

    at: datetime
    change: Change
    who: str | None


class SightLogStore(Protocol):
    """Dónde se apunta lo que ve."""

    def add(self, changes: Sequence[SeenChange]) -> None:
        """Apunta ``changes``."""
        ...

    def since(self, moment: datetime) -> tuple[SeenChange, ...]:
        """Lo apuntado desde ``moment``, del más viejo al más nuevo."""
        ...

    def drop_before(self, moment: datetime) -> int:
        """Borra lo apuntado antes de ``moment``; cuántos cambios."""
        ...

    def forget(self, who: str) -> int:
        """Quita el nombre ``who`` de lo apuntado: pasa a ser nadie. Cuántos cambios."""
        ...
