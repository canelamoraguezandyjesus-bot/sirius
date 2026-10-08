"""Los hechos: proponerlos, confirmarlos, corregirlos y leerlos (pieza G de ADR-233, ADR-239).

Un hecho entra siempre igual: alguien lo propone —el sueño, «eso no es así»— y
queda como sugerencia hasta que el propietario dice que sí. Confirmar es lo que
lo apunta, cerrando el de antes si había uno de la misma persona y el mismo tema.

Lo que dice Sirius nunca entra como hecho: ni se puede proponer con «quién lo
dijo» Sirius, ni proponer desde una respuesta suya (``propose_from_message``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sirius.application.confirm_memory_suggestion import ConfirmMemorySuggestionUseCase
from sirius.domain.conversation import MessageRole
from sirius.domain.event import (
    MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE,
    MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE,
    SIRIUS_ACTOR,
    USER_ACTOR,
)
from sirius.domain.facts import (
    OWNER,
    Certainty,
    FactSpan,
    ProposedFact,
    is_owner,
    is_sirius,
    mentioned_people,
    span_of,
)
from sirius.domain.memory import Memory
from sirius.domain.memory_suggestion import MemorySuggestion, ensure_can_confirm
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.memory_repository import FactMemoryRepository
from sirius.ports.memory_suggestion_repository import MemorySuggestionRepository
from sirius.ports.unit_of_work import FactUnitOfWork

__all__ = [
    "CONFIRMED_CORRECTION_ORIGIN",
    "CONFIRMED_FACT_ORIGIN",
    "ConfirmFactSuggestionUseCase",
    "FactProposals",
    "FactsUseCase",
    "PendingCorrection",
    "PersonCard",
]

CONFIRMED_FACT_ORIGIN = "Hecho confirmado por el usuario"
CONFIRMED_CORRECTION_ORIGIN = "Corrección confirmada por el usuario"


@dataclass(frozen=True, slots=True)
class PendingCorrection:
    """Una corrección de «eso no es así» que espera su sí."""

    suggestion_id: int
    memory_id: int
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class PersonCard:
    """La ficha de una persona: sus hechos vigentes y lo que el propietario ha dicho de ella."""

    name: str
    facts: tuple[str, ...]
    mentions: tuple[str, ...]


class FactProposals:
    """Proponer hechos y correcciones: quedan pendientes de su sí."""

    def __init__(self, unit_of_work: FactUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def propose(
        self,
        fact: ProposedFact,
        *,
        message_id: int | None = None,
        dreamed_day: date | None = None,
        by_sirius: bool = False,
    ) -> MemorySuggestion:
        """Deja ``fact`` como sugerencia. ``by_sirius`` si lo propone el sueño.

        De dónde sale queda dicho, para que olvidarlo se lo lleve: ``message_id``
        el mensaje, o ``dreamed_day`` el día que soñaba el sueño.
        """
        if not fact.person.strip() or not fact.text.strip():
            msg = "Un hecho necesita persona y texto."
            raise ValueError(msg)
        if is_sirius(fact.said_by):
            msg = "Lo que dice Sirius nunca es un hecho."
            raise ValueError(msg)
        with self._unit_of_work as uow:
            event = uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE,
                actor=SIRIUS_ACTOR if by_sirius else USER_ACTOR,
                message_id=message_id,
            )
            suggestion = uow.memory_suggestion_repository.create_suggestion(
                fact.text.strip(),
                source_event_id=event.id,
                person=fact.person.strip(),
                topic=fact.topic.strip() if fact.topic else None,
                valid_from=fact.since,
                said_by=fact.said_by.strip(),
                certainty=Certainty(fact.certainty).value,
                dreamed_day=dreamed_day,
            )
            uow.commit()
        return suggestion

    def propose_correction(
        self, memory_id: int, text: str, *, message_id: int | None = None
    ) -> MemorySuggestion:
        """«Eso no es así»: propone que el hecho ``memory_id`` pase a decir ``text``."""
        if not text.strip():
            msg = "Una corrección necesita el texto nuevo."
            raise ValueError(msg)
        with self._unit_of_work as uow:
            memory = uow.memory_repository.get_memory(memory_id)
            if not memory.is_fact:
                msg = "Solo se corrige así un hecho."
                raise ValueError(msg)
            event = uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            suggestion = uow.memory_suggestion_repository.create_suggestion(
                text.strip(),
                source_event_id=event.id,
                person=memory.person,
                topic=memory.topic,
                corrects_memory_id=memory_id,
                said_by=OWNER,
                certainty=Certainty.SURE.value,
            )
            uow.commit()
        return suggestion

    def propose_from_message(self, message_id: int, content: str) -> MemorySuggestion | None:
        """«Proponer guardar…» desde un mensaje: solo vale uno del propietario.

        Lo que dice Sirius nunca entra como hecho suyo (PA-R02-14): desde una
        respuesta de Sirius no se propone nada y se devuelve ``None``.
        """
        with self._unit_of_work as uow:
            message = uow.conversation_repository.get_message(message_id)
            if message is None or message.role is not MessageRole.USER:
                return None
            text = content.strip() or (message.content or "").strip()
            if not text:
                return None
            event = uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            suggestion = uow.memory_suggestion_repository.create_suggestion(
                text, source_event_id=event.id
            )
            uow.commit()
        return suggestion


class ConfirmFactSuggestionUseCase(ConfirmMemorySuggestionUseCase):
    """Confirmar una sugerencia: un recuerdo, un hecho o una corrección.

    Un recuerdo se confirma como en 0.1. Un hecho se apunta con su fecha, quién
    lo dijo y con qué seguridad, y cierra el que hubiera de la misma persona y el
    mismo tema. Una corrección es una revisión nueva del hecho que corrige: la de
    antes queda en su historia con quién la dijo, y la nueva la dice él, segura.
    """

    def __init__(self, unit_of_work: FactUnitOfWork) -> None:
        super().__init__(unit_of_work)
        self._fact_unit_of_work = unit_of_work

    def confirm(self, suggestion_id: int, *, message_id: int | None = None) -> Memory:
        """Confirma la sugerencia. ``message_id`` es el mensaje con el que dijo que sí,
        si lo dijo hablando: lo que cambia queda ligado a él, y olvidarlo se lo lleva."""
        with self._fact_unit_of_work as uow:
            suggestion = uow.memory_suggestion_repository.get_suggestion(suggestion_id)
        if suggestion.person is None and suggestion.corrects_memory_id is None:
            return super().confirm(suggestion_id)
        with self._fact_unit_of_work as uow:
            suggestion = uow.memory_suggestion_repository.get_suggestion(suggestion_id)
            ensure_can_confirm(suggestion)
            event = uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            certainty = Certainty(suggestion.certainty or Certainty.SURE)
            if suggestion.corrects_memory_id is not None:
                memory = uow.memory_repository.correct_fact(
                    suggestion.corrects_memory_id,
                    suggestion.content,
                    CONFIRMED_CORRECTION_ORIGIN,
                    source_event_id=event.id,
                    said_by=suggestion.said_by or OWNER,
                    certainty=certainty,
                )
            else:
                assert suggestion.person is not None
                memory = uow.memory_repository.record_fact(
                    suggestion.person,
                    suggestion.topic,
                    suggestion.content,
                    CONFIRMED_FACT_ORIGIN,
                    since=suggestion.valid_from or date.today(),
                    said_by=suggestion.said_by or OWNER,
                    certainty=certainty,
                    source_event_id=event.id,
                )
            uow.memory_suggestion_repository.confirm_suggestion(
                suggestion_id, resulting_memory_id=memory.id, resolved_at=datetime.now(UTC)
            )
            uow.commit()
        return memory


class FactsUseCase:
    """Lo que se sabe: los hechos vigentes, su historia y la ficha de cada persona."""

    def __init__(
        self,
        facts: FactMemoryRepository,
        suggestions: MemorySuggestionRepository,
        conversations: ConversationRepository,
    ) -> None:
        self._facts = facts
        self._suggestions = suggestions
        self._conversations = conversations

    def current(self, person: str = OWNER) -> list[Memory]:
        return self._facts.list_current_facts(person)

    def known_people(self) -> list[str]:
        return self._facts.known_people()

    def history(self, person: str, topic: str) -> list[FactSpan]:
        """Los tramos del hecho de ``person`` sobre ``topic``, del más viejo al vigente."""
        return [
            span_of(revision)
            for revision in self._facts.find_fact_history(person, topic)
            if revision.content
        ]

    def card(self, name: str) -> PersonCard:
        """La ficha de ``name``: sus hechos vigentes y los mensajes suyos que la nombran."""
        facts = tuple(
            memory.current_revision.content
            for memory in self._facts.list_current_facts(name)
            if memory.current_revision.content
        )
        mentions: tuple[str, ...] = ()
        conversation = self._conversations.get_main_conversation()
        if conversation is not None and not is_owner(name):
            mentions = tuple(
                message.content
                for message in self._conversations.list_messages(conversation.id)
                if message.role is MessageRole.USER
                and message.content
                and mentioned_people(message.content, [name])
            )
        return PersonCard(name=name, facts=facts, mentions=mentions)

    def pending_facts(self) -> list[MemorySuggestion]:
        """Los hechos propuestos que esperan su sí, sin las correcciones."""
        return [
            suggestion
            for suggestion in self._suggestions.list_pending_suggestions()
            if suggestion.person is not None and suggestion.corrects_memory_id is None
        ]

    def pending_corrections(self) -> list[PendingCorrection]:
        """Cada «eso no es así» que espera su sí: el hecho de antes y el texto nuevo."""
        pending: list[PendingCorrection] = []
        for suggestion in self._suggestions.list_pending_suggestions():
            if suggestion.corrects_memory_id is None:
                continue
            try:
                memory = self._facts.get_memory(suggestion.corrects_memory_id)
            except ValueError:
                continue
            before = memory.current_revision.content
            if before:
                pending.append(
                    PendingCorrection(
                        suggestion.id, suggestion.corrects_memory_id, before, suggestion.content
                    )
                )
        return pending
