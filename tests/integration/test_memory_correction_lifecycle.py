"""End-to-end integration tests for B4c memory correction (RF-022, PA-012).

Wires the real SQLite adapters (no fakes) behind ``SaveManualMemoryUseCase``,
``CorrectMemoryUseCase`` and ``GetMemoryOriginUseCase`` exactly as
``composition_root`` does, proving the whole vertical slice: a correction
creates a new, immutable, current revision; the previous revision stays
consultable as history; the pointer moves atomically; unknown ids and
non-correctable statuses fail safely; and everything survives reopening
the store.
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
from sirius.application.correct_memory import (
    MEMORY_CORRECTION_ORIGIN,
    CorrectMemoryUseCase,
    MemoryNotCorrectableError,
    UnknownMemoryError,
)
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.conversation import MessageRole
from sirius.domain.event import MEMORY_CORRECTED_EVENT_TYPE
from sirius.domain.memory import MemoryStatus


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


@pytest.mark.integration
def test_correcting_a_memory_creates_a_new_current_revision_and_keeps_the_previous_one(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    original_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "guarda que prefiero respuestas breves"
    )
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "El usuario prefiere respuestas breves", message_id=original_message.id
    )

    correction_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "corrige eso: prefiero respuestas detalladas"
    )
    corrected = CorrectMemoryUseCase(unit_of_work).correct(
        memory.id, "El usuario prefiere respuestas detalladas", message_id=correction_message.id
    )

    # PA-012: la versión aumenta exactamente en uno y el puntero apunta solo
    # a la nueva revisión.
    assert corrected.current_revision.version == memory.current_revision.version + 1
    assert corrected.current_revision.content == "El usuario prefiere respuestas detalladas"
    assert corrected.current_revision.origin == MEMORY_CORRECTION_ORIGIN
    assert corrected.status is MemoryStatus.CURRENT

    # La consulta ordinaria (get_memory) devuelve el contenido nuevo.
    fetched = memory_repository.get_memory(memory.id)
    assert fetched.current_revision.id == corrected.current_revision.id
    assert fetched.current_revision.content == "El usuario prefiere respuestas detalladas"

    # La consulta histórica devuelve ambas versiones, en orden, y la
    # revisión anterior permanece inmutable.
    history = memory_repository.get_history(memory.id)
    assert [revision.version for revision in history] == [1, 2]
    assert history[0].content == "El usuario prefiere respuestas breves"
    assert history[0].id == memory.current_revision.id
    assert history[1].id == corrected.current_revision.id

    # El evento de corrección queda enlazado, con fecha y origen propios, y
    # el mensaje real de corrección queda enlazado.
    assert corrected.current_revision.source_event_id is not None
    origin = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    ).get_origin(memory.id)
    assert origin.event_type == MEMORY_CORRECTED_EVENT_TYPE
    assert origin.event_id == corrected.current_revision.source_event_id
    assert origin.message_id == correction_message.id
    assert origin.message_content == "corrige eso: prefiero respuestas detalladas"


@pytest.mark.integration
def test_correcting_an_unknown_memory_id_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    with pytest.raises(UnknownMemoryError):
        CorrectMemoryUseCase(unit_of_work).correct(999, "contenido nuevo")


@pytest.mark.integration
def test_correcting_an_archived_memory_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    memory_repository.archive_memory(memory.id)

    with pytest.raises(MemoryNotCorrectableError):
        CorrectMemoryUseCase(unit_of_work).correct(memory.id, "no debería aplicarse")

    still_archived = memory_repository.get_memory(memory.id)
    assert still_archived.status is MemoryStatus.ARCHIVED
    assert still_archived.current_revision.content == "preferencia original"


@pytest.mark.integration
def test_correcting_a_deleted_memory_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    memory_repository.delete_memory(memory.id)

    with pytest.raises(MemoryNotCorrectableError):
        CorrectMemoryUseCase(unit_of_work).correct(memory.id, "no debería aplicarse")

    assert memory_repository.get_memory(memory.id).status is MemoryStatus.DELETED


@pytest.mark.integration
def test_multiple_corrections_are_each_a_new_version_in_stable_order(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = CorrectMemoryUseCase(unit_of_work)

    memory = SaveManualMemoryUseCase(unit_of_work).save("v1")
    use_case.correct(memory.id, "v2")
    latest = use_case.correct(memory.id, "v3")

    assert latest.current_revision.version == 3
    history = memory_repository.get_history(memory.id)
    assert [revision.content for revision in history] == ["v1", "v2", "v3"]


@pytest.mark.integration
def test_a_failed_correction_can_be_followed_by_a_valid_one(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = CorrectMemoryUseCase(unit_of_work)

    memory = SaveManualMemoryUseCase(unit_of_work).save("v1")

    with pytest.raises(UnknownMemoryError):
        use_case.correct(999, "no debería persistir")

    corrected = use_case.correct(memory.id, "v2")

    assert corrected.current_revision.version == 2
    history = memory_repository.get_history(memory.id)
    assert [revision.content for revision in history] == ["v1", "v2"]


@pytest.mark.integration
def test_corrected_memory_and_its_history_survive_closing_and_reopening_the_store(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)

    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save("preferencia original")
    corrected = CorrectMemoryUseCase(unit_of_work).correct(memory.id, "preferencia corregida")

    memory_repository.close()
    event_repository.close()
    conversation_repository.close()
    unit_of_work.close()

    reopened_memory_repository = build_sqlite_memory_repository(database_path)
    reopened_event_repository = build_sqlite_event_repository(database_path)
    reopened_conversation_repository = build_sqlite_conversation_repository(database_path)

    fetched = reopened_memory_repository.get_memory(memory.id)
    assert fetched.current_revision.content == "preferencia corregida"
    assert fetched.current_revision.id == corrected.current_revision.id

    history = reopened_memory_repository.get_history(memory.id)
    assert [revision.content for revision in history] == [
        "preferencia original",
        "preferencia corregida",
    ]

    origin = GetMemoryOriginUseCase(
        reopened_memory_repository, reopened_event_repository, reopened_conversation_repository
    ).get_origin(memory.id)
    assert origin.event_type == MEMORY_CORRECTED_EVENT_TYPE
