"""End-to-end integration tests for B4a (RF-019, RF-021, PA-010).

Wires the real SQLite adapters (no fakes) behind ``SaveManualMemoryUseCase``
and ``GetMemoryOriginUseCase`` exactly as ``composition_root`` does, proving
the whole vertical slice — explicit save, real origin link, later query,
safe handling of a bad id, and survival across reopening the store.
"""

from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.memory_origin import GetMemoryOriginUseCase, MemoryOriginNotFoundError
from sirius.application.save_manual_memory import MANUAL_MEMORY_ORIGIN, SaveManualMemoryUseCase
from sirius.domain.conversation import MessageRole
from sirius.domain.memory import MemoryStatus


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


@pytest.mark.integration
def test_explicit_save_creates_a_traceable_memory_and_its_origin_can_be_opened(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    source_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )

    save_use_case = SaveManualMemoryUseCase(unit_of_work)
    memory = save_use_case.save(
        "El usuario prefiere respuestas breves", message_id=source_message.id
    )

    # PA-010: origen, fecha, estado y versión quedan observables de inmediato.
    assert memory.status is MemoryStatus.CURRENT
    assert memory.current_revision.version == 1
    assert memory.current_revision.origin == MANUAL_MEMORY_ORIGIN
    assert memory.current_revision.source_event_id is not None
    assert memory.created_at is not None

    # RF-021: el origen puede consultarse después, y abre el mensaje real.
    origin_use_case = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    )
    origin = origin_use_case.get_origin(memory.id)

    assert origin.event_id == memory.current_revision.source_event_id
    assert origin.message_id == source_message.id
    assert origin.message_content == "guarda que prefiero respuestas breves"


@pytest.mark.integration
def test_querying_the_origin_of_an_unknown_memory_id_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    origin_use_case = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    )

    with pytest.raises(MemoryOriginNotFoundError):
        origin_use_case.get_origin(999)


@pytest.mark.integration
def test_querying_the_origin_of_a_pre_b4a_memory_with_no_recorded_origin_is_handled_safely(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)

    # A memory created directly through the repository (as every V4 memory
    # was, before B4a) has no source_event_id.
    legacy_memory = memory_repository.create_memory("recuerdo antiguo", "manual")

    origin_use_case = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    )
    with pytest.raises(MemoryOriginNotFoundError):
        origin_use_case.get_origin(legacy_memory.id)


@pytest.mark.integration
def test_manual_memory_and_its_origin_survive_closing_and_reopening_the_store(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    source_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda esta preferencia"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "preferencia guardada", message_id=source_message.id
    )
    conversation_repository.close()
    memory_repository.close()
    event_repository.close()
    unit_of_work.close()

    reopened_conversation_repository = build_sqlite_conversation_repository(database_path)
    reopened_memory_repository = build_sqlite_memory_repository(database_path)
    reopened_event_repository = build_sqlite_event_repository(database_path)
    origin = GetMemoryOriginUseCase(
        reopened_memory_repository, reopened_event_repository, reopened_conversation_repository
    ).get_origin(memory.id)

    assert origin.message_content == "guarda esta preferencia"
    assert reopened_memory_repository.get_memory(memory.id).current_revision.content == (
        "preferencia guardada"
    )
