from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from sirius.adapters.persistence.database import build_engine

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PREVIOUS_HEAD_REVISION = "0902e8217d75"  # head immediately before B3b's "add project blockers"


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
    assert {
        "conversations",
        "messages",
        "projects",
        "project_revisions",
        "memories",
        "memory_revisions",
        "events",
        "identities",
        "identity_versions",
        "llm_usage",
    }.issubset(set(inspector.get_table_names()))


@pytest.mark.integration
def test_upgrade_head_columns_match_the_domain_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    conversation_columns = {c["name"] for c in inspector.get_columns("conversations")}
    message_columns = {c["name"] for c in inspector.get_columns("messages")}
    project_columns = {c["name"] for c in inspector.get_columns("projects")}
    project_revision_columns = {c["name"] for c in inspector.get_columns("project_revisions")}
    memory_columns = {c["name"] for c in inspector.get_columns("memories")}
    memory_revision_columns = {c["name"] for c in inspector.get_columns("memory_revisions")}
    event_columns = {c["name"] for c in inspector.get_columns("events")}
    identity_columns = {c["name"] for c in inspector.get_columns("identities")}
    identity_version_columns = {c["name"] for c in inspector.get_columns("identity_versions")}
    llm_usage_columns = {c["name"] for c in inspector.get_columns("llm_usage")}

    assert conversation_columns == {"id", "created_at", "is_main"}
    assert message_columns == {
        "id",
        "conversation_id",
        "sequence",
        "role",
        "content",
        "created_at",
        "operation_id",
        "identity_version",
        "status",
    }
    assert llm_usage_columns == {"id", "year_month", "spent_usd", "updated_at"}
    assert project_columns == {
        "id",
        "name",
        "objective",
        "current_state",
        "blockers",
        "next_step",
        "is_active",
        "status",
        "completed_at",
        "current_revision_id",
        "created_at",
        "updated_at",
    }
    assert project_revision_columns == {
        "id",
        "project_id",
        "version",
        "objective",
        "state_summary",
        "blockers_json",
        "next_step",
        "source_event_id",
        "created_at",
    }
    assert "is_current" not in project_revision_columns  # SIRIUS-ARQ-0.1 S7.3: no such field
    assert memory_columns == {"id", "status", "created_at", "updated_at"}
    assert memory_revision_columns == {
        "id",
        "memory_id",
        "version",
        "content",
        "origin",
        "source_event_id",
        "is_current",
        "created_at",
    }
    assert event_columns == {
        "id",
        "event_type",
        "actor",
        "message_id",
        "created_at",
        "redacted_at",
    }
    assert identity_columns == {"id", "created_at"}
    assert identity_version_columns == {
        "id",
        "identity_id",
        "version",
        "name",
        "description",
        "personality_instructions",
        "is_current",
        "created_at",
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
def test_upgrade_head_creates_current_revision_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """SIRIUS-ARQ-0.1 S7.3: projects.current_revision_id is the single
    authoritative pointer to the current revision — no is_current flag, no
    second source of truth."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("projects")
    current_revision_fks = [
        fk for fk in foreign_keys if fk["referred_table"] == "project_revisions"
    ]

    assert len(current_revision_fks) == 1
    assert current_revision_fks[0]["constrained_columns"] == ["current_revision_id"]
    assert current_revision_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_upgrade_head_creates_source_event_id_as_a_physical_foreign_key(tmp_path: Path) -> None:
    """B4a, RF-021: memory_revisions.source_event_id is a real, enforced link
    to events, not just a free-text field."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("memory_revisions")
    source_event_fks = [fk for fk in foreign_keys if fk["referred_table"] == "events"]

    assert len(source_event_fks) == 1
    assert source_event_fks[0]["constrained_columns"] == ["source_event_id"]
    assert source_event_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_upgrade_head_creates_the_single_current_revision_per_memory_index(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    indexes = {index["name"]: index for index in inspector.get_indexes("memory_revisions")}

    assert "uq_memory_revisions_single_current_per_memory" in indexes
    assert bool(indexes["uq_memory_revisions_single_current_per_memory"]["unique"])


@pytest.mark.integration
def test_upgrade_head_creates_the_single_current_version_per_identity_index(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    indexes = {index["name"]: index for index in inspector.get_indexes("identity_versions")}

    assert "uq_identity_versions_single_current_per_identity" in indexes
    assert bool(indexes["uq_identity_versions_single_current_per_identity"]["unique"])


@pytest.mark.integration
def test_upgrade_head_creates_the_operation_role_idempotency_constraint(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    constraints = {c["name"] for c in inspector.get_unique_constraints("messages")}

    assert "uq_messages_operation_role" in constraints


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
    assert not {
        "projects",
        "project_revisions",
        "memories",
        "memory_revisions",
        "identities",
        "identity_versions",
    }.intersection(table_names)
    assert {"conversations", "messages"}.issubset(table_names)


@pytest.mark.integration
def test_downgrade_to_v3_removes_only_memory_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "5ee754bfb0c2")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert not {"memories", "memory_revisions", "identities", "identity_versions"}.intersection(
        table_names
    )
    assert {"conversations", "messages", "projects"}.issubset(table_names)


@pytest.mark.integration
def test_downgrade_to_v4_removes_only_identity_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "4022f15cc8df")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert not {"identities", "identity_versions"}.intersection(table_names)
    assert {"conversations", "messages", "projects", "memories", "memory_revisions"}.issubset(
        table_names
    )


@pytest.mark.integration
def test_downgrade_to_v5_removes_only_the_new_message_columns(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "bd39e7e3df5e")

    message_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("messages")
    }
    assert message_columns == {
        "id",
        "conversation_id",
        "sequence",
        "role",
        "content",
        "created_at",
    }


@pytest.mark.integration
def test_downgrade_to_v6b_message_fields_removes_only_llm_usage(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "f5fb28ed426a")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert "llm_usage" not in table_names
    assert "messages" in table_names

    message_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("messages")
    }
    assert "status" in message_columns
    assert "operation_id" in message_columns


@pytest.mark.integration
def test_downgrade_to_v7_removes_only_the_blockers_column(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, _PREVIOUS_HEAD_REVISION)

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert "projects" in table_names
    assert "llm_usage" in table_names  # unaffected by this downgrade

    project_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("projects")
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
def test_downgrade_to_v8_removes_only_the_events_table_and_the_memory_link(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "6f710ea6c2d2")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert "events" not in table_names
    assert {"memories", "memory_revisions", "projects", "project_revisions"}.issubset(
        table_names
    )  # unaffected by this downgrade

    memory_revision_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("memory_revisions")
    }
    assert memory_revision_columns == {
        "id",
        "memory_id",
        "version",
        "content",
        "origin",
        "is_current",
        "created_at",
    }


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_existing_memories(tmp_path: Path) -> None:
    """B4a compatibility: a base created before this migration existed (still
    at the previous head, 6f710ea6c2d2) upgrades to the new head without
    losing an existing memory or its revision; ``source_event_id`` starts
    NULL for it, since no event existed yet when it was created."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "6f710ea6c2d2")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO memories (id, status, created_at, updated_at) "
                "VALUES (1, 'current', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO memory_revisions "
                "(memory_id, version, content, origin, is_current, created_at) "
                "VALUES (1, 1, 'recuerdo previo a B4a', 'manual', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    engine = build_engine(database_path)
    with engine.begin() as connection:
        memory_rows = connection.execute(text("SELECT id, status FROM memories")).fetchall()
        revision_rows = connection.execute(
            text(
                "SELECT memory_id, version, content, origin, source_event_id, is_current "
                "FROM memory_revisions"
            )
        ).fetchall()

    assert len(memory_rows) == 1
    assert memory_rows[0].id == 1
    assert memory_rows[0].status == "current"

    assert len(revision_rows) == 1
    revision_row = revision_rows[0]
    assert revision_row.memory_id == 1
    assert revision_row.version == 1
    assert revision_row.content == "recuerdo previo a B4a"
    assert revision_row.origin == "manual"
    assert revision_row.source_event_id is None
    assert revision_row.is_current == 1


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_the_existing_project(tmp_path: Path) -> None:
    """B3b compatibility: a base created before this migration existed (still
    at the previous head) upgrades to the new head without losing the
    existing project row, its id, or any of its other fields; ``blockers``
    starts empty for it, and the single-active-project row stays unique."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _PREVIOUS_HEAD_REVISION)

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, created_at, updated_at) "
                "VALUES (:name, :objective, :state, :next_step, 1, :now, :now)"
            ),
            {
                "name": "Sirius 0.1",
                "objective": "Cerrar B3b",
                "state": "en curso",
                "next_step": "probar la migración",
                "now": now,
            },
        )

    command.upgrade(config, "head")

    engine = build_engine(database_path)
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                "SELECT id, name, objective, current_state, next_step, is_active, blockers, "
                "status, completed_at, current_revision_id FROM projects"
            )
        ).fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row.name == "Sirius 0.1"
    assert row.objective == "Cerrar B3b"
    assert row.current_state == "en curso"
    assert row.next_step == "probar la migración"
    assert row.is_active == 1
    assert row.blockers == ""
    assert row.status == "active"
    assert row.completed_at is None
    assert row.current_revision_id is not None

    with engine.begin() as connection:
        revision_rows = connection.execute(
            text(
                "SELECT id, project_id, version, objective, state_summary, blockers_json, "
                "next_step FROM project_revisions"
            )
        ).fetchall()

    assert len(revision_rows) == 1
    revision_row = revision_rows[0]
    assert revision_row.project_id == row.id
    assert revision_row.version == 1
    assert revision_row.objective == "Cerrar B3b"
    assert revision_row.state_summary == "en curso"
    assert revision_row.blockers_json == "[]"
    assert revision_row.next_step == "probar la migración"
    # current_revision_id is the sole pointer: it must resolve to exactly
    # this backfilled revision, never left NULL for a configured project.
    assert row.current_revision_id == revision_row.id


@pytest.mark.integration
def test_upgrade_backfills_an_inactive_row_as_completed(tmp_path: Path) -> None:
    """A row already inactive before this migration (not expected in
    practice — no prior code path ever produced one, but handled and
    tested) migrates to COMPLETED with its updated_at as completed_at."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _PREVIOUS_HEAD_REVISION)

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, created_at, updated_at) "
                "VALUES (:name, :objective, :state, :next_step, 0, :now, :now)"
            ),
            {
                "name": "Proyecto viejo",
                "objective": "objetivo viejo",
                "state": "estado viejo",
                "next_step": "n",
                "now": now,
            },
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        rows = connection.execute(text("SELECT status, completed_at FROM projects")).fetchall()

    assert len(rows) == 1
    assert rows[0].status == "completed"
    assert rows[0].completed_at == now


@pytest.mark.integration
def test_upgrade_backfills_an_unconfigured_placeholder_with_no_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _PREVIOUS_HEAD_REVISION)

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, created_at, updated_at) "
                "VALUES ('', '', '', '', 1, :now, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        project_rows = connection.execute(
            text("SELECT id, status, current_revision_id FROM projects")
        ).fetchall()
        revision_rows = connection.execute(text("SELECT * FROM project_revisions")).fetchall()

    assert len(project_rows) == 1
    assert project_rows[0].status == "active"
    assert project_rows[0].current_revision_id is None
    assert revision_rows == []


@pytest.mark.integration
def test_downgrade_to_b3b_head_syncs_legacy_columns_from_the_current_revision(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "head")

    engine = build_engine(database_path)
    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    with engine.begin() as connection:
        project_id = connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, blockers, is_active, status, "
                "completed_at, created_at, updated_at) "
                "VALUES ('Sirius', '', '', '', '', 1, 'active', NULL, :now, :now)"
            ),
            {"now": now},
        ).lastrowid
        revision_id = connection.execute(
            text(
                "INSERT INTO project_revisions "
                "(project_id, version, objective, state_summary, blockers_json, next_step, "
                "source_event_id, created_at) "
                "VALUES (:pid, 1, 'objetivo revisado', 'estado revisado', "
                "'[\"bloqueo uno\"]', 'siguiente revisado', NULL, :now)"
            ),
            {"pid": project_id, "now": now},
        ).lastrowid
        connection.execute(
            text("UPDATE projects SET current_revision_id = :rid WHERE id = :pid"),
            {"rid": revision_id, "pid": project_id},
        )

    command.downgrade(config, "66951344e4b9")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert "project_revisions" not in table_names

    project_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("projects")
    }
    assert "status" not in project_columns
    assert "completed_at" not in project_columns
    assert "current_revision_id" not in project_columns

    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT objective, current_state, blockers, next_step FROM projects")
        ).fetchall()

    assert len(rows) == 1
    assert rows[0].objective == "objetivo revisado"
    assert rows[0].current_state == "estado revisado"
    assert rows[0].blockers == "bloqueo uno"
    assert rows[0].next_step == "siguiente revisado"


@pytest.mark.integration
def test_a_fresh_database_created_directly_at_head_includes_blockers(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    project_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("projects")
    }
    assert "blockers" in project_columns


@pytest.mark.integration
def test_downgrade_removes_the_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    inspector = inspect(build_engine(database_path))
    assert not {
        "conversations",
        "messages",
        "projects",
        "memories",
        "memory_revisions",
        "identities",
        "identity_versions",
        "llm_usage",
    }.intersection(set(inspector.get_table_names()))
