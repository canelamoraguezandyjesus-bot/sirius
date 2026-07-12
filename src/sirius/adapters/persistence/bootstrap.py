"""Persistence bootstrap run once at application startup."""

from __future__ import annotations

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.infrastructure.paths import SiriusPaths, ensure_paths


def initialize_persistence(paths: SiriusPaths) -> None:
    """Prepare local directories, apply pending migrations, and ensure the main conversation.

    Safe to call on every startup: directory creation, migrations, and the
    main-conversation lookup are all idempotent.
    """
    ensure_paths(paths)
    database_path = paths.data_dir / "sirius.db"
    upgrade_to_head(database_path)
    repository = build_sqlite_conversation_repository(database_path)
    repository.get_or_create_main_conversation()
