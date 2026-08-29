"""Unit tests for ProjectContinuityUseCase (B3b/B3c, D-02, RF-016/017).

Uses an in-memory fake ``ProjectRepository`` so behavior is verified
independently of SQLite (that gets its own dedicated integration coverage in
``tests/integration/test_sqlite_project_repository.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.application.project_continuity import (
    InvalidProjectContinuityDataError,
    ProjectContinuityError,
    ProjectContinuityUseCase,
    ProjectNotConfiguredError,
)
from sirius.domain.project import Project, ProjectRevision, ProjectStatus, normalize_blockers


class _FakeProjectRepository:
    def __init__(
        self,
        initial: Project | None = None,
        *,
        raise_on_get: bool = False,
        raise_on_update: bool = False,
    ) -> None:
        self._project = initial
        self._raise_on_get = raise_on_get
        self._raise_on_update = raise_on_update
        self.append_revision_calls: list[dict[str, object]] = []

    def get_active_project(self) -> Project | None:
        if self._raise_on_get:
            raise RuntimeError("fallo simulado de infraestructura")
        return self._project

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called by ProjectContinuityUseCase")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called by ProjectContinuityUseCase")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        raise AssertionError("must never be called by ProjectContinuityUseCase")

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        raise AssertionError("must never be called by ProjectContinuityUseCase")

    def complete_active_project(self, project_id: int) -> Project:
        raise AssertionError("must never be called by ProjectContinuityUseCase")

    def list_completed_projects(self) -> tuple[Project, ...]:
        raise AssertionError("must never be called by ProjectContinuityUseCase")

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
        if self._raise_on_update:
            raise RuntimeError("fallo simulado de infraestructura con detalle sensible")
        self.append_revision_calls.append(
            {
                "objective": objective,
                "state_summary": state_summary,
                "blockers": blockers,
                "next_step": next_step,
            }
        )
        assert self._project is not None
        assert self._project.id == project_id
        assert self._project.current_revision is not None
        new_revision = ProjectRevision(
            id=self._project.current_revision.id + 1,
            project_id=project_id,
            version=self._project.current_revision.version + 1,
            objective=objective,
            state_summary=state_summary,
            blockers=blockers,
            next_step=next_step,
            source_event_id=source_event_id,
            created_at=datetime.now(UTC),
        )
        self._project = Project(
            id=self._project.id,
            name=self._project.name,
            status=self._project.status,
            current_revision=new_revision,
            created_at=self._project.created_at,
            updated_at=datetime.now(UTC),
            completed_at=self._project.completed_at,
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
    project_id: int = 1,
    *,
    name: str = "Sirius 0.1",
    objective: str = "Cerrar B3b",
    current_state: str = "en curso",
    blockers: str = "",
    next_step: str = "escribir pruebas",
) -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=1,
        project_id=project_id,
        version=1,
        objective=objective,
        state_summary=current_state,
        blockers=normalize_blockers(blockers),
        next_step=next_step,
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


# --- get_summary ------------------------------------------------------------


def test_get_summary_returns_every_continuity_field() -> None:
    project = _configured(blockers="bloqueo 1\nbloqueo 2")
    use_case = ProjectContinuityUseCase(_FakeProjectRepository(project))
    assert project.current_revision is not None

    summary = use_case.get_summary()

    assert summary.project_id == project.id
    assert summary.name == project.name
    assert summary.objective == project.current_revision.objective
    assert summary.current_state == project.current_revision.state_summary
    assert summary.blockers == "bloqueo 1\nbloqueo 2"
    assert summary.next_step == project.current_revision.next_step
    assert summary.updated_at == project.updated_at


def test_get_summary_never_creates_a_project() -> None:
    repository = _FakeProjectRepository(None)
    use_case = ProjectContinuityUseCase(repository)

    with pytest.raises(ProjectNotConfiguredError):
        use_case.get_summary()

    assert repository.append_revision_calls == []


def test_get_summary_rejects_absence_of_a_project() -> None:
    use_case = ProjectContinuityUseCase(_FakeProjectRepository(None))

    with pytest.raises(ProjectNotConfiguredError):
        use_case.get_summary()


def test_get_summary_rejects_the_bootstrap_placeholder() -> None:
    use_case = ProjectContinuityUseCase(_FakeProjectRepository(_placeholder()))

    with pytest.raises(ProjectNotConfiguredError):
        use_case.get_summary()


def test_get_summary_never_returns_the_placeholder_as_a_valid_summary() -> None:
    use_case = ProjectContinuityUseCase(_FakeProjectRepository(_placeholder()))

    try:
        use_case.get_summary()
    except ProjectNotConfiguredError:
        pass
    else:
        pytest.fail("expected ProjectNotConfiguredError for the placeholder")


def test_get_summary_translates_an_infrastructure_failure_safely() -> None:
    use_case = ProjectContinuityUseCase(_FakeProjectRepository(raise_on_get=True))

    with pytest.raises(ProjectContinuityError) as exc_info:
        use_case.get_summary()

    assert "RuntimeError" not in str(exc_info.value)
    assert "fallo simulado" not in str(exc_info.value)


# --- update: happy path ------------------------------------------------------


def test_update_normalizes_state_and_next_step() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    summary = use_case.update("  en pausa  ", "", "  retomar mañana  ")

    assert summary.current_state == "en pausa"
    assert summary.next_step == "retomar mañana"


def test_update_normalizes_multiple_blocker_lines() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    summary = use_case.update("estado", "\n\n  bloqueo uno  \n  bloqueo dos\n\n", "siguiente")

    assert summary.blockers == "bloqueo uno\nbloqueo dos"


def test_update_preserves_an_intentional_interior_blank_line_in_blockers() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    summary = use_case.update("estado", "uno\n\ndos", "siguiente")

    assert summary.blockers == "uno\n\ndos"


def test_update_allows_empty_blockers() -> None:
    repository = _FakeProjectRepository(_configured(blockers="algo previo"))
    use_case = ProjectContinuityUseCase(repository)

    summary = use_case.update("estado", "   \n\n  ", "siguiente")

    assert summary.blockers == ""


def test_update_returns_the_persisted_authoritative_state() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    summary = use_case.update("nuevo estado", "bloqueo", "nuevo paso")

    assert summary.current_state == "nuevo estado"
    assert summary.blockers == "bloqueo"
    assert summary.next_step == "nuevo paso"


def test_update_preserves_the_objective_untouched() -> None:
    repository = _FakeProjectRepository(_configured(objective="Cerrar B3c"))
    use_case = ProjectContinuityUseCase(repository)

    summary = use_case.update("estado", "bloqueo", "siguiente")

    assert summary.objective == "Cerrar B3c"


def test_update_persists_all_three_fields_in_a_single_repository_call() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    use_case.update("estado", "bloqueo", "siguiente")

    assert len(repository.append_revision_calls) == 1
    call = repository.append_revision_calls[0]
    assert call["state_summary"] == "estado"
    assert call["blockers"] == ("bloqueo",)
    assert call["next_step"] == "siguiente"


# --- update: validation -------------------------------------------------------


def test_update_rejects_empty_current_state() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    with pytest.raises(InvalidProjectContinuityDataError):
        use_case.update("", "bloqueo", "siguiente")

    assert repository.append_revision_calls == []


def test_update_rejects_whitespace_only_current_state() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    with pytest.raises(InvalidProjectContinuityDataError):
        use_case.update("   ", "bloqueo", "siguiente")

    assert repository.append_revision_calls == []


def test_update_rejects_empty_next_step() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    with pytest.raises(InvalidProjectContinuityDataError):
        use_case.update("estado", "bloqueo", "")

    assert repository.append_revision_calls == []


def test_update_rejects_whitespace_only_next_step() -> None:
    repository = _FakeProjectRepository(_configured())
    use_case = ProjectContinuityUseCase(repository)

    with pytest.raises(InvalidProjectContinuityDataError):
        use_case.update("estado", "bloqueo", "   ")

    assert repository.append_revision_calls == []


def test_update_rejects_when_no_project_is_configured() -> None:
    use_case = ProjectContinuityUseCase(_FakeProjectRepository(_placeholder()))

    with pytest.raises(ProjectNotConfiguredError):
        use_case.update("estado", "bloqueo", "siguiente")


def test_update_translates_an_infrastructure_failure_safely_and_without_partial_writes() -> None:
    repository = _FakeProjectRepository(_configured(), raise_on_update=True)
    use_case = ProjectContinuityUseCase(repository)

    with pytest.raises(ProjectContinuityError) as exc_info:
        use_case.update("estado", "bloqueo", "siguiente")

    assert "RuntimeError" not in str(exc_info.value)
    assert "detalle sensible" not in str(exc_info.value)
