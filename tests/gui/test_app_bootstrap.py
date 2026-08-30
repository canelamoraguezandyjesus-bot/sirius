"""GUI tests for the full startup gate: location, onboarding, initial project.

``sirius.main`` decides which top-level window to show first and next,
using only ``ApiKeySettingsUseCase.has_key()`` (B2a),
``DataLocationUseCase.resolve()`` (B2b), and
``InitialProjectUseCase.is_configured()`` (B3a) — never the secret store,
keyring, provider SDK, or ``ProjectRepository`` directly. No test here ever
touches the real Windows Credential Manager (``FakeSecretStore`` everywhere)
or the real OpenAI API.
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
from sirius.presentation.initial_project_window import InitialProjectWindow
from sirius.presentation.onboarding_window import OnboardingWindow
from sirius.presentation.project_continuity_widget import NO_BLOCKERS_TEXT
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


def _bootstrapped_database(database_path: Path, *, configure_project: bool = True) -> Path:
    """Seed the three bootstrap singletons.

    ``configure_project=True`` (the default, matching every pre-B3a caller
    in this file) also completes the placeholder project with a name and
    objective, representing an installation that has already been through
    B3a's first-project screen. Pass ``configure_project=False`` to keep the
    neutral placeholder in place, for B3a tests that specifically exercise
    the "no project configured yet" gate.
    """
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    if configure_project:
        project_repository.create_project(
            "Proyecto de prueba",
            "Probar Sirius",
            state_summary="estado inicial",
            blockers=(),
            next_step="siguiente paso inicial",
        )
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


# --- B3a: initial project screen gates opening the real main window ---------


@pytest.mark.gui
def test_key_and_project_already_configured_opens_the_main_window_directly(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Scenario 1: nothing left to configure — straight to ValidatedMainWindow."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")  # project configured
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-already-configured")
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []

    window = _build_initial_window(dependencies, windows)
    qtbot.addWidget(window)

    assert isinstance(window, ValidatedMainWindow)
    assert not isinstance(window, InitialProjectWindow)


@pytest.mark.gui
def test_key_exists_but_no_project_configured_shows_the_initial_project_window(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Scenario 2: a key exists but no project has been configured yet."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db", configure_project=False)
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-already-configured")
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []

    window = _build_initial_window(dependencies, windows)
    qtbot.addWidget(window)

    assert isinstance(window, InitialProjectWindow)
    assert not isinstance(window, ValidatedMainWindow)


@pytest.mark.gui
def test_completing_onboarding_without_a_configured_project_shows_the_project_window(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Scenario 9: the project is consulted right after onboarding completes,
    and the conversation is never opened prematurely."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db", configure_project=False)
    secret_store = FakeSecretStore()
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []
    onboarding = _build_onboarding_window(dependencies, windows)
    windows.append(onboarding)
    qtbot.addWidget(onboarding)
    onboarding.show()
    onboarding._validate_and_save_api_key_use_case = ValidateAndSaveApiKeyUseCase(
        _RecordingValidator(), secret_store
    )
    onboarding._thread_pool = cast(QThreadPool, _ImmediateThreadPool())

    onboarding.api_key_input.setText("sk-candidate")
    onboarding._handle_continue_clicked()

    assert len(windows) == 2
    assert isinstance(windows[1], InitialProjectWindow)
    assert not isinstance(windows[1], ValidatedMainWindow)
    assert windows[1].isVisible() is True
    assert onboarding.isVisible() is False


@pytest.mark.gui
def test_creating_the_initial_project_opens_the_main_window_in_the_same_run(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db", configure_project=False)
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-already-configured")
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []

    window = _build_initial_window(dependencies, windows)
    windows.append(window)
    qtbot.addWidget(window)
    window.show()
    assert isinstance(window, InitialProjectWindow)

    window.name_input.setText("Mi Proyecto")
    window.objective_input.setText("Aprender Sirius")
    window._handle_create_clicked()

    assert len(windows) == 2
    assert isinstance(windows[1], ValidatedMainWindow)
    assert windows[1].isVisible() is True
    assert window.isVisible() is False
    assert dependencies.initial_project_use_case.is_configured() is True

    # Scenario 12: the continuity section reflects the just-created project
    # immediately, in the same run — no reopen required.
    main_window = windows[1]
    assert main_window.project_continuity_widget.name_label.text() == "Mi Proyecto"
    assert main_window.project_continuity_widget.objective_label.text() == "Aprender Sirius"
    assert main_window.project_continuity_widget.blockers_label.text() == NO_BLOCKERS_TEXT


@pytest.mark.gui
def test_simulated_restart_recovers_the_updated_continuity_summary(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Scenario 13: update continuity, close repositories, rebuild composition
    (a fresh ``ConversationDependencies``, simulating a real restart), open
    again, and confirm the summary and "Ahora toca" reflect what was saved."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")  # project configured
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-already-configured")

    first_dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    first_dependencies.project_continuity_use_case.update(
        "estado tras actualizar", "bloqueo pendiente", "paso tras actualizar"
    )
    first_dependencies.close_database_connections()

    second_dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=secret_store
    )
    windows: list[QMainWindow] = []
    window = _build_initial_window(second_dependencies, windows)
    qtbot.addWidget(window)

    assert isinstance(window, ValidatedMainWindow)
    assert window.project_continuity_widget.current_state_label.text() == "estado tras actualizar"
    assert window.project_continuity_widget.blockers_label.text() == "bloqueo pendiente"
    assert (
        window.project_continuity_widget.next_step_label.text()
        == "Ahora toca: paso tras actualizar"
    )


@pytest.mark.gui
def test_full_fresh_install_chain_reaches_the_main_window_in_one_run(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario 3/8: DataLocationWindow -> OnboardingWindow ->
    InitialProjectWindow -> ValidatedMainWindow, all in the same run."""
    shared_secret_store = FakeSecretStore()
    monkeypatch.setattr(
        "sirius.composition_root.build_keyring_secret_store", lambda: shared_secret_store
    )
    windows: list[QMainWindow] = []

    window = _build_first_window(_location_use_case(), windows)
    qtbot.addWidget(window)
    assert isinstance(window, DataLocationWindow)

    window.accept_default_button.click()

    assert len(windows) == 1
    assert isinstance(windows[0], OnboardingWindow)
    onboarding = windows[0]
    onboarding._validate_and_save_api_key_use_case = ValidateAndSaveApiKeyUseCase(
        _RecordingValidator(), shared_secret_store
    )
    onboarding._thread_pool = cast(QThreadPool, _ImmediateThreadPool())
    onboarding.api_key_input.setText("sk-candidate")
    onboarding._handle_continue_clicked()

    assert len(windows) == 2
    assert isinstance(windows[1], InitialProjectWindow)
    project_window = windows[1]

    project_window.name_input.setText("Mi Proyecto")
    project_window.objective_input.setText("Aprender Sirius")
    project_window._handle_create_clicked()

    assert len(windows) == 3
    assert isinstance(windows[2], ValidatedMainWindow)
    assert windows[2].isVisible() is True
    assert onboarding.isVisible() is False
    assert project_window.isVisible() is False


# --- Model Studio llega a la aplicación real ----------------------------
#
# Estas pruebas existen por un fallo real: la voz y la captura se construían
# en la raíz de composición y se conectaban a MainWindow, pero `main.py` monta
# `ValidatedMainWindow` SIN pasárselas. Resultado: en la aplicación de verdad
# el micrófono salía apagado y Sirius no hablaba nunca, sin un solo error a la
# vista, porque no había voz que pudiera fallar.
#
# Las pruebas anteriores no lo detectaron porque construían la ventana a mano
# pasándole las verticales. Comprobaban la ventana, no la aplicación. Estas
# entran por el mismo camino que el arranque real.


def _real_main_window(tmp_path: Path, qtbot: QtBot) -> ValidatedMainWindow:
    """La ventana tal como la construye ``main.py``, sin atajos."""
    from sirius.main import _build_main_window

    paths = resolve_paths(tmp_path)
    initialize_persistence(paths)
    project_repository = build_sqlite_project_repository(paths.data_dir / "sirius.db")
    project_repository.create_project(
        "HEAD-R1", "Cabeza", state_summary="montando", blockers=(), next_step="probar"
    )
    dependencies = build_conversation_dependencies(
        paths.data_dir / "sirius.db", paths.backups_dir, secret_store=FakeSecretStore()
    )
    window = _build_main_window(dependencies, [])
    qtbot.addWidget(window)
    # _build_main_window devuelve QMainWindow por contrato; aquí interesa la
    # ventana concreta, que es la que tiene Model Studio.
    assert isinstance(window, ValidatedMainWindow)
    return window


@pytest.mark.gui
def test_the_real_app_wires_the_voice_into_model_studio(qtbot: QtBot, tmp_path: Path) -> None:
    window = _real_main_window(tmp_path, qtbot)

    assert window._studio_voice_use_case is not None, (
        "la aplicación real montó la ventana sin voz: el micrófono saldría "
        "apagado y Sirius no hablaría nunca"
    )


@pytest.mark.gui
def test_the_real_app_wires_the_capture_into_model_studio(qtbot: QtBot, tmp_path: Path) -> None:
    window = _real_main_window(tmp_path, qtbot)

    assert window._studio_capture_use_case is not None


@pytest.mark.gui
def test_the_real_app_offers_the_voice_controls(qtbot: QtBot, tmp_path: Path) -> None:
    """Lo que el usuario ve: el micrófono se puede pulsar."""
    window = _real_main_window(tmp_path, qtbot)

    assert window.studio_page.voice_available
    assert window.studio_page.microphone_button.isEnabled()


@pytest.mark.gui
def test_the_real_app_starts_with_capture_off(qtbot: QtBot, tmp_path: Path) -> None:
    """Disponible no es lo mismo que encendido: abrir Sirius no conecta nada."""
    window = _real_main_window(tmp_path, qtbot)

    assert window.studio_page.capture_available
    assert not window.studio_page.capture_panel_open
    capture = window._studio_capture_use_case
    assert capture is not None
    assert not capture.is_enabled


@pytest.mark.gui
def test_the_real_app_can_save_the_chosen_voice(tmp_path: Path, qtbot: QtBot) -> None:
    """El mismo fallo de cableado que ya se coló una vez, vigilado aquí.

    Que el diálogo de ajustes funcione en una ventana montada a mano no dice
    nada: lo que importa es que la aplicación de verdad le pase cómo guardar.
    Sin eso, elegir una voz funcionaría hasta cerrar Sirius.
    """
    window = _real_main_window(tmp_path, qtbot)

    assert window._save_studio_voice is not None


@pytest.mark.gui
def test_the_real_app_offers_the_two_studio_buttons(tmp_path: Path, qtbot: QtBot) -> None:
    window = _real_main_window(tmp_path, qtbot)

    assert window.studio_page.read_all_button.isEnabled()


# --- D7 (M8) llega a KnowledgeWidget por el camino completo de producción --
#
# CLAUDE-M8-002: ninguna prueba usaba _real_main_window para comprobar que
# tag_category_use_case/set_category_use_case/thread_pool llegan de verdad,
# por el camino completo (composition_root -> main.py -> ValidatedMainWindow
# -> MainWindow -> KnowledgeWidget), hasta KnowledgeWidget. Todas las pruebas
# de etiquetado en KnowledgeWidget construían el widget a mano, inyectando
# sus propios dobles, así que una regresión que olvidara pasar
# tag_category_use_case/set_category_use_case en cualquiera de esos pasos
# pasaría la suite completa en verde, igual que ocurrió antes con la voz de
# Model Studio.


@pytest.mark.gui
def test_the_real_app_wires_category_tagging_into_the_knowledge_widget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window = _real_main_window(tmp_path, qtbot)

    assert window.knowledge_widget._tag_category_use_case is not None, (
        "la aplicación real montó KnowledgeWidget sin TagCategoryUseCase: un "
        "recuerdo o decisión nuevo nunca recibiría categoría automática"
    )


@pytest.mark.gui
def test_the_real_app_wires_manual_category_editing_into_the_knowledge_widget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window = _real_main_window(tmp_path, qtbot)

    assert window.knowledge_widget._set_category_use_case is not None, (
        "la aplicación real montó KnowledgeWidget sin SetCategoryUseCase: el "
        "usuario no podría corregir una clasificación (CODEX-001)"
    )
    assert window.studio_page.settings_button.isEnabled()
