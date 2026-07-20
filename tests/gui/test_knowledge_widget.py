"""GUI tests for the B4f observable memory/decision panel (RF-019 a RF-026,
PA-010 a PA-016).

Every use case here is the real one, wired by ``build_conversation_dependencies``
against a temporary SQLite database (the same pattern ``test_main_window.py``
uses) — no fake ``UnitOfWork``/repository stand-ins are hand-rolled. Every
dialog seam (``prompt_line``/``prompt_multiline``/``confirm_action``/
``confirm_delete_memory``/``choose_superseding_decision``) is injected with a
deterministic double, matching ``tests/gui/conftest.py``'s guarantee that no
test ever opens a real Qt dialog.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.delete_memory import OLD_BACKUP_WARNING, SourceMessageChoice
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.decision import Decision
from sirius.presentation.knowledge_widget import KnowledgeWidget, _DeleteMemoryDialog


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_dependencies(
    tmp_path: Path, *, configure_project: bool = True
) -> ConversationDependencies:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    if configure_project:
        project_repository.create_project(
            "Proyecto de prueba",
            "Objetivo de prueba",
            state_summary="en curso",
            blockers=(),
            next_step="siguiente paso",
        )
    return build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )


class _Recorder:
    """Records every warning/information dialog shown, for assertions."""

    def __init__(self) -> None:
        self.warnings: list[tuple[str, str]] = []
        self.informations: list[tuple[str, str]] = []

    def show_warning(self, title: str, text: str) -> None:
        self.warnings.append((title, text))

    def show_information(self, title: str, text: str) -> None:
        self.informations.append((title, text))


def _build_widget(
    dependencies: ConversationDependencies,
    recorder: _Recorder,
    *,
    confirm_action: bool = True,
    prompt_line_value: str | None = None,
    prompt_multiline_value: str | None = None,
    confirm_delete_memory_value: SourceMessageChoice | None = None,
    choose_superseding_decision: Callable[[Sequence[Decision]], Decision | None] | None = None,
) -> KnowledgeWidget:
    def _choose_superseding(candidates: Sequence[Decision]) -> Decision | None:
        if choose_superseding_decision is None:
            return None
        return choose_superseding_decision(candidates)

    return KnowledgeWidget(
        dependencies.get_knowledge_overview_use_case,
        dependencies.save_manual_memory_use_case,
        dependencies.get_memory_origin_use_case,
        dependencies.correct_memory_use_case,
        dependencies.archive_memory_use_case,
        dependencies.delete_memory_use_case,
        dependencies.propose_decision_use_case,
        dependencies.approve_decision_use_case,
        dependencies.get_decision_origin_use_case,
        dependencies.supersede_decision_use_case,
        dependencies.archive_decision_use_case,
        dependencies.detect_precedence_conflicts_use_case,
        dependencies.project_continuity_use_case,
        show_warning=recorder.show_warning,
        show_information=recorder.show_information,
        confirm_action=lambda title, text: confirm_action,
        prompt_line=lambda title, label: prompt_line_value,
        prompt_multiline=lambda title, label: prompt_multiline_value,
        confirm_delete_memory=lambda: confirm_delete_memory_value,
        choose_superseding_decision=_choose_superseding,
    )


@pytest.mark.gui
def test_refresh_lists_current_and_archived_memories(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia guardada")
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    assert widget.memories_list.count() == 1
    assert "preferencia guardada" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_save_memory_button_creates_a_new_memory(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(
        dependencies, _Recorder(), prompt_multiline_value="recuerda esto por favor"
    )
    qtbot.addWidget(widget)

    widget.save_memory_button.click()

    assert widget.memories_list.count() == 1
    assert "recuerda esto por favor" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_save_memory_cancelled_prompt_creates_nothing(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder(), prompt_multiline_value=None)
    qtbot.addWidget(widget)

    widget.save_memory_button.click()

    assert widget.memories_list.count() == 0


@pytest.mark.gui
def test_correct_memory_creates_a_new_revision(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("contenido original")
    widget = _build_widget(dependencies, _Recorder(), prompt_multiline_value="contenido corregido")
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.correct_memory_button.click()

    assert widget.memories_list.count() == 1
    assert "contenido corregido" in widget.memories_list.item(0).text()
    assert "v2" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_correct_memory_without_selection_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)

    widget.correct_memory_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_archive_memory_moves_it_out_of_current(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia archivable")
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.archive_memory_button.click()

    assert "(archived)" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_archive_memory_cancelled_confirmation_leaves_it_current(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia")
    widget = _build_widget(dependencies, _Recorder(), confirm_action=False)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.archive_memory_button.click()

    assert "(current)" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_delete_memory_preserving_source_message_shows_old_backup_warning(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("secreto a borrar")
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        confirm_delete_memory_value=SourceMessageChoice.PRESERVE,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.delete_memory_button.click()

    # A deleted memory leaves both list_current_memories() and
    # list_archived_memories() (MemoryStatus.DELETED is excluded from both),
    # so the overview this panel renders from no longer includes it.
    assert widget.memories_list.count() == 0
    assert recorder.informations[-1][1] == OLD_BACKUP_WARNING


@pytest.mark.gui
def test_delete_memory_redacting_source_message_shows_old_backup_warning(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("secreto a redactar")
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        confirm_delete_memory_value=SourceMessageChoice.REDACT,
    )
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.delete_memory_button.click()

    assert widget.memories_list.count() == 0
    assert recorder.informations[-1][1] == OLD_BACKUP_WARNING


@pytest.mark.gui
def test_delete_memory_dialog_ok_button_disabled_until_explicit_choice(qtbot: QtBot) -> None:
    dialog = _DeleteMemoryDialog()
    qtbot.addWidget(dialog)
    ok_button = dialog._ok_button

    assert ok_button.isEnabled() is False
    assert dialog.preserve_radio.isChecked() is False
    assert dialog.redact_radio.isChecked() is False

    dialog.redact_radio.setChecked(True)

    assert ok_button.isEnabled() is True


@pytest.mark.gui
def test_delete_memory_cancelled_dialog_leaves_memory_untouched(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("contenido intacto")
    widget = _build_widget(dependencies, _Recorder(), confirm_delete_memory_value=None)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.delete_memory_button.click()

    assert "contenido intacto" in widget.memories_list.item(0).text()


@pytest.mark.gui
def test_view_memory_origin_shows_the_recorded_event(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    dependencies.save_manual_memory_use_case.save("preferencia con origen")
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)
    widget.memories_list.setCurrentRow(0)

    widget.memory_origin_button.click()

    assert len(recorder.informations) == 1
    assert "memory.manual_save" in recorder.informations[0][1]


@pytest.mark.gui
def test_propose_decision_without_active_project_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path, configure_project=False)
    recorder = _Recorder()
    widget = _build_widget(
        dependencies,
        recorder,
        prompt_line_value="Motor de persistencia",
        prompt_multiline_value="Usar SQLite",
    )
    qtbot.addWidget(widget)

    widget.propose_decision_button.click()

    assert widget.decisions_list.count() == 0
    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_propose_decision_creates_a_proposed_decision(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(
        dependencies,
        _Recorder(),
        prompt_line_value="Motor de persistencia",
        prompt_multiline_value="Usar SQLite local",
    )
    qtbot.addWidget(widget)

    widget.propose_decision_button.click()

    assert widget.decisions_list.count() == 1
    assert "(proposed)" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_approve_decision_moves_it_to_approved(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.approve_decision_button.click()

    assert "(approved)" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_supersede_decision_with_no_candidates_warns(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    approved = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(approved.id, confirmed=True)
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder, choose_superseding_decision=None)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.supersede_decision_button.click()

    assert len(recorder.warnings) == 1


@pytest.mark.gui
def test_supersede_decision_replaces_the_approved_one(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    original = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(original.id, confirmed=True)
    substitute = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )

    def _pick_last(candidates: Sequence[Decision]) -> Decision:
        assert [c.id for c in candidates] == [substitute.id]
        return candidates[0]

    widget = _build_widget(
        dependencies,
        _Recorder(),
        confirm_action=True,
        choose_superseding_decision=_pick_last,
    )
    qtbot.addWidget(widget)
    original_row = next(
        row
        for row in range(widget.decisions_list.count())
        if f"#{original.id} " in widget.decisions_list.item(row).text()
    )
    widget.decisions_list.setCurrentRow(original_row)

    widget.supersede_decision_button.click()

    # A superseded decision leaves list_current_decisions() (only APPROVED)
    # without ever becoming PROPOSED or ARCHIVED, so the overview this panel
    # renders from no longer includes it; its link stays reachable, when
    # needed, through DecisionRepository.get_superseding_decision.
    texts = [widget.decisions_list.item(row).text() for row in range(widget.decisions_list.count())]
    assert not any(f"#{original.id} " in text for text in texts)
    assert any(f"#{substitute.id} " in text and "(approved)" in text for text in texts)


@pytest.mark.gui
def test_archive_decision_moves_it_out_of_current(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    approved = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(approved.id, confirmed=True)
    widget = _build_widget(dependencies, _Recorder(), confirm_action=True)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.archive_decision_button.click()

    assert "(archived)" in widget.decisions_list.item(0).text()


@pytest.mark.gui
def test_view_decision_origin_shows_the_recorded_event(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    recorder = _Recorder()
    widget = _build_widget(dependencies, recorder)
    qtbot.addWidget(widget)
    widget.decisions_list.setCurrentRow(0)

    widget.decision_origin_button.click()

    assert len(recorder.informations) == 1
    assert "decision.proposed" in recorder.informations[0][1]


@pytest.mark.gui
def test_detect_conflicts_reports_none_when_precedence_is_unambiguous(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.detect_conflicts_button.click()

    assert widget.conflicts_list.count() == 0
    assert "No hay conflictos" in widget.conflicts_status_label.text()


@pytest.mark.gui
def test_detect_conflicts_lists_unresolved_conflicts_without_choosing_a_winner(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    project_id = dependencies.project_continuity_use_case.get_summary().project_id
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project_id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto", subject_key="Motor de persistencia", project_id=project_id
    )
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.detect_conflicts_button.click()

    assert widget.conflicts_list.count() == 1
    assert "Motor de persistencia" in widget.conflicts_list.item(0).text()
    assert "requieren aclaración" in widget.conflicts_status_label.text()


@pytest.mark.gui
def test_set_external_busy_disables_every_action_button(qtbot: QtBot, tmp_path: Path) -> None:
    dependencies = _bootstrapped_dependencies(tmp_path)
    widget = _build_widget(dependencies, _Recorder())
    qtbot.addWidget(widget)

    widget.set_external_busy(True)

    assert not widget.save_memory_button.isEnabled()
    assert not widget.propose_decision_button.isEnabled()
    assert not widget.detect_conflicts_button.isEnabled()

    widget.set_external_busy(False)

    assert widget.save_memory_button.isEnabled()
    assert widget.propose_decision_button.isEnabled()
    assert widget.detect_conflicts_button.isEnabled()
