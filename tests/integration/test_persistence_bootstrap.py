from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import (
    ConversationModel,
    MemoryModel,
    MemoryRevisionModel,
    ProjectModel,
)
from sirius.infrastructure.paths import resolve_paths


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _conversation_rows(database_path: Path) -> list[ConversationModel]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return list(session.scalars(select(ConversationModel)).all())


def _project_rows(database_path: Path) -> list[ProjectModel]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return list(session.scalars(select(ProjectModel)).all())


def _memory_rows(database_path: Path) -> list[MemoryModel]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return list(session.scalars(select(MemoryModel)).all())


def _memory_revision_rows(database_path: Path) -> list[MemoryRevisionModel]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return list(session.scalars(select(MemoryRevisionModel)).all())


@pytest.mark.integration
def test_initialize_persistence_creates_directories_schema_main_conversation_and_project() -> None:
    paths = resolve_paths()

    initialize_persistence(paths)

    assert all(directory.is_dir() for directory in paths.all_dirs())
    database_path = paths.data_dir / "sirius.db"
    assert database_path.is_file()

    conversation_rows = _conversation_rows(database_path)
    assert len(conversation_rows) == 1
    assert conversation_rows[0].is_main is True

    project_rows = _project_rows(database_path)
    assert len(project_rows) == 1
    assert project_rows[0].is_active is True
    assert project_rows[0].name == ""


@pytest.mark.integration
def test_initialize_persistence_creates_memory_tables_without_seeding_any_memory() -> None:
    paths = resolve_paths()

    initialize_persistence(paths)

    database_path = paths.data_dir / "sirius.db"
    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert {"memories", "memory_revisions"}.issubset(table_names)
    assert _memory_rows(database_path) == []
    assert _memory_revision_rows(database_path) == []


@pytest.mark.integration
def test_starting_sirius_twice_is_idempotent_and_does_not_duplicate_anything() -> None:
    paths = resolve_paths()

    initialize_persistence(paths)  # first startup
    initialize_persistence(paths)  # second startup, same local data directory

    database_path = paths.data_dir / "sirius.db"
    assert len(_conversation_rows(database_path)) == 1
    assert len(_project_rows(database_path)) == 1
    assert _memory_rows(database_path) == []
