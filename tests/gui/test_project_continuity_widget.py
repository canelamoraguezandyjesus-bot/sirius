"""GUI tests for the B3b/B3c project continuity and lifecycle section
(RF-016/017/018, D-02).

No test ever touches the real Windows Credential Manager, SQLite, or the LLM
provider: every widget here wraps a real ``ProjectContinuityUseCase`` and
``ProjectLifecycleUseCase`` around an in-memory fake ``ProjectRepository`` —
the same pattern used throughout this repo (e.g. B3a's
``test_initial_project_window.py``).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pytestqt.qtbot import QtBot

from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.project_lifecycle import ProjectLifecycleUseCase
from sirius.domain.project import Project, ProjectRevision, ProjectStatus, normalize_blockers
from sirius.presentation.project_continuity_widget import (
    NO_BLOCKERS_TEXT,
    ProjectContinuityWidget,
)


class _FakeProjectRepository:
    def __init__(
        self,
        initial: Project | None,
        *,
        raise_on_update: bool = False,
        raise_on_complete: bool = False,
    ) -> None:
        self._project = initial
        self._raise_on_update = raise_on_update
        self._raise_on_complete = raise_on_complete
        self.append_revision_calls: list[dict[str, object]] = []
        self.complete_calls: list[int] = []

    def get_active_project(self) -> Project | None:
        return self._project

    def ensure_bootstrap_project(self) -> None:
        raise AssertionError("must never be called from this widget")

    def get_project(self, project_id: int) -> Project | None:
        raise AssertionError("must never be called from this widget")

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        raise AssertionError("must never be called from this widget")

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        raise AssertionError("must never be called from this widget")

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
            {"state_summary": state_summary, "blockers": blockers, "next_step": next_step}
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
        self._project = dataclasses.replace(
            self._project, current_revision=new_revision, updated_at=datetime.now(UTC)
        )
        return self._project

    def complete_active_project(self, project_id: int) -> Project:
        if self._raise_on_complete:
            raise RuntimeError("fallo simulado de infraestructura con detalle sensible")
        self.complete_calls.append(project_id)
        assert self._project is not None
        assert self._project.id == project_id
        now = datetime.now(UTC)
        self._project = dataclasses.replace(
            self._project, status=ProjectStatus.COMPLETED, completed_at=now, updated_at=now
        )
        return self._project

    def list_completed_projects(self) -> tuple[Project, ...]:
        raise AssertionError("must never be called from this widget")


def _configured_project(
    *, name: str = "Sirius 0.1", objective: str = "Cerrar B3b", blockers: str = ""
) -> Project:
    now = datetime.now(UTC)
    revision = ProjectRevision(
        id=1,
        project_id=1,
        version=1,
        objective=objective,
        state_summary="en curso",
        blockers=normalize_blockers(blockers),
        next_step="escribir pruebas",
        source_event_id=None,
        created_at=now,
    )
    return Project(
        id=1,
        name=name,
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _placeholder() -> Project:
    now = datetime.now(UTC)
    return Project(
        id=1,
        name="",
        status=ProjectStatus.ACTIVE,
        current_revision=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _build_widget(
    project: Project | None,
    *,
    raise_on_update: bool = False,
    raise_on_complete: bool = False,
    confirm_completion: Callable[[str, str], bool] | None = None,
) -> tuple[ProjectContinuityWidget, _FakeProjectRepository]:
    repository = _FakeProjectRepository(
        project, raise_on_update=raise_on_update, raise_on_complete=raise_on_complete
    )
    continuity_use_case = ProjectContinuityUseCase(repository)
    lifecycle_use_case = ProjectLifecycleUseCase(repository)
    widget = ProjectContinuityWidget(
        continuity_use_case,
        lifecycle_use_case,
        show_warning=lambda title, text: None,
        confirm_completion=confirm_completion or (lambda title, text: True),
    )
    return widget, repository


# --- Summary on open ---------------------------------------------------------


@pytest.mark.gui
def test_summary_appears_on_open_with_name_objective_and_state(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)

    assert widget.name_label.text() == "Sirius 0.1"
    assert widget.objective_label.text() == "Cerrar B3b"
    assert widget.current_state_label.text() == "en curso"


@pytest.mark.gui
def test_summary_shows_no_blockers_registered_when_empty(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project(blockers=""))
    qtbot.addWidget(widget)

    assert widget.blockers_label.text() == NO_BLOCKERS_TEXT


@pytest.mark.gui
def test_summary_shows_registered_blockers_when_present(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project(blockers="bloqueo uno"))
    qtbot.addWidget(widget)

    assert widget.blockers_label.text() == "bloqueo uno"


@pytest.mark.gui
def test_summary_highlights_ahora_toca_with_the_next_step(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)

    assert widget.next_step_label.text() == "Ahora toca: escribir pruebas"


@pytest.mark.gui
def test_unconfigured_project_shows_a_safe_state_without_crashing(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_placeholder())
    qtbot.addWidget(widget)

    assert widget._stack.currentWidget() is widget.not_configured_label
    assert widget.not_configured_label.text() != ""


@pytest.mark.gui
def test_missing_project_entirely_shows_a_safe_state_without_crashing(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(None)
    qtbot.addWidget(widget)

    assert widget._stack.currentWidget() is widget.not_configured_label


# --- Edit mode ---------------------------------------------------------------


@pytest.mark.gui
def test_actualizar_proyecto_shows_the_edit_controls_precargados(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project(blockers="bloqueo existente"))
    qtbot.addWidget(widget)

    widget.update_button.click()

    assert widget._stack.currentWidget() is not None
    assert widget.current_state_input.toPlainText() == "en curso"
    assert widget.blockers_input.toPlainText() == "bloqueo existente"
    assert widget.next_step_input.text() == "escribir pruebas"


@pytest.mark.gui
def test_saving_persists_and_refreshes_the_summary(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()

    widget.current_state_input.setPlainText("estado nuevo")
    widget.blockers_input.setPlainText("bloqueo nuevo")
    widget.next_step_input.setText("paso nuevo")
    widget._handle_save_clicked()

    assert len(repository.append_revision_calls) == 1
    assert widget.current_state_label.text() == "estado nuevo"
    assert widget.blockers_label.text() == "bloqueo nuevo"
    assert widget.next_step_label.text() == "Ahora toca: paso nuevo"


@pytest.mark.gui
def test_saving_clears_blockers_when_left_empty(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project(blockers="bloqueo previo"))
    qtbot.addWidget(widget)
    widget.update_button.click()

    widget.blockers_input.setPlainText("")
    widget._handle_save_clicked()

    assert repository.append_revision_calls[0]["blockers"] == ()
    assert widget.blockers_label.text() == NO_BLOCKERS_TEXT


@pytest.mark.gui
def test_cancel_does_not_persist_and_restores_the_summary(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()
    widget.current_state_input.setPlainText("cambio no guardado")

    widget._handle_cancel_clicked()

    assert repository.append_revision_calls == []
    assert widget.current_state_label.text() == "en curso"


@pytest.mark.gui
def test_reopening_edit_after_cancel_reloads_the_persisted_values(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()
    widget.current_state_input.setPlainText("cambio no guardado")
    widget._handle_cancel_clicked()

    widget.update_button.click()

    assert widget.current_state_input.toPlainText() == "en curso"


@pytest.mark.gui
def test_empty_state_is_rejected_with_an_actionable_error(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()

    widget.current_state_input.setPlainText("   ")
    widget._handle_save_clicked()

    assert repository.append_revision_calls == []
    assert widget.edit_error_label.text() != ""
    assert widget.save_button.isEnabled() is True
    assert widget.current_state_input.isEnabled() is True


@pytest.mark.gui
def test_empty_next_step_is_rejected_with_an_actionable_error(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()

    widget.next_step_input.setText("   ")
    widget._handle_save_clicked()

    assert repository.append_revision_calls == []
    assert widget.edit_error_label.text() != ""


@pytest.mark.gui
def test_error_preserves_what_the_user_typed(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()

    widget.current_state_input.setPlainText("")
    widget.blockers_input.setPlainText("bloqueo tecleado")
    widget.next_step_input.setText("paso tecleado")
    widget._handle_save_clicked()

    assert widget.blockers_input.toPlainText() == "bloqueo tecleado"
    assert widget.next_step_input.text() == "paso tecleado"


@pytest.mark.gui
def test_repository_failure_never_shows_internal_details(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project(), raise_on_update=True)
    qtbot.addWidget(widget)
    widget.update_button.click()

    widget.current_state_input.setPlainText("estado")
    widget.next_step_input.setText("siguiente")
    widget._handle_save_clicked()

    assert "RuntimeError" not in widget.edit_error_label.text()
    assert "detalle sensible" not in widget.edit_error_label.text()
    assert widget.edit_error_label.text() != ""
    assert widget.save_button.isEnabled() is True
    assert widget.current_state_input.isEnabled() is True


@pytest.mark.gui
def test_double_submit_is_prevented(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()
    widget.current_state_input.setPlainText("estado")
    widget.next_step_input.setText("siguiente")

    widget._handle_save_clicked()
    widget._handle_save_clicked()  # redundant call right after success

    assert len(repository.append_revision_calls) == 1


# --- Completar proyecto (B3c, RF-018) -----------------------------------------


@pytest.mark.gui
def test_complete_button_is_visible_on_the_summary_page(qtbot: QtBot) -> None:
    widget, _repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.show()

    assert widget.complete_button.isVisible() is True


@pytest.mark.gui
def test_completing_asks_for_confirmation_before_touching_the_repository(qtbot: QtBot) -> None:
    prompts: list[tuple[str, str]] = []

    def _confirm(title: str, text: str) -> bool:
        prompts.append((title, text))
        return False

    widget, repository = _build_widget(_configured_project(), confirm_completion=_confirm)
    qtbot.addWidget(widget)

    widget.complete_button.click()

    assert len(prompts) == 1
    assert repository.complete_calls == []


@pytest.mark.gui
def test_declining_the_confirmation_never_completes_the_project(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project(), confirm_completion=lambda t, x: False)
    qtbot.addWidget(widget)

    widget.complete_button.click()

    assert repository.complete_calls == []
    assert widget._stack.currentWidget() is not widget.not_configured_label


@pytest.mark.gui
def test_confirming_completes_the_project_and_emits_project_completed(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.project_completed, timeout=1000):
        widget.complete_button.click()

    assert repository.complete_calls == [1]


@pytest.mark.gui
def test_completion_failure_never_shows_internal_details(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project(), raise_on_complete=True)
    qtbot.addWidget(widget)

    widget.complete_button.click()

    assert repository.complete_calls == []
    assert widget.complete_button.isEnabled() is True
    assert widget.update_button.isEnabled() is True
