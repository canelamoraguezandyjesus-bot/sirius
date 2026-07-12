"""Use case: read the main conversation's message history."""

from __future__ import annotations

from sirius.domain.conversation import Message
from sirius.ports.conversation_repository import ConversationRepository


class ConversationNotInitializedError(RuntimeError):
    """Raised when the main conversation does not exist yet.

    Seeding it is the exclusive responsibility of ``initialize_persistence()``;
    this use case only ever reads.
    """


class GetConversationHistoryUseCase:
    """Minimal read-only use case wrapping the conversation port."""

    def __init__(self, conversation_repository: ConversationRepository) -> None:
        self._conversation_repository = conversation_repository

    def get_history(self) -> list[Message]:
        """Return every message of the main conversation, in stable order."""
        conversation = self._conversation_repository.get_main_conversation()
        if conversation is None:
            msg = "No main conversation found; has initialize_persistence() run?"
            raise ConversationNotInitializedError(msg)
        return self._conversation_repository.list_messages(conversation.id)
