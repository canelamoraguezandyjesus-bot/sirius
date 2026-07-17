import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, ProjectModel
from sirius.adapters.persistence.sqlite_project_repository import (
    SqliteProjectRepository,
    build_sqlite_project_repository,
)


def _build_repository(database_path: Path) -> SqliteProjectRepository:
    repository = build_sqlite_project_repository(database_path)
    Base.metadata.create_all(build_engine(database_path))
    return repository


@pytest.mark.integration
def test_get_or_create_active_project_creates_exactly_one_row_with_neutral_values(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    project = repository.get_or_create_active_project()

    assert project.name == ""
    assert project.objective == ""
    assert project.current_state == ""
    assert project.next_step == ""

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1
    assert rows[0].id == project.id


@pytest.mark.integration
def test_get_or_create_active_project_is_idempotent_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    first_repository = _build_repository(database_path)
    first_project = first_repository.get_or_create_active_project()

    # Simulate closing the app and reopening the store with a brand-new engine.
    second_repository = build_sqlite_project_repository(database_path)
    second_project = second_repository.get_or_create_active_project()

    assert second_project.id == first_project.id

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1


@pytest.mark.integration
def test_project_updates_persist_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()

    repository.update_project(
        project.id,
        name="Sirius",
        objective="Cerrar V3",
        current_state="en curso",
        next_step="escribir pruebas",
    )

    reopened_repository = build_sqlite_project_repository(database_path)
    reopened_project = reopened_repository.get_or_create_active_project()

    assert reopened_project.name == "Sirius"
    assert reopened_project.objective == "Cerrar V3"
    assert reopened_project.current_state == "en curso"
    assert reopened_project.next_step == "escribir pruebas"


@pytest.mark.integration
def test_update_project_full_update_sets_every_field(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()

    updated = repository.update_project(
        project.id,
        name="Sirius",
        objective="objetivo",
        current_state="estado",
        next_step="siguiente",
    )

    assert updated.name == "Sirius"
    assert updated.objective == "objetivo"
    assert updated.current_state == "estado"
    assert updated.next_step == "siguiente"


@pytest.mark.integration
def test_update_project_partial_update_leaves_other_fields_untouched(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()
    repository.update_project(
        project.id,
        name="Sirius",
        objective="objetivo original",
        current_state="estado original",
        next_step="siguiente original",
    )

    updated = repository.update_project(project.id, next_step="siguiente actualizado")

    assert updated.name == "Sirius"
    assert updated.objective == "objetivo original"
    assert updated.current_state == "estado original"
    assert updated.next_step == "siguiente actualizado"


@pytest.mark.integration
def test_get_or_create_active_project_seeds_empty_blockers(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    project = repository.get_or_create_active_project()

    assert project.blockers == ""


@pytest.mark.integration
def test_update_project_writes_and_reads_back_blockers(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()

    updated = repository.update_project(project.id, blockers="bloqueo uno\nbloqueo dos")

    assert updated.blockers == "bloqueo uno\nbloqueo dos"

    reopened = build_sqlite_project_repository(database_path).get_or_create_active_project()
    assert reopened.blockers == "bloqueo uno\nbloqueo dos"


@pytest.mark.integration
def test_update_project_updates_state_blockers_and_next_step_together(tmp_path: Path) -> None:
    """B3b: a single continuity update writes all three fields in one call."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()
    repository.update_project(project.id, name="Sirius", objective="objetivo")

    updated = repository.update_project(
        project.id,
        current_state="en curso",
        blockers="esperando revisión",
        next_step="publicar",
    )

    assert updated.name == "Sirius"  # untouched by this call
    assert updated.objective == "objetivo"  # untouched by this call
    assert updated.current_state == "en curso"
    assert updated.blockers == "esperando revisión"
    assert updated.next_step == "publicar"


@pytest.mark.integration
def test_update_project_leaves_blockers_untouched_when_not_passed(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()
    repository.update_project(project.id, blockers="bloqueo persistente")

    updated = repository.update_project(project.id, current_state="nuevo estado")

    assert updated.blockers == "bloqueo persistente"
    assert updated.current_state == "nuevo estado"


@pytest.mark.integration
def test_update_project_blockers_can_be_cleared_explicitly(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()
    repository.update_project(project.id, blockers="bloqueo temporal")

    updated = repository.update_project(project.id, blockers="")

    assert updated.blockers == ""


@pytest.mark.integration
def test_update_project_advances_updated_at_when_only_blockers_change(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()

    time.sleep(0.01)
    updated = repository.update_project(project.id, blockers="bloqueo nuevo")

    assert updated.updated_at > project.updated_at
    assert updated.created_at == project.created_at


@pytest.mark.integration
def test_failed_continuity_update_leaves_no_partial_change(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()
    repository.update_project(
        project.id,
        current_state="estado original",
        blockers="bloqueo original",
        next_step="siguiente original",
    )

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        model = session.get(ProjectModel, project.id)
        assert model is not None
        model.current_state = "corrupto a mitad de camino"
        model.blockers = "bloqueo corrupto a mitad de camino"
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        model = session.get(ProjectModel, project.id)
        assert model is not None
        assert model.current_state == "estado original"
        assert model.blockers == "bloqueo original"
        assert model.next_step == "siguiente original"


@pytest.mark.integration
def test_update_project_advances_updated_at(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()

    time.sleep(0.01)
    updated = repository.update_project(project.id, current_state="en curso")

    assert updated.updated_at > project.updated_at
    assert updated.created_at == project.created_at


@pytest.mark.integration
def test_update_project_rejects_unknown_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown project"):
        repository.update_project(999, name="fantasma")


@pytest.mark.integration
def test_database_rejects_a_second_active_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    with session_scope(session_factory) as session:
        session.add(
            ProjectModel(
                name="",
                objective="",
                current_state="",
                next_step="",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(
            ProjectModel(
                name="",
                objective="",
                current_state="",
                next_step="",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()

    with session_scope(session_factory) as session:
        rows = session.scalars(select(ProjectModel)).all()
    assert len(rows) == 1


@pytest.mark.integration
def test_failed_update_leaves_no_partial_change(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project = repository.get_or_create_active_project()
    repository.update_project(project.id, name="original", objective="objetivo original")

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        model = session.get(ProjectModel, project.id)
        assert model is not None
        model.name = "corrupto a mitad de camino"
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        model = session.get(ProjectModel, project.id)
        assert model is not None
        assert model.name == "original"
        assert model.objective == "objetivo original"
