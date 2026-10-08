"""Atender las órdenes de memoria sin pasar por el modelo (pieza G de ADR-233, ADR-239).

«Olvida eso», «olvida lo de…», «eso no es así», «¿qué sabes de mí?» y «¿qué
sabes de Lucía?». ``SendMessageUseCase`` pregunta aquí antes de montar el
contexto: si es una orden, se cumple aquí y ni el modelo de la charla ni el de
huellas ven el mensaje. Si no lo es, la charla sigue igual.

Lo que contesta Sirius sale de aquí en dos partes (ADR-240): una frase fija, que
el modelo puede decir con la voz de Sirius porque no lleva nada de lo olvidado ni
del mensaje de la orden, y lo exacto, que va detrás tal cual y nunca pasa por el
modelo. Si el modelo no le pone la voz, va la frase de siempre.

Lo que no se sabe atender sin el modelo no se atiende aquí: un «eso no es así»
que no casa con ningún hecho apuntado, o un «¿qué sabes de…?» de alguien sin
ficha, van a la charla como cualquier mensaje.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sirius.application.facts import ConfirmFactSuggestionUseCase, FactProposals, FactsUseCase
from sirius.application.reject_memory_suggestion import RejectMemorySuggestionUseCase
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.facts import OWNER, fact_note, mentioned_people, same_person
from sirius.domain.memory import Memory
from sirius.domain.memory_commands import MemoryCommandKind, detect_memory_command
from sirius.domain.plain_text import plain
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.forget import ForgetReport, Forgetter

__all__ = ["ASK_TO_CONFIRM", "FORGOT", "CommandAnswer", "CommandReply", "MemoryCommandService"]

#: Cómo acaba la pregunta de Sirius tras «eso no es así». Un «sí» o un «no» justo
#: después la contestan; en cualquier otro momento son charla.
ASK_TO_CONFIRM = "Dime «sí» y lo cambio."

#: Lo que se guarda de «olvida lo de…»: el tema no, que es lo que hay que olvidar.
FORGET_ABOUT_STORED = "Olvida lo de…"

#: Lo que va delante del tema y no es el tema: «mi vecino Ramiro» es «vecino Ramiro».
_LEADING = "mi mis tu tus su sus el la los las un una unos unas lo al del de que"
_LEADING_WORDS = frozenset(_LEADING.split())
_TOPIC_WORD = re.compile(r"[^\W_]{4,}")
_BACKUPS_NOTE = "Las copias de seguridad que hiciste antes lo siguen guardando."

#: Lo que dice Sirius al olvidar lo último, cuando no lo dice con su voz.
FORGOT = "Hecho: ya no lo recuerdo."


@dataclass(frozen=True, slots=True)
class CommandReply:
    """Lo que contesta Sirius a una orden de memoria (ADR-240).

    ``said`` es lo que puede decir con su voz: una frase fija, con números como
    mucho y, en «¿qué sabes de…?», el nombre de la persona. Nunca lleva nada de lo
    que se olvida ni del mensaje de la orden. ``exact`` va detrás tal cual y no pasa
    por el modelo: la lista de hechos, la corrección que pregunta o el aviso de las
    copias. ``fixed`` es la frase de siempre, la que va si no hay voz.
    """

    said: str
    exact: str = ""
    fixed: str = ""

    def __post_init__(self) -> None:
        if not self.fixed:
            object.__setattr__(self, "fixed", " ".join(p for p in (self.said, self.exact) if p))


@dataclass(frozen=True, slots=True)
class CommandAnswer:
    """Lo que se guarda del mensaje del propietario y cómo contesta Sirius.

    ``respond`` hace lo que la orden manda y devuelve lo que contesta Sirius. Se
    llama con el mensaje de la orden ya guardado y recibe su id: así lo que la orden
    cambia queda ligado a él, y si guardarlo falla no ha cambiado nada (rondas 2 y 3
    de Codex). Decidir si es una orden, en cambio, no cambia nada.
    """

    stored_user_text: str
    respond: Callable[[int], CommandReply]


def _says(reply: CommandReply) -> Callable[[int], CommandReply]:
    """Una respuesta que no cambia nada."""
    return lambda _message_id: reply


class MemoryCommandService:
    """Reconoce la orden y la cumple, o devuelve ``None`` para que siga la charla."""

    def __init__(
        self,
        conversations: ConversationRepository,
        forgetter: Forgetter,
        facts: FactsUseCase,
        proposals: FactProposals,
        confirm: ConfirmFactSuggestionUseCase,
        reject: RejectMemorySuggestionUseCase,
        *,
        backups_exist: Callable[[], bool] = lambda: False,
    ) -> None:
        self._conversations = conversations
        self._forgetter = forgetter
        self._facts = facts
        self._proposals = proposals
        self._confirm = confirm
        self._reject = reject
        self._backups_exist = backups_exist

    def handle(self, text: str) -> CommandAnswer | None:
        command = detect_memory_command(text)
        if command is None:
            return None
        if command.kind is MemoryCommandKind.FORGET_LAST:
            return CommandAnswer(text, self._forget_last)
        if command.kind is MemoryCommandKind.FORGET_ABOUT:
            topic = command.argument
            return CommandAnswer(FORGET_ABOUT_STORED, lambda _command_id: self._forget_about(topic))
        if command.kind is MemoryCommandKind.CORRECT:
            return self._correct(text, command.argument)
        if command.kind is MemoryCommandKind.ABOUT_ME:
            return CommandAnswer(text, _says(self._what_i_know(OWNER, "ti", "")))
        if command.kind is MemoryCommandKind.ABOUT_PERSON:
            return self._about_person(text, command.argument)
        return self._answer_pending(text, yes=command.kind is MemoryCommandKind.YES)

    # --- Olvidar ---

    def _forget_last(self, command_id: int) -> CommandReply:
        """Olvida lo último que dijo antes de la orden ``command_id``, ya guardada.

        Una orden que se quedó sin respuesta no cuenta: falló, y él la está
        repitiendo ahora. Y lo último que dijo, si ya está olvidado, no se busca más
        atrás: repetir «olvida eso» nunca se lleva otra cosa (ronda 3 de Codex).
        """
        messages = self._messages()
        failed = _failed_commands(messages)
        for message in reversed(messages):
            if message.id >= command_id or message.role is not MessageRole.USER:
                continue
            if message.id in failed:
                continue
            if message.status is MessageStatus.REDACTED or not message.content:
                return CommandReply("Eso ya lo había olvidado.")
            self._forgetter.forget_message(message.id)
            return self._with_backups_note(FORGOT)
        return CommandReply("No me has dicho nada que olvidar.")

    def _forget_about(self, topic: str) -> CommandReply:
        phrase = _without_leading_words(topic)
        report = self._forgetter.forget_phrase(phrase) if phrase else ForgetReport()
        if not report.anything:
            return CommandReply(
                "No encuentro nada dicho con esas palabras. Prueba con las palabras exactas."
            )
        return self._with_backups_note(f"Hecho. He borrado {_count(report)}.")

    def _with_backups_note(self, said: str) -> CommandReply:
        return CommandReply(said, _BACKUPS_NOTE if self._backups_exist() else "")

    # --- Eso no es así ---

    def _correct(self, text: str, new_text: str) -> CommandAnswer | None:
        target = self._fact_to_correct(new_text)
        if target is None:
            return None
        if not new_text:
            return CommandAnswer(
                text,
                _says(
                    CommandReply(
                        "Dime cómo es.",
                        "Así: «eso no es así: …».",
                        fixed="Dime cómo es, así: «eso no es así: …».",
                    )
                ),
            )
        after = new_text[:1].upper() + new_text[1:]
        revision = target.current_revision
        note = fact_note(revision.said_by, revision.certainty)
        reply = CommandReply(
            "¿Lo cambio?",
            f"Ahora tengo «{revision.content}»{note}. Lo nuevo: «{after}». {ASK_TO_CONFIRM}",
        )

        def respond(command_id: int) -> CommandReply:
            # Si la orden se repite porque antes falló, no deja dos iguales esperando.
            waiting = any(
                pending.memory_id == target.id and pending.after == after
                for pending in self._facts.pending_corrections()
            )
            if not waiting:
                self._proposals.propose_correction(target.id, after, message_id=command_id)
            return reply

        return CommandAnswer(text, respond)

    def _fact_to_correct(self, new_text: str) -> Memory | None:
        """El hecho que más casa con lo último que se habló y con la corrección.

        Los candidatos son los hechos que la charla tenía delante: los suyos y los de
        las personas que nombró. Sin ninguna palabra en común con ninguno, no se
        sabe qué corregir y no se adivina.
        """
        messages = [m for m in self._messages() if m.status is MessageStatus.COMPLETED]
        # Una orden que falló no es de lo que se hablaba: él la está repitiendo ahora.
        failed = _failed_commands(messages)
        last_said = next(
            (
                m.content
                for m in reversed(messages)
                if m.role is MessageRole.USER and m.content and m.id not in failed
            ),
            "",
        )
        last_reply = next(
            (m.content for m in reversed(messages) if m.role is MessageRole.SIRIUS and m.content),
            "",
        )
        talk = _topic_words(f"{last_said} {last_reply} {new_text}")
        people = mentioned_people(f"{last_said} {new_text}", self._facts.known_people())
        candidates = [*self._facts.current(OWNER)]
        for person in people:
            candidates += self._facts.current(person)
        best: Memory | None = None
        best_score = 0
        for memory in candidates:
            about = f"{memory.current_revision.content or ''} {memory.topic or ''}"
            score = len(talk & _topic_words(about))
            if score > best_score:
                best, best_score = memory, score
        return best

    def _answer_pending(self, text: str, *, yes: bool) -> CommandAnswer | None:
        """Un «sí» o un «no» justo después de preguntar si cambia un hecho."""
        replies = [
            m
            for m in self._messages()
            if m.role is MessageRole.SIRIUS and m.status is MessageStatus.COMPLETED
        ]
        if not replies or not (replies[-1].content or "").endswith(ASK_TO_CONFIRM):
            return None
        pending = self._facts.pending_corrections()
        if not pending:
            return None
        correction = pending[-1]

        def confirm(command_id: int) -> CommandReply:
            # Ligado a su «sí»: «olvida eso» justo después se lleva lo cambiado.
            self._confirm.confirm(correction.suggestion_id, message_id=command_id)
            return CommandReply("Hecho.", f"Ahora tengo «{correction.after}».")

        def reject(_command_id: int) -> CommandReply:
            self._reject.reject(correction.suggestion_id)
            return CommandReply(
                "Vale, lo dejo como estaba.",
                f"Sigo con «{correction.before}».",
                fixed=f"Vale, lo dejo como estaba: «{correction.before}».",
            )

        return CommandAnswer(text, confirm if yes else reject)

    # --- ¿Qué sabes de…? ---

    def _about_person(self, text: str, name: str) -> CommandAnswer | None:
        person = next(
            (known for known in self._facts.known_people() if same_person(known, name)), None
        )
        if person is None:
            return None
        mentions = len(self._facts.card(person).mentions)
        talked = (
            f"Me has hablado de {person} en {_plural(mentions, 'mensaje')}." if mentions else ""
        )
        return CommandAnswer(text, _says(self._what_i_know(person, person, talked)))

    def _what_i_know(self, person: str, called: str, talked: str) -> CommandReply:
        """Lo que sabe de ``person``: la lista va tal cual, y ``talked`` detrás."""
        facts = self._facts.current(person)
        if not facts:
            said = f"Todavía no tengo ningún hecho de {called} apuntado."
            return CommandReply(said, talked, fixed="\n".join(p for p in (said, talked) if p))
        lines = [
            f"- {memory.current_revision.content}"
            f"{fact_note(memory.current_revision.said_by, memory.current_revision.certainty)}"
            for memory in facts
            if memory.current_revision.content
        ]
        said = f"Esto es lo que sé de {called}:"
        exact = "\n".join([*lines, *([talked] if talked else [])])
        return CommandReply(said, exact, fixed="\n".join([said, exact]))

    def _messages(self) -> list[Message]:
        conversation = self._conversations.get_main_conversation()
        if conversation is None:
            return []
        return self._conversations.list_messages(conversation.id)


def _failed_commands(messages: Sequence[Message]) -> set[int]:
    """Las órdenes suyas que se quedaron sin respuesta de Sirius: fallaron al guardarse,
    y cuando él las repite no cuentan como lo último que dijo (ronda 3 de Codex)."""
    answered = {m.operation_id for m in messages if m.role is MessageRole.SIRIUS and m.operation_id}
    return {
        m.id
        for m in messages
        if m.role is MessageRole.USER
        and m.content
        and detect_memory_command(m.content) is not None
        and m.operation_id not in answered
    }


def _without_leading_words(topic: str) -> str:
    """«mi vecino Ramiro» → «vecino Ramiro»: lo que dijo, sin el artículo ni el posesivo."""
    words = topic.split()
    while words and plain(words[0]) in _LEADING_WORDS:
        words = words[1:]
    return " ".join(words)


def _topic_words(text: str) -> set[str]:
    return set(_TOPIC_WORD.findall(plain(text)))


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _count(report: ForgetReport) -> str:
    parts: Sequence[tuple[int, str, str]] = (
        (report.messages, "mensaje", "mensajes"),
        (report.memories, "recuerdo", "recuerdos"),
        (report.suggestions, "sugerencia", "sugerencias"),
        (report.summaries, "resumen", "resúmenes"),
    )
    said = [f"{n} {one if n == 1 else many}" for n, one, many in parts if n]
    return said[0] if len(said) == 1 else f"{', '.join(said[:-1])} y {said[-1]}"
