"""Unit tests for InitialProjectUseCase (B3a/B3c, D-02, RF-014/015/016).

Uses an in-memory fake ``ProjectRepository`` so behavior is verified
independently of SQLite (that gets its own dedicated integration coverage in
``tests/integration/test_initial_project_persistence.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.application.initial_project import (
    InitialProjectAlreadyConfiguredError,
    InitialProjectUseCase,
    InvalidInitialProjectDataError,
)
from sirius.domain.project import (
    INITIAL_PROJECT_NEXT_STEP,
    INITIAL_PROJECT_STATE,
    Project,
    ProjectRevision,
    ProjectStatus,
)


class _FakeProjectRepository:
    def __init__(self, initial: Project | None = None) -> None:
        self._project = initial
        self.create_calls: list[tuple[str, str]] = []

    def get_active_project(self) -> Project | None:
        return self._project

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called by InitialProjectUseCase")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called by InitialProjectUseCase")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        raise AssertionError("must never be called by InitialProjectUseCase")

    def append_revision(
        self,
        project_id: int,
        *,
        objective: str,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
        source_event_id: int | None = None,
    ) -> Project:
        raise AssertionError("must never be called by InitialProjectUseCase")

    def complete_active_project(self, project_id: int) -> Project:
        raise AssertionError("must never be called by InitialProjectUseCase")

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        self.create_calls.append((name, objective))
        now = datetime.now(UTC)
        base_id = self._project.id if self._project is not None else 1
        base_created_at = self._project.created_at if self._project is not None else now
        revision = ProjectRevision(
            id=1,
            project_id=base_id,
            version=1,
            objective=objective,
            state_summary=state_summary,
            blockers=blockers,
            next_step=next_step,
            source_event_id=None,
            created_at=now,
        )
        self._project = Project(
            id=base_id,
            name=name,
            status=ProjectStatus.ACTIVE,
            current_revision=revision,
            created_at=base_created_at,
            updated_at=now,
            completed_at=None,
        )
        return self._project


def _placeholder(project_id: int = 1) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=project_id,
        name="",
        status=ProjectStatus.ACTIVE,
        current_revision=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _configured(
    project_id: int = 1, *, name: str = "Sirius", objective: str = "Cerrar B3a"
) -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=1,
        project_id=project_id,
        version=1,
        objective=objective,
        state_summary=INITIAL_PROJECT_STATE,
        blockers=(),
        next_step=INITIAL_PROJECT_NEXT_STEP,
        source_event_id=None,
        created_at=now,
    )
    return Project(
        id=project_id,
        name=name,
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def test_is_configured_is_false_for_the_bootstrap_placeholder() -> None:
    use_case = InitialProjectUseCase(_FakeProjectRepository(_placeholder()))

    assert use_case.is_configured() is False


def test_is_configured_is_false_when_no_project_exists_yet() -> None:
    use_case = InitialProjectUseCase(_FakeProjectRepository(None))

    assert use_case.is_configured() is False


def test_is_configured_is_true_for_a_real_project() -> None:
    use_case = InitialProjectUseCase(_FakeProjectRepository(_configured()))

    assert use_case.is_configured() is True


def test_get_active_project_returns_the_project_without_creating_one() -> None:
    repository = _FakeProjectRepository(None)
    use_case = InitialProjectUseCase(repository)

    assert use_case.get_active_project() is None
    assert repository._project is None  # never created as a side effect of reading


def test_create_initial_project_normalizes_and_persists_name_and_objective() -> None:
    repository = _FakeProjectRepository(_placeholder())
    use_case = InitialProjectUseCase(repository)

    created = use_case.create_initial_project("  Mi Proyecto  ", "  Aprender Sirius  ")

    assert created.name == "Mi Proyecto"
    assert created.current_revision is not None
    assert created.current_revision.objective == "Aprender Sirius"


def test_create_initial_project_assigns_the_canonical_initial_state_and_next_step() -> None:
    use_case = InitialProjectUseCase(_FakeProjectRepository(_placeholder()))

    created = use_case.create_initial_project("Mi Proyecto", "Aprender Sirius")

    assert created.current_revision is not None
    assert created.current_revision.state_summary == INITIAL_PROJECT_STATE
    assert created.current_revision.next_step == INITIAL_PROJECT_NEXT_STEP


def test_create_initial_project_completes_the_existing_placeholder_row() -> None:
    """Same id before and after: the placeholder is completed, not replaced."""
    repository = _FakeProjectRepository(_placeholder(project_id=7))
    use_case = InitialProjectUseCase(repository)

    created = use_case.create_initial_project("Mi Proyecto", "Aprender Sirius")

    assert created.id == 7
    assert len(repository.create_calls) == 1


def test_create_initial_project_becomes_the_single_active_project() -> None:
    repository = _FakeProjectRepository(_placeholder())
    use_case = InitialProjectUseCase(repository)

    use_case.create_initial_project("Mi Proyecto", "Aprender Sirius")

    assert use_case.is_configured() is True


@pytest.mark.parametrize(
    ("name", "objective"),
    [
        ("", "Aprender Sirius"),
        ("Mi Proyecto", ""),
        ("   ", "Aprender Sirius"),
        ("Mi Proyecto", "   "),
        ("", ""),
    ],
)
def test_create_initial_project_rejects_empty_or_whitespace_only_fields(
    name: str, objective: str
) -> None:
    repository = _FakeProjectRepository(_placeholder())
    use_case = InitialProjectUseCase(repository)

    with pytest.raises(InvalidInitialProjectDataError):
        use_case.create_initial_project(name, objective)

    assert repository.create_calls == []


def test_create_initial_project_rejects_a_second_configured_project() -> None:
    original = _configured(name="Original", objective="Objetivo original")
    repository = _FakeProjectRepository(original)
    use_case = InitialProjectUseCase(repository)

    with pytest.raises(InitialProjectAlreadyConfiguredError):
        use_case.create_initial_project("Segundo", "Otro objetivo")

    assert repository.create_calls == []
    assert repository.get_active_project() is original


def test_rejected_second_project_leaves_the_current_project_completely_intact() -> None:
    original = _configured(name="Original", objective="Objetivo original")
    repository = _FakeProjectRepository(original)
    use_case = InitialProjectUseCase(repository)

    with pytest.raises(InitialProjectAlreadyConfiguredError):
        use_case.create_initial_project("Segundo", "Otro objetivo")

    assert repository.get_active_project() is original
