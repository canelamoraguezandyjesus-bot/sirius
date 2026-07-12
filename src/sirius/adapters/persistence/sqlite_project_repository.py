"""SQLite-backed implementation of the project repository port."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import ProjectModel
from sirius.domain.project import Project


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_project(model: ProjectModel) -> Project:
    return Project(
        id=model.id,
        name=model.name,
        objective=model.objective,
        current_state=model.current_state,
        next_step=model.next_step,
        created_at=model.created_at.replace(tzinfo=UTC),
        updated_at=model.updated_at.replace(tzinfo=UTC),
    )


def _find_active_project_model(session: Session) -> ProjectModel | None:
    return session.scalars(
        select(ProjectModel).where(ProjectModel.is_active.is_(True)).limit(1)
    ).first()


class SqliteProjectRepository:
    """Project repository backed by a local SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_or_create_active_project(self) -> Project:
        with session_scope(self._session_factory) as session:
            model = _find_active_project_model(session)
            if model is None:
                now = _utc_now_naive()
                model = ProjectModel(
                    name="",
                    objective="",
                    current_state="",
                    next_step="",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(model)
                session.flush()
            return _to_domain_project(model)

    def get_active_project(self) -> Project | None:
        with session_scope(self._session_factory) as session:
            model = _find_active_project_model(session)
            if model is None:
                return None
            return _to_domain_project(model)

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        objective: str | None = None,
        current_state: str | None = None,
        next_step: str | None = None,
    ) -> Project:
        with session_scope(self._session_factory) as session:
            model = session.get(ProjectModel, project_id)
            if model is None:
                msg = f"Unknown project id: {project_id}"
                raise ValueError(msg)

            if name is not None:
                model.name = name
            if objective is not None:
                model.objective = objective
            if current_state is not None:
                model.current_state = current_state
            if next_step is not None:
                model.next_step = next_step
            model.updated_at = _utc_now_naive()

            session.flush()
            return _to_domain_project(model)


def build_sqlite_project_repository(database_path: Path) -> SqliteProjectRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteProjectRepository(session_factory)
