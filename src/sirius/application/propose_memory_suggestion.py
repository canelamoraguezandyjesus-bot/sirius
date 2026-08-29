"""Explicit or LLM-drafted memory suggestion proposal (M5, SIRIUS-ARQ-0.2 §3.5).

Mirrors ``ProposeDecisionUseCase`` (B4b) literally: validates non-empty
content, opens a ``MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE`` event, and creates
the suggestion as PENDING with that event as its ``source_event_id`` — all
within a single ``UnitOfWork`` transaction. A suggestion never becomes a real
``Memory`` here; only ``ConfirmMemorySuggestionUseCase`` does that, and only
on the user's explicit later action (§3.2/§3.5).

Nothing in the ordinary conversation flow (``SendMessageUseCase``) calls this
— per §3.2, the interface surface (§3.6) is the only caller, whether the
automatic path (an LLM-drafted suggestion attached to a completed turn) or
the manual "Proponer guardar…" action.
"""

from __future__ import annotations

from sirius.domain.event import MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory_suggestion import MemorySuggestion
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "InvalidMemorySuggestionProposalDataError",
    "ProposeMemorySuggestionUseCase",
]

INVALID_MEMORY_SUGGESTION_CONTENT_MESSAGE = "El contenido de la sugerencia no puede estar vacío."


class InvalidMemorySuggestionProposalDataError(ValueError):
    """Raised when the content of a proposed memory suggestion is empty."""


class ProposeMemorySuggestionUseCase:
    """Registra una sugerencia de memoria pendiente de confirmación (§3.5)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def propose(self, content: str, *, message_id: int | None = None) -> MemorySuggestion:
        """Create a new PENDING memory suggestion from a proposal.

        ``message_id`` identifies the user message (manual path) or the
        completed SIRIUS turn (automatic path) the proposal is attached to,
        when the caller has one; it becomes the source event's traceable
        link. Raises ``InvalidMemorySuggestionProposalDataError`` if
        ``content`` is empty after trimming, checked before any write.

        The event and the suggestion are created and committed within a
        single transaction: if either write fails, both are rolled back and
        nothing persists.
        """
        clean_content = content.strip()
        if not clean_content:
            raise InvalidMemorySuggestionProposalDataError(
                INVALID_MEMORY_SUGGESTION_CONTENT_MESSAGE
            )

        with self._unit_of_work as uow:
            event = uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            suggestion = uow.memory_suggestion_repository.create_suggestion(
                clean_content,
                source_event_id=event.id,
            )
            uow.commit()

        return suggestion
