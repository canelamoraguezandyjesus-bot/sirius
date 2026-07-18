"""Atomicity of the manual memory save, via ``SqliteUnitOfWork`` (B4a fix).

PR #36 review (Fase C, BLOCKER): the original ``SaveManualMemoryUseCase``
committed the origin event and the memory in two independent
repository sessions, so a failure between them could leave an orphan event.
SIRIUS-ARQ-0.1 S4/S8.1 require both writes to share one transaction. These
tests exercise that guarantee directly against the real SQLite adapters (no
fakes): the event, the memory, and its first revision commit together or not
at all, a mid-transaction failure at either write point leaves the database
exactly as it was before the attempt, and a following valid attempt still
succeeds.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence import sqlite_memory_repository
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, EventModel, MemoryModel, MemoryRevisionModel
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.save_manual_memory import MANUAL_MEMORY_ORIGIN, SaveManualMemoryUseCase


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _row_counts(database_path: Path) -> tuple[int, int, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        events = len(session.scalars(select(EventModel)).all())
        memories = len(session.scalars(select(MemoryModel)).all())
        revisions = len(session.scalars(select(MemoryRevisionModel)).all())
        return events, memories, revisions


@pytest.mark.integration
def test_event_memory_and_revision_commit_together_in_one_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    unit_of_work.begin()
    event = unit_of_work.event_repository.append("memory.manual_save", "user", None)
    unit_of_work.memory_repository.create_memory(
        "preferencia sin confirmar", MANUAL_MEMORY_ORIGIN, source_event_id=event.id
    )

    # Nothing is visible from an independent connection before commit: both
    # writes live in the same, still-open transaction.
    assert _row_counts(database_path) == (0, 0, 0)

    unit_of_work.commit()
    unit_of_work.close()

    # Once committed, the event, the memory, and its first revision are all
    # visible together.
    assert _row_counts(database_path) == (1, 1, 1)


@pytest.mark.integration
def test_use_case_rolls_back_the_event_when_memory_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = SaveManualMemoryUseCase(unit_of_work)

    def _boom(origin: str) -> None:
        msg = "simulated memory-creation failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_memory_repository, "ensure_valid_origin", _boom)

    with pytest.raises(RuntimeError):
        use_case.save("preferencia que nunca debería persistir")

    # The event write happened first, inside the same not-yet-committed
    # transaction as the failed memory write; both must be gone.
    assert _row_counts(database_path) == (0, 0, 0)


@pytest.mark.integration
def test_use_case_rolls_back_everything_when_revision_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = SaveManualMemoryUseCase(unit_of_work)

    class _FailingRevisionModel:
        def __init__(self, *args: object, **kwargs: object) -> None:
            msg = "simulated revision-creation failure"
            raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_memory_repository, "MemoryRevisionModel", _FailingRevisionModel)

    with pytest.raises(RuntimeError):
        use_case.save("preferencia cuya revisión nunca debería persistir")

    # The event and the memory row were both written inside the same
    # not-yet-committed transaction as the failed revision write; none of
    # the three may survive — not even the memory whose revision failed.
    assert _row_counts(database_path) == (0, 0, 0)


@pytest.mark.integration
def test_a_valid_save_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = SaveManualMemoryUseCase(unit_of_work)

    def _boom(origin: str) -> None:
        msg = "simulated memory-creation failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_memory_repository, "ensure_valid_origin", _boom)
    with pytest.raises(RuntimeError):
        use_case.save("primer intento, falla")

    monkeypatch.undo()
    memory = use_case.save("segundo intento, correcto")

    assert memory.current_revision.content == "segundo intento, correcto"
    assert _row_counts(database_path) == (1, 1, 1)
