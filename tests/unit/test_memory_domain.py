from datetime import UTC, datetime

import pytest

from sirius.domain.memory import (
    Memory,
    MemoryRevision,
    MemoryStatus,
    ensure_can_archive,
    ensure_can_correct,
    ensure_can_delete,
    ensure_subject_key_has_a_project,
    ensure_valid_origin,
    ensure_valid_subject_key,
    next_revision_version,
)


def _revision(
    version: int = 1, content: str | None = "algo", source_event_id: int | None = None
) -> MemoryRevision:
    return MemoryRevision(
        id=1,
        memory_id=1,
        version=version,
        content=content,
        origin="manual",
        source_event_id=source_event_id,
        created_at=datetime.now(UTC),
    )


def _memory(status: MemoryStatus, revision: MemoryRevision | None = None) -> Memory:
    now = datetime.now(UTC)
    return Memory(
        id=1,
        status=status,
        current_revision=revision or _revision(),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize("origin", ["", "   ", "\t\n"])
def test_ensure_valid_origin_rejects_empty_or_blank(origin: str) -> None:
    with pytest.raises(ValueError, match="non-empty origin"):
        ensure_valid_origin(origin)


def test_ensure_valid_origin_accepts_non_empty_string() -> None:
    ensure_valid_origin("manual")  # must not raise


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_ensure_can_correct_rejects_non_current(status: MemoryStatus) -> None:
    with pytest.raises(ValueError, match="Cannot correct"):
        ensure_can_correct(_memory(status))


def test_ensure_can_correct_accepts_current() -> None:
    ensure_can_correct(_memory(MemoryStatus.CURRENT))  # must not raise


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_ensure_can_archive_rejects_non_current(status: MemoryStatus) -> None:
    with pytest.raises(ValueError, match="Cannot archive"):
        ensure_can_archive(_memory(status))


def test_ensure_can_delete_rejects_already_deleted() -> None:
    with pytest.raises(ValueError, match="already deleted"):
        ensure_can_delete(_memory(MemoryStatus.DELETED))


@pytest.mark.parametrize("status", [MemoryStatus.CURRENT, MemoryStatus.ARCHIVED])
def test_ensure_can_delete_accepts_current_or_archived(status: MemoryStatus) -> None:
    ensure_can_delete(_memory(status))  # must not raise


def test_next_revision_version_increments_from_current() -> None:
    assert next_revision_version(_revision(version=1)) == 2
    assert next_revision_version(_revision(version=7)) == 8


def test_memory_revision_source_event_id_defaults_to_none_and_round_trips() -> None:
    assert _revision().source_event_id is None
    assert _revision(source_event_id=42).source_event_id == 42


def test_memory_is_immutable() -> None:
    memory = _memory(MemoryStatus.CURRENT)

    with pytest.raises(AttributeError):
        memory.status = MemoryStatus.ARCHIVED  # type: ignore[misc]


def test_memory_subject_key_and_project_id_default_to_none() -> None:
    memory = _memory(MemoryStatus.CURRENT)

    assert memory.subject_key is None
    assert memory.project_id is None


@pytest.mark.parametrize("subject_key", ["", "   ", "\t\n"])
def test_ensure_valid_subject_key_rejects_blank_when_given(subject_key: str) -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        ensure_valid_subject_key(subject_key)


def test_ensure_valid_subject_key_accepts_none() -> None:
    ensure_valid_subject_key(None)  # must not raise


def test_ensure_valid_subject_key_accepts_non_blank_string() -> None:
    ensure_valid_subject_key("Motor de persistencia")  # must not raise


def test_ensure_subject_key_has_a_project_accepts_both_none() -> None:
    ensure_subject_key_has_a_project(None, None)  # must not raise


def test_ensure_subject_key_has_a_project_accepts_subject_with_project() -> None:
    ensure_subject_key_has_a_project("Motor de persistencia", 1)  # must not raise


def test_ensure_subject_key_has_a_project_rejects_subject_without_project() -> None:
    with pytest.raises(ValueError, match="must also be associated with a project"):
        ensure_subject_key_has_a_project("Motor de persistencia", None)
