"""pytest-qt tests for the "Exportar" action in "Configuración" (B9b/S12.1).

Mirrors ``test_backup_recovery_ui.py``: no test ever touches the real Windows
Credential Manager (``FakeSecretStore`` everywhere) or a real dialog/folder
picker (every seam is injected). Uses fake use cases for deterministic,
fast control over success/failure and over the "operation in progress"
window, without any arbitrary sleep.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

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
from sirius.ports.export import ExportError
from sirius.presentation.main_window import MainWindow


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    upgrade_to_head(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    try:
        conversation_repository.get_or_create_main_conversation()
    finally:
        conversation_repository.close()

    project_repository = build_sqlite_project_repository(database_path)
    try:
        project_repository.ensure_bootstrap_project()
    finally:
        project_repository.close()

    identity_repository = build_sqlite_identity_repository(database_path)
    try:
        identity_repository.get_or_create_current_identity()
    finally:
        identity_repository.close()

    return database_path


class _FakeExportStructuredUseCase:
    def __init__(self, result: Path | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.received: list[Path] = []

    def export_structured(self, destination_dir: Path) -> Path:
        self.received.append(destination_dir)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class _BlockingExportStructuredUseCase:
    """Blocks until the test calls ``release()``, for deterministic control
    over the "export in progress" window without any arbitrary sleep.
    """

    def __init__(self) -> None:
        self._continue_event = threading.Event()
        self._result: Path | None = None
        self.received: list[Path] = []

    def set_result(self, result: Path) -> None:
        self._result = result

    def release(self) -> None:
        self._continue_event.set()

    def export_structured(self, destination_dir: Path) -> Path:
        self.received.append(destination_dir)
        self._continue_event.wait(timeout=5)
        assert self._result is not None
        return self._result


def _build_window(
    database_path: Path,
    *,
    export_structured_use_case: Any = None,
    show_warning: Any = None,
    show_information: Any = None,
    confirm_export: Any = None,
    choose_export_directory: Any = None,
) -> MainWindow:
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    return MainWindow(
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
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        export_structured_use_case=export_structured_use_case
        or dependencies.export_structured_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=show_warning or (lambda title, text: None),
        show_information=show_information or (lambda title, text: None),
        # Destructive-by-default-no, like confirm_restore: a test that
        # forgets to inject this must not accidentally exercise the
        # confirmed path.
        confirm_export=confirm_export or (lambda title, text: False),
        choose_export_directory=choose_export_directory or (lambda title: ""),
    )


# --- Aviso previo (S12.1) ----------------------------------------------------


@pytest.mark.gui
def test_export_shows_the_personal_data_and_no_api_key_notice_before_exporting(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeExportStructuredUseCase()
    confirm_calls: list[tuple[str, str]] = []

    def _recording_confirm_export(title: str, text: str) -> bool:
        confirm_calls.append((title, text))
        return False

    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=_recording_confirm_export,
    )
    qtbot.addWidget(window)

    window.export_button.click()

    assert len(confirm_calls) == 1
    _title, text = confirm_calls[0]
    assert "personal" in text.lower()
    assert "clave" in text.lower() and "API" in text
    assert use_case.received == []


@pytest.mark.gui
def test_export_cancelled_at_the_notice_never_calls_the_use_case(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeExportStructuredUseCase()
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: False,
    )
    qtbot.addWidget(window)

    window.export_button.click()

    assert use_case.received == []


@pytest.mark.gui
def test_export_confirmed_but_no_folder_chosen_never_calls_the_use_case(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeExportStructuredUseCase()
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: "",
    )
    qtbot.addWidget(window)

    window.export_button.click()

    assert use_case.received == []


# --- Confirmar y ejecutar en segundo plano ----------------------------------


@pytest.mark.gui
def test_export_confirmed_calls_the_use_case_exactly_once_with_the_chosen_directory(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    created_dir = tmp_path / "sirius-export-20260722-1200"
    use_case = _FakeExportStructuredUseCase(result=created_dir)
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
    )
    qtbot.addWidget(window)

    window.export_button.click()

    qtbot.waitUntil(lambda: use_case.received != [], timeout=5000)
    assert use_case.received == [Path(tmp_path)]
    qtbot.waitUntil(lambda: window.export_button.isEnabled(), timeout=5000)


@pytest.mark.gui
def test_export_success_shows_the_exact_created_path(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    created_dir = tmp_path / "sirius-export-20260722-1200"
    use_case = _FakeExportStructuredUseCase(result=created_dir)
    infos: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
        show_information=lambda title, text: infos.append((title, text)),
    )
    qtbot.addWidget(window)

    window.export_button.click()

    qtbot.waitUntil(lambda: len(infos) == 1, timeout=5000)
    assert str(created_dir) in infos[0][1]


@pytest.mark.gui
def test_export_failure_shows_a_safe_message(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeExportStructuredUseCase(
        error=ExportError("no se pudo escribir en la carpeta seleccionada")
    )
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.export_button.click()

    qtbot.waitUntil(lambda: len(warnings) == 1, timeout=5000)
    assert "carpeta seleccionada" in warnings[0][1]
    qtbot.waitUntil(lambda: window.export_button.isEnabled(), timeout=5000)


@pytest.mark.gui
def test_export_unexpected_crash_shows_a_generic_safe_message(qtbot: QtBot, tmp_path: Path) -> None:
    """No internal exception detail may ever reach the user; also proves the
    worker's failure signal safely reaches the GUI thread.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")

    class _CrashingExportStructuredUseCase:
        def export_structured(self, destination_dir: Path) -> Path:
            del destination_dir
            msg = "boom - should never reach the user"
            raise RuntimeError(msg)

    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        export_structured_use_case=_CrashingExportStructuredUseCase(),
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.export_button.click()

    qtbot.waitUntil(lambda: len(warnings) == 1, timeout=5000)
    assert "boom" not in warnings[0][1]
    assert warnings[0][1] == "No se pudo completar la operación. Inténtalo de nuevo."
    qtbot.waitUntil(lambda: window.export_button.isEnabled(), timeout=5000)


# --- Exclusión mutua ---------------------------------------------------------


@pytest.mark.gui
def test_export_disables_send_and_backup_controls_while_running_and_reenables_after(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _BlockingExportStructuredUseCase()
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
    )
    qtbot.addWidget(window)

    window.export_button.click()
    qtbot.waitUntil(lambda: use_case.received != [], timeout=5000)

    assert window.export_button.isEnabled() is False
    assert window.send_button.isEnabled() is False
    assert window.create_backup_button.isEnabled() is False
    assert window.validate_backup_button.isEnabled() is False
    assert window.restore_backup_button.isEnabled() is False

    use_case.set_result(tmp_path / "sirius-export-20260722-1200")
    use_case.release()

    qtbot.waitUntil(lambda: window.export_button.isEnabled(), timeout=5000)
    assert window.send_button.isEnabled() is True
    assert window.create_backup_button.isEnabled() is True
    assert window.validate_backup_button.isEnabled() is True
    assert window.restore_backup_button.isEnabled() is True


@pytest.mark.gui
def test_export_is_blocked_while_a_message_is_sending(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeExportStructuredUseCase(result=tmp_path / "sirius-export-x")
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
    )
    qtbot.addWidget(window)

    window._is_sending = True  # simulate a message actively streaming

    window.export_button.click()

    assert use_case.received == []


@pytest.mark.gui
def test_export_is_blocked_while_a_backup_operation_is_busy(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeExportStructuredUseCase(result=tmp_path / "sirius-export-x")
    window = _build_window(
        database_path,
        export_structured_use_case=use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
    )
    qtbot.addWidget(window)

    window._is_backup_busy = True  # simulate a backup/restore in progress

    window.export_button.click()

    assert use_case.received == []


@pytest.mark.gui
def test_backup_operations_are_blocked_while_export_is_busy(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    export_use_case = _BlockingExportStructuredUseCase()
    window = _build_window(
        database_path,
        export_structured_use_case=export_use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
    )
    qtbot.addWidget(window)

    window.export_button.click()
    qtbot.waitUntil(lambda: export_use_case.received != [], timeout=5000)

    window.create_backup_password_input.setText("correct horse battery staple")
    window.create_backup_password_repeat_input.setText("correct horse battery staple")
    window.create_backup_button.click()

    assert window._is_backup_busy is False

    export_use_case.set_result(tmp_path / "sirius-export-20260722-1200")
    export_use_case.release()
    qtbot.waitUntil(lambda: window.export_button.isEnabled(), timeout=5000)


@pytest.mark.gui
def test_sending_is_blocked_while_export_is_busy(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    export_use_case = _BlockingExportStructuredUseCase()
    window = _build_window(
        database_path,
        export_structured_use_case=export_use_case,
        confirm_export=lambda title, text: True,
        choose_export_directory=lambda title: str(tmp_path),
    )
    qtbot.addWidget(window)

    window.export_button.click()
    qtbot.waitUntil(lambda: export_use_case.received != [], timeout=5000)

    window.message_input.setText("hola")
    window.send_button.click()

    assert window._is_sending is False

    export_use_case.set_result(tmp_path / "sirius-export-20260722-1200")
    export_use_case.release()
    qtbot.waitUntil(lambda: window.export_button.isEnabled(), timeout=5000)
