"""GUI tests for the B2a first-run onboarding screen (RF-001).

No test ever touches the real Windows Credential Manager (``FakeSecretStore``
everywhere) or the real OpenAI API: a recording/blocking test double replaces
``CredentialValidator``, exactly like ``tests/gui/test_validated_main_window.py``.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import cast

import pytest
from PySide6.QtCore import QRunnable, QThreadPool
from pytestqt.qtbot import QtBot

from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
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
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.llm_provider_settings import LLMProviderKind, resolve_openai_provider_settings
from sirius.config.settings import load_settings
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidationKind,
    CredentialValidator,
)
from sirius.presentation.onboarding_window import DATA_POLICY_TEXT, OnboardingWindow

_DEFAULT_MODEL = resolve_openai_provider_settings({}).model


class _RecordingValidator:
    def __init__(self, error: CredentialValidationError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def validate(self, credential: str, model: str) -> None:
        self.calls.append((credential, model))
        if self.error is not None:
            raise self.error


class _BlockingUntilReleasedValidator:
    """Test double: blocks ``validate()`` until the test calls ``release()``.

    Gives deterministic control over "close while a validation is genuinely
    in flight" without any arbitrary sleep (mirrors
    ``_BlockingUntilReleasedProvider`` in ``tests/gui/test_conversation_ui.py``).
    """

    def __init__(self) -> None:
        self._continue_event = threading.Event()
        self.calls: list[tuple[str, str]] = []

    def release(self) -> None:
        self._continue_event.set()

    def validate(self, credential: str, model: str) -> None:
        self.calls.append((credential, model))
        self._continue_event.wait()


class _ImmediateThreadPool:
    def start(self, worker: QRunnable) -> None:
        worker.run()


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path / "appdata"))


def _bootstrapped_database(database_path: Path) -> Path:
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_project_repository(database_path).get_or_create_active_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def _build_onboarding(
    database_path: Path,
    validator: CredentialValidator,
    secret_store: FakeSecretStore,
) -> tuple[OnboardingWindow, ConversationDependencies]:
    dependencies = build_conversation_dependencies(
        database_path,
        database_path.parent / "backups",
        secret_store=secret_store,
    )
    window = OnboardingWindow(
        validate_and_save_api_key_use_case=ValidateAndSaveApiKeyUseCase(validator, secret_store),
        activate_llm_provider=dependencies.activate_configured_llm_provider,
        default_provider=LLMProviderKind.OPENAI.value,
        default_model=_DEFAULT_MODEL,
    )
    return window, dependencies


def test_data_policy_text_covers_the_required_concepts() -> None:
    assert "localmente" in DATA_POLICY_TEXT
    assert "proveedor" in DATA_POLICY_TEXT
    assert "almacén seguro" in DATA_POLICY_TEXT
    assert "no se guarda en la base de datos local" in DATA_POLICY_TEXT
    assert "registros" in DATA_POLICY_TEXT
    assert "copias de seguridad" in DATA_POLICY_TEXT
    assert "herramientas externas" in DATA_POLICY_TEXT


@pytest.mark.gui
def test_onboarding_shows_policy_defaults_and_a_masked_key_field(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window, _ = _build_onboarding(
        _bootstrapped_database(tmp_path / "sirius.db"), _RecordingValidator(), FakeSecretStore()
    )
    qtbot.addWidget(window)

    assert window.provider_label.text() == f"Proveedor: openai    Modelo: {_DEFAULT_MODEL}"
    assert window.api_key_input.echoMode() == window.api_key_input.EchoMode.Password
    assert window.continue_button.isEnabled() is True


@pytest.mark.gui
def test_missing_key_is_rejected_without_starting_validation(qtbot: QtBot, tmp_path: Path) -> None:
    validator = _RecordingValidator()
    warnings: list[tuple[str, str]] = []
    window, dependencies = _build_onboarding(
        _bootstrapped_database(tmp_path / "sirius.db"), validator, FakeSecretStore()
    )
    window._show_warning = lambda title, text: warnings.append((title, text))
    qtbot.addWidget(window)

    window._handle_continue_clicked()

    assert validator.calls == []
    assert not dependencies.api_key_settings_use_case.has_key()
    assert len(warnings) == 1


@pytest.mark.gui
def test_successful_validation_saves_the_key_activates_the_provider_and_opens_the_way_forward(
    qtbot: QtBot, tmp_path: Path
) -> None:
    validator = _RecordingValidator()
    secret_store = FakeSecretStore()
    window, dependencies = _build_onboarding(
        _bootstrapped_database(tmp_path / "sirius.db"), validator, secret_store
    )
    window._thread_pool = cast(QThreadPool, _ImmediateThreadPool())
    qtbot.addWidget(window)
    configured_calls: list[None] = []
    window.configured.connect(lambda: configured_calls.append(None))

    window.api_key_input.setText("sk-candidate")
    window._handle_continue_clicked()

    assert validator.calls == [("sk-candidate", _DEFAULT_MODEL)]
    assert dependencies.api_key_settings_use_case.has_key() is True
    assert window.api_key_input.text() == ""
    assert len(configured_calls) == 1
    assert window._is_credential_busy is False
    assert window.continue_button.isEnabled() is True
    assert load_settings()["llm_provider"] == "openai"
    assert isinstance(
        dependencies.send_message_use_case._llm_provider,
        OpenAIResponsesProvider,
    )


@pytest.mark.gui
def test_rejected_key_is_not_saved_and_onboarding_stays_in_place(
    qtbot: QtBot, tmp_path: Path
) -> None:
    validator = _RecordingValidator(
        CredentialValidationError(CredentialValidationKind.AUTHENTICATION)
    )
    secret_store = FakeSecretStore()
    window, dependencies = _build_onboarding(
        _bootstrapped_database(tmp_path / "sirius.db"), validator, secret_store
    )
    window._thread_pool = cast(QThreadPool, _ImmediateThreadPool())
    qtbot.addWidget(window)
    configured_calls: list[None] = []
    window.configured.connect(lambda: configured_calls.append(None))

    window.api_key_input.setText("sk-invalid")
    window._handle_continue_clicked()

    assert not dependencies.api_key_settings_use_case.has_key()
    assert window.api_key_input.text() == ""
    assert window.status_label.text() == "La clave no es válida."
    assert configured_calls == []
    assert window.continue_button.isEnabled() is True
    assert window.api_key_input.isEnabled() is True
    assert "llm_provider" not in load_settings()


@pytest.mark.gui
def test_validation_in_progress_disables_controls_and_a_second_click_does_not_duplicate(
    qtbot: QtBot, tmp_path: Path
) -> None:
    validator = _RecordingValidator()
    window, _ = _build_onboarding(
        _bootstrapped_database(tmp_path / "sirius.db"), validator, FakeSecretStore()
    )
    qtbot.addWidget(window)

    window.api_key_input.setText("sk-candidate")
    window.continue_button.click()

    # Disabling happens synchronously, before the worker is handed to the
    # thread pool — true regardless of how fast the background thread runs.
    assert window.continue_button.isEnabled() is False
    assert window.api_key_input.isEnabled() is False

    window.continue_button.click()  # must be a harmless no-op while busy

    qtbot.waitUntil(lambda: not window._is_credential_busy, timeout=5000)
    assert validator.calls == [("sk-candidate", _DEFAULT_MODEL)]


@pytest.mark.gui
def test_closing_while_validating_is_deferred_and_completes_without_a_crash(
    qtbot: QtBot, tmp_path: Path
) -> None:
    validator = _BlockingUntilReleasedValidator()
    secret_store = FakeSecretStore()
    window, dependencies = _build_onboarding(
        _bootstrapped_database(tmp_path / "sirius.db"), validator, secret_store
    )
    qtbot.addWidget(window)
    window.show()
    configured_calls: list[None] = []
    window.configured.connect(lambda: configured_calls.append(None))

    window.api_key_input.setText("sk-candidate")
    window.continue_button.click()
    assert window._is_credential_busy is True

    window.close()  # must return immediately: deferred, not blocked

    assert window.isVisible() is True
    assert window._close_requested is True

    validator.release()
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=5000)

    # The already-in-flight validation was allowed to finish (never an
    # incomplete/partial save); but the pending close takes precedence over
    # opening the way to the main conversation.
    assert dependencies.api_key_settings_use_case.has_key() is True
    assert configured_calls == []
