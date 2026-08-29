"""GUI acceptance test for M6's manual flow (SIRIUS-ARQ-0.2 §3.6, §8-M6).

Over an already-completed conversation turn: click «Proponer guardar…» on
the Sirius message, see the suggestion appear in «Sugerencias pendientes»,
confirm it, and see it appear in the current memories of the same panel
after ``refresh()`` — all without ``SendMessageUseCase`` (nor its provider)
ever being invoked a second time, and without the first send ever getting
stuck.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import build_conversation_dependencies
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta
from sirius.presentation.main_window import MainWindow
from sirius.presentation.message_view import MessageItemWidget


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


class _CountingProvider:
    """A minimal ``LLMProvider`` that counts every call to ``stream_response``,
    so the test can assert ``SendMessageUseCase`` (and its provider) is
    invoked exactly once by the whole scenario — the manual propose/confirm
    flow never sends a second turn."""

    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.calls = 0

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        self.calls += 1
        yield LLMTextDelta(text=self._reply)
        yield LLMCompleted(text=self._reply, input_tokens=1, output_tokens=len(self._reply))

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _bootstrapped_database(database_path: Path) -> Path:
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="estado inicial",
        blockers=(),
        next_step="siguiente paso inicial",
    )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


class _PromptMultilineRecorder:
    """Spy for ``prompt_multiline_with_default`` that records the precharge
    argument (``initial``), so tests can assert MainWindow really precharges
    the dialog with the completed message's own content (SIRIUS-ARQ-0.2
    §3.6) — a fixed-return lambda would pass even if the precharge were
    empty, stale, or from a different message."""

    def __init__(self, response: str | None) -> None:
        self._response = response
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, title: str, label: str, initial: str) -> str | None:
        self.calls.append((title, label, initial))
        return self._response


def _build_window(
    database_path: Path, *, proposed_content: str | None
) -> tuple[MainWindow, _PromptMultilineRecorder]:
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    prompt_recorder = _PromptMultilineRecorder(proposed_content)
    window = MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        project_lifecycle_use_case=dependencies.project_lifecycle_use_case,
        save_manual_memory_use_case=dependencies.save_manual_memory_use_case,
        get_memory_origin_use_case=dependencies.get_memory_origin_use_case,
        correct_memory_use_case=dependencies.correct_memory_use_case,
        archive_memory_use_case=dependencies.archive_memory_use_case,
        delete_memory_use_case=dependencies.delete_memory_use_case,
        propose_decision_use_case=dependencies.propose_decision_use_case,
        approve_decision_use_case=dependencies.approve_decision_use_case,
        get_decision_origin_use_case=dependencies.get_decision_origin_use_case,
        supersede_decision_use_case=dependencies.supersede_decision_use_case,
        archive_decision_use_case=dependencies.archive_decision_use_case,
        detect_precedence_conflicts_use_case=dependencies.detect_precedence_conflicts_use_case,
        get_knowledge_overview_use_case=dependencies.get_knowledge_overview_use_case,
        propose_memory_suggestion_use_case=dependencies.propose_memory_suggestion_use_case,
        confirm_memory_suggestion_use_case=dependencies.confirm_memory_suggestion_use_case,
        reject_memory_suggestion_use_case=dependencies.reject_memory_suggestion_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        export_structured_use_case=dependencies.export_structured_use_case,
        historical_projects_use_case=dependencies.historical_projects_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
        # Same seam MainWindow's real dialog uses; the recorder confirms
        # with the message's own content (or None to simulate a cancel) and
        # records the precharge (``initial``) it received.
        prompt_multiline_with_default=prompt_recorder,
    )
    return window, prompt_recorder


def _sirius_widget(window: MainWindow) -> MessageItemWidget:
    item = window.message_list.item(1)
    widget = window.message_list.itemWidget(item)
    assert isinstance(widget, MessageItemWidget)
    return widget


@pytest.mark.gui
def test_manual_propose_confirm_flow_never_resends_or_blocks_the_first_turn(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window, prompt_recorder = _build_window(
        database_path, proposed_content="El usuario prefiere respuestas breves"
    )
    qtbot.addWidget(window)
    window.show()
    provider = _CountingProvider("Entendido.")
    window._send_message_use_case.set_llm_provider(provider)

    window.message_input.setText("recuerda que prefiero respuestas breves")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    assert provider.calls == 1
    assert window.message_list.count() == 2
    sirius_widget = _sirius_widget(window)
    assert sirius_widget.propose_suggestion_button().isVisible()

    sirius_widget.propose_suggestion_button().click()

    # El diálogo se precarga con el contenido real del mensaje de Sirius ya
    # completado ("Entendido."), no con un texto vacío, obsoleto o de otro
    # mensaje (SIRIUS-ARQ-0.2 §3.6): "editable antes de confirmar" presupone
    # que arranca con el contenido real.
    assert prompt_recorder.calls == [
        ("Proponer guardar…", "Contenido a proponer como recuerdo:", "Entendido.")
    ]

    assert window.knowledge_widget.suggestions_list.count() == 1
    assert (
        "El usuario prefiere respuestas breves"
        in window.knowledge_widget.suggestions_list.item(0).text()
    )
    assert window.knowledge_widget.memories_list.count() == 0

    window.knowledge_widget.suggestions_list.setCurrentRow(0)
    window.knowledge_widget.confirm_suggestion_button.click()

    assert window.knowledge_widget.suggestions_list.count() == 0
    assert window.knowledge_widget.memories_list.count() == 1
    assert (
        "El usuario prefiere respuestas breves"
        in window.knowledge_widget.memories_list.item(0).text()
    )

    # Ni una segunda invocación del envío ni un bloqueo de la primera: el
    # proveedor solo se llamó una vez, y el botón de enviar sigue disponible.
    assert provider.calls == 1
    assert window.send_button.isEnabled()
    assert window._is_sending is False


@pytest.mark.gui
def test_cancelling_the_propose_dialog_creates_no_suggestion(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window, _prompt_recorder = _build_window(database_path, proposed_content=None)
    qtbot.addWidget(window)

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    _sirius_widget(window).propose_suggestion_button().click()

    assert window.knowledge_widget.suggestions_list.count() == 0


@pytest.mark.gui
def test_propose_button_is_hidden_on_the_user_message(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window, _prompt_recorder = _build_window(database_path, proposed_content=None)
    qtbot.addWidget(window)
    window.show()

    window.message_input.setText("hola")
    window.send_button.click()
    qtbot.waitUntil(lambda: window.send_button.isEnabled(), timeout=5000)

    user_item = window.message_list.item(0)
    user_widget = window.message_list.itemWidget(user_item)
    assert isinstance(user_widget, MessageItemWidget)
    assert not user_widget.propose_suggestion_button().isVisible()
