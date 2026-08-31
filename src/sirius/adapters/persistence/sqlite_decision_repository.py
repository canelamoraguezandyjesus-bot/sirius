"""SQLite-backed implementation of the decision repository port."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import CursorResult, Engine, exists, select, update
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    chunked,
    session_scope,
    sqlite_variable_limit,
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
        category=model.category,
        category_locked=model.category_locked,
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


def _load_decisions(session: Session, models: Sequence[DecisionModel]) -> list[Decision]:
    """Load the current revision of every model in a bounded number of queries.

    ``_load_decision`` issues one query per model; called from a list method
    that turns into N+1 queries for N models. This loads every current
    revision the set needs via ``IN (...)`` queries instead, batched to the
    connection's ``SQLITE_LIMIT_VARIABLE_NUMBER`` so a large set doesn't blow
    past SQLite's bound-parameter limit in a single statement.
    """
    if not models:
        return []
    decision_ids = [model.id for model in models]
    revisions_by_decision_id: dict[int, DecisionRevisionModel] = {}
    for batch in chunked(decision_ids, sqlite_variable_limit(session)):
        revision_models = session.scalars(
            select(DecisionRevisionModel).where(
                DecisionRevisionModel.decision_id.in_(batch),
                DecisionRevisionModel.is_current.is_(True),
            )
        ).all()
        revisions_by_decision_id.update(
            (revision.decision_id, revision) for revision in revision_models
        )
    decisions = []
    for model in models:
        revision_model = revisions_by_decision_id.get(model.id)
        if revision_model is None:
            msg = f"Decision {model.id} has no current revision; data is corrupt."
            raise ValueError(msg)
        decisions.append(_to_domain_decision(model, revision_model))
    return decisions


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
            return _load_decisions(session, models)

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        if not categories:
            return []
        with self._scope() as session:
            models = session.scalars(
                select(DecisionModel)
                .where(
                    DecisionModel.status == DecisionStatus.APPROVED,
                    DecisionModel.category.is_not(None),
                )
                .order_by(DecisionModel.id)
            ).all()
            return _load_decisions(session, models)

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
            return _load_decisions(session, models)

    def list_proposed_decisions(self) -> list[Decision]:
        with self._scope() as session:
            models = session.scalars(
                select(DecisionModel)
                .where(DecisionModel.status == DecisionStatus.PROPOSED)
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

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        with self._scope() as session:
            statement = (
                update(DecisionModel)
                .where(
                    DecisionModel.id == decision_id,
                    DecisionModel.category_locked.is_(False),
                    exists().where(
                        DecisionRevisionModel.decision_id == DecisionModel.id,
                        DecisionRevisionModel.is_current.is_(True),
                        DecisionRevisionModel.version == observed_revision_version,
                    ),
                )
                .values(category=category)
            )
            result = cast(CursorResult[None], session.execute(statement))
            return result.rowcount > 0

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        with self._scope() as session:
            decision_model = session.get(DecisionModel, decision_id)
            if decision_model is None:
                msg = f"Unknown decision id: {decision_id}"
                raise ValueError(msg)
            decision_model.category = category
            decision_model.category_locked = True
            session.flush()
            return _load_decision(session, decision_model)

    def list_uncategorized(self) -> list[Decision]:
        with self._scope() as session:
            models = session.scalars(
                select(DecisionModel)
                .where(
                    DecisionModel.category.is_(None),
                    DecisionModel.category_locked.is_(False),
                )
                .order_by(DecisionModel.id)
            ).all()
            return _load_decisions(session, models)


def build_sqlite_decision_repository(database_path: Path) -> SqliteDecisionRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteDecisionRepository(session_factory, engine)


def bind_sqlite_decision_repository(session: Session) -> SqliteDecisionRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteDecisionRepository(None, None, session=session)
