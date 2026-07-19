"""Atomicity of memory archival, via ``SqliteUnitOfWork`` (B4d).

Mirrors ``test_correct_memory_unit_of_work.py``: the event and the status
change must commit together or not at all, a mid-transaction failure leaves
the database exactly as it was before the attempt, and a following valid
attempt still succeeds.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence import sqlite_memory_repository
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, EventModel, MemoryModel
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.memory import MemoryStatus


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _row_counts(database_path: Path) -> tuple[int, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        events = len(session.scalars(select(EventModel)).all())
        memories = len(session.scalars(select(MemoryModel)).all())
        return events, memories


def _memory_status(database_path: Path, memory_id: int) -> MemoryStatus:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(MemoryModel, memory_id)
        assert model is not None
        return MemoryStatus(model.status)


def _create_memory(database_path: Path) -> int:
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    return memory.id


@pytest.mark.integration
def test_event_and_status_change_commit_together_in_one_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)
    events_before, memories_before = _row_counts(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    unit_of_work.begin()
    unit_of_work.event_repository.append("memory.archived", "user", None)

    # Nothing new is visible from an independent connection before commit,
    # and the status has not moved yet either.
    assert _row_counts(database_path) == (events_before, memories_before)
    assert _memory_status(database_path, memory_id) is MemoryStatus.CURRENT

    unit_of_work.memory_repository.archive_memory(memory_id)
    unit_of_work.commit()
    unit_of_work.close()

    events_after, memories_after = _row_counts(database_path)
    assert events_after == events_before + 1
    assert memories_after == memories_before
    assert _memory_status(database_path, memory_id) is MemoryStatus.ARCHIVED


def _boom_archive_memory(self: object, memory_id: int) -> None:
    msg = "simulated archive failure"
    raise RuntimeError(msg)


@pytest.mark.integration
def test_archive_rolls_back_the_event_when_the_status_change_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)
    counts_before = _row_counts(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ArchiveMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_memory_repository.SqliteMemoryRepository, "archive_memory", _boom_archive_memory
    )

    with pytest.raises(RuntimeError):
        use_case.archive(memory_id)

    assert _row_counts(database_path) == counts_before
    monkeypatch.undo()
    assert _memory_status(database_path, memory_id) is MemoryStatus.CURRENT


@pytest.mark.integration
def test_a_valid_archive_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ArchiveMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_memory_repository.SqliteMemoryRepository, "archive_memory", _boom_archive_memory
    )
    with pytest.raises(RuntimeError):
        use_case.archive(memory_id)

    monkeypatch.undo()
    archived = use_case.archive(memory_id)

    assert archived.status is MemoryStatus.ARCHIVED
