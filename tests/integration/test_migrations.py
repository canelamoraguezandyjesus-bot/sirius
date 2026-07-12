from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from sirius.adapters.persistence.database import build_engine

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(database_path: Path) -> Config:
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


@pytest.mark.integration
def test_upgrade_head_creates_the_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    assert {"conversations", "messages", "projects"}.issubset(set(inspector.get_table_names()))


@pytest.mark.integration
def test_upgrade_head_columns_match_the_domain_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    conversation_columns = {c["name"] for c in inspector.get_columns("conversations")}
    message_columns = {c["name"] for c in inspector.get_columns("messages")}
    project_columns = {c["name"] for c in inspector.get_columns("projects")}

    assert conversation_columns == {"id", "created_at", "is_main"}
    assert message_columns == {
        "id",
        "conversation_id",
        "sequence",
        "role",
        "content",
        "created_at",
    }
    assert project_columns == {
        "id",
        "name",
        "objective",
        "current_state",
        "next_step",
        "is_active",
        "created_at",
        "updated_at",
    }


@pytest.mark.integration
def test_upgrade_head_creates_the_single_main_conversation_index(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    indexes = {index["name"]: index for index in inspector.get_indexes("conversations")}

    assert "uq_conversations_single_main" in indexes
    assert bool(indexes["uq_conversations_single_main"]["unique"])


@pytest.mark.integration
def test_upgrade_head_creates_the_single_active_project_index(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    indexes = {index["name"]: index for index in inspector.get_indexes("projects")}

    assert "uq_projects_single_active" in indexes
    assert bool(indexes["uq_projects_single_active"]["unique"])


@pytest.mark.integration
def test_upgrade_head_is_safe_to_run_again_on_an_existing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    inspector = inspect(build_engine(database_path))
    assert "messages" in inspector.get_table_names()


@pytest.mark.integration
def test_downgrade_to_v2_removes_only_projects(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "c4d8fc9d6f51")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert "projects" not in table_names
    assert {"conversations", "messages"}.issubset(table_names)


@pytest.mark.integration
def test_downgrade_removes_the_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    inspector = inspect(build_engine(database_path))
    assert not {"conversations", "messages", "projects"}.intersection(
        set(inspector.get_table_names())
    )
