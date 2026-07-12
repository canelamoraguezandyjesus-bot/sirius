from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import ConversationModel
from sirius.infrastructure.paths import resolve_paths


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _conversation_rows(database_path: Path) -> list[ConversationModel]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return list(session.scalars(select(ConversationModel)).all())


@pytest.mark.integration
def test_initialize_persistence_creates_directories_schema_and_main_conversation() -> None:
    paths = resolve_paths()

    initialize_persistence(paths)

    assert all(directory.is_dir() for directory in paths.all_dirs())
    database_path = paths.data_dir / "sirius.db"
    assert database_path.is_file()

    rows = _conversation_rows(database_path)
    assert len(rows) == 1
    assert rows[0].is_main is True


@pytest.mark.integration
def test_starting_sirius_twice_is_idempotent_and_does_not_duplicate_the_main_conversation() -> None:
    paths = resolve_paths()

    initialize_persistence(paths)  # first startup
    initialize_persistence(paths)  # second startup, same local data directory

    rows = _conversation_rows(paths.data_dir / "sirius.db")
    assert len(rows) == 1
