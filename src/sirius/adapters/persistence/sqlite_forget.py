"""Olvidar de verdad en sirius.db (pieza G de ADR-233, ADR-239).

El plan: «Olvidar borra de verdad, también de los resúmenes». Aquí se borra de
cada sitio donde puede quedar lo que dijo el propietario, y ``FORGET_COVERAGE``
dice cuáles son: cada columna de texto del esquema está ahí, o porque olvidar la
limpia o con la razón de que no guarda nada suyo. Una guarda
(``tests/integration/test_olvidar.py``) falla si aparece una columna de texto
que no esté, así que una tabla nueva no puede quedarse fuera sin que nadie lo
decida.

Borrar de verdad también es que no quede en el fichero: la conexión de olvidar
lleva ``secure_delete``, que pone a ceros lo borrado, y el índice de palabras se
compacta al acabar, que es cuando suelta los términos borrados.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, delete, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import (
    ConversationSummaryModel,
    DaySummaryModel,
    EventModel,
    MemoryModel,
    MemoryRevisionModel,
    MemorySuggestionModel,
    MessageModel,
)
from sirius.domain.conversation import MessageStatus
from sirius.domain.memory import MemoryStatus
from sirius.domain.memory_suggestion import MemorySuggestionStatus
from sirius.domain.plain_text import plain
from sirius.ports.forget import ForgetReport

__all__ = [
    "FORGET_COVERAGE",
    "SqliteForgetter",
    "build_sqlite_forgetter",
    "phrase_matcher",
    "without_sentences",
]

#: Olvidar la limpia.
FORGETS = "olvidar la limpia"

#: Cada columna de texto del esquema y qué hace olvidar con ella.
FORGET_COVERAGE: dict[str, str] = {
    "messages.content": FORGETS,
    "memory_revisions.content": FORGETS,
    "memory_revisions.said_by": FORGETS,
    "memories.person": FORGETS,
    "memories.topic": FORGETS,
    "memory_suggestions.content": FORGETS,
    "memory_suggestions.person": FORGETS,
    "memory_suggestions.topic": FORGETS,
    "memory_suggestions.said_by": FORGETS,
    "conversation_summaries.content": FORGETS,
    "day_summaries.content": FORGETS,
    "memory_embeddings.embedding": (
        "la huella se va con el recuerdo: la borran los disparadores de ADR-238 al borrarlo"
    ),
    "memory_embeddings.model": "el nombre del modelo de huellas",
    "messages.operation_id": "un identificador del turno, sin texto suyo",
    "messages.role": "un valor fijo",
    "messages.status": "un valor fijo",
    "memories.status": "un valor fijo",
    "memories.subject_key": "el asunto de un recuerdo de 0.1; la charla del robot no lo pone",
    "memories.category": "una de las categorías fijas de 0.1",
    "memories.criticality": "una de las criticidades fijas de 0.1",
    "memory_revisions.origin": "de dónde salió el recuerdo, con frases fijas de Sirius",
    "memory_revisions.certainty": "«segura» o «dudosa»",
    "memory_suggestions.status": "un valor fijo",
    "memory_suggestions.subject_key": "el asunto de 0.1; la charla del robot no lo pone",
    "memory_suggestions.certainty": "«segura» o «dudosa»",
    "events.event_type": "el tipo de evento, fijo",
    "events.actor": "quién hizo el cambio, fijo",
    "identity_versions.name": "la identidad de Sirius: la escribe él al marcar la semilla",
    "identity_versions.description": "la identidad de Sirius",
    "identity_versions.personality_instructions": "la identidad de Sirius",
    "projects.name": "el proyecto de 0.1; el robot solo tiene «Charla con Sirius»",
    "projects.objective": "el proyecto de 0.1",
    "projects.current_state": "el proyecto de 0.1",
    "projects.next_step": "el proyecto de 0.1",
    "projects.blockers": "el proyecto de 0.1",
    "projects.status": "un valor fijo",
    "project_revisions.objective": "el proyecto de 0.1",
    "project_revisions.state_summary": "el proyecto de 0.1",
    "project_revisions.blockers_json": "el proyecto de 0.1",
    "project_revisions.next_step": "el proyecto de 0.1",
    "decisions.subject": "las decisiones de 0.1; la charla del robot no crea ninguna",
    "decisions.status": "un valor fijo",
    "decisions.category": "una de las categorías fijas de 0.1",
    "decisions.criticality": "una de las criticidades fijas de 0.1",
    "decision_revisions.content": "las decisiones de 0.1; la charla del robot no crea ninguna",
    "llm_usage.year_month": "el mes del gasto",
    "conversation_modes.mode": "«normal» o «serio»",
    "reply_marks.mark": "«eso es Sirius» o «eso no»",
    "reply_marks.model": "el nombre del modelo que dio la respuesta",
}

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def phrase_matcher(phrase: str) -> Callable[[str], bool]:
    """Si un texto nombra ``phrase``, en llano y por palabras enteras.

    «Olvida lo de casa» no puede llevarse «casado» ni «Casandra»: olvidar borra de
    verdad, y lo que no se pidió olvidar no se toca.
    """
    words = plain(phrase).split()
    if not words:
        return lambda text: False
    pattern = re.compile(
        r"(?<![^\W_])" + r"\s+".join(re.escape(word) for word in words) + r"(?![^\W_])"
    )
    return lambda text: bool(pattern.search(plain(text)))


def without_sentences(content: str, mentions: Callable[[str], bool]) -> str:
    """``content`` sin las frases que nombran lo olvidado, línea a línea."""
    kept_lines: list[str] = []
    for line in content.splitlines():
        sentences = [s for s in _SENTENCE_END.split(line) if not mentions(s)]
        kept = " ".join(sentence for sentence in sentences if sentence.strip())
        if kept.strip() or not line.strip():
            kept_lines.append(kept)
    return "\n".join(kept_lines).strip()


def _secure_delete(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA secure_delete=ON")
    cursor.close()


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SqliteForgetter:
    """``Forgetter`` sobre la base de la charla, en una transacción por orden."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        self._engine.dispose()

    def forget_message(self, message_id: int) -> ForgetReport:
        with session_scope(self._session_factory) as session:
            message = session.get(MessageModel, message_id)
            if message is None or message.content is None:
                return ForgetReport()
            mentions = phrase_matcher(message.content)
            turn = _turn_of(session, message)
            said_on = message.created_at.replace(tzinfo=UTC).astimezone().date()
            # Lo que salió de él: lo ligado a cualquier mensaje del turno, y lo que
            # el sueño propuso de ese día y aún espera su sí. El resumen de ese día
            # se borra abajo, así que el día se vuelve a soñar con lo que queda.
            events = _events_of(session, turn)
            suggestions, linked_memories = self._forget_suggestions(
                session, lambda texts: _any(texts, mentions), events, frozenset({said_on})
            )
            memories = self._forget_memories(
                session, lambda texts: _any(texts, mentions), events, linked_memories
            )
            # Los resúmenes que ya cubrían el mensaje se borran enteros: lo que dicen
            # de él puede estar con otras palabras. La charla rehará el suyo.
            summaries = self._delete(
                session,
                delete(ConversationSummaryModel).where(
                    ConversationSummaryModel.conversation_id == message.conversation_id,
                    ConversationSummaryModel.up_to_sequence >= message.sequence,
                ),
            )
            summaries += self._delete(
                session, delete(DaySummaryModel).where(DaySummaryModel.day == said_on)
            )
            for redacted in turn:
                _redact(redacted)
            session.flush()
            self._compact(session)
            report = ForgetReport(len(turn), memories, suggestions, summaries)
        return report

    def forget_phrase(self, phrase: str) -> ForgetReport:
        if not plain(phrase).split():
            return ForgetReport()
        mentions = phrase_matcher(phrase)
        with session_scope(self._session_factory) as session:
            # Cada mensaje que lo nombra, con su turno: la respuesta a lo que dijo
            # habla de lo mismo aunque no lo nombre.
            said: dict[int, MessageModel] = {}
            for message in session.scalars(
                select(MessageModel).where(MessageModel.content.is_not(None))
            ):
                if mentions(message.content or ""):
                    for in_turn in _turn_of(session, message):
                        said[in_turn.id] = in_turn
            messages = list(said.values())
            events = _events_of(session, messages)
            suggestions, linked_memories = self._forget_suggestions(
                session, lambda texts: _any(texts, mentions), events
            )
            memories = self._forget_memories(
                session, lambda texts: _any(texts, mentions), events, linked_memories
            )
            for message in messages:
                _redact(message)
            summaries = self._trim_summaries(session, mentions)
            session.flush()
            self._compact(session)
            report = ForgetReport(len(messages), memories, suggestions, summaries)
        return report

    def _forget_memories(
        self,
        session: Session,
        matches: Callable[[Iterable[str | None]], bool],
        events: set[int],
        memory_ids: set[int],
    ) -> int:
        """Borra como «borrar» de 0.1 cada recuerdo que casa, con su historia entera."""
        revisions: dict[int, list[MemoryRevisionModel]] = {}
        for revision in session.scalars(select(MemoryRevisionModel)):
            revisions.setdefault(revision.memory_id, []).append(revision)
        forgotten = 0
        for memory in session.scalars(
            select(MemoryModel).where(MemoryModel.status != MemoryStatus.DELETED)
        ):
            history = revisions.get(memory.id, [])
            texts = [memory.person, memory.topic]
            texts += [revision.content for revision in history]
            texts += [revision.said_by for revision in history]
            linked = memory.id in memory_ids or any(
                revision.source_event_id in events for revision in history
            )
            if not (linked or matches(texts)):
                continue
            for revision in history:
                revision.content = None
                revision.said_by = None
            memory.person = None
            memory.topic = None
            memory.status = MemoryStatus.DELETED
            memory.updated_at = _now()
            forgotten += 1
        return forgotten

    def _forget_suggestions(
        self,
        session: Session,
        matches: Callable[[Iterable[str | None]], bool],
        events: set[int],
        dreamed_days: frozenset[date] = frozenset(),
    ) -> tuple[int, set[int]]:
        """Borra las sugerencias que casan; devuelve cuántas y los recuerdos que dieron.

        De lo que soñó el sueño en ``dreamed_days`` se borra lo que espera su sí: sale
        de todos los mensajes del día y no se sabe de cuál. Lo que él ya contestó se
        queda, salvo que case: es suyo.
        """
        forgotten = 0
        memories: set[int] = set()
        for suggestion in session.scalars(select(MemorySuggestionModel)):
            texts = [suggestion.content, suggestion.person, suggestion.topic, suggestion.said_by]
            dreamed_then = (
                suggestion.dreamed_day in dreamed_days
                and suggestion.status is MemorySuggestionStatus.PENDING
            )
            if suggestion.source_event_id in events or dreamed_then or matches(texts):
                if suggestion.resulting_memory_id is not None:
                    memories.add(suggestion.resulting_memory_id)
                session.delete(suggestion)
                forgotten += 1
        return forgotten, memories

    def _trim_summaries(self, session: Session, mentions: Callable[[str], bool]) -> int:
        """Quita de cada resumen las frases que nombran lo olvidado; si no queda nada, lo borra."""
        changed = 0
        summaries: list[ConversationSummaryModel | DaySummaryModel] = [
            *session.scalars(select(ConversationSummaryModel)),
            *session.scalars(select(DaySummaryModel)),
        ]
        for summary in summaries:
            if not mentions(summary.content):
                continue
            kept = without_sentences(summary.content, mentions)
            if kept:
                summary.content = kept
            else:
                session.delete(summary)
            changed += 1
        return changed

    @staticmethod
    def _delete(session: Session, statement: Any) -> int:
        result = session.execute(statement)
        return int(getattr(result, "rowcount", 0) or 0)

    @staticmethod
    def _compact(session: Session) -> None:
        """Compacta el índice de palabras, que hasta entonces guarda los términos borrados.

        En la misma transacción que lo demás: si compactar falla, no se olvida nada y
        la orden se puede repetir sobre el mismo mensaje (ronda 2 de Codex).
        """
        session.execute(text("INSERT INTO message_fts(message_fts) VALUES('optimize')"))
        session.execute(text("INSERT INTO knowledge_fts(knowledge_fts) VALUES('optimize')"))


def _turn_of(session: Session, message: MessageModel) -> list[MessageModel]:
    """``message`` y los de su mismo turno: lo que dijo y lo que le contestó Sirius."""
    turn = [message]
    if message.operation_id is not None:
        turn += session.scalars(
            select(MessageModel).where(
                MessageModel.conversation_id == message.conversation_id,
                MessageModel.operation_id == message.operation_id,
                MessageModel.id != message.id,
            )
        ).all()
    return turn


def _events_of(session: Session, messages: Iterable[MessageModel]) -> set[int]:
    """Los eventos ligados a ``messages``: de ahí cuelga lo que salió de ellos."""
    ids = [message.id for message in messages]
    if not ids:
        return set()
    return set(session.scalars(select(EventModel.id).where(EventModel.message_id.in_(ids))))


def _any(texts: Iterable[str | None], mentions: Callable[[str], bool]) -> bool:
    return any(value and mentions(value) for value in texts)


def _redact(message: MessageModel) -> None:
    """Como «borrar» un mensaje en 0.1 (PA-016): sin contenido y marcado borrado."""
    message.content = None
    message.status = MessageStatus.REDACTED
    message.redacted_at = _now()


def build_sqlite_forgetter(database_path: Path) -> SqliteForgetter:
    engine = build_engine(database_path)
    event.listen(engine, "connect", _secure_delete)
    return SqliteForgetter(build_session_factory(engine), engine)
