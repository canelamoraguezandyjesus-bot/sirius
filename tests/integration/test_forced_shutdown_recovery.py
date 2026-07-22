"""B11 (A-02, RNF-005/006; automatable slice of PA-019): recovery after a
forced/unexpected shutdown.

Demonstrates, against the real SQLite adapters migrated with Alembic (no
fakes, no mocks), that Sirius reopens in the last transactionally coherent
state: nothing confirmed is lost or corrupted, ``PRAGMA integrity_check``
reports ``ok``, a turn interrupted mid-stream leaves a coherent history
(the USER row present, no partial/dangling SIRIUS row — because
``send_message.py`` only ever writes the SIRIUS row once the stream
finishes), and ``initialize_persistence`` is idempotent when it reopens
after the forced shutdown, not just across two ordinary clean startups.

The "forced shutdown" itself is simulated by simply never calling
``close()`` on any repository/engine used before it — each write already
committed in its own transaction (``session_scope``), so abandoning the
Python objects that wrote it is what a real killed process does: it never
gets the chance to run any orderly shutdown code either.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import (
    ConversationModel,
    IdentityModel,
    MessageModel,
    ProjectModel,
)
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import (
    build_sqlite_project_repository,
)
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.infrastructure.paths import resolve_paths


def _integrity_check_ok(database_path: Path) -> bool:
    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
        return len(rows) == 1 and str(rows[0][0]) == "ok"
    finally:
        connection.close()


@pytest.mark.integration
def test_forced_shutdown_preserves_confirmed_state_and_reopens_coherently() -> None:
    paths = resolve_paths()
    initialize_persistence(paths)
    database_path = paths.data_dir / "sirius.db"

    # --- Confirmed state written before the forced shutdown --------------
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()

    completed_operation_id = str(uuid.uuid4())
    conversation_repository.append_message(
        conversation.id,
        MessageRole.USER,
        "hola sirius",
        operation_id=completed_operation_id,
        status=MessageStatus.COMPLETED,
    )
    conversation_repository.append_message(
        conversation.id,
        MessageRole.SIRIUS,
        "hola, ¿en qué puedo ayudarte?",
        operation_id=completed_operation_id,
        status=MessageStatus.COMPLETED,
    )

    project_repository = build_sqlite_project_repository(database_path)
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En curso",
        blockers=("bloqueo pendiente",),
        next_step="Siguiente paso",
    )

    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "prefiere respuestas breves",
        subject_key="estilo-respuesta",
        project_id=project.id,
    )

    # A turn interrupted mid-stream: the USER row is COMPLETED (persisted
    # before streaming begins, per send_message.py), but Sirius's row for
    # this same operation is never written at all — exactly what a real
    # forced shutdown mid-stream leaves behind, since SendMessageUseCase
    # only appends the SIRIUS row after the stream finishes.
    interrupted_operation_id = str(uuid.uuid4())
    interrupted_user_message = conversation_repository.append_message(
        conversation.id,
        MessageRole.USER,
        "cuéntame algo mientras se corta la luz",
        operation_id=interrupted_operation_id,
        status=MessageStatus.COMPLETED,
    )

    # --- Forced shutdown: every repository/engine above is abandoned here,
    # never given the chance to run close()/dispose(), matching a real
    # killed process. ------------------------------------------------------

    # --- Reopen: brand-new repositories/engines against the same file,
    # exactly as Sirius does on its next real startup. ---------------------
    initialize_persistence(paths)

    with session_scope(build_session_factory(build_engine(database_path))) as session:
        conversations = list(session.scalars(select(ConversationModel)).all())
        projects = list(session.scalars(select(ProjectModel)).all())
        identities = list(session.scalars(select(IdentityModel)).all())
        messages = list(
            session.scalars(
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation.id)
                .order_by(MessageModel.sequence)
            ).all()
        )

    # Idempotent reopen: the main conversation, the identity and the active
    # project are not duplicated.
    assert len(conversations) == 1
    assert len(identities) == 1
    assert len(projects) == 1

    rows = [(message.role, message.content, message.status) for message in messages]
    assert (MessageRole.USER, "hola sirius", MessageStatus.COMPLETED) in rows
    assert (
        MessageRole.SIRIUS,
        "hola, ¿en qué puedo ayudarte?",
        MessageStatus.COMPLETED,
    ) in rows

    # The interrupted turn: exactly the USER row survives, unchanged and
    # uncorrupted; no SIRIUS row (partial or otherwise) was ever written for
    # its operation_id.
    interrupted_turn_rows = [
        message for message in messages if message.operation_id == interrupted_operation_id
    ]
    assert len(interrupted_turn_rows) == 1
    assert interrupted_turn_rows[0].id == interrupted_user_message.id
    assert interrupted_turn_rows[0].role == MessageRole.USER
    assert interrupted_turn_rows[0].content == "cuéntame algo mientras se corta la luz"
    assert interrupted_turn_rows[0].status == MessageStatus.COMPLETED

    reopened_project = build_sqlite_project_repository(database_path).get_project(project.id)
    assert reopened_project is not None
    assert reopened_project.current_revision is not None
    assert reopened_project.current_revision.objective == "Objetivo de prueba"
    assert reopened_project.current_revision.blockers == ("bloqueo pendiente",)

    reopened_memory = build_sqlite_memory_repository(database_path).get_memory(memory.id)
    assert reopened_memory.current_revision.content == "prefiere respuestas breves"

    assert _integrity_check_ok(database_path) is True

    # Reopening again (a second, independent startup) stays idempotent too:
    # nothing above gets duplicated by repeating the exact same startup that
    # just followed the forced shutdown.
    initialize_persistence(paths)
    with session_scope(build_session_factory(build_engine(database_path))) as session:
        assert len(list(session.scalars(select(ConversationModel)).all())) == 1
        assert len(list(session.scalars(select(IdentityModel)).all())) == 1
        assert len(list(session.scalars(select(ProjectModel)).all())) == 1

    assert _integrity_check_ok(database_path) is True
