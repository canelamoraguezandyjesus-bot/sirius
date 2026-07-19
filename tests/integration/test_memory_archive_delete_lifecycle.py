"""End-to-end integration tests for B4d archive and deletion (RF-024,
RF-025, PA-015, PA-016, SP-06).

Wires the real SQLite adapters (no fakes) behind ``ArchiveMemoryUseCase``,
``DeleteMemoryUseCase`` and ``GetMemoryOriginUseCase`` exactly as
``composition_root`` does, proving the whole vertical slice: archiving keeps
content and history fully consultable while leaving ordinary queries;
deletion redacts structured content across the full history and, when
chosen, the source message; both survive reopening the store.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.archive_memory import (
    ArchiveMemoryUseCase,
    MemoryNotArchivableError,
)
from sirius.application.archive_memory import (
    UnknownMemoryError as ArchiveUnknownMemoryError,
)
from sirius.application.context import ContextBuilder
from sirius.application.delete_memory import (
    DeleteMemoryUseCase,
    DeletionNotConfirmedError,
    MemoryNotDeletableError,
)
from sirius.application.delete_memory import (
    UnknownMemoryError as DeleteUnknownMemoryError,
)
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.conversation import MessageRole, MessageStatus, SourceMessageChoice
from sirius.domain.memory import MemoryStatus


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


@pytest.mark.integration
def test_archiving_a_memory_keeps_content_and_history_but_leaves_ordinary_queries(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")

    archived = ArchiveMemoryUseCase(unit_of_work).archive(memory.id)

    assert archived.status is MemoryStatus.ARCHIVED
    assert archived.current_revision.content == "preferencia original"

    # RF-024: sigue consultable con contenido e historial completos...
    fetched = memory_repository.get_memory(memory.id)
    assert fetched.current_revision.content == "preferencia original"
    history = memory_repository.get_history(memory.id)
    assert [r.content for r in history] == ["preferencia original"]

    # ...pero queda fuera del contexto ordinario...
    assert memory.id not in [m.id for m in memory_repository.list_current_memories()]
    # ...y la consulta explícita de archivados lo recupera.
    assert [m.id for m in memory_repository.list_archived_memories()] == [memory.id]


@pytest.mark.integration
def test_archiving_a_memory_leaves_its_origin_fully_consultable(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    order_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves", message_id=order_message.id
    )

    ArchiveMemoryUseCase(unit_of_work).archive(memory.id)

    origin = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    ).get_origin(memory.id)
    assert origin.message_id == order_message.id
    assert origin.message_content == "guarda que prefiero respuestas breves"


@pytest.mark.integration
def test_archiving_one_memory_leaves_other_current_memories_in_ordinary_queries(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    to_archive = SaveManualMemoryUseCase(unit_of_work).save("archivar este")
    to_keep = SaveManualMemoryUseCase(unit_of_work).save("mantener este")

    ArchiveMemoryUseCase(unit_of_work).archive(to_archive.id)

    current_ids = {m.id for m in memory_repository.list_current_memories()}
    assert current_ids == {to_keep.id}


@pytest.mark.integration
def test_archiving_an_unknown_memory_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    with pytest.raises(ArchiveUnknownMemoryError):
        ArchiveMemoryUseCase(unit_of_work).archive(999)


@pytest.mark.integration
def test_archiving_a_deleted_memory_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    with pytest.raises(MemoryNotArchivableError):
        ArchiveMemoryUseCase(unit_of_work).archive(memory.id)


@pytest.mark.integration
def test_archived_memory_survives_closing_and_reopening_the_store(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    ArchiveMemoryUseCase(unit_of_work).archive(memory.id)

    memory_repository.close()
    unit_of_work.close()

    reopened = build_sqlite_memory_repository(database_path)
    fetched = reopened.get_memory(memory.id)
    assert fetched.status is MemoryStatus.ARCHIVED
    assert fetched.current_revision.content == "preferencia original"
    assert [m.id for m in reopened.list_archived_memories()] == [memory.id]


@pytest.mark.integration
def test_deleting_without_confirmation_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")

    with pytest.raises(DeletionNotConfirmedError):
        DeleteMemoryUseCase(unit_of_work).delete(
            memory.id, confirmed=False, source_message_choice=SourceMessageChoice.PRESERVE
        )

    memory_repository = build_sqlite_memory_repository(database_path)
    assert memory_repository.get_memory(memory.id).status is MemoryStatus.CURRENT
    assert memory_repository.get_memory(memory.id).current_revision.content == (
        "preferencia original"
    )


@pytest.mark.integration
def test_deleting_an_unknown_memory_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    with pytest.raises(DeleteUnknownMemoryError):
        DeleteMemoryUseCase(unit_of_work).delete(
            999, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
        )


@pytest.mark.integration
def test_deleting_twice_is_rejected_not_silently_idempotent(tmp_path: Path) -> None:
    """``MemoryRepository.delete_memory`` (V4) already rejects an
    already-DELETED memory rather than treating a second deletion as a
    no-op; the approved sources never state deletion should be idempotent,
    so this pre-existing, tested repository contract is preserved as-is."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    with pytest.raises(MemoryNotDeletableError):
        DeleteMemoryUseCase(unit_of_work).delete(
            memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
        )


@pytest.mark.integration
def test_deleting_a_memory_with_multiple_revisions_redacts_content_across_all_of_them(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("v1")
    memory_repository.correct_memory(memory.id, "v2", "Corrección manual del usuario")

    result = DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    assert result.memory.status is MemoryStatus.DELETED
    history = memory_repository.get_history(memory.id)
    assert [r.content for r in history] == [None, None]
    assert [r.version for r in history] == [1, 2]  # marker survives, redacted


@pytest.mark.integration
def test_deletion_keeps_only_the_approved_minimal_marker_fields(tmp_path: Path) -> None:
    """DR-012/Product S7: deletion keeps "solo un marcador mínimo sin
    contenido" — id, version, origin and created_at survive unchanged;
    only ``content`` becomes ``None``."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    original_revision = memory.current_revision

    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    (marker,) = memory_repository.get_history(memory.id)
    assert marker.id == original_revision.id
    assert marker.version == original_revision.version
    assert marker.origin == original_revision.origin
    assert marker.created_at == original_revision.created_at
    assert marker.content is None


@pytest.mark.integration
def test_deleting_one_memory_leaves_other_current_memories_in_ordinary_queries(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    to_delete = SaveManualMemoryUseCase(unit_of_work).save("eliminar este")
    to_keep = SaveManualMemoryUseCase(unit_of_work).save("mantener este")

    DeleteMemoryUseCase(unit_of_work).delete(
        to_delete.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    current_ids = {m.id for m in memory_repository.list_current_memories()}
    assert current_ids == {to_keep.id}


@pytest.mark.integration
def test_deleting_without_a_source_message_choice_raises_before_opening_a_transaction(
    tmp_path: Path,
) -> None:
    """``source_message_choice`` has no default: omitting it entirely fails
    (a ``TypeError``, before ``DeleteMemoryUseCase.delete`` even runs) —
    RF-025's "recibir una elección explícita... rechazar una elección
    ausente"."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")

    with pytest.raises(TypeError):
        DeleteMemoryUseCase(unit_of_work).delete(  # type: ignore[call-arg]
            memory.id, confirmed=True
        )

    memory_repository = build_sqlite_memory_repository(database_path)
    assert memory_repository.get_memory(memory.id).status is MemoryStatus.CURRENT


@pytest.mark.integration
def test_deleted_memory_origin_stays_consultable_without_exposing_content(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    order_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves", message_id=order_message.id
    )

    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    origin = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    ).get_origin(memory.id)
    assert origin.message_id == order_message.id
    assert origin.message_content == "guarda que prefiero respuestas breves"
    fetched = memory_repository.get_memory(memory.id)
    assert fetched.current_revision.content is None


@pytest.mark.integration
def test_deleting_with_redact_choice_removes_the_source_message_content(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    order_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves", message_id=order_message.id
    )

    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT
    )

    redacted_message = conversation_repository.get_message(order_message.id)
    assert redacted_message is not None
    assert redacted_message.content is None
    assert redacted_message.status is MessageStatus.REDACTED
    assert redacted_message.sequence == order_message.sequence


@pytest.mark.integration
def test_redacting_a_source_message_never_touches_other_messages(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    order_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )
    other_message = conversation_repository.append_message(
        conversation.id, MessageRole.SIRIUS, "de acuerdo, lo tendré en cuenta"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves", message_id=order_message.id
    )

    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT
    )

    untouched = conversation_repository.get_message(other_message.id)
    assert untouched is not None
    assert untouched.content == "de acuerdo, lo tendré en cuenta"
    assert untouched.status is MessageStatus.COMPLETED


@pytest.mark.integration
def test_deletion_and_redaction_survive_closing_and_reopening_the_store(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    order_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves", message_id=order_message.id
    )
    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT
    )

    memory_repository.close()
    conversation_repository.close()
    unit_of_work.close()

    reopened_memory_repository = build_sqlite_memory_repository(database_path)
    reopened_conversation_repository = build_sqlite_conversation_repository(database_path)

    fetched = reopened_memory_repository.get_memory(memory.id)
    assert fetched.status is MemoryStatus.DELETED
    assert fetched.current_revision.content is None
    assert reopened_memory_repository.list_current_memories() == []

    reopened_message = reopened_conversation_repository.get_message(order_message.id)
    assert reopened_message is not None
    assert reopened_message.content is None
    assert reopened_message.status is MessageStatus.REDACTED


@pytest.mark.integration
def test_a_redacted_message_is_excluded_from_a_freshly_built_context(tmp_path: Path) -> None:
    """PA-016/test 27: redacted content must never appear in a future
    context — proven here through the real ``ContextBuilder``, not just by
    inspecting the message's own status."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identity_repository = build_sqlite_identity_repository(database_path)
    identity_repository.get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    memory_repository = build_sqlite_memory_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    order_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "secreto: mi contraseña temporal es 1234"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "dato sensible", message_id=order_message.id
    )
    DeleteMemoryUseCase(unit_of_work).delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.REDACT
    )

    context = ContextBuilder(
        identity_repository,
        project_repository,
        memory_repository,
        conversation_repository,
        build_sqlite_decision_repository(database_path),
    ).build("¿qué recuerdas de mí?")

    assert all(
        m.content != "secreto: mi contraseña temporal es 1234" for m in context.recent_messages
    )
    assert order_message.id not in [m.id for m in context.recent_messages]
