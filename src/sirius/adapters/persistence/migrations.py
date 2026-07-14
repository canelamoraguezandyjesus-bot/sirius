"""Alembic runner used to bring the local SQLite schema up to date."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

_REPO_ROOT = Path(__file__).resolve().parents[4]


def upgrade_to_head(database_path: Path) -> None:
    """Apply every pending Alembic migration to the given SQLite file."""
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


@lru_cache(maxsize=1)
def get_supported_schema_version() -> str:
    """Return the Alembic head revision this installed version of Sirius supports.

    Unlike ``upgrade_to_head``, this reads only the migration scripts and needs
    no database file, so backup restoration can check schema compatibility
    even when no current database exists yet.
    """
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        msg = "No se encontró ninguna revisión de esquema en las migraciones de Sirius."
        raise RuntimeError(msg)
    return head
