"""Atomicity of memory deletion, via ``SqliteUnitOfWork`` (B4d).

Covers the whole operation: the audit event, the optional source-message
redaction, and the memory's own content redaction must commit together or
not at all — including a failure at each of the three steps individually,
each of which must revert everything already applied in that same attempt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence import sqlite_conversation_repository, sqlite_memory_repository
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, EventModel, MemoryModel, MessageModel
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.domain.conversation import MessageRole, MessageStatus, SourceMessageChoice
from sirius.domain.memory import MemoryStatus


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _row_counts(database_path: Path) -> tuple[int, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        events = len(session.scalars(select(EventModel)).all())
        memories = len(session.scalars(select(MemoryModel)).all())
        return events, memories


def _memory_snapshot(database_path: Path, memory_id: int) -> tuple[MemoryStatus, ...]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(MemoryModel, memory_id)
        assert model is not None
        return (MemoryStatus(model.status),)


def _message_snapshot(database_path: Path, message_id: int) -> tuple[str | None, MessageStatus]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(MessageModel, message_id)
        assert model is not None
        return (model.content, MessageStatus(model.status))


def _create_memory_with_source_message(database_path: Path) -> tuple[int, int]:
    """Create a memory whose source event links a real message, mirroring
    how ``SendMessageUseCase``/manual save would in production."""
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        conversation = sqlite_conversation_repository.bind_sqlite_conversation_repository(
            session
        ).get_or_create_main_conversation()
        message = sqlite_conversation_repository.bind_sqlite_conversation_repository(
            session
        ).append_message(conversation.id, MessageRole.USER, "recuerda esto")
        message_id = message.id

    unit_of_work = build_sqlite_unit_of_work(database_path)
    unit_of_work.begin()
    event = unit_of_work.event_repository.append("memory.manual_save", "user", message_id)
    memory = unit_of_work.memory_repository.create_memory(
        "preferencia original", "Guardado manual del usuario", source_event_id=event.id
    )
    unit_of_work.commit()
    unit_of_work.close()
    return memory.id, message_id


@pytest.mark.integration
def test_event_message_redaction_and_content_removal_commit_together(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id, message_id = _create_memory_with_source_message(database_path)
    events_before, memories_before = _row_counts(database_path)

    use_case = DeleteMemoryUseCase(build_sqlite_unit_of_work(database_path))
    result = use_case.delete(
        memory_id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT
    )

    assert result.memory.status is MemoryStatus.DELETED
    events_after, memories_after = _row_counts(database_path)
    assert events_after == events_before + 1
    assert memories_after == memories_before
    content, status = _message_snapshot(database_path, message_id)
    assert content is None
    assert status is MessageStatus.REDACTED


def _boom_delete_memory(self: object, memory_id: int) -> None:
    msg = "simulated content-removal failure"
    raise RuntimeError(msg)


@pytest.mark.integration
def test_delete_reverts_the_message_redaction_when_content_removal_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id, message_id = _create_memory_with_source_message(database_path)
    counts_before = _row_counts(database_path)
    message_before = _message_snapshot(database_path, message_id)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = DeleteMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_memory_repository.SqliteMemoryRepository, "delete_memory", _boom_delete_memory
    )

    with pytest.raises(RuntimeError):
        use_case.delete(memory_id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    monkeypatch.undo()
    assert _row_counts(database_path) == counts_before
    assert _memory_snapshot(database_path, memory_id) == (MemoryStatus.CURRENT,)
    assert _message_snapshot(database_path, message_id) == message_before


def _boom_redact_message(self: object, message_id: int) -> None:
    msg = "simulated redaction failure"
    raise RuntimeError(msg)


@pytest.mark.integration
def test_delete_reverts_the_event_when_redacting_the_message_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id, message_id = _create_memory_with_source_message(database_path)
    counts_before = _row_counts(database_path)
    message_before = _message_snapshot(database_path, message_id)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = DeleteMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_conversation_repository.SqliteConversationRepository,
        "redact_message",
        _boom_redact_message,
    )

    with pytest.raises(RuntimeError):
        use_case.delete(memory_id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    monkeypatch.undo()
    assert _row_counts(database_path) == counts_before
    assert _memory_snapshot(database_path, memory_id) == (MemoryStatus.CURRENT,)
    assert _message_snapshot(database_path, message_id) == message_before


@pytest.mark.integration
def test_a_valid_deletion_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id, message_id = _create_memory_with_source_message(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = DeleteMemoryUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_memory_repository.SqliteMemoryRepository, "delete_memory", _boom_delete_memory
    )
    with pytest.raises(RuntimeError):
        use_case.delete(memory_id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    monkeypatch.undo()
    result = use_case.delete(
        memory_id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT
    )

    assert result.memory.status is MemoryStatus.DELETED
    content, status = _message_snapshot(database_path, message_id)
    assert content is None
    assert status is MessageStatus.REDACTED


@pytest.mark.integration
def test_preserving_the_source_message_never_touches_it_even_transactionally(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_id, message_id = _create_memory_with_source_message(database_path)

    use_case = DeleteMemoryUseCase(build_sqlite_unit_of_work(database_path))
    result = use_case.delete(
        memory_id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    assert result.memory.status is MemoryStatus.DELETED
    content, status = _message_snapshot(database_path, message_id)
    assert content == "recuerda esto"
    assert status is MessageStatus.COMPLETED
