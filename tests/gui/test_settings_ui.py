"""pytest-qt tests for the "Configuración" tab (V7A: provider, model, limits,
budget, and the masked API-key field). No test ever touches the real Windows
Credential Manager: a ``FakeSecretStore`` is injected everywhere. No test
ever shows a real QMessageBox either: ``_build_window`` injects no-op
doubles by default (``tests/gui/conftest.py`` also blocks the real ones as a
backstop).
"""

from __future__ import annotations

from collections.abc import Callable
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
from sirius.composition_root import build_conversation_dependencies
from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.config.settings import load_settings
from sirius.presentation.main_window import MainWindow

_FAKE_KEY = "sk-should-never-be-shown-1234567890"


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
    secret_store: FakeSecretStore,
    *,
    show_warning: Callable[[str, str], None] | None = None,
    show_information: Callable[[str, str], None] | None = None,
) -> MainWindow:
    dependencies = build_conversation_dependencies(database_path, secret_store=secret_store)
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        show_warning=show_warning or (lambda title, text: None),
        show_information=show_information or (lambda title, text: None),
    )


@pytest.mark.gui
def test_provider_defaults_to_fake(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path, FakeSecretStore())
    qtbot.addWidget(window)

    assert window.provider_combo.currentText() == "fake"


@pytest.mark.gui
def test_key_status_label_shows_no_key_by_default(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path, FakeSecretStore())
    qtbot.addWidget(window)

    assert "no configurada" in window.key_status_label.text()


@pytest.mark.gui
def test_api_key_field_is_masked(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path, FakeSecretStore())
    qtbot.addWidget(window)

    assert window.api_key_input.echoMode() == window.api_key_input.EchoMode.Password


@pytest.mark.gui
def test_saving_a_key_clears_the_field_and_shows_inline_feedback(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Success is shown inline (``key_feedback_label``), never via a modal dialog."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    window = _build_window(database_path, secret_store)
    qtbot.addWidget(window)

    window.api_key_input.setText(_FAKE_KEY)
    window._save_api_key()

    assert window.api_key_input.text() == ""
    assert "configurada" in window.key_status_label.text()
    assert window.key_feedback_label.text() == "Clave guardada."
    assert secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) == _FAKE_KEY


@pytest.mark.gui
def test_saving_a_blank_key_is_rejected_without_touching_the_store(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path, secret_store, show_warning=lambda title, text: warnings.append((title, text))
    )
    qtbot.addWidget(window)

    window.api_key_input.setText("   ")
    window._save_api_key()

    assert secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) is None
    assert len(warnings) == 1


@pytest.mark.gui
def test_deleting_a_key_updates_the_status_label(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, _FAKE_KEY)
    infos: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        secret_store,
        show_information=lambda title, text: infos.append((title, text)),
    )
    qtbot.addWidget(window)

    window._delete_api_key()

    assert secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) is None
    assert "no configurada" in window.key_status_label.text()
    assert len(infos) == 1
    assert _FAKE_KEY not in infos[0][1]


@pytest.mark.gui
def test_an_existing_key_is_never_prefilled_into_the_field(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, _FAKE_KEY)
    window = _build_window(database_path, secret_store)
    qtbot.addWidget(window)

    assert window.api_key_input.text() == ""
    assert "configurada" in window.key_status_label.text()


@pytest.mark.gui
def test_the_key_never_appears_anywhere_in_the_visible_interface(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    window = _build_window(database_path, secret_store)
    qtbot.addWidget(window)

    window.api_key_input.setText(_FAKE_KEY)
    window._save_api_key()

    assert _FAKE_KEY not in window.key_status_label.text()
    assert _FAKE_KEY not in window.key_feedback_label.text()
    for index in range(window.message_list.count()):
        assert _FAKE_KEY not in window.message_list.item(index).text()


@pytest.mark.gui
def test_saving_configuration_persists_provider_model_limits_and_budget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path, FakeSecretStore())
    qtbot.addWidget(window)

    window.name_input.setText("Ada")
    window.provider_combo.setCurrentText("openai")
    window.model_input.setText("gpt-5.6-luna")
    window.max_output_tokens_input.setText("2048")
    window.budget_input.setText("30")

    window._save_configuration()

    settings = load_settings()
    assert settings["llm_provider"] == "openai"
    assert settings["openai_model"] == "gpt-5.6-luna"
    assert settings["openai_max_output_tokens"] == 2048
    assert settings["openai_monthly_budget_usd"] == 30.0


@pytest.mark.gui
def test_saving_configuration_with_invalid_numbers_shows_a_warning(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    warnings: list[tuple[str, str]] = []
    window = _build_window(
        database_path,
        FakeSecretStore(),
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)

    window.name_input.setText("Ada")
    window.max_output_tokens_input.setText("not-a-number")

    window._save_configuration()

    assert len(warnings) == 1
