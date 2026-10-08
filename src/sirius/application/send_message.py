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
from sirius.application.memory_commands import CommandAnswer, MemoryCommandService
from sirius.application.robot_conversation import ConversationSummaryService
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.conversation_mode import (
    ENTERING_SERIOUS_MODE,
    MODE_INSTRUCTIONS,
    ConversationMode,
    detect_mode_command,
)
from sirius.domain.facts import fact_lines, memory_note
from sirius.domain.identity import IdentityVersion
from sirius.domain.own_memory import render_own_memory
from sirius.domain.project import blockers_to_text
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import (
    MEMORY_SUGGESTION_DELIMITER,
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
)
from sirius.ports.robot_conversation import ConversationModeRepository, ReplyMarkRepository


@dataclass(frozen=True, slots=True)
class SendMessageResult:
    """Outcome of sending a message.

    ``sirius_message.status`` mirrors ``outcome``: ``COMPLETED`` only when
    the stream finished successfully; ``CANCELLED``/``FAILED`` messages
    carry whatever partial text streamed, kept for traceability.

    ``memory_suggestion`` (§3.2/§3.6, M6) mirrors ``LLMCompleted.memory_suggestion``
    verbatim, copied only when ``outcome`` is ``COMPLETED`` — this class never
    interprets it or calls ``ProposeMemorySuggestionUseCase`` itself; that
    decision belongs to the interface surface that orchestrates sending
    (§0.1.2), never to this use case.
    """

    outcome: MessageStatus
    user_message: Message
    sirius_message: Message
    #: ``None`` cuando el mensaje era una orden de memoria (pieza G, ADR-239): se
    #: contesta sin montar contexto ni llamar al modelo.
    context: Context | None
    error_kind: LLMErrorKind | None = None
    memory_suggestion: str | None = None


_NO_BLOCKERS_CONTEXT_TEXT = "Ninguno registrado."


def render_identity(version: IdentityVersion) -> str:
    """La parte de las instrucciones que es la identidad de Sirius.

    La misma en la charla y en la prueba a ciegas (pieza C de ADR-233): los
    modelos se comparan con la semilla con la que van a conversar.
    """
    return "\n".join(
        [
            f"# Identidad (v{version.version}): {version.name}",
            version.description,
            version.personality_instructions,
        ]
    )


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
    lines = [render_identity(context.identity.current_version), ""]
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
        *(
            f"- ({memory.id}) {memory.current_revision.content}{memory_note(memory)}"
            for memory in context.memories
        ),
        "",
    ]
    if context.owner_facts:
        # Pieza G (ADR-239): lo que se sabe de él va siempre, con su fecha y de dónde sale.
        lines += ["# Lo que sabes de tu dueño", *fact_lines(context.owner_facts), ""]
    for person, facts in context.people_facts:
        lines += [f"# Lo que sabes de {person}", *fact_lines(facts), ""]
    if context.recent_days:
        lines += [
            "# Los últimos días, como los resumiste al soñar",
            *(f"- {day:%d-%m-%Y}: {content}" for day, content in context.recent_days),
            "",
        ]
    if context.own_memory:
        # PA-R02-07: lo que ya dijo de esto, y lo que sí es y no es según sus marcas.
        lines += render_own_memory(context.own_memory)
    if context.summary is not None:
        # PA-R02-05: lo anterior a los mensajes recientes, ya resumido.
        lines += ["# Resumen de la charla", context.summary, ""]
    lines += [
        "# Mensajes recientes",
        *(f"[{message.role.value}] {message.content}" for message in context.recent_messages),
        "",
        "# Sugerir un recuerdo (opcional, SIRIUS-ARQ-0.2 §3.2)",
        "Si, y solo si, esta conversación contiene una preferencia o un dato "
        "del usuario que merezca guardarse como recuerdo duradero, añade al "
        "final de tu respuesta, dentro de la misma contestación, el texto "
        f"exacto {MEMORY_SUGGESTION_DELIMITER} seguido del contenido propuesto. "
        "No lo incluyas si no hay nada que proponer.",
    ]
    return "\n".join(lines)


class SendMessageUseCase:
    """Wires context building, the streaming LLM provider, and persistence."""

    def __init__(
        self,
        context_builder: ContextBuilder,
        conversation_repository: ConversationRepository,
        llm_provider: LLMProvider,
        *,
        mode_repository: ConversationModeRepository | None = None,
        reply_marks: ReplyMarkRepository | None = None,
        summary_service: ConversationSummaryService | None = None,
        reminder: str = "",
        memory_commands: MemoryCommandService | None = None,
    ) -> None:
        """Lo de la charla del robot (pieza D de ADR-233) es opcional: sin ello,
        este caso de uso hace exactamente lo de antes.

        - ``mode_repository``: «ponte serio» y «para» (PA-R02-04).
        - ``reply_marks``: apunta con qué modelo se dio cada respuesta, para sus
          marcas (PA-R02-06).
        - ``summary_service``: resume la charla larga al acabar el turno
          (PA-R02-05).
        - ``reminder``: el recordatorio de la semilla, lo último de cada
          petición (PA-R02-05).
        - ``memory_commands`` (pieza G, ADR-239): «olvida eso», «eso no es así» y
          «¿qué sabes de mí?» se contestan antes de montar el contexto, sin el
          modelo.
        """
        self._memory_commands = memory_commands
        self._mode_repository = mode_repository
        self._reply_marks = reply_marks
        self._summary_service = summary_service
        self._reminder = reminder.strip()
        self._context_builder = context_builder
        self._conversation_repository = conversation_repository
        self._llm_provider = llm_provider
        #: El modelo de cada respuesta en curso. Si la charla cambia de modelo a
        #: mitad de una, esa respuesta sigue con el suyo de principio a fin: se
        #: cancela, se atribuye y se resume con él (ronda 3 de Codex).
        self._in_flight: dict[str, LLMProvider] = {}

    def set_llm_provider(self, llm_provider: LLMProvider) -> None:
        """Swap the active provider (e.g. after B2a onboarding validates a key).

        Lets the composition root activate a freshly validated OpenAI
        provider in the same run, without rebuilding persistence or asking
        the user to restart Sirius.
        """
        self._llm_provider = llm_provider

    @property
    def llm_provider(self) -> LLMProvider:
        """El modelo con el que conversa ahora: las preguntas trampa se le hacen a él."""
        return self._llm_provider

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
        provider = self._llm_provider
        self._in_flight[operation_id] = provider
        try:
            return self._send(provider, user_text, operation_id, on_delta, extra_instructions)
        finally:
            self._in_flight.pop(operation_id, None)

    def _send(
        self,
        provider: LLMProvider,
        user_text: str,
        operation_id: str,
        on_delta: Callable[[str], None] | None,
        extra_instructions: str,
    ) -> SendMessageResult:
        if self._memory_commands is not None:
            # Antes que nada: una orden de memoria no puede llegar al modelo ni a
            # la búsqueda, que pediría la huella de la frase a olvidar.
            answer = self._memory_commands.handle(user_text)
            if answer is not None:
                return self._answer_without_model(answer, operation_id, on_delta)
        context = self._context_builder.build(user_text)

        conversation = self._conversation_repository.get_or_create_main_conversation()
        mode_block = self._mode_block(conversation.id, user_text)
        user_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.USER,
            user_text,
            operation_id=operation_id,
            status=MessageStatus.COMPLETED,
        )

        instructions = render_instructions(context)
        if mode_block:
            instructions = f"{instructions}\n\n{mode_block}"
        if extra_instructions.strip():
            instructions = f"{instructions}\n\n{extra_instructions.strip()}"
        if self._reminder:
            # Lo último que lee el modelo en cada turno: contra la deriva, la
            # semilla se le recuerda cerca del final (PA-R02-05).
            instructions = f"{instructions}\n\n{self._reminder}"
        request = LLMRequest(
            operation_id=operation_id,
            instructions=instructions,
            input_text=user_text,
        )

        accumulated: list[str] = []
        status = MessageStatus.FAILED
        error_kind: LLMErrorKind | None = None
        final_text = ""
        memory_suggestion: str | None = None

        for event in provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                status = MessageStatus.COMPLETED
                final_text = event.text
                memory_suggestion = event.memory_suggestion
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
        if status is MessageStatus.COMPLETED:
            if self._reply_marks is not None:
                model = getattr(provider, "model_name", None)
                self._reply_marks.record_model(
                    sirius_message.id, model if isinstance(model, str) else None
                )
            if self._summary_service is not None:
                self._summary_service.maybe_summarize(conversation.id, provider)

        return SendMessageResult(
            outcome=status,
            user_message=user_message,
            sirius_message=sirius_message,
            context=context,
            error_kind=error_kind,
            memory_suggestion=memory_suggestion,
        )

    def _answer_without_model(
        self,
        answer: CommandAnswer,
        operation_id: str,
        on_delta: Callable[[str], None] | None,
    ) -> SendMessageResult:
        """Guarda la orden y lo que contesta Sirius, sin modelo y sin contexto."""
        conversation = self._conversation_repository.get_or_create_main_conversation()
        user_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.USER,
            answer.stored_user_text,
            operation_id=operation_id,
            status=MessageStatus.COMPLETED,
        )
        if answer.after_store is not None:
            # Lo que la orden propone queda ligado a su mensaje, ya guardado.
            answer.after_store(user_message.id)
        if on_delta is not None:
            on_delta(answer.reply)
        sirius_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.SIRIUS,
            answer.reply,
            operation_id=operation_id,
            status=MessageStatus.COMPLETED,
        )
        return SendMessageResult(
            outcome=MessageStatus.COMPLETED,
            user_message=user_message,
            sirius_message=sirius_message,
            context=None,
        )

    def cancel(self, operation_id: str) -> None:
        """Request cooperative cancellation of an in-flight operation. Idempotent.

        Va al modelo que está dando esa respuesta, aunque la charla ya haya cambiado
        de modelo; si no hay respuesta en curso con ese id, al modelo de ahora.
        """
        self._in_flight.get(operation_id, self._llm_provider).cancel(operation_id)

    def _mode_block(self, conversation_id: int, user_text: str) -> str:
        """Aplica la orden de modo del mensaje, si la hay, y devuelve lo que toca añadir.

        La orden vale desde este mismo turno: a «ponte serio» ya contesta serio,
        después de vacilarle, y a «ya puedes volver a ser tú» ya contesta como él.
        """
        if self._mode_repository is None:
            return ""
        command = detect_mode_command(user_text)
        if command is not None:
            self._mode_repository.set_mode(conversation_id, command)
        mode = self._mode_repository.get_mode(conversation_id)
        block = MODE_INSTRUCTIONS[mode]
        if mode is ConversationMode.SERIO and command is ConversationMode.SERIO:
            block = f"{block}\n{ENTERING_SERIOUS_MODE}"
        return block
