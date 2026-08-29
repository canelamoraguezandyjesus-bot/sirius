"""pytest-qt tests for the backup/recovery section of "Configuración".

No test ever touches the real Windows Credential Manager (``FakeSecretStore``
everywhere) or a real dialog/file picker (every seam is injected; the
autouse fixtures in ``tests/gui/conftest.py`` block the real Qt statics as a
backstop). Most scenarios use fake use cases for deterministic, fast control
over success/failure; a couple of end-to-end tests wire the real use cases
from ``composition_root`` to prove the whole cycle — including the
dispose-before-replace fix for Windows file locks — actually works together.
"""

from __future__ import annotations

import gc
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QTabWidget, QWidget
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
from sirius.ports.backup import (
    BackupError,
    BackupManifest,
    BackupRestoreError,
    BackupRestoreResult,
    BackupResult,
    BackupValidationError,
    BackupValidationResult,
)
from sirius.presentation.main_window import (
    BACKUP_STATE_CANCELLED,
    BACKUP_STATE_CREATED,
    BACKUP_STATE_PROPERTY,
    BACKUP_STATE_REJECTED,
    BACKUP_STATE_RESTORED,
    BACKUP_STATE_VALIDATED,
    MainWindow,
)

_PASSWORD = "correct horse battery staple"


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    """Mimic initialize_persistence(): real Alembic migrations (backup/restore
    reads ``alembic_version``, unlike the other GUI test suites' schema-only
    bootstrap) plus the three canonical singletons.

    Each repository is temporary and closed immediately after use, exactly
    like ``initialize_persistence()`` itself: left unclosed, its pooled
    connection is only reclaimed whenever the cyclic garbage collector
    happens to run, which is not guaranteed to happen before the real,
    same-process restore later replaces this exact database file — on
    Windows that stray open handle makes the atomic replace fail with
    ``PermissionError: [WinError 5] Acceso denegado``.
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
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


def test_bootstrapped_database_helper_leaves_no_connection_blocking_a_file_replace(
    tmp_path: Path,
) -> None:
    """Regression test for a real, reproducible flake: with a repository left
    for the garbage collector to close (instead of closed deterministically),
    an unrelated same-process ``os.replace()`` of this exact database file —
    such as the one a real restore performs — failed with
    ``PermissionError: [WinError 5] Acceso denegado`` on Windows, because the
    stray pooled connection is only reclaimed whenever the cyclic garbage
    collector happens to run next, which depends on unrelated allocations
    elsewhere in the same pytest process. ``gc.disable()`` removes that
    process-wide luck factor so this test fails deterministically without the
    fix instead of only intermittently. Exercises the same file-replace
    Windows uses to enforce open-handle exclusion that a real restore relies
    on, without any Qt/thread timing.
    """
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        database_path = _bootstrapped_database(tmp_path / "sirius.db")
        replacement = tmp_path / "sirius.db.replacement"
        replacement.write_bytes(database_path.read_bytes())

        os.replace(replacement, database_path)
    finally:
        if gc_was_enabled:
            gc.enable()


def _fake_manifest(**overrides: Any) -> BackupManifest:
    defaults: dict[str, Any] = {
        "format": "siriusbackup",
        "app_version": "0.1.0.dev0",
        "schema_version": "abc123",
        "created_at": datetime(2026, 7, 1, tzinfo=UTC),
        "sha256": "0" * 64,
    }
    defaults.update(overrides)
    return BackupManifest(**defaults)


def _fake_backup_result(path: Path) -> BackupResult:
    return BackupResult(path=path, manifest=_fake_manifest(), size_bytes=2048)


def _fake_validation_result(path: Path) -> BackupValidationResult:
    return BackupValidationResult(path=path, manifest=_fake_manifest(), size_bytes=2048)


def _fake_restore_result(path: Path, safety_backup_path: Path | None) -> BackupRestoreResult:
    return BackupRestoreResult(
        path=path, manifest=_fake_manifest(), size_bytes=2048, safety_backup_path=safety_backup_path
    )


class _FakeCreateBackupUseCase:
    def __init__(self, result: BackupResult | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.received_passwords: list[str] = []

    def create_backup(self, password: str) -> BackupResult:
        self.received_passwords.append(password)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class _BlockingCreateBackupUseCase:
    """Blocks until the test calls ``release()``, for deterministic control
    over the "operation in progress" window without any arbitrary sleep.
    """

    def __init__(self) -> None:
        import threading

        self._continue_event = threading.Event()
        self._result: BackupResult | None = None
        self.received_passwords: list[str] = []

    def set_result(self, result: BackupResult) -> None:
        self._result = result

    def release(self) -> None:
        self._continue_event.set()

    def create_backup(self, password: str) -> BackupResult:
        self.received_passwords.append(password)
        self._continue_event.wait(timeout=5)
        assert self._result is not None
        return self._result


class _FakeValidateBackupUseCase:
    def __init__(
        self, result: BackupValidationResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result
        self._error = error
        self.received: list[tuple[Path, str]] = []

    def validate_backup(self, backup_path: Path, password: str) -> BackupValidationResult:
        self.received.append((backup_path, password))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class _BlockingValidateBackupUseCase:
    """Blocks until the test calls ``release()``, mirroring
    ``_BlockingCreateBackupUseCase`` but for the pre-validation step of a
    restore, so tests can deterministically observe "validation in progress".
    """

    def __init__(self) -> None:
        import threading

        self._continue_event = threading.Event()
        self._result: BackupValidationResult | None = None
        self.received: list[tuple[Path, str]] = []

    def set_result(self, result: BackupValidationResult) -> None:
        self._result = result

    def release(self) -> None:
        self._continue_event.set()

    def validate_backup(self, backup_path: Path, password: str) -> BackupValidationResult:
        self.received.append((backup_path, password))
        self._continue_event.wait(timeout=5)
        assert self._result is not None
        return self._result


class _FakeRestoreBackupUseCase:
    def __init__(
        self, result: BackupRestoreResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[tuple[Path, str, bool]] = []

    def restore_backup(
        self, backup_path: Path, password: str, *, confirmed: bool
    ) -> BackupRestoreResult:
        self.calls.append((backup_path, password, confirmed))
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _build_window(
    database_path: Path,
    *,
    create_backup_use_case: Any = None,
    validate_backup_use_case: Any = None,
    restore_backup_use_case: Any = None,
    close_database_connections: Any = None,
    show_warning: Any = None,
    show_information: Any = None,
    confirm_restore: Any = None,
    choose_backup_file: Any = None,
    open_containing_folder: Any = None,
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
        create_backup_use_case=create_backup_use_case or dependencies.create_backup_use_case,
        validate_backup_use_case=validate_backup_use_case or dependencies.validate_backup_use_case,
        restore_backup_use_case=restore_backup_use_case or dependencies.restore_backup_use_case,
        export_structured_use_case=dependencies.export_structured_use_case,
        historical_projects_use_case=dependencies.historical_projects_use_case,
        close_database_connections=close_database_connections
        or dependencies.close_database_connections,
        show_warning=show_warning or (lambda title, text: None),
        show_information=show_information or (lambda title, text: None),
        # Destructive by default must default to "no": a test that forgets to
        # inject this must not accidentally exercise the confirmed path.
        confirm_restore=confirm_restore or (lambda title, text: False),
        choose_backup_file=choose_backup_file or (lambda title: ""),
        open_containing_folder=open_containing_folder or (lambda path: None),
    )


# --- Crear copia -----------------------------------------------------------


@pytest.mark.gui
def test_create_backup_rejects_an_empty_password_without_calling_the_use_case(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeCreateBackupUseCase()
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        create_backup_use_case=use_case,
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.create_backup_button.click()

    assert use_case.received_passwords == []
    assert len(warnings) == 1


@pytest.mark.gui
def test_create_backup_rejects_mismatched_passwords_without_calling_the_use_case(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeCreateBackupUseCase()
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        create_backup_use_case=use_case,
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.create_backup_password_input.setText("clave-uno")
    window.create_backup_password_repeat_input.setText("clave-dos")
    window.create_backup_button.click()

    assert use_case.received_passwords == []
    assert len(warnings) == 1


@pytest.mark.gui
def test_create_backup_never_keeps_the_password_in_the_fields(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeCreateBackupUseCase(result=_fake_backup_result(tmp_path / "b.siriusbackup"))
    window = _build_window(database_path, create_backup_use_case=use_case)
    qtbot.addWidget(window)

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    assert window.create_backup_password_input.text() == ""
    assert window.create_backup_password_repeat_input.text() == ""
    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=5000)


@pytest.mark.gui
def test_create_backup_disables_controls_while_running_and_reenables_after_success(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _BlockingCreateBackupUseCase()
    window = _build_window(database_path, create_backup_use_case=use_case)
    qtbot.addWidget(window)

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    assert window.create_backup_button.isEnabled() is False
    assert window.validate_backup_button.isEnabled() is False
    assert window.restore_backup_button.isEnabled() is False
    assert window.send_button.isEnabled() is False
    assert window.create_backup_status_label.text() != ""

    use_case.set_result(_fake_backup_result(tmp_path / "b.siriusbackup"))
    use_case.release()

    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=5000)
    assert window.validate_backup_button.isEnabled() is True
    assert window.restore_backup_button.isEnabled() is True
    assert window.send_button.isEnabled() is True


@pytest.mark.gui
def test_create_backup_success_shows_the_exact_backup_path(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "sirius-backup-x.siriusbackup"
    use_case = _FakeCreateBackupUseCase(result=_fake_backup_result(backup_path))
    infos: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        create_backup_use_case=use_case,
        show_information=lambda title, text: infos.append((title, text)),
    )
    qtbot.addWidget(window)

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    qtbot.waitUntil(lambda: len(infos) == 1, timeout=5000)
    assert str(backup_path) in infos[0][1]


@pytest.mark.gui
def test_create_backup_failure_shows_a_safe_message(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeCreateBackupUseCase(error=BackupError("la copia supera el límite de 100 MB"))
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        create_backup_use_case=use_case,
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    qtbot.waitUntil(lambda: len(warnings) == 1, timeout=5000)
    assert "100 MB" in warnings[0][1]


@pytest.mark.gui
def test_create_backup_unexpected_crash_shows_a_generic_safe_message(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """No internal exception detail (or traceback) may ever reach the user;
    also proves the worker's failure signal safely reaches the GUI thread.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")

    class _CrashingCreateBackupUseCase:
        def create_backup(self, password: str) -> BackupResult:
            del password
            msg = "boom - should never reach the user"
            raise RuntimeError(msg)

    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        create_backup_use_case=_CrashingCreateBackupUseCase(),
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    qtbot.waitUntil(lambda: len(warnings) == 1, timeout=5000)
    assert "boom" not in warnings[0][1]
    assert warnings[0][1] == "No se pudo completar la operación. Inténtalo de nuevo."
    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=5000)


@pytest.mark.gui
def test_backup_operations_are_blocked_while_a_message_is_sending(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeCreateBackupUseCase(result=_fake_backup_result(tmp_path / "b.siriusbackup"))
    window = _build_window(database_path, create_backup_use_case=use_case)
    qtbot.addWidget(window)

    window._is_sending = True  # simulate a message actively streaming

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    assert use_case.received_passwords == []


# --- Estructura de la pestaña "Configuración" -------------------------------


@pytest.mark.gui
def test_settings_tab_is_a_resizable_scroll_area_reaching_the_restore_section(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """The backup/recovery section must live inside the existing
    "Configuración" tab (no new screen) and stay reachable, by mouse and by
    keyboard, inside the default 900x620 window.

    Deliberately structural, not behavioural: this asserts the static
    widget tree and Tab-order chain that Qt builds at construction time, so
    it needs no ``show()``, no real OS-level focus (which the previous
    version waited on via ``waitUntil``/``hasFocus()`` and which is
    unreliable — often outright unavailable — for an unfocused/offscreen
    window in headless CI), and no event-loop timeout.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.size().width() == 900
    assert window.size().height() == 620

    tabs = window.tabs
    assert isinstance(tabs, QTabWidget)
    assert tabs.tabText(2) == "Configuración"
    settings_page = tabs.widget(2)
    assert isinstance(settings_page, QScrollArea)
    assert settings_page.widgetResizable() is True

    scrolled_widget = settings_page.widget()
    restore_controls = [
        window.restore_backup_path_input,
        window.restore_backup_browse_button,
        window.restore_backup_password_input,
        window.restore_backup_button,
    ]
    for control in restore_controls:
        assert control.isEnabled()
        assert _is_descendant(control, scrolled_widget)
        # TabFocus is the bit shared by every keyboard-reachable policy
        # (TabFocus, StrongFocus, WheelFocus) but absent from ClickFocus and
        # NoFocus: a purely structural stand-in for "can Tab reach this?".
        assert control.focusPolicy() & Qt.FocusPolicy.TabFocus

    # Deterministic focus-chain reachability: walk QWidget's own Tab-order
    # linked list (built at construction time, independent of visibility)
    # forward from an earlier Configuración control until a restore control
    # is found or the chain cycles back on itself.
    node: QWidget | None = window.validate_backup_button
    visited_ids = {id(node)}
    restore_control_ids = {id(control) for control in restore_controls}
    reached_restore_section = False
    for _ in range(500):
        if node is None:
            break
        node = node.nextInFocusChain()
        if node is None:
            break
        if id(node) in restore_control_ids:
            reached_restore_section = True
            break
        if id(node) in visited_ids:
            break
        visited_ids.add(id(node))
    assert reached_restore_section


def _is_descendant(widget: Any, ancestor: Any) -> bool:
    parent = widget.parent()
    while parent is not None:
        if parent is ancestor:
            return True
        parent = parent.parent()
    return False


# --- Validar copia -----------------------------------------------------------


@pytest.mark.gui
def test_validate_backup_shows_the_summary_for_a_valid_backup(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    window = _build_window(database_path, validate_backup_use_case=use_case)
    qtbot.addWidget(window)

    window.validate_backup_path_input.setText(str(backup_path))
    window.validate_backup_password_input.setText(_PASSWORD)
    window.validate_backup_button.click()

    qtbot.waitUntil(
        lambda: "0.1.0.dev0" in window.validate_backup_result_label.text(), timeout=5000
    )
    summary = window.validate_backup_result_label.text()
    assert "0.1.0.dev0" in summary
    assert "abc123" in summary
    assert "2,048" in summary
    assert use_case.received == [(backup_path, _PASSWORD)]
    assert window.validate_backup_password_input.text() == ""


@pytest.mark.gui
def test_validate_backup_shows_a_safe_error_message_for_an_invalid_backup(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _FakeValidateBackupUseCase(
        error=BackupValidationError("la contraseña es incorrecta o la copia está dañada")
    )
    window = _build_window(database_path, validate_backup_use_case=use_case)
    qtbot.addWidget(window)

    window.validate_backup_path_input.setText(str(tmp_path / "b.siriusbackup"))
    window.validate_backup_password_input.setText("clave-incorrecta")
    window.validate_backup_button.click()

    qtbot.waitUntil(
        lambda: "incorrecta" in window.validate_backup_result_label.text(), timeout=5000
    )
    assert "incorrecta" in window.validate_backup_result_label.text()


# --- Restaurar copia -----------------------------------------------------------


@pytest.mark.gui
def test_restore_backup_requires_a_file_and_a_password(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    restore_use_case = _FakeRestoreBackupUseCase()
    validate_use_case = _FakeValidateBackupUseCase()
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        restore_backup_use_case=restore_use_case,
        validate_backup_use_case=validate_use_case,
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.restore_backup_button.click()

    assert len(warnings) == 1
    assert restore_use_case.calls == []
    assert validate_use_case.received == []


@pytest.mark.gui
def test_restore_backup_cancelled_at_confirmation_never_calls_restore(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    validate_use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    restore_use_case = _FakeRestoreBackupUseCase()
    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=restore_use_case,
        confirm_restore=lambda title, text: False,
    )
    qtbot.addWidget(window)

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: window.restore_backup_feedback_label.text() != "", timeout=5000)
    assert restore_use_case.calls == []
    assert "cancel" in window.restore_backup_feedback_label.text().lower()
    assert window.restore_backup_button.isEnabled() is True


@pytest.mark.gui
def test_restore_backup_confirmed_calls_restore_exactly_once_with_confirmed_true(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    safety_path = tmp_path / "backups" / "safety.siriusbackup"
    validate_use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    restore_use_case = _FakeRestoreBackupUseCase(
        result=_fake_restore_result(backup_path, safety_path)
    )
    close_calls: list[bool] = []
    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=restore_use_case,
        confirm_restore=lambda title, text: True,
        close_database_connections=lambda: close_calls.append(True),
    )
    qtbot.addWidget(window)
    window.show()

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: restore_use_case.calls != [], timeout=5000)
    assert restore_use_case.calls == [(backup_path, _PASSWORD, True)]
    assert close_calls == [True]


@pytest.mark.gui
def test_restore_backup_disposes_connections_before_calling_restore(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """The order matters: connections must be released before the atomic
    file replace, or it fails on Windows with an open pooled connection.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    order: list[str] = []

    class _OrderedRestoreBackupUseCase:
        def restore_backup(
            self, backup_path: Path, password: str, *, confirmed: bool
        ) -> BackupRestoreResult:
            del password, confirmed
            order.append("restore")
            return _fake_restore_result(backup_path, None)

    validate_use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=_OrderedRestoreBackupUseCase(),
        confirm_restore=lambda title, text: True,
        close_database_connections=lambda: order.append("close"),
    )
    qtbot.addWidget(window)
    window.show()

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: "restore" in order, timeout=5000)
    assert order == ["close", "restore"]


@pytest.mark.gui
def test_restore_backup_success_shows_safety_path_and_closes_the_window(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    safety_path = tmp_path / "backups" / "safety.siriusbackup"
    validate_use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    restore_use_case = _FakeRestoreBackupUseCase(
        result=_fake_restore_result(backup_path, safety_path)
    )
    infos: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=restore_use_case,
        confirm_restore=lambda title, text: True,
        close_database_connections=lambda: None,
        show_information=lambda title, text: infos.append((title, text)),
    )
    qtbot.addWidget(window)
    window.show()

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5000)
    assert len(infos) == 1
    assert str(safety_path) in infos[0][1]
    assert "cerrará" in infos[0][1].lower()


@pytest.mark.gui
def test_restore_backup_failure_shows_a_safe_message_and_keeps_the_window_open(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    validate_use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    restore_use_case = _FakeRestoreBackupUseCase(
        error=BackupRestoreError(
            "La base restaurada no superó la validación posterior; "
            "se revirtió automáticamente al estado anterior."
        )
    )
    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=restore_use_case,
        confirm_restore=lambda title, text: True,
        close_database_connections=lambda: None,
    )
    qtbot.addWidget(window)
    window.show()

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: window.restore_backup_feedback_label.text() != "", timeout=5000)
    assert "revirtió" in window.restore_backup_feedback_label.text()
    assert window.isVisible() is True
    assert window.restore_backup_button.isEnabled() is True


@pytest.mark.gui
def test_restore_backup_path_fields_are_disabled_while_pre_validation_is_in_progress(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Neither path field may be edited while the pre-restore validation
    (which already read the currently displayed path) is still running.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    validate_use_case = _BlockingValidateBackupUseCase()
    window = _build_window(database_path, validate_backup_use_case=validate_use_case)
    qtbot.addWidget(window)

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: validate_use_case.received != [], timeout=5000)
    assert window.restore_backup_path_input.isEnabled() is False
    assert window.validate_backup_path_input.isEnabled() is False

    validate_use_case.set_result(_fake_validation_result(backup_path))
    validate_use_case.release()

    qtbot.waitUntil(lambda: window.restore_backup_button.isEnabled(), timeout=5000)
    assert window.restore_backup_path_input.isEnabled() is True
    assert window.validate_backup_path_input.isEnabled() is True


@pytest.mark.gui
def test_closing_during_a_blocked_pre_restore_validation_never_confirms_or_restores(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    validate_use_case = _BlockingValidateBackupUseCase()
    restore_use_case = _FakeRestoreBackupUseCase()
    confirm_calls: list[tuple[str, str]] = []

    def _recording_confirm_restore(title: str, text: str) -> bool:
        confirm_calls.append((title, text))
        return True

    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=restore_use_case,
        confirm_restore=_recording_confirm_restore,
    )
    qtbot.addWidget(window)
    window.show()

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()
    qtbot.waitUntil(lambda: validate_use_case.received != [], timeout=5000)

    window.close()  # must defer, not block, while the validation is in flight
    assert window.isVisible() is True

    validate_use_case.set_result(_fake_validation_result(backup_path))
    validate_use_case.release()

    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5000)
    assert confirm_calls == []
    assert restore_use_case.calls == []


@pytest.mark.gui
def test_restore_backup_never_calls_restore_if_closing_connections_fails(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    validate_use_case = _FakeValidateBackupUseCase(result=_fake_validation_result(backup_path))
    restore_use_case = _FakeRestoreBackupUseCase(result=_fake_restore_result(backup_path, None))

    def _broken_close() -> None:
        msg = "simulated failure disposing the connection pools"
        raise RuntimeError(msg)

    window = _build_window(
        database_path,
        validate_backup_use_case=validate_use_case,
        restore_backup_use_case=restore_use_case,
        confirm_restore=lambda title, text: True,
        close_database_connections=_broken_close,
    )
    qtbot.addWidget(window)
    window.show()

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: window.restore_backup_feedback_label.text() != "", timeout=5000)
    assert restore_use_case.calls == []
    assert "simulated failure" not in window.restore_backup_feedback_label.text()
    assert window.isVisible() is True
    assert window.restore_backup_button.isEnabled() is True


@pytest.mark.gui
def test_a_pending_close_after_create_backup_succeeds_shows_no_new_dialog(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    use_case = _BlockingCreateBackupUseCase()
    infos: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        create_backup_use_case=use_case,
        show_information=lambda title, text: infos.append((title, text)),
    )
    qtbot.addWidget(window)
    window.show()

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()
    qtbot.waitUntil(lambda: use_case.received_passwords != [], timeout=5000)

    window.close()  # deferred: an operation is still in progress
    assert window.isVisible() is True

    use_case.set_result(_fake_backup_result(tmp_path / "b.siriusbackup"))
    use_case.release()

    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5000)
    assert infos == []


# --- Integración real de extremo a extremo ------------------------------------


@pytest.mark.gui
def test_create_then_validate_then_restore_a_real_backup_end_to_end(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """One continuous real flow (create -> validate -> restore) through the
    actual use cases wired by ``composition_root``, proving the whole cycle
    — including the dispose-before-replace fix for Windows file locks —
    genuinely works together, not just against fakes. Kept as a single test
    (rather than one real end-to-end test per flow) because two separate
    real, Argon2id-backed ``MainWindow``/``QThreadPool`` instances running
    back-to-back in the same pytest process were observed to make the
    second one's worker thread hang; a single continuous flow does not.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    infos: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        confirm_restore=lambda title, text: True,
        show_information=lambda title, text: infos.append((title, text)),
    )
    qtbot.addWidget(window)
    window.show()

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()
    qtbot.waitUntil(lambda: window.create_backup_button.isEnabled(), timeout=30000)

    created_files = list((database_path.parent / "backups").glob("*.siriusbackup"))
    assert len(created_files) == 1
    backup_path = created_files[0]

    window.validate_backup_path_input.setText(str(backup_path))
    window.validate_backup_password_input.setText(_PASSWORD)
    window.validate_backup_button.click()
    qtbot.waitUntil(lambda: "Esquema" in window.validate_backup_result_label.text(), timeout=30000)

    window.restore_backup_path_input.setText(str(backup_path))
    window.restore_backup_password_input.setText(_PASSWORD)
    window.restore_backup_button.click()

    qtbot.waitUntil(lambda: not window.isVisible(), timeout=30000)
    # Un aviso por paso, en orden: la copia creada (con su ruta), la copia
    # validada y la restauración terminada.
    assert [title for title, _text in infos] == [
        "Copia creada",
        "Copia validada",
        "Restauración completada",
    ]
    assert str(backup_path) in infos[0][1]
    assert "cerrará" in infos[-1][1].lower()


# --- Feedback visible de las copias -----------------------------------------
#
# El defecto: "Validar copia" no confirmaba nada con la contraseña correcta ni
# avisaba con la incorrecta, y "Restaurar copia" rechazaba la contraseña
# equivocada en silencio. Las etiquetas SÍ se escribían; lo que fallaba es que
# están al final de una pestaña más alta que la ventana (900x620), de modo que
# el resultado de validar quedaba cortado por la mitad en el borde inferior y
# el de restaurar caía entero fuera del área visible. Medido antes de la
# corrección: la etiqueta de restauración tenía la región visible VACÍA.
#
# Por eso estas pruebas comprueban dos cosas distintas y las dos importan: que
# el estado del desenlace sea el correcto y esté diferenciado, y que el texto
# se pueda ver de verdad sin que la persona tenga que desplazarse a buscarlo.


def _shown_settings_window(qtbot: QtBot, window: MainWindow) -> MainWindow:
    """La ventana real, a su tamaño por omisión, con Configuración delante."""
    qtbot.addWidget(window)
    window.show()
    tabs = window.tabs
    assert isinstance(tabs, QTabWidget)
    tabs.setCurrentIndex(2)
    qtbot.waitUntil(lambda: window.validate_backup_button.width() > 0, timeout=5000)
    return window


def _is_fully_visible(label: QLabel) -> bool:
    """¿Se ve la etiqueta ENTERA, sin que nadie tenga que desplazarse?

    ``visibleRegion`` devuelve la parte del widget que no está recortada por
    sus ancestros —aquí, el área de desplazamiento de la pestaña—. Vacía
    significa "fuera de la vista"; más baja que el widget, "cortada".
    """
    QApplication.processEvents()
    region = label.visibleRegion()
    return not region.isEmpty() and region.boundingRect().height() >= label.height()


@pytest.mark.gui
def test_a_valid_backup_is_confirmed_explicitly_and_the_confirmation_is_visible(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """El resumen por sí solo no confirma nada: enumera fecha, versión y
    tamaño, datos ante los cuales no se distingue "válida" de "no ha pasado
    nada". Hace falta decirlo, y que se vea.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"
    infos: list[tuple[str, str]] = []
    window = _shown_settings_window(
        qtbot,
        _build_window(
            database_path,
            validate_backup_use_case=_FakeValidateBackupUseCase(
                result=_fake_validation_result(backup_path)
            ),
            show_information=lambda title, text: infos.append((title, text)),
        ),
    )

    window.validate_backup_path_input.setText(str(backup_path))
    window.validate_backup_password_input.setText(_PASSWORD)
    window.validate_backup_button.click()

    label = window.validate_backup_result_label
    qtbot.waitUntil(lambda: label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_VALIDATED)

    assert "validada" in label.text().lower()
    # El resumen sigue estando: la confirmación se añade, no sustituye.
    assert "0.1.0.dev0" in label.text()
    assert "abc123" in label.text()
    assert _is_fully_visible(label), (
        "la confirmación se escribió fuera del área visible: es exactamente el "
        "defecto por el que validar parecía no hacer nada"
    )
    assert len(infos) == 1
    assert "validada" in infos[0][0].lower()


@pytest.mark.gui
def test_a_wrong_password_when_validating_is_reported_as_rejected_and_is_visible(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    warnings: list[tuple[str, str]] = []
    window = _shown_settings_window(
        qtbot,
        _build_window(
            database_path,
            validate_backup_use_case=_FakeValidateBackupUseCase(
                error=BackupValidationError("la contraseña es incorrecta o la copia está dañada")
            ),
            show_warning=lambda title, text: warnings.append((title, text)),
        ),
    )

    window.validate_backup_path_input.setText(str(tmp_path / "b.siriusbackup"))
    window.validate_backup_password_input.setText("clave-incorrecta")
    window.validate_backup_button.click()

    label = window.validate_backup_result_label
    qtbot.waitUntil(lambda: label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_REJECTED)

    assert "incorrecta" in label.text()
    assert _is_fully_visible(label)
    assert len(warnings) == 1
    assert "incorrecta" in warnings[0][1]


@pytest.mark.gui
def test_validating_never_leaves_success_and_failure_looking_the_same(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """El síntoma literal del informe: "el comportamiento visible es idéntico
    en ambos casos". Aquí se comparan los dos desenlaces uno contra otro.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "b.siriusbackup"

    valid_window = _shown_settings_window(
        qtbot,
        _build_window(
            database_path,
            validate_backup_use_case=_FakeValidateBackupUseCase(
                result=_fake_validation_result(backup_path)
            ),
        ),
    )
    valid_window.validate_backup_path_input.setText(str(backup_path))
    valid_window.validate_backup_password_input.setText(_PASSWORD)
    valid_window.validate_backup_button.click()
    valid_label = valid_window.validate_backup_result_label
    qtbot.waitUntil(lambda: valid_label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_VALIDATED)

    rejected_window = _shown_settings_window(
        qtbot,
        _build_window(
            _bootstrapped_database(tmp_path / "otra" / "sirius.db"),
            validate_backup_use_case=_FakeValidateBackupUseCase(
                error=BackupValidationError("la contraseña es incorrecta")
            ),
        ),
    )
    rejected_window.validate_backup_path_input.setText(str(backup_path))
    rejected_window.validate_backup_password_input.setText("mal")
    rejected_window.validate_backup_button.click()
    rejected_label = rejected_window.validate_backup_result_label
    qtbot.waitUntil(lambda: rejected_label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_REJECTED)

    assert valid_label.text() != rejected_label.text()
    assert valid_label.property(BACKUP_STATE_PROPERTY) != rejected_label.property(
        BACKUP_STATE_PROPERTY
    )
    # Ni siquiera el color coincide: se distinguen sin leer.
    assert valid_label.styleSheet() != rejected_label.styleSheet()


@pytest.mark.gui
def test_a_wrong_password_when_restoring_warns_instead_of_doing_nothing(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Que la restauración no se ejecute es correcto; hacerlo en silencio no.

    Antes de la corrección el mensaje se escribía en una etiqueta cuya región
    visible estaba vacía: la persona solo percibía que "no pasa nada".
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    restore_use_case = _FakeRestoreBackupUseCase()
    warnings: list[tuple[str, str]] = []
    window = _shown_settings_window(
        qtbot,
        _build_window(
            database_path,
            validate_backup_use_case=_FakeValidateBackupUseCase(
                error=BackupValidationError("la contraseña es incorrecta o la copia está dañada")
            ),
            restore_backup_use_case=restore_use_case,
            show_warning=lambda title, text: warnings.append((title, text)),
        ),
    )

    window.restore_backup_path_input.setText(str(tmp_path / "b.siriusbackup"))
    window.restore_backup_password_input.setText("clave-incorrecta")
    window.restore_backup_button.click()

    label = window.restore_backup_feedback_label
    qtbot.waitUntil(lambda: label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_REJECTED)

    assert restore_use_case.calls == []
    assert "incorrecta" in label.text()
    assert _is_fully_visible(label), (
        "el aviso quedó fuera del área visible: es el defecto por el que "
        "restaurar con la contraseña equivocada parecía no hacer nada"
    )
    assert len(warnings) == 1
    assert "incorrecta" in warnings[0][1]


@pytest.mark.gui
def test_the_four_backup_outcomes_stay_distinguishable(qtbot: QtBot, tmp_path: Path) -> None:
    """validada, restaurada, cancelada y rechazada son cuatro cosas distintas.

    Se recogen los cuatro estados tal y como los deja la interfaz y se exige
    que no se solapen: sin esto, "cancelada" y "rechazada" acaban contándose
    como el mismo "no se hizo nada".
    """
    backup_path = tmp_path / "b.siriusbackup"
    observed: dict[str, str] = {}

    validating = _shown_settings_window(
        qtbot,
        _build_window(
            _bootstrapped_database(tmp_path / "validar" / "sirius.db"),
            validate_backup_use_case=_FakeValidateBackupUseCase(
                result=_fake_validation_result(backup_path)
            ),
        ),
    )
    validating.validate_backup_path_input.setText(str(backup_path))
    validating.validate_backup_password_input.setText(_PASSWORD)
    validating.validate_backup_button.click()
    qtbot.waitUntil(
        lambda: (
            validating.validate_backup_result_label.property(BACKUP_STATE_PROPERTY)
            == BACKUP_STATE_VALIDATED
        )
    )
    observed["validada"] = validating.validate_backup_result_label.text()

    cancelling = _shown_settings_window(
        qtbot,
        _build_window(
            _bootstrapped_database(tmp_path / "cancelar" / "sirius.db"),
            validate_backup_use_case=_FakeValidateBackupUseCase(
                result=_fake_validation_result(backup_path)
            ),
            restore_backup_use_case=_FakeRestoreBackupUseCase(),
            confirm_restore=lambda title, text: False,
        ),
    )
    cancelling.restore_backup_path_input.setText(str(backup_path))
    cancelling.restore_backup_password_input.setText(_PASSWORD)
    cancelling.restore_backup_button.click()
    cancelled_label = cancelling.restore_backup_feedback_label
    qtbot.waitUntil(
        lambda: cancelled_label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_CANCELLED
    )
    observed["cancelada"] = cancelled_label.text()
    assert _is_fully_visible(cancelled_label)

    rejecting = _shown_settings_window(
        qtbot,
        _build_window(
            _bootstrapped_database(tmp_path / "rechazar" / "sirius.db"),
            validate_backup_use_case=_FakeValidateBackupUseCase(
                error=BackupValidationError("la contraseña es incorrecta")
            ),
            restore_backup_use_case=_FakeRestoreBackupUseCase(),
        ),
    )
    rejecting.restore_backup_path_input.setText(str(backup_path))
    rejecting.restore_backup_password_input.setText("mal")
    rejecting.restore_backup_button.click()
    rejected_label = rejecting.restore_backup_feedback_label
    qtbot.waitUntil(lambda: rejected_label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_REJECTED)
    observed["rechazada"] = rejected_label.text()

    restoring = _shown_settings_window(
        qtbot,
        _build_window(
            _bootstrapped_database(tmp_path / "restaurar" / "sirius.db"),
            validate_backup_use_case=_FakeValidateBackupUseCase(
                result=_fake_validation_result(backup_path)
            ),
            restore_backup_use_case=_FakeRestoreBackupUseCase(
                result=_fake_restore_result(backup_path, None)
            ),
            confirm_restore=lambda title, text: True,
        ),
    )
    restored_label = restoring.restore_backup_feedback_label
    restoring.restore_backup_path_input.setText(str(backup_path))
    restoring.restore_backup_password_input.setText(_PASSWORD)
    restoring.restore_backup_button.click()
    qtbot.waitUntil(lambda: restored_label.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_RESTORED)
    observed["restaurada"] = restored_label.text()

    assert set(observed) == {"validada", "cancelada", "rechazada", "restaurada"}
    assert len(set(observed.values())) == 4, f"desenlaces indistinguibles: {observed}"
    for state, text in observed.items():
        assert state in text.lower(), f"el texto de «{state}» no dice en qué estado quedó: {text!r}"


# --- La ruta de la copia creada ---------------------------------------------


@pytest.mark.gui
def test_creating_a_backup_shows_its_full_path_and_offers_the_folder_and_reuse(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "backups" / "sirius-20260701.siriusbackup"
    opened: list[Path] = []
    window = _shown_settings_window(
        qtbot,
        _build_window(
            database_path,
            create_backup_use_case=_FakeCreateBackupUseCase(
                result=_fake_backup_result(backup_path)
            ),
            open_containing_folder=opened.append,
        ),
    )

    # Sin copia creada todavía no hay carpeta que abrir ni ruta que reusar.
    assert window.open_backup_folder_button.isEnabled() is False
    assert window.use_last_backup_button.isEnabled() is False

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()

    status = window.create_backup_status_label
    qtbot.waitUntil(lambda: status.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_CREATED)

    assert str(backup_path) in window.create_backup_path_label.text()
    assert _is_fully_visible(window.create_backup_path_label)
    assert window.open_backup_folder_button.isEnabled() is True
    assert window.use_last_backup_button.isEnabled() is True

    window.open_backup_folder_button.click()
    assert opened == [backup_path]

    window.use_last_backup_button.click()
    assert window.validate_backup_path_input.text() == str(backup_path)
    assert window.restore_backup_path_input.text() == str(backup_path)


@pytest.mark.gui
def test_the_created_path_stays_selectable_so_it_can_be_copied(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """El aviso modal se cierra; la ruta tiene que seguir ahí y poder copiarse."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    backup_path = tmp_path / "backups" / "sirius-20260701.siriusbackup"
    window = _shown_settings_window(
        qtbot,
        _build_window(
            database_path,
            create_backup_use_case=_FakeCreateBackupUseCase(
                result=_fake_backup_result(backup_path)
            ),
        ),
    )

    window.create_backup_password_input.setText(_PASSWORD)
    window.create_backup_password_repeat_input.setText(_PASSWORD)
    window.create_backup_button.click()
    status = window.create_backup_status_label
    qtbot.waitUntil(lambda: status.property(BACKUP_STATE_PROPERTY) == BACKUP_STATE_CREATED)

    flags = window.create_backup_path_label.textInteractionFlags()
    assert flags & Qt.TextInteractionFlag.TextSelectableByMouse


@pytest.mark.gui
def test_opening_the_folder_does_nothing_before_any_backup_exists(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """El botón está apagado, pero el manejador tampoco puede caerse si se
    invoca por teclado o por programa sin ruta guardada.
    """
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    opened: list[Path] = []
    window = _build_window(database_path, open_containing_folder=opened.append)
    qtbot.addWidget(window)

    window._handle_open_backup_folder_clicked()
    window._handle_use_last_backup_clicked()

    assert opened == []
    assert window.validate_backup_path_input.text() == ""
