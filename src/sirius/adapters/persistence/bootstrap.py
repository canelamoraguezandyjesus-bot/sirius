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
    conversation, the current identity, and (only the very first time) a
    bootstrap project placeholder exist.

    Safe to call on every startup: directory creation, migrations, and every
    get-or-create/ensure lookup are idempotent. After a project has been
    completed, this deliberately does *not* create a replacement — Sirius
    may legitimately have zero ``ACTIVE`` projects between a completion and
    the user's next explicit "Crear nuevo proyecto".
    """
    ensure_paths(paths)
    database_path = paths.data_dir / "sirius.db"
    upgrade_to_head(database_path)

    # Each repository is temporary: used once at startup, then closed
    # deterministically (never left for the garbage collector) so its pooled
    # connection cannot linger. The ``finally`` closes whatever repository was
    # actually built even if its own call raises, without touching a
    # repository that was never constructed.
    conversation_repository = build_sqlite_conversation_repository(database_path)
    try:
        conversation_repository.get_or_create_main_conversation()
    finally:
        conversation_repository.close()

    project_repository = build_sqlite_project_repository(database_path)
    try:
        project_repository.ensure_bootstrap_project()
    finally:
        project_repository.close()

    identity_repository = build_sqlite_identity_repository(database_path)
    try:
        identity_repository.get_or_create_current_identity()
    finally:
        identity_repository.close()
