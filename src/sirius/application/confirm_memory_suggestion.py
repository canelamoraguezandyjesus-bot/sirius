"""Explicit confirmation of a pending memory suggestion (M5, SIRIUS-ARQ-0.2 §3.5).

Mirrors ``SaveManualMemoryUseCase`` (B4a) for the part that creates the real
memory: within a single ``UnitOfWork`` transaction, this fetches the
suggestion, checks ``ensure_can_confirm``, opens a
``MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE`` event, creates the real ``Memory``
from the suggestion's own content with a traceable origin (same mechanism as
``GetMemoryOriginUseCase``), and finally marks the suggestion CONFIRMED,
linking the memory it produced. Confirming is the only path from a pending
suggestion to a real, CURRENT memory (§4.4 of the Product definition).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.domain.event import MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import Memory
from sirius.domain.memory_suggestion import ensure_can_confirm
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "CONFIRMED_MEMORY_SUGGESTION_ORIGIN",
    "ConfirmMemorySuggestionUseCase",
]

CONFIRMED_MEMORY_SUGGESTION_ORIGIN = "Sugerencia confirmada por el usuario"


class ConfirmMemorySuggestionUseCase:
    """Confirma una sugerencia pendiente, materializándola como recuerdo real (§3.5, §4.4)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def confirm(self, suggestion_id: int) -> Memory:
        """Confirm a PENDING suggestion, creating the real ``Memory`` it becomes.

        Raises whatever ``ensure_can_confirm`` raises (a plain ``ValueError``)
        if the suggestion is not PENDING — checked after fetching it, inside
        the transaction, so a stale or already-resolved suggestion never
        produces a memory.

        The event, the memory (with its first revision), and the suggestion's
        CONFIRMED transition are all written and committed within a single
        transaction: if any write fails, all of them are rolled back and
        nothing persists.
        """
        with self._unit_of_work as uow:
            suggestion = uow.memory_suggestion_repository.get_suggestion(suggestion_id)
            ensure_can_confirm(suggestion)

            event = uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=None,
            )
            memory = uow.memory_repository.create_memory(
                suggestion.content,
                CONFIRMED_MEMORY_SUGGESTION_ORIGIN,
                source_event_id=event.id,
                subject_key=suggestion.subject_key,
                project_id=suggestion.project_id,
            )
            uow.memory_suggestion_repository.confirm_suggestion(
                suggestion_id,
                resulting_memory_id=memory.id,
                resolved_at=datetime.now(UTC),
            )
            uow.commit()

        return memory
