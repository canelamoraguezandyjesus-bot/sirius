"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.composition_root import build_conversation_dependencies
from sirius.infrastructure.logging import configure_logging, get_logger
from sirius.infrastructure.paths import resolve_paths
from sirius.presentation.validated_main_window import ValidatedMainWindow


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

    window = ValidatedMainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        validate_and_save_api_key_use_case=dependencies.validate_and_save_api_key_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        close_database_connections=dependencies.close_database_connections,
    )
    window.show()
    logger.info("Sirius iniciado")

    if not owns_app:
        return 0
    return app.exec()
