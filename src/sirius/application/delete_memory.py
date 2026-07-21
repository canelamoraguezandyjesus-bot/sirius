"""Explicit memory deletion (B4d, RF-025, PA-016, SP-06, DR-012).

RF-025 "Eliminar: Aplicar la política de eliminación y confirmación
explícita." DR-012 "Archivo y eliminación": "Eliminar borra contenido
estructurado e índices y conserva solo un marcador mínimo sin contenido. El
mensaje fuente se redacta solo si el usuario lo solicita." Product S7
"Reglas de memoria": "Eliminar un recuerdo borra su contenido estructurado y
sus índices; conserva un evento mínimo de borrado sin el contenido
original. El mensaje de origen no se elimina automáticamente. El usuario
puede elegir también redactar su contenido, conservando solo secuencia,
fecha y marcador de eliminación. Las copias existentes no se reescriben al
eliminar datos."

Deletion is deliberately not modeled for decisions in this cut: see the
module docstring of ``sirius.domain.decision`` for why RF-025/DR-012's
elimination scope is limited to ``Memory``.

Two explicit gates must both be satisfied before anything is written:

- ``confirmed`` must be ``True`` (mirrors ``ApproveDecisionUseCase``/
  ``RestoreBackupUseCase``/``SupersedeDecisionUseCase``): a caller cannot
  delete merely by calling ``delete()`` with default arguments.
- ``source_message_choice`` (``sirius.domain.conversation
  .SourceMessageChoice``) must be an explicit, valid member — there is no
  default, so an absent choice fails with a ``TypeError`` before this
  function's body even runs, and an invalid one (not a real
  ``SourceMessageChoice`` member) fails with a typed error, both before any
  transaction opens.

``MemoryRepository.delete_memory`` (V4/B4d, already used by the SQLite
adapter) does the structured-content redaction this use case requires:
every revision's ``content`` becomes ``None`` — not just the current one —
so no earlier version of the deleted content survives anywhere
(``get_history`` keeps only the minimal marker: id, version, origin,
created_at). "Retirar índices derivados" is no longer a no-op: B6a adds
``knowledge_fts`` (FTS5, was explicitly out of scope for B4d) and syncs it
via a SQLite trigger on ``memory_revisions`` that fires on this exact
content-to-``NULL`` update, in the same transaction — this use case does
not call anything new to make that happen.

SIRIUS-ARQ-0.1 S8.1's transactional rule applies to the whole operation:
the audit event, the optional source-message redaction, and the memory's
content redaction are all written through the same ``UnitOfWork`` and
committed together. Ordering matters for atomicity coverage: the event is
recorded first, then the source message (if chosen), then the memory's
content — so a failure at any later step rolls back every earlier one in
the same attempt, including an already-applied message redaction.
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius.domain.conversation import SourceMessageChoice
from sirius.domain.event import MEMORY_DELETED_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import Memory, ensure_can_delete
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "DeleteMemoryUseCase",
    "DeletionNotConfirmedError",
    "InvalidSourceMessageChoiceError",
    "MemoryDeletionResult",
    "MemoryNotDeletableError",
    "SourceMessageChoice",
    "UnknownMemoryError",
]

NOT_CONFIRMED_MESSAGE = "Eliminar un recuerdo exige una confirmación explícita."
INVALID_SOURCE_MESSAGE_CHOICE_MESSAGE = (
    "Debes elegir explícitamente si se conserva o se redacta el mensaje fuente."
)
OLD_BACKUP_WARNING = (
    "Las copias de seguridad existentes no se reescriben al eliminar datos: "
    "restaurar una copia antigua puede reintroducir información que ya eliminaste."
)


class UnknownMemoryError(LookupError):
    """Raised when ``memory_id`` does not refer to an existing memory."""


class MemoryNotDeletableError(ValueError):
    """Raised when the memory exists but is already DELETED."""


class DeletionNotConfirmedError(ValueError):
    """Raised when deletion is requested without an explicit confirmation."""


class InvalidSourceMessageChoiceError(ValueError):
    """Raised when ``source_message_choice`` is not a valid ``SourceMessageChoice`` member."""


@dataclass(frozen=True, slots=True)
class MemoryDeletionResult:
    """Outcome of deleting a memory.

    ``old_backup_warning`` is SP-06/DR-012's approved warning, returned (not
    merely documented) so any caller can surface it without hardcoding its
    own copy — the presentation-layer wiring for this belongs to B4f, but
    the text itself is exposed here, by the use case, as this task requires.
    """

    memory: Memory
    old_backup_warning: str


class DeleteMemoryUseCase:
    """Elimina un recuerdo con confirmación explícita (RF-025)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def delete(
        self,
        memory_id: int,
        *,
        confirmed: bool,
        source_message_choice: SourceMessageChoice,
        message_id: int | None = None,
    ) -> MemoryDeletionResult:
        """Redact a memory's structured content across its full history.

        ``confirmed`` must be ``True`` or ``DeletionNotConfirmedError`` is
        raised before anything is touched. ``source_message_choice`` selects
        whether the memory's source message (if it has one, resolved via its
        current revision's recorded origin event) is left untouched
        (``PRESERVE``) or redacted alongside the memory
        (``REDACT``) — an invalid value raises
        ``InvalidSourceMessageChoiceError`` before any transaction opens.
        ``message_id`` identifies the user message that gave the explicit
        delete order, when the caller has one; it is recorded on the audit
        event (distinct from the memory's *source* message, which
        ``source_message_choice`` governs).

        Raises ``UnknownMemoryError`` for an unknown ``memory_id``, or
        ``MemoryNotDeletableError`` if the memory is already DELETED — in
        both cases nothing is written. A memory that is currently CURRENT or
        ARCHIVED can always be deleted.

        Choosing ``REDACT`` when the memory has no recorded source message
        (predates B4a, or its origin event has no linked message) is a
        no-op for the message: there is nothing to redact, and the memory
        deletion still proceeds normally.
        """
        if not confirmed:
            raise DeletionNotConfirmedError(NOT_CONFIRMED_MESSAGE)
        if not isinstance(source_message_choice, SourceMessageChoice):
            raise InvalidSourceMessageChoiceError(INVALID_SOURCE_MESSAGE_CHOICE_MESSAGE)

        with self._unit_of_work as uow:
            try:
                memory = uow.memory_repository.get_memory(memory_id)
            except Exception as exc:
                raise UnknownMemoryError(f"Recuerdo desconocido: {memory_id}") from exc

            try:
                ensure_can_delete(memory)
            except ValueError as exc:
                raise MemoryNotDeletableError(str(exc)) from exc

            uow.event_repository.append(
                event_type=MEMORY_DELETED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )

            if source_message_choice is SourceMessageChoice.REDACT:
                source_message_id = self._resolve_source_message_id(uow, memory)
                if source_message_id is not None:
                    uow.conversation_repository.redact_message(source_message_id)

            deleted = uow.memory_repository.delete_memory(memory_id)
            uow.commit()

        return MemoryDeletionResult(memory=deleted, old_backup_warning=OLD_BACKUP_WARNING)

    @staticmethod
    def _resolve_source_message_id(uow: UnitOfWork, memory: Memory) -> int | None:
        """Find the message that originated ``memory``'s current revision, if any."""
        source_event_id = memory.current_revision.source_event_id
        if source_event_id is None:
            return None
        event = uow.event_repository.get_source(source_event_id)
        if event is None:
            return None
        return event.message_id
