"""Use case: send a user message, stream Sirius's response, persist both.

Persistence strategy (explicit, tested — not a single shared transaction):
the user's message and Sirius's response are each persisted through their
own independently-committed write (every ``ConversationRepository`` write
already is). This codebase has no cross-repository Unit of Work yet (the
architecture document reserves that contract for a later vertical), so
introducing one now would be more machinery than this vertical needs.

Cancellation/failure semantics follow SIRIUS-ARQ-0.1 S5.1 exactly: "Al
terminar, se guarda la respuesta final... y estado COMPLETADO. Ante
cancelación o fallo, se conserva el contenido parcial con estado CANCELADO o
FALLIDO y no se usa como respuesta completa." So:
  - a failure while building the context leaves nothing persisted;
  - a failure persisting the user's message leaves nothing persisted;
  - a provider failure or cancellation persists Sirius's message with
    whatever partial text streamed, tagged ``FAILED``/``CANCELLED`` — never
    ``COMPLETED``, so it is excluded from a future context (see
    ``ContextBuilder``) while remaining visible in the conversation history
    for traceability;
  - a failure persisting Sirius's reply still leaves the user's message
    persisted and no partial/dangling Sirius row (that single write is still
    atomic);
  - the USER and SIRIUS message of one turn share ``operation_id``, and
    ``ConversationRepository.append_message`` is idempotent per
    ``(conversation, operation_id, role)``: retrying the same operation_id
    after a persistence failure never duplicates the USER message.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sirius.application.context import Context, ContextBuilder
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.project import blockers_to_text
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
)


@dataclass(frozen=True, slots=True)
class SendMessageResult:
    """Outcome of sending a message.

    ``sirius_message.status`` mirrors ``outcome``: ``COMPLETED`` only when
    the stream finished successfully; ``CANCELLED``/``FAILED`` messages
    carry whatever partial text streamed, kept for traceability.
    """

    outcome: MessageStatus
    user_message: Message
    sirius_message: Message
    context: Context
    error_kind: LLMErrorKind | None = None


_NO_BLOCKERS_CONTEXT_TEXT = "Ninguno registrado."


def render_instructions(context: Context) -> str:
    """Render an already-built Context into the instructions text for the provider.

    Deterministic given the same Context; never queries a repository itself.
    The "# Proyecto activo" section is omitted entirely when
    ``context.project`` is ``None`` (SIRIUS-ARQ-0.1 S3,
    ``LLMRequest.project_context: str | None``) — no placeholder text, no
    fabricated project. "# Decisiones vigentes relacionadas" (B6d, S6.1)
    always renders, with an empty body when ``context.decisions`` is empty —
    the safe state when none are relevant or none exist, never a fabricated
    decision.
    """
    lines = [
        f"# Identidad (v{context.identity.current_version.version}): "
        f"{context.identity.current_version.name}",
        context.identity.current_version.description,
        context.identity.current_version.personality_instructions,
        "",
    ]
    if context.project is not None:
        revision = context.project.current_revision
        assert revision is not None  # ContextBuilder only resolves a configured project
        lines += [
            "# Proyecto activo",
            f"Nombre: {context.project.name}",
            f"Objetivo: {revision.objective}",
            f"Estado: {revision.state_summary}",
            f"Bloqueos: {blockers_to_text(revision.blockers) or _NO_BLOCKERS_CONTEXT_TEXT}",
            f"Siguiente paso: {revision.next_step}",
            "",
        ]
    lines += [
        "# Decisiones vigentes relacionadas",
        *(
            f"- ({decision.id}) [{decision.subject}] {decision.current_revision.content}"
            for decision in context.decisions
        ),
        "",
        "# Memorias vigentes",
        *(f"- ({memory.id}) {memory.current_revision.content}" for memory in context.memories),
        "",
        "# Mensajes recientes",
        *(f"[{message.role.value}] {message.content}" for message in context.recent_messages),
    ]
    return "\n".join(lines)


class SendMessageUseCase:
    """Wires context building, the streaming LLM provider, and persistence."""

    def __init__(
        self,
        context_builder: ContextBuilder,
        conversation_repository: ConversationRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._context_builder = context_builder
        self._conversation_repository = conversation_repository
        self._llm_provider = llm_provider

    def set_llm_provider(self, llm_provider: LLMProvider) -> None:
        """Swap the active provider (e.g. after B2a onboarding validates a key).

        Lets the composition root activate a freshly validated OpenAI
        provider in the same run, without rebuilding persistence or asking
        the user to restart Sirius.
        """
        self._llm_provider = llm_provider

    def send_message(
        self,
        user_text: str,
        *,
        operation_id: str | None = None,
        on_delta: Callable[[str], None] | None = None,
        extra_instructions: str = "",
    ) -> SendMessageResult:
        """Persist the user's message, stream Sirius's reply, and persist its outcome.

        ``on_delta`` is invoked synchronously, once per text fragment, in the
        caller's thread — it never touches persistence or Qt itself.

        ``extra_instructions`` es una indicación **efímera** que se añade al
        final de las instrucciones de esta petición y nada más: no se guarda en
        la conversación, no se guarda en la memoria y no crea una versión nueva
        de la identidad. Va al final a propósito, para que no pueda desplazar ni
        reinterpretar la identidad canónica que la precede. Model Studio la usa
        para pedir respuestas breves mientras se graba (#126).
        """
        operation_id = operation_id or str(uuid.uuid4())
        context = self._context_builder.build(user_text)

        conversation = self._conversation_repository.get_or_create_main_conversation()
        user_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.USER,
            user_text,
            operation_id=operation_id,
            status=MessageStatus.COMPLETED,
        )

        instructions = render_instructions(context)
        if extra_instructions.strip():
            instructions = f"{instructions}\n\n{extra_instructions.strip()}"
        request = LLMRequest(
            operation_id=operation_id,
            instructions=instructions,
            input_text=user_text,
        )

        accumulated: list[str] = []
        status = MessageStatus.FAILED
        error_kind: LLMErrorKind | None = None
        final_text = ""

        for event in self._llm_provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                status = MessageStatus.COMPLETED
                final_text = event.text
            elif isinstance(event, LLMCancelled):
                status = MessageStatus.CANCELLED
                final_text = event.partial_text
            elif isinstance(event, LLMError):
                status = MessageStatus.FAILED
                error_kind = event.kind
                final_text = event.partial_text
            else:
                accumulated.append(event.text)
                if on_delta is not None:
                    on_delta(event.text)

        if not final_text and status is not MessageStatus.COMPLETED:
            final_text = "".join(accumulated)

        sirius_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.SIRIUS,
            final_text,
            operation_id=operation_id,
            identity_version=context.identity.current_version.version,
            status=status,
        )

        return SendMessageResult(
            outcome=status,
            user_message=user_message,
            sirius_message=sirius_message,
            context=context,
            error_kind=error_kind,
        )

    def cancel(self, operation_id: str) -> None:
        """Request cooperative cancellation of an in-flight operation. Idempotent."""
        self._llm_provider.cancel(operation_id)
