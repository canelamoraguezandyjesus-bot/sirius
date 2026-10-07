"""SQLite del modo, las marcas y los resúmenes de la charla (pieza D de ADR-233) y del juez (E)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import (
    ConversationModeModel,
    ConversationSummaryModel,
    JudgeScoreModel,
    MessageModel,
    ReplyMarkModel,
)
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.conversation_mode import ConversationMode
from sirius.domain.conversation_summary import ConversationSummary
from sirius.domain.reply_judge import JudgeScore
from sirius.domain.reply_mark import MarkedReply, ReplyMark


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SqliteRobotConversationRepository:
    """Modo, marcas, resúmenes y notas del juez, en la misma base que la conversación."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        self._engine.dispose()

    # --- Modo ---

    def get_mode(self, conversation_id: int) -> ConversationMode:
        with session_scope(self._session_factory) as session:
            row = session.get(ConversationModeModel, conversation_id)
            return ConversationMode(row.mode) if row is not None else ConversationMode.NORMAL

    def set_mode(self, conversation_id: int, mode: ConversationMode) -> None:
        with session_scope(self._session_factory) as session:
            row = session.get(ConversationModeModel, conversation_id)
            if row is None:
                session.add(
                    ConversationModeModel(
                        conversation_id=conversation_id,
                        mode=mode.value,
                        updated_at=_utc_now_naive(),
                    )
                )
            else:
                row.mode = mode.value
                row.updated_at = _utc_now_naive()

    # --- Marcas ---

    def record_model(self, message_id: int, model: str | None) -> None:
        with session_scope(self._session_factory) as session:
            row = session.get(ReplyMarkModel, message_id)
            if row is None:
                session.add(ReplyMarkModel(message_id=message_id, model=model))
            else:
                row.model = model

    def set_mark(self, message_id: int, mark: ReplyMark) -> None:
        with session_scope(self._session_factory) as session:
            message = session.get(MessageModel, message_id)
            if message is None or message.role is not MessageRole.SIRIUS:
                msg = f"El mensaje {message_id} no es una respuesta de Sirius."
                raise ValueError(msg)
            row = session.get(ReplyMarkModel, message_id)
            if row is None:
                row = ReplyMarkModel(message_id=message_id, model=None)
                session.add(row)
            row.mark = mark.value
            row.marked_at = _utc_now_naive()

    def marked_replies(self) -> list[MarkedReply]:
        with session_scope(self._session_factory) as session:
            rows = session.execute(
                select(ReplyMarkModel, MessageModel)
                .join(MessageModel, MessageModel.id == ReplyMarkModel.message_id)
                .where(ReplyMarkModel.mark.is_not(None))
                .order_by(MessageModel.conversation_id, MessageModel.sequence)
            ).all()
            return [
                MarkedReply(
                    message_id=message.id,
                    sequence=message.sequence,
                    mark=ReplyMark(mark_row.mark),
                    model=mark_row.model,
                    identity_version=message.identity_version,
                )
                for mark_row, message in rows
            ]

    # --- Resúmenes ---

    def latest(self, conversation_id: int) -> ConversationSummary | None:
        with session_scope(self._session_factory) as session:
            row = session.scalars(
                select(ConversationSummaryModel)
                .where(ConversationSummaryModel.conversation_id == conversation_id)
                .order_by(ConversationSummaryModel.up_to_sequence.desc())
                .limit(1)
            ).first()
            if row is None:
                return None
            return ConversationSummary(
                conversation_id=row.conversation_id,
                up_to_sequence=row.up_to_sequence,
                content=row.content,
            )

    def add(self, conversation_id: int, up_to_sequence: int, content: str) -> None:
        with session_scope(self._session_factory) as session:
            session.add(
                ConversationSummaryModel(
                    conversation_id=conversation_id,
                    up_to_sequence=up_to_sequence,
                    content=content,
                    created_at=_utc_now_naive(),
                )
            )

    # --- El juez ---

    def add_score(self, message_id: int, score: int, *, warned: bool) -> None:
        with session_scope(self._session_factory) as session:
            session.add(
                JudgeScoreModel(
                    message_id=message_id,
                    score=score,
                    warned=warned,
                    judged_at=_utc_now_naive(),
                )
            )

    def unjudged_replies(self) -> list[tuple[int, str]]:
        with session_scope(self._session_factory) as session:
            rows = session.execute(
                select(MessageModel.id, MessageModel.content)
                .join(ReplyMarkModel, ReplyMarkModel.message_id == MessageModel.id)
                .outerjoin(JudgeScoreModel, JudgeScoreModel.message_id == MessageModel.id)
                .where(
                    JudgeScoreModel.message_id.is_(None),
                    # Solo las de la 0.2: una respuesta vieja marcada desde el
                    # historial tiene fila de marca, pero sin modelo (ADR-237).
                    ReplyMarkModel.model.is_not(None),
                    MessageModel.role == MessageRole.SIRIUS,
                    MessageModel.status == MessageStatus.COMPLETED,
                    MessageModel.content.is_not(None),
                )
                .order_by(MessageModel.id)
            ).all()
            return [(row.id, row.content) for row in rows if row.content and row.content.strip()]

    def judge_scores(self) -> list[JudgeScore]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(JudgeScoreModel).order_by(JudgeScoreModel.message_id)
            ).all()
            return [
                JudgeScore(message_id=row.message_id, score=row.score, warned=row.warned)
                for row in rows
            ]


def build_sqlite_robot_conversation_repository(
    database_path: Path,
) -> SqliteRobotConversationRepository:
    engine = build_engine(database_path)
    return SqliteRobotConversationRepository(build_session_factory(engine), engine)
