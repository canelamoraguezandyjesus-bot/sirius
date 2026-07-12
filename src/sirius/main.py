"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.infrastructure.paths import resolve_paths
from sirius.presentation.main_window import MainWindow


def main() -> int:
    """Start the Sirius desktop application."""
    initialize_persistence(resolve_paths())

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    if not owns_app:
        return 0
    return app.exec()
