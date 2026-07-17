"""Integration tests for SqliteProjectRepository (B3a/B3b/B3c).

Exercises the real SQLite-backed repository (schema, constraints, and
cross-reopen persistence) against the B3c contract: a single ``ACTIVE``
project plus an append-only, versioned revision history.
"""

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, ProjectModel, ProjectRevisionModel
from sirius.adapters.persistence.sqlite_project_repository import (
    CorruptProjectRevisionError,
    InconsistentProjectRevisionError,
    SqliteProjectRepository,
    build_sqlite_project_repository,
)
from sirius.domain.project import Project, ProjectStatus


def _build_repository(database_path: Path) -> SqliteProjectRepository:
    repository = build_sqlite_project_repository(database_path)
    Base.metadata.create_all(build_engine(database_path))
    return repository


def _create_configured_project(
    repository: SqliteProjectRepository,
    *,
    name: str = "Sirius",
    objective: str = "objetivo",
    state_summary: str = "estado",
    blockers: tuple[str, ...] = (),
    next_step: str = "siguiente",
) -> Project:
    repository.ensure_bootstrap_project()
    return repository.create_project(
        name, objective, state_summary=state_summary, blockers=blockers, next_step=next_step
    )


# --- ensure_bootstrap_project -------------------------------------------------


@pytest.mark.integration
def test_ensure_bootstrap_project_creates_exactly_one_placeholder_row(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    repository.ensure_bootstrap_project()

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1
    assert rows[0].name == ""
    assert rows[0].status is ProjectStatus.ACTIVE
    assert rows[0].current_revision_id is None

    project = repository.get_active_project()
    assert project is not None
    assert project.current_revision is None


@pytest.mark.integration
def test_ensure_bootstrap_project_is_a_no_op_when_a_row_already_exists(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, name="Sirius", objective="objetivo")

    repository.ensure_bootstrap_project()

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1
    assert repository.get_active_project() == created


@pytest.mark.integration
def test_ensure_bootstrap_project_is_idempotent_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    first_repository = _build_repository(database_path)
    first_repository.ensure_bootstrap_project()

    second_repository = build_sqlite_project_repository(database_path)
    second_repository.ensure_bootstrap_project()

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1


# --- create_project -----------------------------------------------------------


@pytest.mark.integration
def test_create_project_reuses_the_bootstrap_placeholder_row(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.ensure_bootstrap_project()
    placeholder = repository.get_active_project()
    assert placeholder is not None

    created = repository.create_project(
        "Sirius", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )

    assert created.id == placeholder.id
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1


@pytest.mark.integration
def test_create_project_inserts_a_new_row_when_no_placeholder_exists(tmp_path: Path) -> None:
    """After a project is completed, the next one gets an independent row —
    never reusing, reactivating, or overwriting the closed project (RF-018)."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    first = _create_configured_project(repository, name="Primero", objective="objetivo uno")
    repository.complete_active_project(first.id)

    second = repository.create_project(
        "Segundo", "objetivo dos", state_summary="estado", blockers=(), next_step="siguiente"
    )

    assert second.id != first.id
    assert second.status is ProjectStatus.ACTIVE
    reloaded_first = repository.get_project(first.id)
    assert reloaded_first is not None
    assert reloaded_first.status is ProjectStatus.COMPLETED
    assert reloaded_first.name == "Primero"  # never overwritten by the new project


@pytest.mark.integration
def test_create_project_sets_the_initial_fields_on_revision_one(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    created = _create_configured_project(
        repository,
        name="Sirius",
        objective="objetivo",
        state_summary="estado inicial",
        blockers=("bloqueo uno", "bloqueo dos"),
        next_step="siguiente paso",
    )

    assert created.name == "Sirius"
    assert created.current_revision is not None
    assert created.current_revision.version == 1
    assert created.current_revision.objective == "objetivo"
    assert created.current_revision.state_summary == "estado inicial"
    assert created.current_revision.blockers == ("bloqueo uno", "bloqueo dos")
    assert created.current_revision.next_step == "siguiente paso"

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(ProjectModel, created.id)
        assert model is not None
        assert model.current_revision_id == created.current_revision.id


@pytest.mark.integration
def test_create_project_rejects_a_second_active_configured_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    _create_configured_project(repository, name="Primero")

    with pytest.raises(ValueError, match="already exists"):
        repository.create_project(
            "Segundo", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
        )


@pytest.mark.integration
def test_project_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(
        repository,
        name="Sirius",
        objective="Cerrar V3",
        state_summary="en curso",
        next_step="escribir pruebas",
    )

    reopened_repository = build_sqlite_project_repository(database_path)
    reopened_project = reopened_repository.get_active_project()

    assert reopened_project is not None
    assert reopened_project.id == created.id
    assert reopened_project.name == "Sirius"
    assert reopened_project.current_revision is not None
    assert reopened_project.current_revision.objective == "Cerrar V3"
    assert reopened_project.current_revision.state_summary == "en curso"
    assert reopened_project.current_revision.next_step == "escribir pruebas"


# --- append_revision -----------------------------------------------------------


@pytest.mark.integration
def test_append_revision_creates_version_two(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)
    assert created.current_revision is not None

    updated = repository.append_revision(
        created.id,
        objective="objetivo",
        state_summary="estado nuevo",
        blockers=("bloqueo",),
        next_step="siguiente nuevo",
    )

    assert updated.current_revision is not None
    assert updated.current_revision.version == 2
    assert updated.current_revision.state_summary == "estado nuevo"
    assert updated.current_revision.blockers == ("bloqueo",)
    assert updated.current_revision.next_step == "siguiente nuevo"

    # The pointer itself, not just the resolved value, must have moved.
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(ProjectModel, created.id)
        assert model is not None
        assert model.current_revision_id == updated.current_revision.id
        assert model.current_revision_id != created.current_revision.id


@pytest.mark.integration
def test_append_revision_never_modifies_an_earlier_revision(tmp_path: Path) -> None:
    """Two consecutive appends create versions 2 and 3 without ever touching
    version 1's content or the version-1 row itself."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, state_summary="estado original")
    assert created.current_revision is not None

    repository.append_revision(
        created.id, objective="objetivo", state_summary="estado v2", blockers=(), next_step="s"
    )
    repository.append_revision(
        created.id, objective="objetivo", state_summary="estado v3", blockers=(), next_step="s"
    )

    history = repository.list_project_revisions(created.id)
    assert [revision.version for revision in history] == [1, 2, 3]
    assert history[0].id == created.current_revision.id
    assert history[0].state_summary == "estado original"
    assert history[1].state_summary == "estado v2"
    assert history[2].state_summary == "estado v3"


@pytest.mark.integration
def test_append_revision_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)
    repository.append_revision(
        created.id,
        objective="objetivo",
        state_summary="estado",
        blockers=("b1", "b2"),
        next_step="s",
    )

    reopened = build_sqlite_project_repository(database_path).get_active_project()

    assert reopened is not None
    assert reopened.current_revision is not None
    assert reopened.current_revision.version == 2
    assert reopened.current_revision.blockers == ("b1", "b2")


@pytest.mark.integration
def test_append_revision_advances_updated_at(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)

    time.sleep(0.01)
    updated = repository.append_revision(
        created.id, objective="objetivo", state_summary="estado", blockers=(), next_step="s"
    )

    assert updated.updated_at > created.updated_at
    assert updated.created_at == created.created_at


@pytest.mark.integration
def test_append_revision_rejects_unknown_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown project"):
        repository.append_revision(
            999, objective="o", state_summary="s", blockers=(), next_step="n"
        )


@pytest.mark.integration
def test_append_revision_rejects_a_completed_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)
    repository.complete_active_project(created.id)

    with pytest.raises(ValueError, match="not active"):
        repository.append_revision(
            created.id, objective="o", state_summary="s", blockers=(), next_step="n"
        )


@pytest.mark.integration
def test_failed_revision_write_leaves_no_partial_change(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, state_summary="estado original")

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        revision_model = session.scalars(
            select(ProjectRevisionModel).where(ProjectRevisionModel.project_id == created.id)
        ).one()
        revision_model.state_summary = "corrupto a mitad de camino"
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        revision_model = session.scalars(
            select(ProjectRevisionModel).where(ProjectRevisionModel.project_id == created.id)
        ).one()
        assert revision_model.state_summary == "estado original"


# --- complete_active_project ---------------------------------------------------


@pytest.mark.integration
def test_complete_active_project_marks_it_completed(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)

    completed = repository.complete_active_project(created.id)

    assert completed.status is ProjectStatus.COMPLETED
    assert completed.completed_at is not None


@pytest.mark.integration
def test_complete_active_project_preserves_the_current_revision(tmp_path: Path) -> None:
    """Completing a project after several revisions leaves current_revision_id
    pointing at the same, final revision — the pointer itself is untouched."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, state_summary="estado v1")
    repository.append_revision(
        created.id, objective="objetivo", state_summary="estado v2", blockers=(), next_step="s"
    )
    final = repository.append_revision(
        created.id, objective="objetivo", state_summary="estado v3", blockers=(), next_step="s"
    )
    assert final.current_revision is not None

    completed = repository.complete_active_project(created.id)

    assert completed.current_revision == final.current_revision

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(ProjectModel, created.id)
        assert model is not None
        assert model.current_revision_id == final.current_revision.id


@pytest.mark.integration
def test_completed_project_is_excluded_from_get_active_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)

    repository.complete_active_project(created.id)

    assert repository.get_active_project() is None


@pytest.mark.integration
def test_completed_project_remains_reachable_via_get_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, name="Histórico")

    repository.complete_active_project(created.id)

    reloaded = repository.get_project(created.id)
    assert reloaded is not None
    assert reloaded.name == "Histórico"
    assert reloaded.status is ProjectStatus.COMPLETED


@pytest.mark.integration
def test_complete_active_project_rejects_unknown_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown project"):
        repository.complete_active_project(999)


@pytest.mark.integration
def test_complete_active_project_rejects_an_already_completed_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)
    repository.complete_active_project(created.id)

    with pytest.raises(ValueError, match="not active"):
        repository.complete_active_project(created.id)


@pytest.mark.integration
def test_completion_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)
    repository.complete_active_project(created.id)

    reopened = build_sqlite_project_repository(database_path)
    assert reopened.get_active_project() is None
    reloaded = reopened.get_project(created.id)
    assert reloaded is not None
    assert reloaded.status is ProjectStatus.COMPLETED


# --- get_project / list_project_revisions --------------------------------------


@pytest.mark.integration
def test_get_project_returns_none_for_an_unknown_id(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    assert repository.get_project(999) is None


@pytest.mark.integration
def test_list_project_revisions_is_empty_for_an_unconfigured_placeholder(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.ensure_bootstrap_project()
    placeholder = repository.get_active_project()
    assert placeholder is not None

    assert repository.list_project_revisions(placeholder.id) == ()


@pytest.mark.integration
def test_list_project_revisions_rejects_an_unknown_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown project"):
        repository.list_project_revisions(999)


# --- blockers JSON codec / corruption -------------------------------------------


@pytest.mark.integration
def test_blockers_round_trip_through_json(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, blockers=("uno", "dos", ""))

    reopened = build_sqlite_project_repository(database_path).get_active_project()

    assert reopened is not None
    assert reopened.current_revision is not None
    assert reopened.current_revision.blockers == ("uno", "dos", "")
    assert created.current_revision is not None
    assert created.current_revision.blockers == ("uno", "dos", "")


@pytest.mark.integration
def test_corrupt_blockers_json_raises_instead_of_silently_becoming_empty(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    with session_scope(session_factory) as session:
        revision_model = session.scalars(
            select(ProjectRevisionModel).where(ProjectRevisionModel.project_id == created.id)
        ).one()
        revision_model.blockers_json = "{esto no es json valido"

    with pytest.raises(CorruptProjectRevisionError):
        repository.get_active_project()


# --- schema-level constraints ----------------------------------------------------


@pytest.mark.integration
def test_database_rejects_a_second_active_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    now = datetime.now(UTC).replace(tzinfo=None)

    def _new_model() -> ProjectModel:
        return ProjectModel(
            name="",
            status=ProjectStatus.ACTIVE,
            is_active=True,
            created_at=now,
            updated_at=now,
            completed_at=None,
            objective="",
            current_state="",
            blockers="",
            next_step="",
        )

    with session_scope(session_factory) as session:
        session.add(_new_model())

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(_new_model())
        session.flush()

    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1


@pytest.mark.integration
def test_current_revision_id_is_the_only_pointer_no_is_current_column_exists(
    tmp_path: Path,
) -> None:
    """B3c architectural correction: current_revision_id (SIRIUS-ARQ-0.1
    S7.3 "Campos mínimos") is the single authoritative source for "which
    revision is current" — project_revisions carries no second, competing
    flag."""
    database_path = tmp_path / "sirius.db"
    _build_repository(database_path)

    inspector = inspect(build_engine(database_path))
    project_columns = {c["name"] for c in inspector.get_columns("projects")}
    revision_columns = {c["name"] for c in inspector.get_columns("project_revisions")}

    assert "current_revision_id" in project_columns
    assert "is_current" not in revision_columns
    assert not hasattr(ProjectRevisionModel, "is_current")


@pytest.mark.integration
def test_current_revision_id_has_a_physical_foreign_key_to_project_revisions(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    _create_configured_project(repository)

    inspector = inspect(build_engine(database_path))
    fk_targets = {fk["referred_table"] for fk in inspector.get_foreign_keys("projects")}
    assert "project_revisions" in fk_targets


@pytest.mark.integration
def test_current_revision_id_rejects_a_revision_belonging_to_another_project(
    tmp_path: Path,
) -> None:
    """A physical FK only guarantees the referenced row exists, not that it
    belongs to the same project — the repository's own read-time validation
    must reject that specific corruption instead of silently returning the
    wrong project's content."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_a = _create_configured_project(repository, name="A", objective="objetivo A")
    repository.complete_active_project(project_a.id)
    project_b = repository.create_project(
        "B", "objetivo B", state_summary="estado", blockers=(), next_step="siguiente"
    )
    assert project_b.current_revision is not None

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    with session_scope(session_factory) as session:
        model_a = session.get(ProjectModel, project_a.id)
        assert model_a is not None
        # Corrupt A's pointer to reference B's revision instead of its own.
        model_a.current_revision_id = project_b.current_revision.id

    with pytest.raises(InconsistentProjectRevisionError):
        repository.get_project(project_a.id)


@pytest.mark.integration
def test_current_revision_id_rejects_a_dangling_reference(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository)

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    with session_scope(session_factory) as session:
        # Disable enforcement for this one connection just long enough to
        # write an otherwise-impossible dangling id, proving the
        # repository's own defense (not just the physical FK) catches it.
        session.execute(text("PRAGMA foreign_keys=OFF"))
        model = session.get(ProjectModel, created.id)
        assert model is not None
        model.current_revision_id = 999999

    with pytest.raises(InconsistentProjectRevisionError):
        repository.get_project(created.id)


@pytest.mark.integration
def test_append_revision_failure_between_insert_and_pointer_update_rolls_back_fully(
    tmp_path: Path,
) -> None:
    """Ante fallo: rollback completo; current_revision_id conserva el valor
    anterior; no queda una revisión huérfana."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = _create_configured_project(repository, state_summary="estado original")
    assert created.current_revision is not None
    original_revision_id = created.current_revision.id

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        # Reproduce append_revision's own sequence — insert the new
        # revision, flush to obtain its id, point the project at it — then
        # fail before the transaction commits.
        new_revision_model = ProjectRevisionModel(
            project_id=created.id,
            version=2,
            objective="objetivo",
            state_summary="estado a mitad de camino",
            blockers_json="[]",
            next_step="n",
            source_event_id=None,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        session.add(new_revision_model)
        session.flush()
        model = session.get(ProjectModel, created.id)
        assert model is not None
        model.current_revision_id = new_revision_model.id
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        model = session.get(ProjectModel, created.id)
        assert model is not None
        assert model.current_revision_id == original_revision_id  # unchanged

        revision_rows = session.scalars(
            select(ProjectRevisionModel).where(ProjectRevisionModel.project_id == created.id)
        ).all()
        assert [r.version for r in revision_rows] == [1]  # no orphaned version-2 row
