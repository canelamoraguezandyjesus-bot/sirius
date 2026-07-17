"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.llm_provider_settings import LLMProviderKind, resolve_openai_provider_settings
from sirius.infrastructure.logging import configure_logging, get_logger
from sirius.infrastructure.paths import resolve_paths
from sirius.presentation.onboarding_window import OnboardingWindow
from sirius.presentation.validated_main_window import ValidatedMainWindow


def _build_main_window(dependencies: ConversationDependencies) -> ValidatedMainWindow:
    return ValidatedMainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        validate_and_save_api_key_use_case=dependencies.validate_and_save_api_key_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        close_database_connections=dependencies.close_database_connections,
    )


def _build_onboarding_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> OnboardingWindow:
    """Build the B2a first-run screen, wired to open the real main window.

    ``windows`` is the caller's own list of top-level windows kept alive for
    the life of the event loop (see ``main()``): a top-level PySide6 widget
    with no Python reference left is garbage-collected immediately even while
    shown, so the window built here on success must be appended to it, not
    just constructed and shown.
    """
    provider_defaults = resolve_openai_provider_settings({})

    def _open_main_window() -> None:
        main_window = _build_main_window(dependencies)
        windows.append(main_window)
        main_window.show()
        onboarding_window.close()

    onboarding_window = OnboardingWindow(
        validate_and_save_api_key_use_case=dependencies.validate_and_save_api_key_use_case,
        activate_llm_provider=dependencies.activate_configured_llm_provider,
        default_provider=LLMProviderKind.OPENAI.value,
        default_model=provider_defaults.model,
    )
    onboarding_window.configured.connect(_open_main_window)
    return onboarding_window


def _build_initial_window(
    dependencies: ConversationDependencies, windows: list[QMainWindow]
) -> QMainWindow:
    """RF-001/D-10 (B2a): onboarding only while no key is configured yet.

    Determined exclusively through ``ApiKeySettingsUseCase.has_key()`` — never
    by touching the secret store, keyring, or any provider SDK directly.
    """
    if dependencies.api_key_settings_use_case.has_key():
        return _build_main_window(dependencies)
    return _build_onboarding_window(dependencies, windows)


def main() -> int:
    """Start the Sirius desktop application."""
    paths = resolve_paths()
    configure_logging(paths.logs_dir)
    logger = get_logger(__name__)
    logger.info("Sirius iniciando")

    initialize_persistence(paths)
    dependencies = build_conversation_dependencies(paths.data_dir / "sirius.db", paths.backups_dir)

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    # Every shown top-level window must stay referenced here for the life of
    # the event loop (see _build_onboarding_window's docstring).
    windows: list[QMainWindow] = []
    window = _build_initial_window(dependencies, windows)
    windows.append(window)
    window.show()
    logger.info("Sirius iniciado")

    if not owns_app:
        return 0
    return app.exec()
