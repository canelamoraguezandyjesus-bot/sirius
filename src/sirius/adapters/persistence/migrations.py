"""Alembic runner used to bring the local SQLite schema up to date."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _resource_root() -> Path:
    """Return the directory containing ``alembic.ini`` and ``migrations/``.

    In development this is the repository root. In a frozen build (PyInstaller
    sets ``sys.frozen``; Nuitka injects a ``__compiled__`` global into the
    ``__main__`` module, not an attribute on ``sys``), the executable ships
    those resources next to itself instead, since the repository root does not
    exist at runtime.
    """
    is_frozen = getattr(sys, "frozen", False) or hasattr(
        sys.modules.get("__main__"), "__compiled__"
    )
    if is_frozen:
        return Path(sys.executable).resolve().parent
    return _REPO_ROOT


def upgrade_to_head(database_path: Path) -> None:
    """Apply every pending Alembic migration to the given SQLite file."""
    resource_root = _resource_root()
    config = Config(str(resource_root / "alembic.ini"))
    config.set_main_option("script_location", str(resource_root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


@lru_cache(maxsize=1)
def get_supported_schema_version() -> str:
    """Return the Alembic head revision this installed version of Sirius supports.

    Unlike ``upgrade_to_head``, this reads only the migration scripts and needs
    no database file, so backup restoration can check schema compatibility
    even when no current database exists yet.
    """
    resource_root = _resource_root()
    config = Config(str(resource_root / "alembic.ini"))
    config.set_main_option("script_location", str(resource_root / "migrations"))
    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        msg = "No se encontró ninguna revisión de esquema en las migraciones de Sirius."
        raise RuntimeError(msg)
    return head
