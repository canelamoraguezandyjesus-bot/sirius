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

import threading
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sirius.application.age import CareWatch, care_block
from sirius.application.context import Context, ContextBuilder
from sirius.application.memory_commands import CommandAnswer, CommandReply, MemoryCommandService
from sirius.application.presence import presence_block
from sirius.application.robot_conversation import (
    ConversationSummaryService,
    summary_operation_id,
)
from sirius.application.seed_examples import SeedExamplePicker
from sirius.application.sight_log import sight_block
from sirius.domain.conversation import Message, MessageRole, MessageStatus, cut_note
from sirius.domain.conversation_mode import (
    ENTERING_SERIOUS_MODE,
    MODE_INSTRUCTIONS,
    ConversationMode,
    detect_mode_command,
)
from sirius.domain.facts import fact_lines, memory_note
from sirius.domain.gestures import Gesture, GestureFilter, Piece, gestures_line, strip_gestures
from sirius.domain.identity import IdentityVersion, SeedExample
from sirius.domain.own_memory import render_own_memory
from sirius.domain.project import blockers_to_text
from sirius.domain.robot_seed import EXAMPLES_FRAME, example_turns, render_examples
from sirius.infrastructure.logging import get_logger
from sirius.ports.age import AgeReading
from sirius.ports.conversation_repository import (
    ConversationRepository,
    CutRecorder,
    ReplyRewriter,
)
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.llm import (
    MEMORY_SUGGESTION_DELIMITER,
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
    runs_on_this_computer,
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

_logger = get_logger(__name__)

#: Lo que se le pide al modelo para que Sirius diga a su manera lo que hizo una orden
#: de memoria (ADR-240). Solo ve una frase fija: nada de lo olvidado ni de la orden.
COMMAND_VOICE_TASK = (
    "# Una orden sobre tu memoria\n"
    "Tu dueño te ha pedido algo sobre tu memoria y ya está hecho. Díselo a tu manera, en "
    "una o dos frases cortas. Solo sabes lo que te pone abajo: no añadas datos ni adivines "
    "de qué iba."
)


def render_identity(
    version: IdentityVersion,
    examples: Sequence[SeedExample] = (),
    *,
    frame: str = EXAMPLES_FRAME,
) -> str:
    """La parte de las instrucciones que es la identidad de Sirius.

    La misma en la charla y en la prueba a ciegas (pieza C de ADR-233): los
    modelos se comparan con la semilla con la que van a conversar. ``examples``
    son los ejemplos de la semilla que lleva esta petición, con ``frame`` delante
    (ADR-240): en la charla, los tres que más se parecen a lo que se habla.
    """
    lines = [
        f"# Identidad (v{version.version}): {version.name}",
        version.description,
        version.personality_instructions,
    ]
    block = render_examples(examples, frame)
    if block:
        lines += ["", block]
    return "\n".join(lines)


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
    lines = [render_identity(context.identity.current_version, context.seed_examples), ""]
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
        *(render_recent_message(message) for message in context.recent_messages),
        "",
        # Pieza C de la 0.4 (ADR-261): la lista cerrada de gestos que hace su cara.
        gestures_line(),
        "",
        "# Sugerir un recuerdo (opcional, SIRIUS-ARQ-0.2 §3.2)",
        "Si, y solo si, esta conversación contiene una preferencia o un dato "
        "del usuario que merezca guardarse como recuerdo duradero, añade al "
        "final de tu respuesta, dentro de la misma contestación, el texto "
        f"exacto {MEMORY_SUGGESTION_DELIMITER} seguido del contenido propuesto. "
        "No lo incluyas si no hay nada que proponer.",
    ]
    return "\n".join(lines)


def render_recent_message(message: Message) -> str:
    """Un mensaje reciente, como lo lee el modelo: quién y qué; y, si a Sirius le cortaron
    esa respuesta, hasta dónde se oyó (``cut_note``, ADR-245)."""
    line = f"[{message.role.value}] {message.content}"
    note = cut_note(message)
    return line if note is None else f"{line}\n{note}"


def recent_message_turns(messages: Sequence[Message]) -> tuple[str, ...]:
    """Cómo empieza cada mensaje de ``render_recent_message`` que hay en ``messages``, sin
    repetir. También son paradas, por lo mismo que los turnos de los ejemplos (incidencia
    #700), y solo de los que están: una parada que no empieza ningún turno de lo que lee
    el modelo podría cortar una respuesta buena (ronda 1 de Codex sobre la PR #701)."""
    return tuple(dict.fromkeys(f"\n[{message.role.value}]" for message in messages))


def context_turns(context: Context) -> tuple[str, ...]:
    """Las paradas de una petición con ``render_instructions(context)``: los comienzos de
    turno de los ejemplos y de los mensajes recientes que lleva (incidencia #700)."""
    return example_turns(context.seed_examples) + recent_message_turns(context.recent_messages)


class CommandVoice:
    """La petición con la que Sirius dice a su manera lo que hizo una orden de memoria.

    Lleva la identidad, con los ejemplos que más se parecen a la frase, el modo de la
    charla, la tarea y el recordatorio; y, con un crío, un anciano o alguien cuya edad no
    se sabe delante, la regla de no insultar (``care``, ronda 1 de Codex sobre la PR
    #703): esta frase también la escribe el modelo. La frase es fija y no sale de la base
    ni del mensaje de la orden: el modelo nunca ve lo olvidado (ADR-240). ``replies``
    cambia la respuesta ya guardada con la frase de siempre por la que dice con su voz.
    """

    def __init__(
        self,
        identities: IdentityRepository,
        examples: SeedExamplePicker,
        replies: ReplyRewriter,
    ) -> None:
        self._identities = identities
        self._examples = examples
        self.replies = replies

    def request(
        self, said: str, *, mode_block: str, reminder: str, operation_id: str, care: str = ""
    ) -> LLMRequest | None:
        identity = self._identities.get_current_identity()
        if identity is None:
            return None
        version = identity.current_version
        examples = self._examples.pick(version.examples, said)
        parts = [render_identity(version, examples)]
        if mode_block:
            parts.append(mode_block)
        parts.append(COMMAND_VOICE_TASK)
        if care:
            parts.append(care)
        if reminder:
            parts.append(reminder)
        return LLMRequest(
            operation_id=operation_id,
            instructions="\n\n".join(parts),
            input_text=f"Lo que le tienes que decir: «{said}»",
            stop=example_turns(examples),
        )


class ChatLeavesThisComputer(RuntimeError):
    """Se pidió que nada saliera de este ordenador y la charla va a un modelo de fuera."""


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
        command_voice: CommandVoice | None = None,
        cuts: CutRecorder | None = None,
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
          «¿qué sabes de mí?» se cumplen antes de montar el contexto, sin el
          modelo.
        - ``command_voice`` (ADR-240): con él, Sirius dice con su voz lo que hizo la
          orden, sin que el modelo vea lo olvidado; sin él, o si el modelo no
          contesta, la frase de siempre.
        - ``cuts`` (ADR-245): donde se apunta hasta dónde se oyó una respuesta que le
          cortaron mientras la decía; sin él, no se apunta.
        """
        self._memory_commands = memory_commands
        self._command_voice = command_voice
        self._cuts = cuts
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
        #: Las respuestas que le cortaron por voz mientras las escribía (ADR-254).
        self._cut_operations: set[str] = set()
        self._cut_lock = threading.Lock()
        #: A quiénes tiene delante, de la vista (pieza E de la 0.4, ADR-263); sin ella, no
        #: se le dice.
        self._presence: Callable[[], Sequence[str | None] | None] | None = None
        self._presence_failed = False
        #: Si hay que cortarse, con la edad que aparentan los que tiene delante, de la
        #: vista (pieza F de la 0.4, ADR-264); sin ella, no se mira.
        self._care_watch = CareWatch()
        #: Lo que recuerda haber visto, como texto (pieza G de la 0.4, ADR-265); sin ello, no
        #: se le dice.
        self._seen: Callable[[], Sequence[str]] | None = None
        self._seen_failed = False

    def set_presence(self, in_front: Callable[[], Sequence[str | None] | None]) -> None:
        """Le dice de dónde saber a quiénes tiene delante: de la vista, su nombre o ``None``
        por cada uno, o ``None`` si no ve (pieza E de la 0.4, ADR-263)."""
        self._presence = in_front

    def set_ages(self, in_front: Callable[[], Sequence[AgeReading | None] | None]) -> None:
        """Le dice de dónde saber la edad que aparentan los que tiene delante: de la vista,
        la de cada uno o ``None`` si no se sabe, o ``None`` si no ve (pieza F de la 0.4,
        ADR-264)."""
        self._care_watch.watch(in_front)

    def mark_cut(self, message_id: int, heard: str) -> None:
        """Le cortaron la respuesta ``message_id`` cuando el propietario había oído
        ``heard``: queda apuntado en ella (ADR-245), que es lo que llevaba escrito cuando le
        cortaron (ADR-254)."""
        if self._cuts is not None:
            self._cuts.mark_cut(message_id, heard)

    def _in_front(self) -> Sequence[str | None] | None:
        """A quiénes tiene delante; si no se puede saber, ``None``, y se apunta una vez."""
        presence = self._presence
        if presence is None:
            return None
        try:
            return presence()
        except Exception as error:
            if not self._presence_failed:
                self._presence_failed = True
                _logger.warning("No se sabe a quiénes tiene delante (%s)", type(error).__name__)
            return None

    def set_seen(self, lines: Callable[[], Sequence[str]]) -> None:
        """Le dice de dónde saber lo que recuerda haber visto: una línea por cambio, con su
        hora (pieza G de la 0.4, ADR-265)."""
        self._seen = lines

    def _seen_lines(self) -> Sequence[str]:
        """Lo que recuerda haber visto; si no se puede saber, nada, y se apunta una vez."""
        seen = self._seen
        if seen is None:
            return ()
        try:
            return seen()
        except Exception as error:
            if not self._seen_failed:
                self._seen_failed = True
                _logger.warning("No se sabe lo que ha visto (%s)", type(error).__name__)
            return ()

    def _care(self) -> bool:
        """Si tiene delante a alguien con quien se corta (``CareWatch``)."""
        return self._care_watch.needed()

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

    def warm_up_in_background(self) -> threading.Thread | None:
        """Pide al modelo de la charla que se cargue ya, en otro hilo y sin esperarle: así
        la primera frase no espera a que cargue (ADR-252). Lo piden la ventana y
        ``sirius-oye`` al arrancar.

        Solo el de este ordenador que sabe cargarse (``warm_up``, el de Ollama); devuelve el
        hilo, o ``None`` si no hay nada que cargar.
        """
        provider = self._llm_provider
        warm_up = getattr(provider, "warm_up", None)
        if not callable(warm_up) or not runs_on_this_computer(provider):
            return None
        thread = threading.Thread(target=warm_up, name="sirius-precarga", daemon=True)
        thread.start()
        return thread

    def send_message(
        self,
        user_text: str,
        *,
        operation_id: str | None = None,
        on_delta: Callable[[str], None] | None = None,
        on_completed: Callable[[], None] | None = None,
        on_gesture: Callable[[str], None] | None = None,
        extra_instructions: str = "",
        only_on_this_computer: bool = False,
        speaker: str | None = None,
    ) -> SendMessageResult:
        """Persist the user's message, stream Sirius's reply, and persist its outcome.

        ``on_delta`` is invoked synchronously, once per text fragment, in the
        caller's thread — it never touches persistence or Qt itself.

        Lo que escribe el modelo pasa antes por ``GestureFilter`` (pieza C de la 0.4,
        ADR-261): ``on_delta`` recibe el texto sin etiquetas, lo que se guarda tampoco las
        lleva, y ``on_gesture`` recibe el nombre de cada gesto de la lista, en el mismo
        hilo y en su sitio: después del texto que va delante de él y antes del de detrás.

        ``on_completed`` se llama una vez, en el mismo hilo, si la respuesta acaba bien:
        en cuanto está guardada entera y antes de lo que la charla hace después del turno.
        Resumir la charla pide otra respuesta al modelo y puede tardar segundos; la voz del
        robot dice ahí lo que le quedaba, sin esperar al resumen (ADR-243). Tampoco debe
        fallar.

        ``extra_instructions`` es una indicación **efímera** que se añade al
        final de las instrucciones de esta petición y nada más: no se guarda en
        la conversación, no se guarda en la memoria y no crea una versión nueva
        de la identidad. Va al final a propósito, para que no pueda desplazar ni
        reinterpretar la identidad canónica que la precede. Model Studio la usa
        para pedir respuestas breves mientras se graba (#126).

        ``only_on_this_computer`` lo pide la voz del robot: ninguna petición sale durante
        un turno de voz (PA-R03-08). Se comprueba el mismo modelo con el que se envía,
        leído una sola vez aquí, así que cambiarlo en marcha no puede sacar el mensaje del
        ordenador. Si es de fuera, no se guarda ni se envía nada y se levanta
        ``ChatLeavesThisComputer`` (ronda 10 de Codex sobre la PR #687).

        ``speaker`` es quién le habla, en un turno de voz: su nombre o «sin identificar»
        (pieza E de la 0.4, ADR-263). Con él y con lo que ve la vista, la petición lleva
        «# Quién hay» (``presence_block``); lo escrito en la ventana no lleva quién lo
        escribe. Y si la vista tiene delante a un crío, a un anciano o a alguien cuya edad
        no se sabe, lleva detrás la regla de no insultar (``care_block``, pieza F de la
        0.4, ADR-264). Antes de «# Quién hay» va lo que recuerda haber visto, quién vino y
        quién se fue, con su hora (``sight_block``, pieza G de la 0.4, ADR-265). Esas dos
        llevan nombres, y solo van a un modelo de este ordenador; la regla va siempre.
        """
        operation_id = operation_id or str(uuid.uuid4())
        provider = self._llm_provider
        if only_on_this_computer and not runs_on_this_computer(provider):
            raise ChatLeavesThisComputer(type(provider).__name__)
        self._in_flight[operation_id] = provider
        try:
            return self._send(
                provider,
                user_text,
                operation_id,
                on_delta,
                on_completed,
                on_gesture,
                extra_instructions,
                speaker,
            )
        finally:
            self._in_flight.pop(operation_id, None)
            with self._cut_lock:
                self._cut_operations.discard(operation_id)

    def _send(
        self,
        provider: LLMProvider,
        user_text: str,
        operation_id: str,
        on_delta: Callable[[str], None] | None,
        on_completed: Callable[[], None] | None,
        on_gesture: Callable[[str], None] | None,
        extra_instructions: str,
        speaker: str | None = None,
    ) -> SendMessageResult:
        if self._memory_commands is not None:
            # Antes que nada: una orden de memoria no puede llegar al modelo ni a
            # la búsqueda, que pediría la huella de la frase a olvidar.
            answer = self._memory_commands.handle(user_text)
            if answer is not None:
                return self._answer_command(provider, answer, operation_id, on_delta, on_completed)
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
        # Lo que ve la cámara de quién hay y de quién vino lleva nombres: solo va a un
        # modelo de este ordenador, como lo que oye. La regla de no insultar no nombra a
        # nadie, y va siempre.
        if runs_on_this_computer(provider):
            seen = sight_block(self._seen_lines())
            if seen:
                instructions = f"{instructions}\n\n{seen}"
            presence = presence_block(speaker=speaker, in_front=self._in_front())
            if presence:
                instructions = f"{instructions}\n\n{presence}"
        if self._care():
            instructions = f"{instructions}\n\n{care_block()}"
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
            stop=context_turns(context),
        )

        accumulated: list[str] = []
        status = MessageStatus.FAILED
        error_kind: LLMErrorKind | None = None
        final_text = ""
        memory_suggestion: str | None = None
        gestures = GestureFilter()

        def deliver(pieces: list[Piece]) -> None:
            for piece in pieces:
                if isinstance(piece, Gesture):
                    if on_gesture is not None:
                        on_gesture(piece.name)
                    continue
                accumulated.append(piece)
                if on_delta is not None:
                    on_delta(piece)

        for event in provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                deliver(gestures.finish())
                status = MessageStatus.COMPLETED
                final_text, _ = strip_gestures(event.text)
                memory_suggestion = event.memory_suggestion
            elif isinstance(event, LLMCancelled):
                status = MessageStatus.CANCELLED
                final_text, _ = strip_gestures(event.partial_text, cut=True)
            elif isinstance(event, LLMError):
                status = MessageStatus.FAILED
                error_kind = event.kind
                final_text, _ = strip_gestures(event.partial_text, cut=True)
            else:
                deliver(gestures.feed(event.text))

        if not final_text and status is not MessageStatus.COMPLETED:
            final_text = "".join(accumulated)
        was_cut = status is MessageStatus.CANCELLED and self._was_cut(operation_id)
        if was_cut:
            # Le cortaron por voz: lo que llevaba escrito es su respuesta (ADR-254).
            status = MessageStatus.COMPLETED

        sirius_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.SIRIUS,
            final_text,
            operation_id=operation_id,
            identity_version=context.identity.current_version.version,
            status=status,
        )
        if status is MessageStatus.COMPLETED:
            if on_completed is not None:
                on_completed()
            if self._reply_marks is not None:
                model = getattr(provider, "model_name", None)
                self._reply_marks.record_model(
                    sirius_message.id, model if isinstance(model, str) else None
                )
            # Tras un corte no se resume: sería otra petición al modelo, y lo que le dijo
            # al cortarle esperaría detrás. Lo mira el turno siguiente (ADR-254). También si
            # le cortan con la respuesta ya escrita, mientras dice la última frase.
            if self._summary_service is not None and not self._was_cut(operation_id):
                self._summary_service.maybe_summarize(conversation.id, provider, operation_id)

        return SendMessageResult(
            outcome=status,
            user_message=user_message,
            sirius_message=sirius_message,
            context=context,
            error_kind=error_kind,
            memory_suggestion=memory_suggestion,
        )

    def _answer_command(
        self,
        provider: LLMProvider,
        answer: CommandAnswer,
        operation_id: str,
        on_delta: Callable[[str], None] | None,
        on_completed: Callable[[], None] | None,
    ) -> SendMessageResult:
        """Cumple la orden sin el modelo y guarda la orden y lo que contesta Sirius.

        Sin contexto: lo único que puede ir al modelo es la frase fija de la voz. La
        respuesta se guarda en cuanto la orden se cumple, con la frase de siempre, y
        solo después se pide la voz: si la voz tarda, falla o Sirius se cierra
        mientras, la orden ya tiene su respuesta (ronda 1 de Codex, ADR-240).
        """
        conversation = self._conversation_repository.get_or_create_main_conversation()
        user_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.USER,
            answer.stored_user_text,
            operation_id=operation_id,
            status=MessageStatus.COMPLETED,
        )
        # Lo que la orden cambia se hace con su mensaje ya guardado y queda ligado a
        # él: si guardarlo falla, la orden no ha cambiado nada.
        reply = answer.respond(user_message.id)
        sirius_message = self._conversation_repository.append_message(
            conversation.id,
            MessageRole.SIRIUS,
            reply.fixed,
            operation_id=operation_id,
            status=MessageStatus.COMPLETED,
        )
        sirius_message = self._with_voice(provider, reply, sirius_message, conversation.id)
        if on_delta is not None:
            on_delta(sirius_message.content or reply.fixed)
        if on_completed is not None:
            on_completed()
        return SendMessageResult(
            outcome=MessageStatus.COMPLETED,
            user_message=user_message,
            sirius_message=sirius_message,
            context=None,
        )

    def _with_voice(
        self, provider: LLMProvider, reply: CommandReply, stored: Message, conversation_id: int
    ) -> Message:
        """La respuesta ya guardada, con la voz de Sirius y, detrás, lo exacto, tal cual.

        Si no hay voz, o el modelo falla, se cancela o no dice nada, se queda la frase
        de siempre, que ya está guardada.
        """
        voice = self._command_voice
        if voice is None:
            return stored
        try:
            request = voice.request(
                reply.said,
                mode_block=self._current_mode_block(conversation_id),
                reminder=self._reminder,
                operation_id=stored.operation_id or str(uuid.uuid4()),
                care=care_block() if self._care() else "",
            )
        except Exception as exc:  # la orden ya está cumplida: sin voz, la frase de siempre
            _logger.warning("No se pudo preparar la voz de la orden (%s)", type(exc).__name__)
            return stored
        said = _completed_text(provider, request) if request is not None else None
        if said is None:
            return stored
        try:
            return voice.replies.replace_reply(
                stored.id, f"{said}\n{reply.exact}" if reply.exact else said
            )
        except Exception as exc:  # se queda la frase de siempre, que ya está guardada
            _logger.warning("No se pudo guardar la voz de la orden (%s)", type(exc).__name__)
            return stored

    def _current_mode_block(self, conversation_id: int) -> str:
        """Lo que añade el modo en que está la charla, sin cambiarlo."""
        if self._mode_repository is None:
            return ""
        return MODE_INSTRUCTIONS[self._mode_repository.get_mode(conversation_id)]

    def cancel(self, operation_id: str) -> None:
        """Request cooperative cancellation of an in-flight operation. Idempotent.

        Va al modelo que está dando esa respuesta, aunque la charla ya haya cambiado
        de modelo; si no hay respuesta en curso con ese id, al modelo de ahora.
        """
        self._in_flight.get(operation_id, self._llm_provider).cancel(operation_id)

    def cut(self, operation_id: str) -> None:
        """Le cortan por voz mientras escribe la respuesta de ``operation_id``: deja de
        escribirla, como con ``cancel``, pero lo que llevaba escrito queda como su respuesta,
        acabada ahí y no cancelada, y el modelo lo lee después con la nota de hasta dónde se
        oyó. Cortarle no es cancelar el envío: lo dicho queda dicho, hasta donde llegó a
        escribir (decisión del propietario del 17-10-2026, ADR-254).

        Si la respuesta ya está escrita y la charla resume, corta también el resumen, que va
        con su operación: lo nuevo no espera a él, y lo hace el turno siguiente."""
        with self._cut_lock:
            self._cut_operations.add(operation_id)
        provider = self._in_flight.get(operation_id, self._llm_provider)
        provider.cancel(operation_id)
        provider.cancel(summary_operation_id(operation_id))

    def _was_cut(self, operation_id: str) -> bool:
        with self._cut_lock:
            return operation_id in self._cut_operations

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


def _completed_text(provider: LLMProvider, request: LLMRequest) -> str | None:
    """El texto que da el modelo, o ``None`` si falla, se cancela o no dice nada."""
    try:
        for event in provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                return event.text.strip() or None
            if isinstance(event, (LLMCancelled, LLMError)):
                return None
    except Exception as exc:  # una voz que falla no deja la orden sin respuesta
        _logger.warning("Sirius no pudo decir la orden con su voz (%s)", type(exc).__name__)
    return None
