"""Explicit memory archival (B4d, RF-024, PA-015).

RF-024 "Archivar: Retirar del contexto normal sin eliminar." Product S7
"Reglas de memoria": "Archivar retira un elemento del contexto ordinario sin
eliminar su contenido." Archiving never touches content, never creates a new
revision, and never redacts anything — it only moves ``Memory.status`` from
CURRENT to ARCHIVED, which is enough for ``MemoryRepository
.list_current_memories`` (and therefore ``ContextBuilder``) to stop
surfacing it, while ``get_memory``/``get_history`` keep it fully consultable
(``list_archived_memories`` recovers it explicitly).

Mirrors ``CorrectMemoryUseCase``: a caller never touches
``MemoryRepository``, ``EventRepository``, ``UnitOfWork``, SQLAlchemy, or
SQLite directly (AGENTS.md: dependency direction presentation -> application
-> domain). Nothing in the ordinary conversation flow
(``SendMessageUseCase``) calls this — the absence of any automatic call site
is what keeps a conversation from ever archiving a memory on its own
(PA-015's implicit negative case, mirroring PA-010/PA-011).

SIRIUS-ARQ-0.1 S8.1's transactional rule still applies: the audit event and
the status change are written through the same ``UnitOfWork`` and committed
together; any failure at any point leaves the transaction uncommitted, so
``UnitOfWork.__exit__`` rolls back everything — never an orphan event, never
a memory whose status moved without a persisted event to back it.
"""

from __future__ import annotations

from sirius.domain.event import MEMORY_ARCHIVED_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import Memory, ensure_can_archive
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "ArchiveMemoryUseCase",
    "MemoryNotArchivableError",
    "UnknownMemoryError",
]


class UnknownMemoryError(LookupError):
    """Raised when ``memory_id`` does not refer to an existing memory."""


class MemoryNotArchivableError(ValueError):
    """Raised when the memory exists but its current status forbids archiving."""


class ArchiveMemoryUseCase:
    """Archiva un recuerdo vigente, retirándolo del contexto ordinario (RF-024)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def archive(self, memory_id: int, *, message_id: int | None = None) -> Memory:
        """Move an existing CURRENT memory to ARCHIVED.

        ``message_id`` identifies the user message that gave the explicit
        archive order, when the caller has one; it is recorded on the audit
        event. Raises ``UnknownMemoryError`` for an unknown ``memory_id``, or
        ``MemoryNotArchivableError`` if the memory is not currently CURRENT
        (for example, already archived or deleted) — in both cases nothing
        is written: the check happens before the audit event is recorded,
        and the whole attempt still runs inside one transaction that only
        commits on success.

        Content, revisions and origin are never touched: only ``status``
        moves, so ``get_memory``/``get_history``/``GetMemoryOriginUseCase``
        keep working exactly as before for an archived memory.
        """
        with self._unit_of_work as uow:
            try:
                memory = uow.memory_repository.get_memory(memory_id)
            except Exception as exc:
                raise UnknownMemoryError(f"Recuerdo desconocido: {memory_id}") from exc

            try:
                ensure_can_archive(memory)
            except ValueError as exc:
                raise MemoryNotArchivableError(str(exc)) from exc

            uow.event_repository.append(
                event_type=MEMORY_ARCHIVED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            archived = uow.memory_repository.archive_memory(memory_id)
            uow.commit()

        return archived
