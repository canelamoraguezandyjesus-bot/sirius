from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_memory_suggestion_repository import (
    SqliteMemorySuggestionRepository,
    build_sqlite_memory_suggestion_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.domain.memory_suggestion import MemorySuggestionStatus


def _build_repository(database_path: Path) -> SqliteMemorySuggestionRepository:
    Base.metadata.create_all(build_engine(database_path))
    return build_sqlite_memory_suggestion_repository(database_path)


def _project_id(database_path: Path) -> int:
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En curso",
        blockers=(),
        next_step="Siguiente paso",
    )
    return project.id


def _real_memory_id(database_path: Path) -> int:
    """``resulting_memory_id`` is a real, enforced foreign key (§3.7): tests
    that confirm a suggestion need an actual row in ``memories`` to link to."""
    memory_repository = build_sqlite_memory_repository(database_path)
    memory = memory_repository.create_memory("recuerdo real", "origen de prueba")
    return memory.id


@pytest.mark.integration
def test_create_and_recover_a_pending_suggestion(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    created = repository.create_suggestion("prefiere respuestas breves")

    assert created.status is MemorySuggestionStatus.PENDING
    assert created.content == "prefiere respuestas breves"
    assert created.resolved_at is None
    assert created.resulting_memory_id is None
    assert created.source_event_id is None
    assert created.subject_key is None
    assert created.project_id is None

    fetched = repository.get_suggestion(created.id)
    assert fetched == created


@pytest.mark.integration
def test_create_suggestion_carries_subject_key_project_id_and_source_event_id(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    created = repository.create_suggestion(
        "usar SQLite local",
        source_event_id=None,
        subject_key="Motor de persistencia",
        project_id=project_id,
    )

    assert created.subject_key == "Motor de persistencia"
    assert created.project_id == project_id


@pytest.mark.integration
def test_get_suggestion_for_an_unknown_id_raises(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown memory suggestion"):
        repository.get_suggestion(999)


@pytest.mark.integration
def test_list_pending_suggestions_excludes_confirmed_and_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory_id = _real_memory_id(database_path)
    still_pending = repository.create_suggestion("sigue pendiente")
    to_confirm = repository.create_suggestion("se va a confirmar")
    to_reject = repository.create_suggestion("se va a rechazar")
    repository.confirm_suggestion(
        to_confirm.id, resulting_memory_id=memory_id, resolved_at=datetime.now(UTC)
    )
    repository.reject_suggestion(to_reject.id, resolved_at=datetime.now(UTC))

    pending = repository.list_pending_suggestions()

    assert [suggestion.id for suggestion in pending] == [still_pending.id]


@pytest.mark.integration
def test_confirm_suggestion_sets_status_resolution_and_resulting_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory_id = _real_memory_id(database_path)
    created = repository.create_suggestion("prefiere respuestas breves")
    resolved_at = datetime.now(UTC)

    confirmed = repository.confirm_suggestion(
        created.id, resulting_memory_id=memory_id, resolved_at=resolved_at
    )

    assert confirmed.status is MemorySuggestionStatus.CONFIRMED
    assert confirmed.resulting_memory_id == memory_id
    assert confirmed.resolved_at == resolved_at

    fetched = repository.get_suggestion(created.id)
    assert fetched.status is MemorySuggestionStatus.CONFIRMED
    assert fetched.resulting_memory_id == memory_id


@pytest.mark.integration
def test_reject_suggestion_sets_status_and_resolution_without_a_resulting_memory(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = repository.create_suggestion("una idea descartable")
    resolved_at = datetime.now(UTC)

    rejected = repository.reject_suggestion(created.id, resolved_at=resolved_at)

    assert rejected.status is MemorySuggestionStatus.REJECTED
    assert rejected.resulting_memory_id is None
    assert rejected.resolved_at == resolved_at


@pytest.mark.integration
def test_confirming_an_already_confirmed_suggestion_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory_id = _real_memory_id(database_path)
    created = repository.create_suggestion("prefiere respuestas breves")
    repository.confirm_suggestion(
        created.id, resulting_memory_id=memory_id, resolved_at=datetime.now(UTC)
    )

    with pytest.raises(ValueError, match="Cannot confirm"):
        repository.confirm_suggestion(
            created.id, resulting_memory_id=memory_id, resolved_at=datetime.now(UTC)
        )


@pytest.mark.integration
def test_confirming_an_already_rejected_suggestion_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = repository.create_suggestion("una idea descartable")
    repository.reject_suggestion(created.id, resolved_at=datetime.now(UTC))

    with pytest.raises(ValueError, match="Cannot confirm"):
        repository.confirm_suggestion(
            created.id, resulting_memory_id=1, resolved_at=datetime.now(UTC)
        )


@pytest.mark.integration
def test_rejecting_an_already_confirmed_suggestion_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory_id = _real_memory_id(database_path)
    created = repository.create_suggestion("prefiere respuestas breves")
    repository.confirm_suggestion(
        created.id, resulting_memory_id=memory_id, resolved_at=datetime.now(UTC)
    )

    with pytest.raises(ValueError, match="Cannot reject"):
        repository.reject_suggestion(created.id, resolved_at=datetime.now(UTC))


@pytest.mark.integration
def test_operations_on_unknown_suggestion_raise(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown memory suggestion"):
        repository.confirm_suggestion(999, resulting_memory_id=1, resolved_at=datetime.now(UTC))
    with pytest.raises(ValueError, match="Unknown memory suggestion"):
        repository.reject_suggestion(999, resolved_at=datetime.now(UTC))


@pytest.mark.integration
def test_suggestion_state_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory_id = _real_memory_id(database_path)
    created = repository.create_suggestion("prefiere respuestas breves")
    repository.confirm_suggestion(
        created.id, resulting_memory_id=memory_id, resolved_at=datetime.now(UTC)
    )
    repository.close()

    reopened = build_sqlite_memory_suggestion_repository(database_path)
    fetched = reopened.get_suggestion(created.id)

    assert fetched.status is MemorySuggestionStatus.CONFIRMED
    assert fetched.resulting_memory_id == memory_id
    reopened.close()


@pytest.mark.integration
def test_several_suggestions_can_be_pending_at_once_even_of_the_same_subject(
    tmp_path: Path,
) -> None:
    """SIRIUS-ARQ-0.2 §3.7: no unique index on status — nothing forbids two
    pending suggestions of the same subject/project."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    first = repository.create_suggestion(
        "primera idea", subject_key="Motor de persistencia", project_id=project_id
    )
    second = repository.create_suggestion(
        "segunda idea", subject_key="Motor de persistencia", project_id=project_id
    )

    pending_ids = {suggestion.id for suggestion in repository.list_pending_suggestions()}
    assert pending_ids == {first.id, second.id}
