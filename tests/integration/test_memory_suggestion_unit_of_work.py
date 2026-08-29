"""``SqliteUnitOfWork.memory_suggestion_repository`` shares the unit of work's
transaction (M4, SIRIUS-ARQ-0.2 §3.4): a suggestion created through it is
invisible from an independent connection until ``commit()``, and a rollback
discards it entirely — the same guarantee already proved for
``decision_repository``/``memory_repository`` in B4a/B4b.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, MemorySuggestionModel
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _suggestion_count(database_path: Path) -> int:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return len(session.scalars(select(MemorySuggestionModel)).all())


@pytest.mark.integration
def test_a_suggestion_created_through_the_unit_of_work_is_invisible_before_commit(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    unit_of_work.begin()
    unit_of_work.memory_suggestion_repository.create_suggestion("prefiere respuestas breves")

    assert _suggestion_count(database_path) == 0

    unit_of_work.commit()
    unit_of_work.close()

    assert _suggestion_count(database_path) == 1


@pytest.mark.integration
def test_exiting_without_commit_rolls_back_the_created_suggestion(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    with unit_of_work as uow:
        uow.memory_suggestion_repository.create_suggestion("no debería persistir")

    assert _suggestion_count(database_path) == 0
    unit_of_work.close()
