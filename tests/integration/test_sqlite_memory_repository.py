from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, MemoryModel, MemoryRevisionModel
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_memory_repository import (
    SqliteMemoryRepository,
    build_sqlite_memory_repository,
)
from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory import MemoryStatus


def _build_repository(database_path: Path) -> SqliteMemoryRepository:
    repository = build_sqlite_memory_repository(database_path)
    Base.metadata.create_all(build_engine(database_path))
    return repository


@pytest.mark.integration
def test_create_memory_rejects_empty_origin(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="non-empty origin"):
        repository.create_memory("algo importante", "")

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        assert session.scalars(select(MemoryModel)).first() is None


@pytest.mark.integration
def test_correct_memory_rejects_empty_origin(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("original", "manual")

    with pytest.raises(ValueError, match="non-empty origin"):
        repository.correct_memory(memory.id, "corregido", "  ")


@pytest.mark.integration
def test_create_and_recover_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    created = repository.create_memory("prefiere respuestas breves", "manual")

    assert created.status is MemoryStatus.CURRENT
    assert created.current_revision.version == 1
    assert created.current_revision.content == "prefiere respuestas breves"
    assert created.current_revision.origin == "manual"

    fetched = repository.get_memory(created.id)
    assert fetched == created

    current_memories = repository.list_current_memories()
    assert [m.id for m in current_memories] == [created.id]


@pytest.mark.integration
def test_create_memory_without_source_event_id_leaves_it_none(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    created = repository.create_memory("prefiere respuestas breves", "manual")

    assert created.current_revision.source_event_id is None


@pytest.mark.integration
def test_create_memory_with_source_event_id_links_the_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    event = event_repository.append(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, message_id=None)

    created = repository.create_memory("v1", "manual", source_event_id=None)
    linked = repository.create_memory("v2", "manual", source_event_id=event.id)

    assert linked.current_revision.source_event_id == event.id
    fetched = repository.get_memory(linked.id)
    assert fetched.current_revision.source_event_id == event.id
    # unrelated memory keeps no link
    assert repository.get_memory(created.id).current_revision.source_event_id is None


@pytest.mark.integration
def test_correct_memory_creates_new_revision_without_overwriting_the_previous_one(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("versión original", "manual")

    corrected = repository.correct_memory(memory.id, "versión corregida", "manual")

    assert corrected.current_revision.version == 2
    assert corrected.current_revision.content == "versión corregida"

    history = repository.get_history(memory.id)
    assert [r.version for r in history] == [1, 2]
    assert history[0].content == "versión original"
    assert history[1].content == "versión corregida"


@pytest.mark.integration
def test_only_one_current_revision_per_memory_after_several_corrections(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("v1", "manual")
    repository.correct_memory(memory.id, "v2", "manual")
    repository.correct_memory(memory.id, "v3", "manual")

    fetched = repository.get_memory(memory.id)
    assert fetched.current_revision.version == 3
    assert fetched.current_revision.content == "v3"

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        revisions = session.scalars(
            select(MemoryRevisionModel).where(MemoryRevisionModel.memory_id == memory.id)
        ).all()
        assert len(revisions) == 3
        current_revisions = [r for r in revisions if r.is_current]
        assert len(current_revisions) == 1
        assert current_revisions[0].version == 3


@pytest.mark.integration
def test_database_rejects_two_current_revisions_for_the_same_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    with session_scope(session_factory) as session:
        memory_model = MemoryModel(status=MemoryStatus.CURRENT, created_at=now, updated_at=now)
        session.add(memory_model)
        session.flush()
        session.add(
            MemoryRevisionModel(
                memory_id=memory_model.id,
                version=1,
                content="v1",
                origin="manual",
                is_current=True,
                created_at=now,
            )
        )
        memory_id = memory_model.id

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(
            MemoryRevisionModel(
                memory_id=memory_id,
                version=2,
                content="v2",
                origin="manual",
                is_current=True,
                created_at=now,
            )
        )
        session.flush()

    with session_scope(session_factory) as session:
        current_revisions = session.scalars(
            select(MemoryRevisionModel).where(
                MemoryRevisionModel.memory_id == memory_id,
                MemoryRevisionModel.is_current.is_(True),
            )
        ).all()
        assert len(current_revisions) == 1


@pytest.mark.integration
def test_current_revisions_of_different_memories_are_independent(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    first = repository.create_memory("primer recuerdo", "manual")
    second = repository.create_memory("segundo recuerdo", "manual")

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        current_revisions = session.scalars(
            select(MemoryRevisionModel).where(MemoryRevisionModel.is_current.is_(True))
        ).all()

    assert {r.memory_id for r in current_revisions} == {first.id, second.id}
    assert len(current_revisions) == 2

    assert repository.get_memory(first.id).current_revision.content == "primer recuerdo"
    assert repository.get_memory(second.id).current_revision.content == "segundo recuerdo"


@pytest.mark.integration
def test_history_is_returned_in_stable_version_order(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("v1", "manual")
    repository.correct_memory(memory.id, "v2", "manual")
    repository.correct_memory(memory.id, "v3", "manual")

    history = repository.get_history(memory.id)

    assert [r.version for r in history] == [1, 2, 3]
    assert [r.content for r in history] == ["v1", "v2", "v3"]


@pytest.mark.integration
def test_correcting_an_archived_or_deleted_memory_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    archived = repository.create_memory("a", "manual")
    repository.archive_memory(archived.id)
    deleted = repository.create_memory("b", "manual")
    repository.delete_memory(deleted.id)

    with pytest.raises(ValueError, match="Cannot correct"):
        repository.correct_memory(archived.id, "x", "manual")
    with pytest.raises(ValueError, match="Cannot correct"):
        repository.correct_memory(deleted.id, "x", "manual")


@pytest.mark.integration
def test_archive_removes_memory_from_current_list_without_deleting_content(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("preferencia", "manual")

    archived = repository.archive_memory(memory.id)

    assert archived.status is MemoryStatus.ARCHIVED
    assert archived.current_revision.content == "preferencia"
    assert repository.list_current_memories() == []

    fetched = repository.get_memory(memory.id)
    assert fetched.current_revision.content == "preferencia"


@pytest.mark.integration
def test_archiving_an_already_archived_or_deleted_memory_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("x", "manual")
    repository.archive_memory(memory.id)

    with pytest.raises(ValueError, match="Cannot archive"):
        repository.archive_memory(memory.id)


@pytest.mark.integration
def test_delete_redacts_content_across_full_history_and_hides_from_current_list(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("v1", "manual")
    repository.correct_memory(memory.id, "v2", "manual")

    deleted = repository.delete_memory(memory.id)

    assert deleted.status is MemoryStatus.DELETED
    assert deleted.current_revision.content is None
    assert repository.list_current_memories() == []

    history = repository.get_history(memory.id)
    assert [r.content for r in history] == [None, None]
    assert [r.version for r in history] == [1, 2]  # the marker survives, just redacted


@pytest.mark.integration
def test_deleting_an_already_deleted_memory_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("x", "manual")
    repository.delete_memory(memory.id)

    with pytest.raises(ValueError, match="already deleted"):
        repository.delete_memory(memory.id)


@pytest.mark.integration
def test_archived_memory_can_still_be_deleted(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("x", "manual")
    repository.archive_memory(memory.id)

    deleted = repository.delete_memory(memory.id)

    assert deleted.status is MemoryStatus.DELETED


@pytest.mark.integration
def test_operations_on_unknown_memory_raise(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown memory"):
        repository.get_memory(999)
    with pytest.raises(ValueError, match="Unknown memory"):
        repository.correct_memory(999, "x", "manual")
    with pytest.raises(ValueError, match="Unknown memory"):
        repository.archive_memory(999)
    with pytest.raises(ValueError, match="Unknown memory"):
        repository.delete_memory(999)
    with pytest.raises(ValueError, match="Unknown memory"):
        repository.get_history(999)


@pytest.mark.integration
def test_memory_state_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("v1", "manual")
    repository.correct_memory(memory.id, "v2", "manual")

    reopened_repository = build_sqlite_memory_repository(database_path)
    fetched = reopened_repository.get_memory(memory.id)
    history = reopened_repository.get_history(memory.id)

    assert fetched.current_revision.content == "v2"
    assert [r.content for r in history] == ["v1", "v2"]


@pytest.mark.integration
def test_failed_operation_leaves_no_partial_data(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        now = datetime.now(UTC).replace(tzinfo=None)
        memory_model = MemoryModel(status=MemoryStatus.CURRENT, created_at=now, updated_at=now)
        session.add(memory_model)
        session.flush()
        revision_model = MemoryRevisionModel(
            memory_id=memory_model.id,
            version=1,
            content="x",
            origin="manual",
            is_current=True,
            created_at=now,
        )
        session.add(revision_model)
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        assert session.scalars(select(MemoryModel)).first() is None
        assert session.scalars(select(MemoryRevisionModel)).first() is None


@pytest.mark.integration
def test_failed_correction_rolls_back_both_the_flip_and_the_new_revision(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    memory = repository.create_memory("original", "manual")

    session_factory = build_session_factory(build_engine(database_path))

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        current_revision_model = session.scalars(
            select(MemoryRevisionModel).where(
                MemoryRevisionModel.memory_id == memory.id,
                MemoryRevisionModel.is_current.is_(True),
            )
        ).one()
        current_revision_model.is_current = False
        session.flush()

        session.add(
            MemoryRevisionModel(
                memory_id=memory.id,
                version=2,
                content="corregido",
                origin="manual",
                is_current=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        session.flush()
        raise Boom

    # The failed correction must not have flipped is_current nor added a revision.
    fetched = repository.get_memory(memory.id)
    assert fetched.current_revision.version == 1
    assert fetched.current_revision.content == "original"
    assert len(repository.get_history(memory.id)) == 1
