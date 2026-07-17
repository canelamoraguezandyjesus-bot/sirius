"""GUI tests for the B2a startup gate: onboarding vs. the normal experience.

``sirius.main`` decides which top-level window to show first, using only
``ApiKeySettingsUseCase.has_key()`` — never the secret store, keyring, or any
provider SDK directly. No test here ever touches the real Windows Credential
Manager (``FakeSecretStore`` everywhere) or the real OpenAI API.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from PySide6.QtCore import QRunnable, QThreadPool
from PySide6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
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
from sirius.application.data_location import DataLocationUseCase
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.infrastructure.bootstrap_location_store import BootstrapLocationStore
from sirius.infrastructure.data_path_validator import WindowsDataPathValidator
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_first_window, _build_initial_window, _build_onboarding_window
from sirius.presentation.data_location_window import RECOVERY_INTRO_TEXT, DataLocationWindow
from sirius.presentation.onboarding_window import OnboardingWindow
from sirius.presentation.validated_main_window import ValidatedMainWindow


class _RecordingValidator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def validate(self, credential: str, model: str) -> None:
        self.calls.append((credential, model))


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


@pytest.mark.gui
def test_no_key_shows_onboarding_and_never_a_usable_main_window(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    windows: list[QMainWindow] = []

    window = _build_initial_window(dependencies, windows)
    qtbot.addWidget(window)

    assert isinstance(window, OnboardingWindow)
    assert not isinstance(window, ValidatedMainWindow)


@pytest.mark.gui
def test_existing_key_opens_the_normal_experience_directly_without_onboarding(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-already-configured")
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []

    window = _build_initial_window(dependencies, windows)
    qtbot.addWidget(window)

    assert isinstance(window, ValidatedMainWindow)


@pytest.mark.gui
def test_successful_onboarding_opens_the_main_window_in_the_same_run(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """B2a: no restart — the main window replaces onboarding in one process."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    secret_store = FakeSecretStore()
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []
    onboarding = _build_onboarding_window(dependencies, windows)
    windows.append(onboarding)
    qtbot.addWidget(onboarding)
    onboarding.show()
    # Composition wires the real, network-calling validator; swap it for a
    # recording double here, same as every other credential test in this repo.
    onboarding._validate_and_save_api_key_use_case = ValidateAndSaveApiKeyUseCase(
        _RecordingValidator(), secret_store
    )
    onboarding._thread_pool = cast(QThreadPool, _ImmediateThreadPool())

    onboarding.api_key_input.setText("sk-candidate")
    onboarding._handle_continue_clicked()

    assert len(windows) == 2
    assert isinstance(windows[1], ValidatedMainWindow)
    assert windows[1].isVisible() is True
    assert onboarding.isVisible() is False


# --- B2b: data location resolved before any SQLite/logging initialization ---


def _location_use_case() -> DataLocationUseCase:
    default_paths = resolve_paths()
    return DataLocationUseCase(
        BootstrapLocationStore(),
        WindowsDataPathValidator(),
        default_data_dir=default_paths.data_dir,
    )


@pytest.mark.gui
def test_fresh_install_shows_the_location_window_before_any_persistence_or_logging(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    persistence_calls: list[Path] = []
    logging_calls: list[Path] = []
    monkeypatch.setattr(
        "sirius.main.initialize_persistence",
        lambda paths: persistence_calls.append(paths.data_dir),
    )
    monkeypatch.setattr(
        "sirius.main.configure_logging",
        lambda logs_dir, **kwargs: logging_calls.append(logs_dir),
    )

    windows: list[QMainWindow] = []
    window = _build_first_window(_location_use_case(), windows)
    qtbot.addWidget(window)

    assert isinstance(window, DataLocationWindow)
    assert persistence_calls == []
    assert logging_calls == []


@pytest.mark.gui
def test_accepting_the_default_location_starts_persistence_in_the_same_run(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B2b: after the location is confirmed, SQLite/composition start in the
    same process — no restart — and the normal B2a onboarding gate applies."""
    monkeypatch.setattr(
        "sirius.composition_root.build_keyring_secret_store", lambda: FakeSecretStore()
    )
    default_paths = resolve_paths()
    use_case = _location_use_case()
    windows: list[QMainWindow] = []

    window = _build_first_window(use_case, windows)
    qtbot.addWidget(window)
    assert isinstance(window, DataLocationWindow)
    assert not (default_paths.data_dir / "sirius.db").exists()

    window.accept_default_button.click()

    assert (default_paths.data_dir / "sirius.db").exists()
    assert len(windows) == 1
    assert isinstance(windows[0], OnboardingWindow)


@pytest.mark.gui
def test_existing_default_installation_without_location_file_skips_the_selection_window(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B2b case 2: an installation that predates the pointer file keeps using
    the default path silently — no migration screen, no second database."""
    monkeypatch.setattr(
        "sirius.composition_root.build_keyring_secret_store", lambda: FakeSecretStore()
    )
    default_paths = resolve_paths()
    initialize_persistence(default_paths)  # simulates a pre-B2b installation

    use_case = _location_use_case()
    windows: list[QMainWindow] = []

    window = _build_first_window(use_case, windows)
    qtbot.addWidget(window)

    assert not isinstance(window, DataLocationWindow)
    assert isinstance(window, OnboardingWindow)
    assert (default_paths.config_dir / "data_location.json").exists()


@pytest.mark.gui
def test_previously_saved_custom_location_is_used_silently_without_reprompting(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "sirius.composition_root.build_keyring_secret_store", lambda: FakeSecretStore()
    )
    custom_dir = tmp_path / "Ubicacion Personalizada"
    custom_dir.mkdir()
    BootstrapLocationStore().save(custom_dir)

    use_case = _location_use_case()
    windows: list[QMainWindow] = []

    window = _build_first_window(use_case, windows)
    qtbot.addWidget(window)

    assert not isinstance(window, DataLocationWindow)
    assert (custom_dir / "sirius.db").exists()


@pytest.mark.gui
def test_corrupted_location_file_shows_recovery_and_never_opens_a_database_silently(
    qtbot: QtBot,
) -> None:
    default_paths = resolve_paths()
    location_file = default_paths.config_dir / "data_location.json"
    location_file.parent.mkdir(parents=True, exist_ok=True)
    location_file.write_text("{esto no es json valido", encoding="utf-8")

    windows: list[QMainWindow] = []
    window = _build_first_window(_location_use_case(), windows)
    qtbot.addWidget(window)

    assert isinstance(window, DataLocationWindow)
    assert window.intro_label.text() == RECOVERY_INTRO_TEXT
    assert not (default_paths.data_dir / "sirius.db").exists()
