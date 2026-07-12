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
