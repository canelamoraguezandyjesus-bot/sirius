"""GUI tests for the B3b project continuity section (RF-016/017, D-02).

No test ever touches the real Windows Credential Manager, SQLite, or the LLM
provider: every widget here wraps a real ``ProjectContinuityUseCase`` around
an in-memory fake ``ProjectRepository`` — the same pattern used throughout
this repo (e.g. B3a's ``test_initial_project_window.py``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pytestqt.qtbot import QtBot

from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.domain.project import Project
from sirius.presentation.project_continuity_widget import (
    NO_BLOCKERS_TEXT,
    ProjectContinuityWidget,
)


class _FakeProjectRepository:
    def __init__(self, initial: Project | None, *, raise_on_update: bool = False) -> None:
        self._project = initial
        self._raise_on_update = raise_on_update
        self.update_calls: list[dict[str, str | None]] = []

    def get_or_create_active_project(self) -> Project:
        raise AssertionError("must never be called from this widget")

    def get_active_project(self) -> Project | None:
        return self._project

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        objective: str | None = None,
        current_state: str | None = None,
        blockers: str | None = None,
        next_step: str | None = None,
    ) -> Project:
        if self._raise_on_update:
            raise RuntimeError("fallo simulado de infraestructura con detalle sensible")
        self.update_calls.append(
            {"current_state": current_state, "blockers": blockers, "next_step": next_step}
        )
        assert self._project is not None
        assert self._project.id == project_id
        self._project = Project(
            id=self._project.id,
            name=name if name is not None else self._project.name,
            objective=objective if objective is not None else self._project.objective,
            current_state=current_state
            if current_state is not None
            else self._project.current_state,
            blockers=blockers if blockers is not None else self._project.blockers,
            next_step=next_step if next_step is not None else self._project.next_step,
            created_at=self._project.created_at,
            updated_at=datetime.now(UTC),
        )
        return self._project


def _configured_project(
    *, name: str = "Sirius 0.1", objective: str = "Cerrar B3b", blockers: str = ""
) -> Project:
    now = datetime.now(UTC)
    return Project(
        id=1,
        name=name,
        objective=objective,
        current_state="en curso",
        blockers=blockers,
        next_step="escribir pruebas",
        created_at=now,
        updated_at=now,
    )


def _placeholder() -> Project:
    now = datetime.now(UTC)
    return Project(
        id=1,
        name="",
        objective="",
        current_state="",
        blockers="",
        next_step="",
        created_at=now,
        updated_at=now,
    )


def _build_widget(
    project: Project | None, *, raise_on_update: bool = False
) -> tuple[ProjectContinuityWidget, _FakeProjectRepository]:
    repository = _FakeProjectRepository(project, raise_on_update=raise_on_update)
    use_case = ProjectContinuityUseCase(repository)
    widget = ProjectContinuityWidget(use_case, show_warning=lambda title, text: None)
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

    assert len(repository.update_calls) == 1
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

    assert repository.update_calls[0]["blockers"] == ""
    assert widget.blockers_label.text() == NO_BLOCKERS_TEXT


@pytest.mark.gui
def test_cancel_does_not_persist_and_restores_the_summary(qtbot: QtBot) -> None:
    widget, repository = _build_widget(_configured_project())
    qtbot.addWidget(widget)
    widget.update_button.click()
    widget.current_state_input.setPlainText("cambio no guardado")

    widget._handle_cancel_clicked()

    assert repository.update_calls == []
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

    assert repository.update_calls == []
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

    assert repository.update_calls == []
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

    assert len(repository.update_calls) == 1
