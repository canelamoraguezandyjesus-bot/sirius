"""Explicit, manual memory creation (B4a, RF-019, PA-010).

Mirrors ``InitialProjectUseCase``: a small, explicit contract so a future
caller never touches ``MemoryRepository``, ``EventRepository``, SQLAlchemy,
or SQLite directly (AGENTS.md: dependency direction presentation ->
application -> domain).

RF-019 "Crear un recuerdo únicamente por orden o confirmación explícita":
this use case is never invoked by the ordinary conversation flow
(``SendMessageUseCase`` does not call it). Memory creation only ever happens
when a caller deliberately calls ``save()`` — that absence of any automatic
call site is what keeps an ordinary conversation from ever creating memory
on its own (PA-010's negative case).

The event is recorded before the memory: SIRIUS-ARQ-0.1 S8.1 wants "evento y
cambio de memoria... en la misma transacción", but neither repository here
shares a session with the other (no ``UnitOfWork`` spans repositories in
this codebase yet — introducing one is out of B4a's scope). Recording the
event first means the one possible failure window (event succeeds, then the
memory write fails) only ever leaves a harmless orphan event; it can never
leave a memory whose ``source_event_id`` points at nothing.
"""

from __future__ import annotations

from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import Memory
from sirius.ports.event_repository import EventRepository
from sirius.ports.memory_repository import MemoryRepository

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

    def __init__(
        self, memory_repository: MemoryRepository, event_repository: EventRepository
    ) -> None:
        self._memory_repository = memory_repository
        self._event_repository = event_repository

    def save(self, content: str, *, message_id: int | None = None) -> Memory:
        """Create a new memory from an explicit save order.

        ``message_id`` identifies the user message that gave the explicit
        order, when the caller has one; it becomes the real, queryable
        origin link RF-021 opens later. Raises
        ``InvalidManualMemoryDataError`` if ``content`` is empty after
        trimming, checked before any write.
        """
        clean_content = content.strip()
        if not clean_content:
            raise InvalidManualMemoryDataError(INVALID_MANUAL_MEMORY_CONTENT_MESSAGE)

        event = self._event_repository.append(
            event_type=MANUAL_MEMORY_SAVE_EVENT_TYPE,
            actor=USER_ACTOR,
            message_id=message_id,
        )
        return self._memory_repository.create_memory(
            clean_content,
            MANUAL_MEMORY_ORIGIN,
            source_event_id=event.id,
        )
