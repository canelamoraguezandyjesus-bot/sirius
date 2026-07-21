"""B6a: transactional synchronization of the FTS5 search indexes
(``message_fts``, ``knowledge_fts``) with the data they index
(SIRIUS-ARQ-0.1 S7.1/S8.1; ATD-004; D-11).

Every write goes through the real use cases and repositories — no fake
adapter — against a database migrated with real Alembic, so the SQLite
triggers the migration creates are actually exercised, exactly as they run
in production (``initialize_persistence`` always applies migrations before
any repository is used).

The critical invariant this file exists to prove (D-11/S7.4/audit): deleted
or redacted content never reappears in the index. It also proves the
transactional half of the contract — an index update never survives a
rollback of the data write it belongs to, and never precedes it either,
since both happen through the very same SQLite transaction via a trigger.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from sirius.adapters.persistence import sqlite_unit_of_work
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.correct_memory import CorrectMemoryUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.conversation import MessageRole, SourceMessageChoice


def _bootstrap(database_path: Path) -> None:
    upgrade_to_head(database_path)


def _message_matches(database_path: Path, term: str) -> list[int]:
    engine = build_engine(database_path)
    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT rowid FROM message_fts WHERE message_fts MATCH :term"), {"term": term}
        ).fetchall()
    return [row.rowid for row in rows]


def _knowledge_matches(database_path: Path, term: str) -> list[tuple[str, int]]:
    engine = build_engine(database_path)
    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT kind, item_id FROM knowledge_fts WHERE knowledge_fts MATCH :term"),
            {"term": term},
        ).fetchall()
    return [(row.kind, row.item_id) for row in rows]


def _memory_row_exists(database_path: Path, memory_id: int) -> bool:
    engine = build_engine(database_path)
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT 1 FROM memories WHERE id = :id"), {"id": memory_id}
        ).fetchone()
    return row is not None


@pytest.mark.integration
def test_appending_a_message_indexes_it_in_the_same_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()

    message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "palabraunicaenelmensaje"
    )

    assert _message_matches(database_path, "palabraunicaenelmensaje") == [message.id]


@pytest.mark.integration
def test_redacting_a_message_removes_its_text_from_the_index(tmp_path: Path) -> None:
    """Critical invariant (D-11/S7.4): a redacted message's text is never
    recoverable via FTS afterward."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "secretodelmensaje que se redactará"
    )
    assert _message_matches(database_path, "secretodelmensaje") == [message.id]

    conversation_repository.redact_message(message.id)

    assert _message_matches(database_path, "secretodelmensaje") == []


@pytest.mark.integration
def test_creating_a_memory_indexes_its_content_in_the_same_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("recuerdopalabraunica del usuario")

    assert _knowledge_matches(database_path, "recuerdopalabraunica") == [("memory", memory.id)]


@pytest.mark.integration
def test_correcting_a_memory_replaces_the_indexed_text(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("contenidooriginalunico")

    CorrectMemoryUseCase(unit_of_work).correct(memory.id, "contenidocorregidounico")

    assert _knowledge_matches(database_path, "contenidooriginalunico") == []
    assert _knowledge_matches(database_path, "contenidocorregidounico") == [("memory", memory.id)]


@pytest.mark.integration
def test_archiving_a_memory_keeps_its_content_searchable(tmp_path: Path) -> None:
    """B6a only keeps the index faithful to the vigente text; whether an
    archived item stays discoverable is a relevance decision left to B6b —
    archiving must not silently corrupt the index either way."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferenciaarchivadaunica")

    ArchiveMemoryUseCase(unit_of_work).archive(memory.id)

    assert _knowledge_matches(database_path, "preferenciaarchivadaunica") == [("memory", memory.id)]


@pytest.mark.integration
def test_deleting_a_memory_removes_its_text_from_the_index(tmp_path: Path) -> None:
    """Critical invariant (D-11/S7.4): a deleted memory's text is never
    recoverable via FTS afterward, even though the marker row survives."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("contenidoeliminableunico")
    assert _knowledge_matches(database_path, "contenidoeliminableunico") == [("memory", memory.id)]

    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    assert _knowledge_matches(database_path, "contenidoeliminableunico") == []
    # The memory row itself survives as a minimal marker (RF-025/DR-012) —
    # only its indexed text is gone.
    assert _memory_row_exists(database_path, memory.id)


@pytest.mark.integration
def test_proposing_a_decision_indexes_its_content(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.get_active_project()
    assert project is not None

    decision = ProposeDecisionUseCase(unit_of_work).propose(
        subject="asunto de la decisión", project_id=project.id, content="decisionpalabraunica"
    )

    assert _knowledge_matches(database_path, "decisionpalabraunica") == [("decision", decision.id)]


@pytest.mark.integration
def test_approving_and_archiving_a_decision_keeps_its_content_searchable(
    tmp_path: Path,
) -> None:
    """A decision's content never changes after proposal (only its status
    does); approving/archiving must never touch, duplicate or drop its
    single indexed entry."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.get_active_project()
    assert project is not None
    decision = ProposeDecisionUseCase(unit_of_work).propose(
        subject="asunto de la decisión",
        project_id=project.id,
        content="decisionaprobadaunica",
    )

    ApproveDecisionUseCase(unit_of_work).approve(decision.id, confirmed=True)
    ArchiveDecisionUseCase(unit_of_work).archive(decision.id)

    assert _knowledge_matches(database_path, "decisionaprobadaunica") == [("decision", decision.id)]


@pytest.mark.integration
def test_a_failed_commit_leaves_neither_the_data_nor_the_index_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIRIUS-ARQ-0.1 S8.1: the index update and the data it indexes live in
    the same SQLite transaction (a trigger fired by the same ``INSERT``, not
    a second connection or a later step). By the time ``create_memory``
    returns, the trigger has already run against the still-open transaction
    and staged the ``knowledge_fts`` row — this forces the *commit* itself
    to fail, so nothing beyond that point ever runs, and proves the
    rollback ``UnitOfWork.__exit__`` performs on failure reverts both the
    staged memory content and the trigger's index write together, leaving
    no trace of either."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    def _boom_commit(self: object) -> None:
        msg = "simulated commit failure after the memory content was already staged"
        raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_unit_of_work.SqliteUnitOfWork, "commit", _boom_commit)

    with pytest.raises(RuntimeError):
        SaveManualMemoryUseCase(unit_of_work).save("contenidoquenuncadebeindexarse")

    monkeypatch.undo()
    assert _knowledge_matches(database_path, "contenidoquenuncadebeindexarse") == []
    engine = build_engine(database_path)
    with engine.begin() as connection:
        memory_rows = connection.execute(text("SELECT id FROM memories")).fetchall()
    assert memory_rows == []
