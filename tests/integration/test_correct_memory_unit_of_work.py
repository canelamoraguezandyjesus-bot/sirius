"""Atomicity of memory correction, via ``SqliteUnitOfWork`` (B4c).

Mirrors ``test_save_manual_memory_unit_of_work.py``: the event and the new
revision must commit together or not at all, a mid-transaction failure
leaves the database exactly as it was before the attempt, and a following
valid attempt still succeeds.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence import sqlite_memory_repository
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, EventModel, MemoryModel, MemoryRevisionModel
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.correct_memory import CorrectMemoryUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _row_counts(database_path: Path) -> tuple[int, int, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        events = len(session.scalars(select(EventModel)).all())
        memories = len(session.scalars(select(MemoryModel)).all())
        revisions = len(session.scalars(select(MemoryRevisionModel)).all())
        return events, memories, revisions


def _create_memory(database_path: Path) -> int:
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    return memory.id


@pytest.mark.integration
def test_event_and_new_revision_commit_together_in_one_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)
    events_before, memories_before, revisions_before = _row_counts(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    unit_of_work.begin()
    event = unit_of_work.event_repository.append("memory.corrected", "user", None)
    unit_of_work.memory_repository.correct_memory(
        memory_id,
        "preferencia corregida",
        "Corrección manual del usuario",
        source_event_id=event.id,
    )

    # Nothing new is visible from an independent connection before commit.
    assert _row_counts(database_path) == (events_before, memories_before, revisions_before)

    unit_of_work.commit()
    unit_of_work.close()

    events_after, memories_after, revisions_after = _row_counts(database_path)
    assert events_after == events_before + 1
    assert memories_after == memories_before
    assert revisions_after == revisions_before + 1


def _boom_correct_memory(
    self: object, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
) -> None:
    msg = "simulated revision-creation failure"
    raise RuntimeError(msg)


@pytest.mark.integration
def test_correction_rolls_back_the_event_when_the_revision_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)
    counts_before = _row_counts(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = CorrectMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_memory_repository.SqliteMemoryRepository, "correct_memory", _boom_correct_memory
    )

    with pytest.raises(RuntimeError):
        use_case.correct(memory_id, "no debería persistir")

    # The event write happened first, inside the same not-yet-committed
    # transaction as the failed revision write; both must be gone, and the
    # memory's pointer must not have moved.
    assert _row_counts(database_path) == counts_before


@pytest.mark.integration
def test_a_valid_correction_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = CorrectMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_memory_repository.SqliteMemoryRepository, "correct_memory", _boom_correct_memory
    )
    with pytest.raises(RuntimeError):
        use_case.correct(memory_id, "primer intento, falla")

    monkeypatch.undo()
    corrected = use_case.correct(memory_id, "segundo intento, correcto")

    assert corrected.current_revision.content == "segundo intento, correcto"
    assert corrected.current_revision.version == 2


@pytest.mark.integration
def test_correcting_an_unlocked_category_clears_it_in_the_same_transaction(
    tmp_path: Path,
) -> None:
    """D7, SIRIUS-ARQ-0.2 §6.1 "Corrección de contenido y reetiquetado": the
    content that produced an automatic (unlocked) category no longer
    describes the memory once corrected — no double, no Qt import, only the
    real ``CorrectMemoryUseCase``/``SqliteUnitOfWork``."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)

    setup_unit_of_work = build_sqlite_unit_of_work(database_path)
    with setup_unit_of_work as uow:
        wrote = uow.memory_repository.set_category(
            memory_id, "trabajo", observed_revision_version=1
        )
        uow.commit()
    assert wrote is True

    use_case = CorrectMemoryUseCase(build_sqlite_unit_of_work(database_path))
    corrected = use_case.correct(memory_id, "contenido corregido")

    assert corrected.category is None
    assert corrected.category_locked is False


@pytest.mark.integration
def test_correcting_a_locked_category_leaves_it_untouched(tmp_path: Path) -> None:
    """D7 point 3: a category the user already set or corrected is
    definitive — correcting the memory's content never reopens it."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id = _create_memory(database_path)

    setup_unit_of_work = build_sqlite_unit_of_work(database_path)
    with setup_unit_of_work as uow:
        uow.memory_repository.set_user_category(memory_id, "personal")
        uow.commit()

    use_case = CorrectMemoryUseCase(build_sqlite_unit_of_work(database_path))
    corrected = use_case.correct(memory_id, "contenido corregido de nuevo")

    assert corrected.category == "personal"
    assert corrected.category_locked is True
