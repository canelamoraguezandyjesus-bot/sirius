"""GUI tests for validate-before-save credential handling."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from PySide6.QtCore import QRunnable, QThreadPool
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
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidationKind,
)
from sirius.presentation.validated_main_window import ValidatedMainWindow


class _RecordingValidator:
    def __init__(self, error: CredentialValidationError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def validate(self, credential: str, model: str) -> None:
        self.calls.append((credential, model))
        if self.error is not None:
            raise self.error


class _ImmediateThreadPool:
    def start(self, worker: QRunnable) -> None:
        worker.run()


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_project_repository(database_path).get_or_create_active_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def _build_window(
    database_path: Path,
    validator: _RecordingValidator,
    secret_store: FakeSecretStore,
) -> ValidatedMainWindow:
    dependencies = build_conversation_dependencies(
        database_path,
        database_path.parent / "backups",
        secret_store=secret_store,
    )
    window = ValidatedMainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        validate_and_save_api_key_use_case=ValidateAndSaveApiKeyUseCase(
            validator,
            secret_store,
        ),
        project_continuity_use_case=dependencies.project_continuity_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )
    window._thread_pool = cast(QThreadPool, _ImmediateThreadPool())
    return window


@pytest.mark.gui
def test_valid_key_is_saved_and_restart_is_explained(qtbot: QtBot, tmp_path: Path) -> None:
    validator = _RecordingValidator()
    secret_store = FakeSecretStore()
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"),
        validator,
        secret_store,
    )
    qtbot.addWidget(window)
    window.api_key_input.setText("sk-candidate")
    window.model_input.setText("gpt-model")

    window._save_api_key()

    qtbot.waitUntil(lambda: not window._is_credential_busy)
    assert validator.calls == [("sk-candidate", "gpt-model")]
    assert window._api_key_settings_use_case.has_key()
    assert window.api_key_input.text() == ""
    assert "Reinicia Sirius" in window.key_feedback_label.text()


@pytest.mark.gui
def test_rejected_key_is_not_saved_and_safe_message_is_shown(
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    validator = _RecordingValidator(
        CredentialValidationError(CredentialValidationKind.AUTHENTICATION)
    )
    secret_store = FakeSecretStore()
    window = _build_window(
        _bootstrapped_database(tmp_path / "sirius.db"),
        validator,
        secret_store,
    )
    qtbot.addWidget(window)
    window.api_key_input.setText("sk-invalid")
    window.model_input.setText("gpt-model")

    window._save_api_key()

    qtbot.waitUntil(lambda: not window._is_credential_busy)
    assert not window._api_key_settings_use_case.has_key()
    assert window.api_key_input.text() == ""
    assert window.key_feedback_label.text() == "La clave no es válida."
