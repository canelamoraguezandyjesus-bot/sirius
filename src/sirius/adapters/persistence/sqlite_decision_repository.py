"""SQLite-backed implementation of the decision repository port."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import DecisionModel, DecisionRevisionModel
from sirius.domain.decision import (
    Decision,
    DecisionRevision,
    DecisionStatus,
    ensure_can_approve,
    ensure_can_archive,
    ensure_can_supersede,
    ensure_valid_content,
    ensure_valid_subject,
)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_revision(model: DecisionRevisionModel) -> DecisionRevision:
    return DecisionRevision(
        id=model.id,
        decision_id=model.decision_id,
        version=model.version,
        content=model.content,
        source_event_id=model.source_event_id,
        created_at=model.created_at.replace(tzinfo=UTC),
    )


def _to_domain_decision(model: DecisionModel, revision_model: DecisionRevisionModel) -> Decision:
    return Decision(
        id=model.id,
        subject=model.subject,
        project_id=model.project_id,
        status=model.status,
        current_revision=_to_domain_revision(revision_model),
        created_at=model.created_at.replace(tzinfo=UTC),
        updated_at=model.updated_at.replace(tzinfo=UTC),
        supersedes_decision_id=model.supersedes_decision_id,
    )


def _get_current_revision_model(session: Session, decision_id: int) -> DecisionRevisionModel:
    revision_model = session.scalars(
        select(DecisionRevisionModel).where(
            DecisionRevisionModel.decision_id == decision_id,
            DecisionRevisionModel.is_current.is_(True),
        )
    ).first()
    if revision_model is None:
        msg = f"Decision {decision_id} has no current revision; data is corrupt."
        raise ValueError(msg)
    return revision_model


def _load_decision(session: Session, model: DecisionModel) -> Decision:
    revision_model = _get_current_revision_model(session, model.id)
    return _to_domain_decision(model, revision_model)


class SqliteDecisionRepository:
    """Decision repository backed by a local SQLite database.

    Normally owns its ``session_factory`` and opens/commits/closes one short
    session per call (via ``session_scope``). When ``session`` is given
    instead, every call writes through that externally owned session and
    never commits or closes it — this is how ``SqliteUnitOfWork`` binds this
    repository to the same transaction as ``SqliteEventRepository``, so both
    commit or roll back together.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None,
        engine: Engine | None,
        *,
        session: Session | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._external_session = session

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        if self._engine is not None:
            self._engine.dispose()

    @contextmanager
    def _scope(self) -> Iterator[Session]:
        if self._external_session is not None:
            yield self._external_session
            return
        assert self._session_factory is not None
        with session_scope(self._session_factory) as session:
            yield session

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        ensure_valid_subject(subject)
        ensure_valid_content(content)
        with self._scope() as session:
            now = _utc_now_naive()
            decision_model = DecisionModel(
                subject=subject,
                project_id=project_id,
                status=DecisionStatus.PROPOSED,
                created_at=now,
                updated_at=now,
            )
            session.add(decision_model)
            session.flush()

            revision_model = DecisionRevisionModel(
                decision_id=decision_model.id,
                version=1,
                content=content,
                source_event_id=source_event_id,
                is_current=True,
                created_at=now,
            )
            session.add(revision_model)
            session.flush()

            return _to_domain_decision(decision_model, revision_model)

    def get_decision(self, decision_id: int) -> Decision:
        with self._scope() as session:
            model = session.get(DecisionModel, decision_id)
            if model is None:
                msg = f"Unknown decision id: {decision_id}"
                raise ValueError(msg)
            return _load_decision(session, model)

    def approve_decision(self, decision_id: int) -> Decision:
        with self._scope() as session:
            decision_model = session.get(DecisionModel, decision_id)
            if decision_model is None:
                msg = f"Unknown decision id: {decision_id}"
                raise ValueError(msg)
            decision = _load_decision(session, decision_model)
            ensure_can_approve(decision)

            decision_model.status = DecisionStatus.APPROVED
            decision_model.updated_at = _utc_now_naive()
            session.flush()

            return _load_decision(session, decision_model)

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        with self._scope() as session:
            superseded_model = session.get(DecisionModel, superseded_decision_id)
            if superseded_model is None:
                msg = f"Unknown decision id: {superseded_decision_id}"
                raise ValueError(msg)
            superseding_model = session.get(DecisionModel, superseding_decision_id)
            if superseding_model is None:
                msg = f"Unknown decision id: {superseding_decision_id}"
                raise ValueError(msg)

            superseded = _load_decision(session, superseded_model)
            superseding = _load_decision(session, superseding_model)
            ensure_can_supersede(superseded, superseding)

            now = _utc_now_naive()
            superseded_model.status = DecisionStatus.SUPERSEDED
            superseded_model.updated_at = now
            superseding_model.status = DecisionStatus.APPROVED
            superseding_model.supersedes_decision_id = superseded_decision_id
            superseding_model.updated_at = now
            session.flush()

            return _load_decision(session, superseding_model)

    def list_current_decisions(self) -> list[Decision]:
        with self._scope() as session:
            models = session.scalars(
                select(DecisionModel)
                .where(DecisionModel.status == DecisionStatus.APPROVED)
                .order_by(DecisionModel.id)
            ).all()
            return [_load_decision(session, model) for model in models]

    def archive_decision(self, decision_id: int) -> Decision:
        with self._scope() as session:
            decision_model = session.get(DecisionModel, decision_id)
            if decision_model is None:
                msg = f"Unknown decision id: {decision_id}"
                raise ValueError(msg)
            decision = _load_decision(session, decision_model)
            ensure_can_archive(decision)

            decision_model.status = DecisionStatus.ARCHIVED
            decision_model.updated_at = _utc_now_naive()
            session.flush()

            return _load_decision(session, decision_model)

    def list_archived_decisions(self) -> list[Decision]:
        with self._scope() as session:
            models = session.scalars(
                select(DecisionModel)
                .where(DecisionModel.status == DecisionStatus.ARCHIVED)
                .order_by(DecisionModel.id)
            ).all()
            return [_load_decision(session, model) for model in models]

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        with self._scope() as session:
            model = session.scalars(
                select(DecisionModel).where(DecisionModel.supersedes_decision_id == decision_id)
            ).first()
            if model is None:
                return None
            return _load_decision(session, model)


def build_sqlite_decision_repository(database_path: Path) -> SqliteDecisionRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteDecisionRepository(session_factory, engine)


def bind_sqlite_decision_repository(session: Session) -> SqliteDecisionRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteDecisionRepository(None, None, session=session)
