"""Explicit, manual memory creation (B4a, RF-019, PA-010).

Mirrors ``InitialProjectUseCase``: a small, explicit contract so a future
caller never touches ``MemoryRepository``, ``EventRepository``,
``UnitOfWork``, SQLAlchemy, or SQLite directly (AGENTS.md: dependency
direction presentation -> application -> domain).

RF-019 "Crear un recuerdo únicamente por orden o confirmación explícita":
this use case is never invoked by the ordinary conversation flow
(``SendMessageUseCase`` does not call it). Memory creation only ever happens
when a caller deliberately calls ``save()`` — that absence of any automatic
call site is what keeps an ordinary conversation from ever creating memory
on its own (PA-010's negative case).

SIRIUS-ARQ-0.1 S8.1 requires "evento y cambio de memoria... en la misma
transacción": the event and the memory (with its first revision) are written
through the same ``UnitOfWork``, and ``commit()`` runs only after both writes
succeed. Any exception from either write leaves the transaction uncommitted,
so ``UnitOfWork.__exit__`` rolls back everything — never an orphan event,
never a memory whose ``source_event_id`` points at nothing.
"""

from __future__ import annotations

from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import Memory, ensure_valid_subject_key
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "INVALID_MANUAL_MEMORY_CONTENT_MESSAGE",
    "MANUAL_MEMORY_ORIGIN",
    "InvalidManualMemoryDataError",
    "SaveManualMemoryUseCase",
]

MANUAL_MEMORY_ORIGIN = "Guardado manual del usuario"
INVALID_MANUAL_MEMORY_CONTENT_MESSAGE = "El contenido del recuerdo no puede estar vacío."


class InvalidManualMemoryDataError(ValueError):
    """Raised when the content to remember is empty after trimming."""


class SaveManualMemoryUseCase:
    """Guarda manualmente una preferencia o un hecho como recuerdo (RF-019)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def save(
        self,
        content: str,
        *,
        message_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        """Create a new memory from an explicit save order.

        ``message_id`` identifies the user message that gave the explicit
        order, when the caller has one; it becomes the real, queryable
        origin link RF-021 opens later. Raises
        ``InvalidManualMemoryDataError`` if ``content`` is empty after
        trimming, checked before any write.

        ``subject_key``/``project_id`` (B4e) are the optional explicit
        subject/project boundary ``sirius.domain.knowledge_precedence``
        compares this memory against others on; omitted, this memory never
        participates in precedence/conflict detection. When given,
        ``subject_key`` must be non-empty after trimming — checked before
        any write, same as ``content``.

        The event and the memory (with its first revision) are created and
        committed within a single transaction: if either write fails, both
        are rolled back and nothing persists.
        """
        clean_content = content.strip()
        if not clean_content:
            raise InvalidManualMemoryDataError(INVALID_MANUAL_MEMORY_CONTENT_MESSAGE)
        if subject_key is not None:
            try:
                ensure_valid_subject_key(subject_key)
            except ValueError as exc:
                raise InvalidManualMemoryDataError(str(exc)) from exc

        with self._unit_of_work as uow:
            event = uow.event_repository.append(
                event_type=MANUAL_MEMORY_SAVE_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            memory = uow.memory_repository.create_memory(
                clean_content,
                MANUAL_MEMORY_ORIGIN,
                source_event_id=event.id,
                subject_key=subject_key,
                project_id=project_id,
            )
            uow.commit()

        return memory
