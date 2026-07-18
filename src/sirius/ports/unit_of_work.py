"""Persistence contract that groups repositories into one atomic transaction.

SIRIUS-ARQ-0.1 S4 defines ``UnitOfWork`` as ``begin()``, ``commit()``,
``rollback()`` that "agrupa repositorios en una transacción": one shared
session/transaction spanning every repository it exposes, so a caller that
writes through more than one of them either commits all of those writes
together or rolls back all of them. S8.1 spells out the concrete rule this
port exists to satisfy: "Evento y cambio de memoria se guardan en la misma
transacción."

B4a's only cross-repository write is ``SaveManualMemoryUseCase`` (event +
memory + first revision); this port therefore exposes only the two
repositories that operation needs.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sirius.ports.event_repository import EventRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["UnitOfWork"]


class UnitOfWork(Protocol):
    """A single transaction shared by the repositories it exposes.

    Used as a context manager: entering (``begin()``, done by ``__enter__``)
    opens the shared transaction and binds ``memory_repository``/
    ``event_repository`` to it; exiting without a prior ``commit()`` rolls
    back everything written through either repository — mirroring
    ``sirius.adapters.persistence.database.session_scope`` but spanning more
    than one repository instead of committing after a single call.
    """

    @property
    def memory_repository(self) -> MemoryRepository:
        """The memory repository bound to this unit of work's shared transaction."""
        ...

    @property
    def event_repository(self) -> EventRepository:
        """The event repository bound to this unit of work's shared transaction."""
        ...

    def __enter__(self) -> Self:
        """Begin the shared transaction and return ``self``."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back the shared transaction unless ``commit()`` already ran."""
        ...

    def commit(self) -> None:
        """Confirm every write made through this unit of work's repositories."""
        ...

    def rollback(self) -> None:
        """Discard every write made through this unit of work's repositories."""
        ...
