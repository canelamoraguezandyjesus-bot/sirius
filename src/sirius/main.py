"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.application.data_location import DataLocationUseCase, LocationFileCorruptedError
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.llm_provider_settings import LLMProviderKind, resolve_openai_provider_settings
from sirius.infrastructure.bootstrap_location_store import build_bootstrap_location_store
from sirius.infrastructure.crash_handler import install_crash_handler
from sirius.infrastructure.data_path_validator import build_data_path_validator
from sirius.infrastructure.logging import configure_logging, get_logger
from sirius.infrastructure.paths import resolve_paths
from sirius.presentation.data_location_window import DataLocationWindow
from sirius.presentation.initial_project_window import InitialProjectWindow
from sirius.presentation.onboarding_window import OnboardingWindow
from sirius.presentation.validated_main_window import ValidatedMainWindow


def _build_main_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> ValidatedMainWindow:
    """Build the real conversation window, wired so completing the active
    project (RF-018) immediately reopens ``InitialProjectWindow`` — same
    process, no restart, exactly as it does the very first time no project
    is configured yet.
    """

    def _on_project_completed() -> None:
        next_window = _build_initial_project_window(dependencies, windows)
        windows.append(next_window)
        next_window.show()
        main_window.close()

    main_window = ValidatedMainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        validate_and_save_api_key_use_case=dependencies.validate_and_save_api_key_use_case,
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
        export_structured_use_case=dependencies.export_structured_use_case,
        close_database_connections=dependencies.close_database_connections,
        studio_voice_use_case=dependencies.studio_voice_use_case,
        studio_capture_use_case=dependencies.studio_capture_use_case,
    )
    main_window.project_completed.connect(_on_project_completed)
    return main_window


def _build_onboarding_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> OnboardingWindow:
    """Build the B2a first-run screen, wired to continue the bootstrap gate.

    ``windows`` is the caller's own list of top-level windows kept alive for
    the life of the event loop (see ``main()``): a top-level PySide6 widget
    with no Python reference left is garbage-collected immediately even while
    shown, so the window built here on success must be appended to it, not
    just constructed and shown.
    """
    provider_defaults = resolve_openai_provider_settings({})

    def _continue_after_onboarding() -> None:
        next_window = _build_post_key_window(dependencies, windows)
        windows.append(next_window)
        next_window.show()
        onboarding_window.close()

    onboarding_window = OnboardingWindow(
        validate_and_save_api_key_use_case=dependencies.validate_and_save_api_key_use_case,
        activate_llm_provider=dependencies.activate_configured_llm_provider,
        default_provider=LLMProviderKind.OPENAI.value,
        default_model=provider_defaults.model,
    )
    onboarding_window.configured.connect(_continue_after_onboarding)
    return onboarding_window


def _build_initial_project_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> InitialProjectWindow:
    """Build the B3a first-project screen, wired to open the real main window.

    See ``_build_onboarding_window`` for why the window built here on success
    must be appended to ``windows``, not just constructed and shown.
    """

    def _open_main_window() -> None:
        main_window = _build_main_window(dependencies, windows)
        windows.append(main_window)
        main_window.show()
        project_window.close()

    project_window = InitialProjectWindow(dependencies.initial_project_use_case)
    project_window.created.connect(_open_main_window)
    return project_window


def _build_post_key_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> QMainWindow:
    """RF-014/D-02 (B3a): the initial-project screen only while a key is
    configured but no project has been set up yet.

    Determined exclusively through ``InitialProjectUseCase.is_configured()``
    — never by querying ``ProjectRepository`` directly. Shared by both paths
    that can reach "a key is now configured": the key already existed at
    startup, and the key was just validated and saved during this run
    (B2a's ``OnboardingWindow``) — so the project check never runs twice or
    is duplicated between callbacks.
    """
    if dependencies.initial_project_use_case.is_configured():
        return _build_main_window(dependencies, windows)
    return _build_initial_project_window(dependencies, windows)


def _build_initial_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> QMainWindow:
    """RF-001/D-10 (B2a): onboarding only while no key is configured yet.

    Determined exclusively through ``ApiKeySettingsUseCase.has_key()`` — never
    by touching the secret store, keyring, or any provider SDK directly.
    """
    if not dependencies.api_key_settings_use_case.has_key():
        return _build_onboarding_window(dependencies, windows)
    return _build_post_key_window(dependencies, windows)


def _start_with_resolved_path(data_dir: Path, windows: list[QMainWindow]) -> QMainWindow:
    """B2b/D-10: everything data-dependent starts only once the data
    directory has been resolved and validated — never before.

    Logging, SQLite, migrations, and composition all derive their paths from
    ``data_dir`` here, and nowhere earlier in startup.
    """
    paths = resolve_paths(data_dir)
    configure_logging(paths.logs_dir)
    logger = get_logger(__name__)
    logger.info("Sirius iniciando")

    initialize_persistence(paths)
    dependencies = build_conversation_dependencies(paths.data_dir / "sirius.db", paths.backups_dir)
    logger.info("Sirius iniciado")

    return _build_initial_window(dependencies, windows)


def _build_data_location_window(
    location_use_case: DataLocationUseCase,
    windows: list[QMainWindow],
    *,
    recovery: bool = False,
) -> DataLocationWindow:
    def _on_resolved(data_dir: str) -> None:
        window = _start_with_resolved_path(Path(data_dir), windows)
        windows.append(window)
        window.show()
        location_window.close()

    location_window = DataLocationWindow(location_use_case, recovery=recovery)
    location_window.resolved.connect(_on_resolved)
    return location_window


def _build_first_window(
    location_use_case: DataLocationUseCase, windows: list[QMainWindow]
) -> QMainWindow:
    """B2b/D-10: resolve the data directory before anything data-dependent runs.

    Only a brand-new install with no installation yet at the default path
    (or a corrupted pointer file) needs an extra screen; every other case
    resolves silently and starts exactly as before B2b.
    """
    try:
        resolution = location_use_case.resolve()
    except LocationFileCorruptedError:
        return _build_data_location_window(location_use_case, windows, recovery=True)

    if resolution.needs_selection:
        return _build_data_location_window(location_use_case, windows)

    return _start_with_resolved_path(resolution.path, windows)


def main() -> int:
    """Start the Sirius desktop application."""
    # Antes de crear nada: si algo escapa del bucle de eventos, que quede
    # registrado en vez de cerrar Sirius sin dejar rastro. La persistencia en
    # logs/application.log solo está garantizada a partir de configure_logging
    # (tras resolver el directorio de datos); en la ventana anterior el
    # manejador solo puede intentar stderr, si existe.
    install_crash_handler()

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    default_paths = resolve_paths()
    location_use_case = DataLocationUseCase(
        location_store=build_bootstrap_location_store(),
        validator=build_data_path_validator(),
        default_data_dir=default_paths.data_dir,
    )

    # Every shown top-level window must stay referenced here for the life of
    # the event loop (see _build_onboarding_window's docstring).
    windows: list[QMainWindow] = []
    window = _build_first_window(location_use_case, windows)
    windows.append(window)
    window.show()

    if not owns_app:
        return 0
    return app.exec()
