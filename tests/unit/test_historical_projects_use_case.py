"""Unit tests for HistoricalProjectsUseCase (§5.3, M1).

Uses an in-memory fake ``ProjectRepository`` so behavior is verified
independently of SQLite (that gets its own dedicated integration coverage in
``tests/integration/test_sqlite_project_repository.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.application.historical_projects import HistoricalProjectsUseCase
from sirius.domain.project import Project, ProjectRevision, ProjectStatus


class _FakeProjectRepository:
    def __init__(
        self,
        completed: tuple[Project, ...] = (),
        revisions: tuple[ProjectRevision, ...] = (),
    ) -> None:
        self._completed = completed
        self._revisions = revisions
        self.list_project_revisions_calls: list[int] = []

    def get_active_project(self) -> Project | None:
        raise AssertionError("must never be called by HistoricalProjectsUseCase")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called by HistoricalProjectsUseCase")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        self.list_project_revisions_calls.append(project_id)
        return self._revisions

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called by HistoricalProjectsUseCase")

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        raise AssertionError("must never be called by HistoricalProjectsUseCase")

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
        raise AssertionError("must never be called by HistoricalProjectsUseCase")

    def complete_active_project(self, project_id: int) -> Project:
        raise AssertionError("must never be called by HistoricalProjectsUseCase")

    def list_completed_projects(self) -> tuple[Project, ...]:
        return self._completed


def _completed_project(
    project_id: int, *, completed_at: datetime, name: str = "Proyecto"
) -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=project_id,
        project_id=project_id,
        version=1,
        objective="objetivo",
        state_summary="estado",
        blockers=(),
        next_step="siguiente",
        source_event_id=None,
        created_at=now,
    )
    return Project(
        id=project_id,
        name=name,
        status=ProjectStatus.COMPLETED,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        completed_at=completed_at,
    )


def test_list_completed_delegates_to_the_repository_verbatim() -> None:
    first = _completed_project(1, completed_at=datetime(2026, 1, 1, tzinfo=UTC))
    second = _completed_project(2, completed_at=datetime(2026, 2, 1, tzinfo=UTC))
    repository = _FakeProjectRepository(completed=(second, first))

    use_case = HistoricalProjectsUseCase(repository)

    assert use_case.list_completed() == (second, first)


def test_list_completed_is_empty_when_nothing_has_been_completed() -> None:
    use_case = HistoricalProjectsUseCase(_FakeProjectRepository(completed=()))

    assert use_case.list_completed() == ()


def test_get_revision_history_delegates_to_the_repository_with_the_project_id() -> None:
    revision = ProjectRevision(
        id=1,
        project_id=7,
        version=1,
        objective="objetivo",
        state_summary="estado",
        blockers=(),
        next_step="siguiente",
        source_event_id=None,
        created_at=datetime.now(UTC),
    )
    repository = _FakeProjectRepository(revisions=(revision,))

    use_case = HistoricalProjectsUseCase(repository)
    result = use_case.get_revision_history(7)

    assert result == (revision,)
    assert repository.list_project_revisions_calls == [7]
