"""Atender las órdenes de memoria sin pasar por el modelo (pieza G de ADR-233, ADR-239).

«Olvida eso», «olvida lo de…», «eso no es así», «¿qué sabes de mí?» y «¿qué
sabes de Lucía?». ``SendMessageUseCase`` pregunta aquí antes de montar el
contexto: si es una orden, la contesta Sirius con estas frases y ni el modelo de
la charla ni el de huellas ven el mensaje. Si no lo es, la charla sigue igual.

Lo que no se sabe atender sin el modelo no se atiende aquí: un «eso no es así»
que no casa con ningún hecho apuntado, o un «¿qué sabes de…?» de alguien sin
ficha, van a la charla como cualquier mensaje.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sirius.application.confirm_memory_suggestion import ConfirmMemorySuggestionUseCase
from sirius.application.facts import FactProposals, FactsUseCase
from sirius.application.reject_memory_suggestion import RejectMemorySuggestionUseCase
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.facts import OWNER, fact_note, mentioned_people, same_person
from sirius.domain.memory import Memory
from sirius.domain.memory_commands import MemoryCommandKind, detect_memory_command
from sirius.domain.plain_text import plain
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.forget import ForgetReport, Forgetter

__all__ = ["ASK_TO_CONFIRM", "CommandAnswer", "MemoryCommandService"]

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


@dataclass(frozen=True, slots=True)
class CommandAnswer:
    """Lo que se guarda del mensaje del propietario y lo que contesta Sirius."""

    stored_user_text: str
    reply: str


class MemoryCommandService:
    """Reconoce la orden y la cumple, o devuelve ``None`` para que siga la charla."""

    def __init__(
        self,
        conversations: ConversationRepository,
        forgetter: Forgetter,
        facts: FactsUseCase,
        proposals: FactProposals,
        confirm: ConfirmMemorySuggestionUseCase,
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
            return self._forget_last(text)
        if command.kind is MemoryCommandKind.FORGET_ABOUT:
            return self._forget_about(command.argument)
        if command.kind is MemoryCommandKind.CORRECT:
            return self._correct(text, command.argument)
        if command.kind is MemoryCommandKind.ABOUT_ME:
            return CommandAnswer(text, self._what_i_know(OWNER, "ti"))
        if command.kind is MemoryCommandKind.ABOUT_PERSON:
            return self._about_person(text, command.argument)
        return self._answer_pending(text, yes=command.kind is MemoryCommandKind.YES)

    # --- Olvidar ---

    def _forget_last(self, text: str) -> CommandAnswer:
        said = [
            message
            for message in self._messages()
            if message.role is MessageRole.USER
            and message.status is MessageStatus.COMPLETED
            and message.content
        ]
        if not said:
            return CommandAnswer(text, "No me has dicho nada que olvidar.")
        self._forgetter.forget_message(said[-1].id)
        return CommandAnswer(text, self._with_backups_note("Hecho: ya no lo recuerdo."))

    def _forget_about(self, topic: str) -> CommandAnswer:
        phrase = _without_leading_words(topic)
        report = self._forgetter.forget_phrase(phrase) if phrase else ForgetReport()
        if not report.anything:
            reply = "No encuentro nada dicho con esas palabras. Prueba con las palabras exactas."
            return CommandAnswer(FORGET_ABOUT_STORED, reply)
        return CommandAnswer(
            FORGET_ABOUT_STORED, self._with_backups_note(f"Hecho. He borrado {_count(report)}.")
        )

    def _with_backups_note(self, reply: str) -> str:
        return f"{reply} {_BACKUPS_NOTE}" if self._backups_exist() else reply

    # --- Eso no es así ---

    def _correct(self, text: str, new_text: str) -> CommandAnswer | None:
        target = self._fact_to_correct(new_text)
        if target is None:
            return None
        if not new_text:
            return CommandAnswer(text, "Dime cómo es, así: «eso no es así: …».")
        after = new_text[:1].upper() + new_text[1:]
        self._proposals.propose_correction(target.id, after)
        revision = target.current_revision
        note = fact_note(revision.said_by, revision.certainty)
        reply = (
            f"¿Lo cambio? Ahora tengo «{revision.content}»{note}. Lo nuevo: «{after}». "
            f"{ASK_TO_CONFIRM}"
        )
        return CommandAnswer(text, reply)

    def _fact_to_correct(self, new_text: str) -> Memory | None:
        """El hecho que más casa con lo último que se habló y con la corrección.

        Los candidatos son los hechos que la charla tenía delante: los suyos y los de
        las personas que nombró. Sin ninguna palabra en común con ninguno, no se
        sabe qué corregir y no se adivina.
        """
        messages = [m for m in self._messages() if m.status is MessageStatus.COMPLETED]
        last_said = next(
            (m.content for m in reversed(messages) if m.role is MessageRole.USER and m.content),
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
        if yes:
            self._confirm.confirm(correction.suggestion_id)
            return CommandAnswer(text, f"Hecho. Ahora tengo «{correction.after}».")
        self._reject.reject(correction.suggestion_id)
        return CommandAnswer(text, f"Vale, lo dejo como estaba: «{correction.before}».")

    # --- ¿Qué sabes de…? ---

    def _about_person(self, text: str, name: str) -> CommandAnswer | None:
        person = next(
            (known for known in self._facts.known_people() if same_person(known, name)), None
        )
        if person is None:
            return None
        reply = self._what_i_know(person, person)
        mentions = len(self._facts.card(person).mentions)
        if mentions:
            reply += f"\nMe has hablado de {person} en {_plural(mentions, 'mensaje')}."
        return CommandAnswer(text, reply)

    def _what_i_know(self, person: str, called: str) -> str:
        facts = self._facts.current(person)
        if not facts:
            return f"Todavía no tengo ningún hecho de {called} apuntado."
        lines = [
            f"- {memory.current_revision.content}"
            f"{fact_note(memory.current_revision.said_by, memory.current_revision.certainty)}"
            for memory in facts
            if memory.current_revision.content
        ]
        return "\n".join([f"Esto es lo que sé de {called}:", *lines])

    def _messages(self) -> list[Message]:
        conversation = self._conversations.get_main_conversation()
        if conversation is None:
            return []
        return self._conversations.list_messages(conversation.id)


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
