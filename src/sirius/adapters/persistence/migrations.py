"""Alembic runner used to bring the local SQLite schema up to date."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

_REPO_ROOT = Path(__file__).resolve().parents[4]


def upgrade_to_head(database_path: Path) -> None:
    """Apply every pending Alembic migration to the given SQLite file."""
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")
