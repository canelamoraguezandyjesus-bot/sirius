"""Explicit memory correction (B4c, RF-022, PA-012).

Consolidates the correction ``MemoryRepository.correct_memory`` already
implements (V4) under the same explicit, transactional contract B4a
established for creation: a caller never touches ``MemoryRepository``,
``EventRepository``, ``UnitOfWork``, SQLAlchemy, or SQLite directly
(AGENTS.md: dependency direction presentation -> application -> domain).

RF-022 "Corregir: Crear nueva versión y desactivar la anterior." A
correction never overwrites the current revision's content: it creates a
new, immutable revision, moves the authoritative ``current_revision``
pointer to it, and keeps the previous revision consultable as history
(``MemoryRepository.get_history``) — behaviour ``correct_memory`` already
implements. What this use case adds is the missing piece: a real, mandatory
origin event, and the same single-transaction guarantee
``SaveManualMemoryUseCase`` gives creation.

SIRIUS-ARQ-0.1 S8.1 requires "evento y cambio de memoria... en la misma
transacción" — a correction is exactly such a change. The existence check,
the correctability check, the event, and the new revision are all written
through the same ``UnitOfWork`` and committed together; any failure at any
point leaves the transaction uncommitted, so ``UnitOfWork.__exit__`` rolls
back everything — never an orphan event, never a memory whose pointer moved
without a persisted revision to back it.
"""

from __future__ import annotations

from sirius.domain.event import MEMORY_CORRECTED_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import Memory, ensure_can_correct
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "INVALID_MEMORY_CORRECTION_CONTENT_MESSAGE",
    "MEMORY_CORRECTION_ORIGIN",
    "CorrectMemoryUseCase",
    "InvalidMemoryCorrectionDataError",
    "MemoryNotCorrectableError",
    "UnknownMemoryError",
]

MEMORY_CORRECTION_ORIGIN = "Corrección manual del usuario"
INVALID_MEMORY_CORRECTION_CONTENT_MESSAGE = "El contenido corregido no puede estar vacío."


class InvalidMemoryCorrectionDataError(ValueError):
    """Raised when the corrected content is empty after trimming."""


class UnknownMemoryError(LookupError):
    """Raised when ``memory_id`` does not refer to an existing memory."""


class MemoryNotCorrectableError(ValueError):
    """Raised when the memory exists but its current status forbids correction."""


class CorrectMemoryUseCase:
    """Corrige un recuerdo existente creando una nueva revisión (RF-022)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def correct(self, memory_id: int, content: str, *, message_id: int | None = None) -> Memory:
        """Create a new, current revision for an existing memory.

        ``message_id`` identifies the user message that gave the explicit
        correction order, when the caller has one; it becomes the real,
        queryable origin link of the new revision. Raises
        ``InvalidMemoryCorrectionDataError`` if ``content`` is empty after
        trimming, checked before any write. Raises ``UnknownMemoryError`` for
        an unknown ``memory_id``, or ``MemoryNotCorrectableError`` if the
        memory is not currently CURRENT (for example, already archived or
        deleted) — in both cases nothing is written: the check happens
        before the audit event is recorded, and the whole attempt still runs
        inside one transaction that only commits on success.

        The previous revision is never overwritten: it stays exactly as it
        was, consultable as history, while the new revision becomes the only
        one the authoritative pointer marks current.
        """
        clean_content = content.strip()
        if not clean_content:
            raise InvalidMemoryCorrectionDataError(INVALID_MEMORY_CORRECTION_CONTENT_MESSAGE)

        with self._unit_of_work as uow:
            try:
                memory = uow.memory_repository.get_memory(memory_id)
            except Exception as exc:
                raise UnknownMemoryError(f"Recuerdo desconocido: {memory_id}") from exc

            try:
                ensure_can_correct(memory)
            except ValueError as exc:
                raise MemoryNotCorrectableError(str(exc)) from exc

            event = uow.event_repository.append(
                event_type=MEMORY_CORRECTED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            corrected = uow.memory_repository.correct_memory(
                memory_id,
                clean_content,
                MEMORY_CORRECTION_ORIGIN,
                source_event_id=event.id,
            )
            uow.commit()

        return corrected
