"""Persistence bootstrap run once at application startup."""

from __future__ import annotations

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import (
    build_sqlite_project_repository,
)
from sirius.infrastructure.paths import SiriusPaths, ensure_paths


def initialize_persistence(paths: SiriusPaths) -> None:
    """Prepare local directories, apply pending migrations, and ensure the main
    conversation, the active project, and the current identity exist.

    Safe to call on every startup: directory creation, migrations, and every
    get-or-create lookup are idempotent.
    """
    ensure_paths(paths)
    database_path = paths.data_dir / "sirius.db"
    upgrade_to_head(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation_repository.get_or_create_main_conversation()

    project_repository = build_sqlite_project_repository(database_path)
    project_repository.get_or_create_active_project()

    identity_repository = build_sqlite_identity_repository(database_path)
    identity_repository.get_or_create_current_identity()
