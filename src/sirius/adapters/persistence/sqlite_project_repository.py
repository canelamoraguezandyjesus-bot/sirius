"""SQLite-backed implementation of the project repository port."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import ProjectModel, ProjectRevisionModel
from sirius.domain.project import (
    Project,
    ProjectRevision,
    ProjectStatus,
    next_project_revision_version,
)


class CorruptProjectRevisionError(ValueError):
    """A revision row's ``blockers_json`` is not valid JSON.

    Raised instead of silently treating corrupted content as an empty
    blocker list, so storage corruption surfaces as an error rather than a
    quietly wrong answer.
    """


class InconsistentProjectRevisionError(ValueError):
    """A project's ``current_revision_id`` points at a revision that does
    not belong to that same project.

    ``current_revision_id`` carries a physical foreign key into
    ``project_revisions`` (guaranteeing the row exists), but a plain FK
    cannot express "and its project_id must match" — this check is the
    repository's own defense against that specific corruption, raised
    instead of silently returning the wrong project's content.
    """


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _blockers_to_json(blockers: tuple[str, ...]) -> str:
    return json.dumps(list(blockers))


def _blockers_from_json(project_id: int, raw: str) -> tuple[str, ...]:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as error:
        msg = f"Project {project_id} has a corrupt blockers_json revision: {error}"
        raise CorruptProjectRevisionError(msg) from error
    return tuple(decoded)


def _to_domain_revision(model: ProjectRevisionModel) -> ProjectRevision:
    return ProjectRevision(
        id=model.id,
        project_id=model.project_id,
        version=model.version,
        objective=model.objective,
        state_summary=model.state_summary,
        blockers=_blockers_from_json(model.project_id, model.blockers_json),
        next_step=model.next_step,
        source_event_id=model.source_event_id,
        created_at=model.created_at.replace(tzinfo=UTC),
    )


def _to_domain_project(model: ProjectModel, revision_model: ProjectRevisionModel | None) -> Project:
    return Project(
        id=model.id,
        name=model.name,
        status=model.status,
        current_revision=_to_domain_revision(revision_model) if revision_model else None,
        created_at=model.created_at.replace(tzinfo=UTC),
        updated_at=model.updated_at.replace(tzinfo=UTC),
        completed_at=model.completed_at.replace(tzinfo=UTC) if model.completed_at else None,
    )


def _find_active_project_model(session: Session) -> ProjectModel | None:
    return session.scalars(
        select(ProjectModel).where(ProjectModel.is_active.is_(True)).limit(1)
    ).first()


def _get_current_revision_model(
    session: Session, model: ProjectModel
) -> ProjectRevisionModel | None:
    """Resolve the project's current revision via ``current_revision_id`` —
    the sole authoritative pointer (SIRIUS-ARQ-0.1 S7.3). Raises
    ``InconsistentProjectRevisionError`` if the referenced row exists but
    belongs to a different project; that can never happen through this
    repository's own write paths, so it always signals external corruption.
    """
    if model.current_revision_id is None:
        return None
    revision_model = session.get(ProjectRevisionModel, model.current_revision_id)
    if revision_model is None:
        # The physical FK makes this unreachable in practice, but a
        # dangling pointer is still corruption, not "no revision yet".
        msg = (
            f"Project {model.id} has current_revision_id={model.current_revision_id}, "
            "which does not exist in project_revisions."
        )
        raise InconsistentProjectRevisionError(msg)
    if revision_model.project_id != model.id:
        msg = (
            f"Project {model.id} has current_revision_id={model.current_revision_id}, "
            f"which belongs to project {revision_model.project_id} instead."
        )
        raise InconsistentProjectRevisionError(msg)
    return revision_model


def _require_current_revision_model(session: Session, model: ProjectModel) -> ProjectRevisionModel:
    revision_model = _get_current_revision_model(session, model)
    if revision_model is None:
        msg = f"Project {model.id} has no current revision; it is not configured."
        raise ValueError(msg)
    return revision_model


def _load_project(session: Session, model: ProjectModel) -> Project:
    revision_model = _get_current_revision_model(session, model)
    return _to_domain_project(model, revision_model)


class SqliteProjectRepository:
    """Project repository backed by a local SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        self._engine.dispose()

    def ensure_bootstrap_project(self) -> None:
        with session_scope(self._session_factory) as session:
            has_any_row = session.scalars(select(ProjectModel.id).limit(1)).first() is not None
            if has_any_row:
                return
            now = _utc_now_naive()
            model = ProjectModel(
                name="",
                status=ProjectStatus.ACTIVE,
                current_revision_id=None,
                is_active=True,
                created_at=now,
                updated_at=now,
                completed_at=None,
                objective="",
                current_state="",
                blockers="",
                next_step="",
            )
            session.add(model)
            session.flush()

    def get_active_project(self) -> Project | None:
        with session_scope(self._session_factory) as session:
            model = _find_active_project_model(session)
            if model is None:
                return None
            return _load_project(session, model)

    def get_project(self, project_id: int) -> Project | None:
        with session_scope(self._session_factory) as session:
            model = session.get(ProjectModel, project_id)
            if model is None:
                return None
            return _load_project(session, model)

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        with session_scope(self._session_factory) as session:
            model = session.get(ProjectModel, project_id)
            if model is None:
                msg = f"Unknown project id: {project_id}"
                raise ValueError(msg)
            revision_models = session.scalars(
                select(ProjectRevisionModel)
                .where(ProjectRevisionModel.project_id == project_id)
                .order_by(ProjectRevisionModel.version)
            ).all()
            return tuple(_to_domain_revision(model) for model in revision_models)

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        with session_scope(self._session_factory) as session:
            now = _utc_now_naive()
            model = _find_active_project_model(session)
            if model is not None:
                existing_revision = _get_current_revision_model(session, model)
                if existing_revision is not None:
                    msg = "An active, configured project already exists."
                    raise ValueError(msg)
                # Reuse the unconfigured placeholder row in place.
                model.name = name
                model.updated_at = now
            else:
                model = ProjectModel(
                    name=name,
                    status=ProjectStatus.ACTIVE,
                    current_revision_id=None,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                    completed_at=None,
                    objective="",
                    current_state="",
                    blockers="",
                    next_step="",
                )
                session.add(model)
                session.flush()

            revision_model = ProjectRevisionModel(
                project_id=model.id,
                version=1,
                objective=objective,
                state_summary=state_summary,
                blockers_json=_blockers_to_json(blockers),
                next_step=next_step,
                source_event_id=None,
                created_at=now,
            )
            session.add(revision_model)
            session.flush()  # assigns revision_model.id

            model.current_revision_id = revision_model.id
            session.flush()

            return _to_domain_project(model, revision_model)

    def append_revision(
        self,
        project_id: int,
        *,
        objective: str,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
        source_event_id: int | None = None,
    ) -> Project:
        with session_scope(self._session_factory) as session:
            model = session.get(ProjectModel, project_id)
            if model is None:
                msg = f"Unknown project id: {project_id}"
                raise ValueError(msg)
            if model.status is not ProjectStatus.ACTIVE:
                msg = f"Project {project_id} is not active."
                raise ValueError(msg)
            current_revision_model = _require_current_revision_model(session, model)

            now = _utc_now_naive()
            new_revision_model = ProjectRevisionModel(
                project_id=project_id,
                version=next_project_revision_version(_to_domain_revision(current_revision_model)),
                objective=objective,
                state_summary=state_summary,
                blockers_json=_blockers_to_json(blockers),
                next_step=next_step,
                source_event_id=source_event_id,
                created_at=now,
            )
            # Inserted, then pointed at, within this same uncommitted
            # transaction: if anything below raises, session_scope() rolls
            # back the whole unit of work, so the insert never persists
            # (no orphaned revision) and current_revision_id keeps its
            # prior, already-committed value — never a half-updated pointer.
            session.add(new_revision_model)
            session.flush()  # assigns new_revision_model.id

            model.current_revision_id = new_revision_model.id
            model.updated_at = now
            session.flush()

            return _to_domain_project(model, new_revision_model)

    def complete_active_project(self, project_id: int) -> Project:
        with session_scope(self._session_factory) as session:
            model = session.get(ProjectModel, project_id)
            if model is None:
                msg = f"Unknown project id: {project_id}"
                raise ValueError(msg)
            if model.status is not ProjectStatus.ACTIVE:
                msg = f"Project {project_id} is not active."
                raise ValueError(msg)
            # current_revision_id is deliberately left untouched: completing
            # a project changes only its lifecycle fields, never which
            # revision is current.
            revision_model = _require_current_revision_model(session, model)

            now = _utc_now_naive()
            model.status = ProjectStatus.COMPLETED
            model.is_active = False
            model.completed_at = now
            model.updated_at = now
            session.flush()

            return _to_domain_project(model, revision_model)

    def list_completed_projects(self) -> tuple[Project, ...]:
        with session_scope(self._session_factory) as session:
            models = session.scalars(
                select(ProjectModel)
                .where(ProjectModel.status == ProjectStatus.COMPLETED)
                .order_by(ProjectModel.completed_at.desc())
            ).all()
            return tuple(_load_project(session, model) for model in models)


def build_sqlite_project_repository(database_path: Path) -> SqliteProjectRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteProjectRepository(session_factory, engine)
