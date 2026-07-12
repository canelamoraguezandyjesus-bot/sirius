"""Use case: send a user message, get Sirius's response, persist both.

Persistence strategy (explicit, tested — see requirement 9's alternative to a
single atomic transaction): the user's message and Sirius's response are each
persisted through their own independently-committed transaction (as every
``ConversationRepository`` write already is). This codebase has no
cross-repository Unit of Work yet (the architecture document reserves that
contract for a later vertical), so introducing one now would be more
machinery than V5 needs. The resulting, tested behaviour is:
  - a failure while building the context leaves nothing persisted;
  - a failure in the provider leaves exactly the user's message persisted;
  - a failure persisting Sirius's reply leaves the user's message persisted
    and no partial/dangling Sirius row (that single write is still atomic).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sirius.application.context import Context, ContextBuilder
from sirius.domain.conversation import Message, MessageRole
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import LLMProvider, LLMRequest


@dataclass(frozen=True, slots=True)
class SendMessageResult:
    """Outcome of sending a message: the persisted turn and the context used."""

    user_message: Message
    sirius_message: Message
    context: Context


def render_instructions(context: Context) -> str:
    """Render an already-built Context into the instructions text for the provider.

    Deterministic given the same Context; never queries a repository itself.
    """
    lines = [
        f"# Identidad (v{context.identity.current_version.version}): "
        f"{context.identity.current_version.name}",
        context.identity.current_version.description,
        context.identity.current_version.personality_instructions,
        "",
        "# Proyecto activo",
        f"Objetivo: {context.project.objective}",
        f"Estado: {context.project.current_state}",
        f"Siguiente paso: {context.project.next_step}",
        "",
        "# Memorias vigentes",
        *(f"- ({memory.id}) {memory.current_revision.content}" for memory in context.memories),
        "",
        "# Mensajes recientes",
        *(f"[{message.role.value}] {message.content}" for message in context.recent_messages),
    ]
    return "\n".join(lines)


class SendMessageUseCase:
    """Minimal use case wiring context building, the LLM provider, and persistence."""

    def __init__(
        self,
        context_builder: ContextBuilder,
        conversation_repository: ConversationRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._context_builder = context_builder
        self._conversation_repository = conversation_repository
        self._llm_provider = llm_provider

    def send_message(self, user_text: str) -> SendMessageResult:
        context = self._context_builder.build(user_text)

        conversation = self._conversation_repository.get_or_create_main_conversation()
        user_message = self._conversation_repository.append_message(
            conversation.id, MessageRole.USER, user_text
        )

        request = LLMRequest(
            operation_id=str(uuid.uuid4()),
            instructions=render_instructions(context),
            input_text=user_text,
        )
        response_text = "".join(chunk.text for chunk in self._llm_provider.stream_response(request))

        sirius_message = self._conversation_repository.append_message(
            conversation.id, MessageRole.SIRIUS, response_text
        )

        return SendMessageResult(
            user_message=user_message,
            sirius_message=sirius_message,
            context=context,
        )
