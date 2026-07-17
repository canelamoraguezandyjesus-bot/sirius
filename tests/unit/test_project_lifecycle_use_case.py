"""Unit tests for ProjectLifecycleUseCase (B3c, D-02, RF-018).

Uses an in-memory fake ``ProjectRepository`` so behavior is verified
independently of SQLite (that gets its own dedicated integration coverage in
``tests/integration/test_sqlite_project_repository.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.application.project_errors import ProjectLifecycleError, ProjectNotConfiguredError
from sirius.application.project_lifecycle import ProjectLifecycleUseCase
from sirius.domain.project import Project, ProjectRevision, ProjectStatus


class _FakeProjectRepository:
    def __init__(self, initial: Project | None = None, *, raise_on_complete: bool = False) -> None:
        self._project = initial
        self._raise_on_complete = raise_on_complete
        self.complete_calls: list[int] = []

    def get_active_project(self) -> Project | None:
        return self._project

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called by ProjectLifecycleUseCase")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called by ProjectLifecycleUseCase")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        raise AssertionError("must never be called by ProjectLifecycleUseCase")

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        raise AssertionError("must never be called by ProjectLifecycleUseCase")

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
        raise AssertionError("must never be called by ProjectLifecycleUseCase")

    def complete_active_project(self, project_id: int) -> Project:
        if self._raise_on_complete:
            raise RuntimeError("fallo simulado de infraestructura con detalle sensible")
        self.complete_calls.append(project_id)
        assert self._project is not None
        assert self._project.id == project_id
        now = datetime.now(UTC)
        self._project = Project(
            id=self._project.id,
            name=self._project.name,
            status=ProjectStatus.COMPLETED,
            current_revision=self._project.current_revision,
            created_at=self._project.created_at,
            updated_at=now,
            completed_at=now,
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


def _configured(project_id: int = 1, *, name: str = "Sirius 0.1") -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=1,
        project_id=project_id,
        version=1,
        objective="Cerrar B3c",
        state_summary="en curso",
        blockers=(),
        next_step="escribir pruebas",
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


def test_get_active_project_returns_the_project_without_completing_it() -> None:
    project = _configured()
    repository = _FakeProjectRepository(project)
    use_case = ProjectLifecycleUseCase(repository)

    assert use_case.get_active_project() is project
    assert repository.complete_calls == []


def test_complete_active_project_marks_it_completed() -> None:
    project = _configured()
    repository = _FakeProjectRepository(project)
    use_case = ProjectLifecycleUseCase(repository)

    completed = use_case.complete_active_project()

    assert completed.status is ProjectStatus.COMPLETED
    assert completed.completed_at is not None
    assert repository.complete_calls == [project.id]


def test_complete_active_project_preserves_the_revision_history() -> None:
    project = _configured()
    repository = _FakeProjectRepository(project)
    use_case = ProjectLifecycleUseCase(repository)

    completed = use_case.complete_active_project()

    assert completed.current_revision == project.current_revision


def test_complete_active_project_rejects_absence_of_a_project() -> None:
    use_case = ProjectLifecycleUseCase(_FakeProjectRepository(None))

    with pytest.raises(ProjectNotConfiguredError):
        use_case.complete_active_project()


def test_complete_active_project_rejects_the_bootstrap_placeholder() -> None:
    use_case = ProjectLifecycleUseCase(_FakeProjectRepository(_placeholder()))

    with pytest.raises(ProjectNotConfiguredError):
        use_case.complete_active_project()


def test_complete_active_project_translates_an_infrastructure_failure_safely() -> None:
    repository = _FakeProjectRepository(_configured(), raise_on_complete=True)
    use_case = ProjectLifecycleUseCase(repository)

    with pytest.raises(ProjectLifecycleError) as exc_info:
        use_case.complete_active_project()

    assert "RuntimeError" not in str(exc_info.value)
    assert "detalle sensible" not in str(exc_info.value)
