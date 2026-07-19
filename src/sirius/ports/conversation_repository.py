"""Persistence contract for the main conversation, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus


class ConversationRepository(Protocol):
    """Contract implemented by real and simulated conversation stores."""

    def get_or_create_main_conversation(self) -> Conversation:
        """Return the single main conversation, creating it if it does not exist yet."""
        ...

    def get_main_conversation(self) -> Conversation | None:
        """Return the main conversation if it exists, without creating it."""
        ...

    def append_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        *,
        operation_id: str | None = None,
        identity_version: int | None = None,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> Message:
        """Persist a new message at the end of the conversation and return it.

        Idempotent when ``operation_id`` is given: calling this again with
        the same ``(conversation_id, operation_id, role)`` returns the
        existing message instead of creating a duplicate — retrying an
        operation after a persistence failure never duplicates the USER
        message.
        """
        ...

    def list_messages(self, conversation_id: int) -> list[Message]:
        """Return every message of a conversation in stable creation order."""
        ...

    def get_message(self, message_id: int) -> Message | None:
        """Return a single message by id, or ``None`` if it does not exist.

        B4a (RF-021): lets an origin query "open" the message a memory's
        source event points at, without exposing the whole conversation.
        """
        ...

    def redact_message(self, message_id: int) -> Message:
        """Redact a single message's content (B4d, RF-025/DR-012).

        Sets ``content`` to ``None`` and ``status`` to ``REDACTED``,
        recording ``redacted_at``; ``sequence``, ``created_at`` and every
        other message stay exactly as they were — Product S7 "conservando
        solo secuencia, fecha y marcador de eliminación". Never touches any
        other message. Raises ``ValueError`` if ``message_id`` does not
        refer to an existing message.
        """
        ...
