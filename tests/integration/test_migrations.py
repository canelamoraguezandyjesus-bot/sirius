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
        "decisions",
        "decision_revisions",
        "identities",
        "identity_versions",
        "llm_usage",
        "memory_suggestions",
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
    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    decision_revision_columns = {c["name"] for c in inspector.get_columns("decision_revisions")}
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
        "redacted_at",
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
    assert memory_columns == {
        "id",
        "status",
        "subject_key",
        "project_id",
        "created_at",
        "updated_at",
        "category",
        "category_locked",
        "criticality",
    }
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
    assert decision_columns == {
        "id",
        "subject",
        "project_id",
        "status",
        "supersedes_decision_id",
        "created_at",
        "updated_at",
        "category",
        "category_locked",
        "criticality",
    }
    assert decision_revision_columns == {
        "id",
        "decision_id",
        "version",
        "content",
        "source_event_id",
        "is_current",
        "created_at",
    }
    memory_suggestion_columns = {c["name"] for c in inspector.get_columns("memory_suggestions")}
    assert memory_suggestion_columns == {
        "id",
        "content",
        "status",
        "subject_key",
        "project_id",
        "source_event_id",
        "resulting_memory_id",
        "created_at",
        "resolved_at",
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
def test_upgrade_head_creates_decision_project_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """B4b, RF-020: decisions.project_id is a real, enforced link to
    projects, not just a free-standing integer."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("decisions")
    project_fks = [fk for fk in foreign_keys if fk["referred_table"] == "projects"]

    assert len(project_fks) == 1
    assert project_fks[0]["constrained_columns"] == ["project_id"]
    assert project_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_upgrade_head_creates_decision_source_event_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """B4b, RF-020: decision_revisions.source_event_id is a real, enforced
    link to events, not just a free-text field."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("decision_revisions")
    source_event_fks = [fk for fk in foreign_keys if fk["referred_table"] == "events"]

    assert len(source_event_fks) == 1
    assert source_event_fks[0]["constrained_columns"] == ["source_event_id"]
    assert source_event_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_upgrade_head_creates_the_single_current_revision_per_decision_index(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    indexes = {index["name"]: index for index in inspector.get_indexes("decision_revisions")}

    assert "uq_decision_revisions_single_current_per_decision" in indexes
    assert bool(indexes["uq_decision_revisions_single_current_per_decision"]["unique"])


@pytest.mark.integration
def test_upgrade_head_creates_supersedes_decision_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """B4c, RF-023: decisions.supersedes_decision_id is a real, enforced
    self-referential link, not just a free-standing integer."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("decisions")
    supersedes_fks = [fk for fk in foreign_keys if fk["referred_table"] == "decisions"]

    assert len(supersedes_fks) == 1
    assert supersedes_fks[0]["constrained_columns"] == ["supersedes_decision_id"]
    assert supersedes_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_supersedes_decision_id(tmp_path: Path) -> None:
    """B4c: downgrading past this migration removes only the
    ``supersedes_decision_id`` column; the ``decisions`` table itself and
    every other table (including ``decision_revisions``) is unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "938fc6ac868c")

    inspector = inspect(build_engine(database_path))
    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    assert "supersedes_decision_id" not in decision_columns
    assert {"decisions", "decision_revisions"}.issubset(set(inspector.get_table_names()))


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_existing_decisions(tmp_path: Path) -> None:
    """B4c compatibility: a base created before this migration existed (still
    at the previous head, 938fc6ac868c) upgrades to the new head without
    losing any existing decision or decision revision; every previously
    stored decision's ``supersedes_decision_id`` backfills to ``NULL``
    (correct — no decision was ever superseded before this migration)."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "938fc6ac868c")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, status, created_at, "
                "updated_at) VALUES (:name, :objective, :state, :next_step, 1, 'active', "
                ":now, :now)"
            ),
            {
                "name": "Sirius 0.1",
                "objective": "Cerrar B4c",
                "state": "en curso",
                "next_step": "probar la migración",
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO decisions (id, subject, project_id, status, created_at, updated_at) "
                "VALUES (1, 'Motor de persistencia', 1, 'approved', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO decision_revisions "
                "(decision_id, version, content, is_current, created_at) "
                "VALUES (1, 1, 'Usar SQLite local', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        decision_rows = connection.execute(
            text("SELECT id, subject, status, supersedes_decision_id FROM decisions")
        ).fetchall()
        revision_rows = connection.execute(
            text("SELECT decision_id, version, content FROM decision_revisions")
        ).fetchall()

    assert len(decision_rows) == 1
    assert decision_rows[0].id == 1
    assert decision_rows[0].subject == "Motor de persistencia"
    assert decision_rows[0].status == "approved"
    assert decision_rows[0].supersedes_decision_id is None

    assert len(revision_rows) == 1
    assert revision_rows[0].decision_id == 1
    assert revision_rows[0].content == "Usar SQLite local"


@pytest.mark.integration
def test_upgrade_head_allows_null_message_content(tmp_path: Path) -> None:
    """B4d: messages.content must accept NULL so a redacted message can be
    stored (SIRIUS-ARQ-0.1 S7.3: "contenido NULL solo si REDACTADO")."""
    database_path = tmp_path / "sirius.db"
    command.upgrade(_alembic_config(database_path), "head")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO conversations (created_at, is_main) VALUES (:now, 1)"), {"now": now}
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(conversation_id, sequence, role, content, created_at, status, redacted_at) "
                "VALUES (1, 1, 'user', NULL, :now, 'redacted', :now)"
            ),
            {"now": now},
        )
        row = connection.execute(text("SELECT content, status FROM messages")).fetchone()

    assert row is not None
    assert row.content is None
    assert row.status == "redacted"


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_message_redaction(tmp_path: Path) -> None:
    """B4d: downgrading past this migration removes only ``redacted_at`` and
    restores ``content`` as NOT NULL; every other table (and column) is
    unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "05559a954593")

    inspector = inspect(build_engine(database_path))
    message_columns = {c["name"] for c in inspector.get_columns("messages")}
    assert "redacted_at" not in message_columns
    content_column = next(c for c in inspector.get_columns("messages") if c["name"] == "content")
    assert content_column["nullable"] is False
    assert {"messages", "decisions", "decision_revisions"}.issubset(
        set(inspector.get_table_names())
    )


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_existing_messages(tmp_path: Path) -> None:
    """B4d compatibility: a base created before this migration existed (still
    at the previous head, 05559a954593) upgrades to the new head without
    losing any existing message; every previously stored message's
    ``redacted_at`` backfills to ``NULL`` (correct — no message was ever
    redacted before this migration)."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "05559a954593")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO conversations (created_at, is_main) VALUES (:now, 1)"), {"now": now}
        )
        connection.execute(
            text(
                "INSERT INTO messages (conversation_id, sequence, role, content, created_at) "
                "VALUES (1, 1, 'user', 'preferencia original', :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT id, content, status, redacted_at FROM messages")
        ).fetchall()

    assert len(rows) == 1
    assert rows[0].content == "preferencia original"
    assert rows[0].status == "completed"
    assert rows[0].redacted_at is None


@pytest.mark.integration
def test_upgrade_head_creates_memory_project_id_as_a_physical_foreign_key(tmp_path: Path) -> None:
    """B4e, RF-026/DR-011: memories.project_id is a real, enforced link to
    projects, not just a free-standing integer."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("memories")
    project_fks = [fk for fk in foreign_keys if fk["referred_table"] == "projects"]

    assert len(project_fks) == 1
    assert project_fks[0]["constrained_columns"] == ["project_id"]
    assert project_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_memory_subject_and_project(
    tmp_path: Path,
) -> None:
    """B4e: downgrading past this migration removes only
    ``subject_key``/``project_id``; the ``memories`` table itself and every
    other table (including ``decisions``) is unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "bf0ac43b986b")

    memory_columns = {
        c["name"] for c in inspect(build_engine(database_path)).get_columns("memories")
    }
    assert "subject_key" not in memory_columns
    assert "project_id" not in memory_columns
    assert {"memories", "memory_revisions", "decisions", "decision_revisions"}.issubset(
        set(inspect(build_engine(database_path)).get_table_names())
    )


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_existing_memories_and_backfills_null(
    tmp_path: Path,
) -> None:
    """B4e compatibility: a base created before this migration existed (still
    at the previous head, bf0ac43b986b) upgrades to the new head without
    losing an existing memory; ``subject_key``/``project_id`` backfill to
    ``NULL`` (correct — no memory declared an explicit subject before this
    migration, so it never participates in precedence or conflict, see
    ``sirius.domain.precedence``)."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "bf0ac43b986b")

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
                "VALUES (1, 1, 'recuerdo previo a B4e', 'manual', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        memory_rows = connection.execute(
            text("SELECT id, status, subject_key, project_id FROM memories")
        ).fetchall()

    assert len(memory_rows) == 1
    assert memory_rows[0].id == 1
    assert memory_rows[0].status == "current"
    assert memory_rows[0].subject_key is None
    assert memory_rows[0].project_id is None


@pytest.mark.integration
def test_memory_project_id_can_reference_an_existing_project(tmp_path: Path) -> None:
    """B4e: a memory can be explicitly associated with a real project, the
    same subject/project boundary decisions already use."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "head")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        project_id = connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, status, created_at, "
                "updated_at) VALUES (:name, '', '', '', 1, 'active', :now, :now)"
            ),
            {"name": "Sirius 0.1", "now": now},
        ).lastrowid
        connection.execute(
            text(
                "INSERT INTO memories (id, status, subject_key, project_id, created_at, "
                "updated_at) VALUES (1, 'current', 'Motor de persistencia', :project_id, "
                ":now, :now)"
            ),
            {"project_id": project_id, "now": now},
        )
        row = connection.execute(
            text("SELECT subject_key, project_id FROM memories WHERE id = 1")
        ).fetchone()

    assert row is not None
    assert row.subject_key == "Motor de persistencia"
    assert row.project_id == project_id


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
def test_downgrade_to_previous_head_removes_only_the_decision_tables(tmp_path: Path) -> None:
    """B4b: downgrading past this migration removes only ``decisions`` and
    ``decision_revisions``; every other table (including ``events`` and
    ``memories``, added by earlier migrations) is unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, "810c1563f6c6")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert not {"decisions", "decision_revisions"}.intersection(table_names)
    assert {"events", "memories", "memory_revisions", "projects", "project_revisions"}.issubset(
        table_names
    )


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_existing_events_and_memories(
    tmp_path: Path,
) -> None:
    """B4b compatibility: a base created before this migration existed (still
    at the previous head, 810c1563f6c6) upgrades to the new head without
    losing any existing event, memory or memory revision."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "810c1563f6c6")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO events (id, event_type, actor, created_at) "
                "VALUES (1, 'memory.manual_save', 'user', :now)"
            ),
            {"now": now},
        )
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
                "(memory_id, version, content, origin, source_event_id, is_current, created_at) "
                "VALUES (1, 1, 'recuerdo previo a B4b', 'manual', 1, 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        event_rows = connection.execute(text("SELECT id, event_type FROM events")).fetchall()
        memory_rows = connection.execute(text("SELECT id, status FROM memories")).fetchall()

    assert len(event_rows) == 1
    assert event_rows[0].id == 1
    assert event_rows[0].event_type == "memory.manual_save"
    assert len(memory_rows) == 1
    assert memory_rows[0].id == 1

    table_names = set(inspect(engine).get_table_names())
    assert {"decisions", "decision_revisions"}.issubset(table_names)


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


_B6A_PREVIOUS_HEAD_REVISION = "94418c79da9d"  # head immediately before B6a's FTS5 indexes


@pytest.mark.integration
def test_upgrade_head_creates_the_fts5_search_tables(tmp_path: Path) -> None:
    """B6a, SIRIUS-ARQ-0.1 S7.1/S8.1; ATD-004; D-11: ``message_fts`` and
    ``knowledge_fts`` exist after upgrading to head."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert {"message_fts", "knowledge_fts"}.issubset(table_names)


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_the_fts5_tables_and_triggers(
    tmp_path: Path,
) -> None:
    """B6a: downgrading past this migration removes ``message_fts``,
    ``knowledge_fts`` and their sync triggers, but no base table or its
    data."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "head")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO conversations (id, created_at, is_main) VALUES (1, :now, 1)"),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(id, conversation_id, sequence, role, content, created_at, status) "
                "VALUES (1, 1, 1, 'user', 'mensaje anterior a la migración', :now, 'completed')"
            ),
            {"now": now},
        )

    command.downgrade(config, _B6A_PREVIOUS_HEAD_REVISION)

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert not {"message_fts", "knowledge_fts"}.intersection(table_names)
    assert {"messages", "memories", "memory_revisions", "decisions", "decision_revisions"}.issubset(
        table_names
    )
    with engine.begin() as connection:
        preserved = connection.execute(text("SELECT content FROM messages WHERE id = 1")).fetchone()
    assert preserved is not None
    assert preserved.content == "mensaje anterior a la migración"


@pytest.mark.integration
def test_upgrading_from_the_previous_head_backfills_existing_messages(tmp_path: Path) -> None:
    """B6a: a message written before this migration existed becomes
    searchable in ``message_fts`` once the database upgrades to head."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _B6A_PREVIOUS_HEAD_REVISION)

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO conversations (id, created_at, is_main) VALUES (1, :now, 1)"),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(id, conversation_id, sequence, role, content, created_at, status) "
                "VALUES (1, 1, 1, 'user', 'palabraprevia a la migración', :now, 'completed')"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT rowid FROM message_fts WHERE message_fts MATCH 'palabraprevia'")
        ).fetchall()
    assert [row.rowid for row in rows] == [1]


@pytest.mark.integration
def test_upgrading_from_the_previous_head_backfills_existing_memories_and_decisions(
    tmp_path: Path,
) -> None:
    """B6a: memories and decisions written before this migration existed
    become searchable in ``knowledge_fts`` once the database upgrades to
    head; a revision that is not current is not backfilled."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _B6A_PREVIOUS_HEAD_REVISION)

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
                "VALUES (1, 1, 'recuerdoviejo obsoleto', 'manual', 0, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO memory_revisions "
                "(memory_id, version, content, origin, is_current, created_at) "
                "VALUES (1, 2, 'recuerdovigente antes de la migración', 'manual', 1, :now)"
            ),
            {"now": now},
        )
        project_id = connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, status, created_at, "
                "updated_at) VALUES ('Sirius 0.1', '', '', '', 1, 'active', :now, :now)"
            ),
            {"now": now},
        ).lastrowid
        connection.execute(
            text(
                "INSERT INTO decisions (id, subject, project_id, status, created_at, updated_at) "
                "VALUES (1, 'asunto', :project_id, 'approved', :now, :now)"
            ),
            {"project_id": project_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO decision_revisions "
                "(decision_id, version, content, is_current, created_at) "
                "VALUES (1, 1, 'decisionvigente antes de la migración', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        current_memory_match = connection.execute(
            text("SELECT item_id FROM knowledge_fts WHERE knowledge_fts MATCH 'recuerdovigente'")
        ).fetchall()
        stale_memory_match = connection.execute(
            text("SELECT item_id FROM knowledge_fts WHERE knowledge_fts MATCH 'recuerdoviejo'")
        ).fetchall()
        decision_match = connection.execute(
            text("SELECT item_id FROM knowledge_fts WHERE knowledge_fts MATCH 'decisionvigente'")
        ).fetchall()

    assert [row.item_id for row in current_memory_match] == [1]
    assert stale_memory_match == []
    assert [row.item_id for row in decision_match] == [1]


_M4_PREVIOUS_HEAD_REVISION = "61be4bb269bf"  # head immediately before M4's memory_suggestions


@pytest.mark.integration
def test_upgrade_head_creates_memory_suggestions_project_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """M4, SIRIUS-ARQ-0.2 §3.7: memory_suggestions.project_id is a real,
    enforced link to projects, not just a free-standing integer."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("memory_suggestions")
    project_fks = [fk for fk in foreign_keys if fk["referred_table"] == "projects"]

    assert len(project_fks) == 1
    assert project_fks[0]["constrained_columns"] == ["project_id"]
    assert project_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_upgrade_head_creates_memory_suggestions_source_event_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """M4: memory_suggestions.source_event_id is a real, enforced link to events."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("memory_suggestions")
    source_event_fks = [fk for fk in foreign_keys if fk["referred_table"] == "events"]

    assert len(source_event_fks) == 1
    assert source_event_fks[0]["constrained_columns"] == ["source_event_id"]
    assert source_event_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_upgrade_head_creates_memory_suggestions_resulting_memory_id_as_a_physical_foreign_key(
    tmp_path: Path,
) -> None:
    """M4, SIRIUS-ARQ-0.2 §3.4: memory_suggestions.resulting_memory_id is a
    real, enforced link to memories, set only once a suggestion is confirmed."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    foreign_keys = inspector.get_foreign_keys("memory_suggestions")
    resulting_memory_fks = [fk for fk in foreign_keys if fk["referred_table"] == "memories"]

    assert len(resulting_memory_fks) == 1
    assert resulting_memory_fks[0]["constrained_columns"] == ["resulting_memory_id"]
    assert resulting_memory_fks[0]["referred_columns"] == ["id"]


@pytest.mark.integration
def test_memory_suggestions_has_no_unique_index_on_status(tmp_path: Path) -> None:
    """M4, SIRIUS-ARQ-0.2 §3.7: unlike ``projects``/``conversations``, nothing
    stops several suggestions from being PENDING at the same time — no
    unique index is created on this table at all."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    indexes = inspector.get_indexes("memory_suggestions")

    assert not any(index["unique"] for index in indexes)


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_the_memory_suggestions_table(
    tmp_path: Path,
) -> None:
    """M4: downgrading past this migration removes only ``memory_suggestions``;
    every other table (including ``memories`` and ``decisions``) is unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, _M4_PREVIOUS_HEAD_REVISION)

    table_names = set(inspect(build_engine(database_path)).get_table_names())
    assert "memory_suggestions" not in table_names
    assert {
        "memories",
        "memory_revisions",
        "decisions",
        "decision_revisions",
        "events",
        "projects",
    }.issubset(table_names)


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_existing_memories_and_decisions(
    tmp_path: Path,
) -> None:
    """M4 compatibility: a base created before this migration existed (still
    at the previous head) upgrades to the new head without losing any
    existing memory or decision; the new table starts empty."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _M4_PREVIOUS_HEAD_REVISION)

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
                "VALUES (1, 1, 'recuerdo previo a M4', 'manual', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        memory_rows = connection.execute(text("SELECT id, status FROM memories")).fetchall()
        suggestion_rows = connection.execute(text("SELECT id FROM memory_suggestions")).fetchall()

    assert len(memory_rows) == 1
    assert memory_rows[0].id == 1
    assert memory_rows[0].status == "current"
    assert suggestion_rows == []


@pytest.mark.integration
def test_memory_suggestion_can_be_inserted_and_read_back(tmp_path: Path) -> None:
    """M4: a full round trip through the new table, independent of the
    application/adapter layer — a pending suggestion with no resolution
    yet, and a confirmed one linked to a real memory."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "head")

    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO memory_suggestions (id, content, status, created_at) "
                "VALUES (1, 'sugerencia pendiente', 'pending', :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO memories (id, status, created_at, updated_at) "
                "VALUES (1, 'current', :now, :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO memory_suggestions "
                "(id, content, status, resulting_memory_id, created_at, resolved_at) "
                "VALUES (2, 'sugerencia confirmada', 'confirmed', 1, :now, :now)"
            ),
            {"now": now},
        )
        rows = connection.execute(
            text(
                "SELECT id, content, status, resulting_memory_id, resolved_at "
                "FROM memory_suggestions ORDER BY id"
            )
        ).fetchall()

    assert len(rows) == 2
    assert rows[0].id == 1
    assert rows[0].status == "pending"
    assert rows[0].resulting_memory_id is None
    assert rows[0].resolved_at is None
    assert rows[1].id == 2
    assert rows[1].status == "confirmed"
    assert rows[1].resulting_memory_id == 1
    assert rows[1].resolved_at == now


_M8_PREVIOUS_HEAD_REVISION = "1975a5496c12"  # head immediately before M8's category columns


@pytest.mark.integration
def test_upgrade_head_adds_category_columns_to_memories_and_decisions(tmp_path: Path) -> None:
    """M8, SIRIUS-ARQ-0.2 §6.1/§8-M8, D7 point 1: the two new columns exist
    on both tables after upgrading to head, purely additive."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    memory_columns = {c["name"] for c in inspector.get_columns("memories")}
    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    assert {"category", "category_locked"}.issubset(memory_columns)
    assert {"category", "category_locked"}.issubset(decision_columns)


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_the_category_columns(tmp_path: Path) -> None:
    """M8: downgrading past this migration removes only ``category``/
    ``category_locked`` from ``memories`` and ``decisions``; every other
    table and column (including both tables themselves) is unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, _M8_PREVIOUS_HEAD_REVISION)

    inspector = inspect(build_engine(database_path))
    memory_columns = {c["name"] for c in inspector.get_columns("memories")}
    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    assert not {"category", "category_locked"}.intersection(memory_columns)
    assert not {"category", "category_locked"}.intersection(decision_columns)
    assert memory_columns == {
        "id",
        "status",
        "subject_key",
        "project_id",
        "created_at",
        "updated_at",
    }
    assert decision_columns == {
        "id",
        "subject",
        "project_id",
        "status",
        "supersedes_decision_id",
        "created_at",
        "updated_at",
    }
    table_names = set(inspector.get_table_names())
    assert {"memories", "memory_revisions", "decisions", "decision_revisions"}.issubset(table_names)


@pytest.mark.integration
def test_upgrading_from_the_previous_head_preserves_memories_and_decisions_and_backfills_category(
    tmp_path: Path,
) -> None:
    """M8 compatibility: a base created before this migration existed (still
    at the previous head) upgrades to the new head without losing any
    existing memory or decision; ``category`` backfills to ``NULL`` and
    ``category_locked`` to ``False`` (D7 point 4: immediately eligible for
    the retroactive tagging pass)."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _M8_PREVIOUS_HEAD_REVISION)

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
                "VALUES (1, 1, 'recuerdo previo a M8', 'manual', 1, :now)"
            ),
            {"now": now},
        )
        project_id = connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, status, created_at, "
                "updated_at) VALUES ('Sirius 0.1', '', '', '', 1, 'active', :now, :now)"
            ),
            {"now": now},
        ).lastrowid
        connection.execute(
            text(
                "INSERT INTO decisions (id, subject, project_id, status, created_at, updated_at) "
                "VALUES (1, 'asunto previo a M8', :project_id, 'approved', :now, :now)"
            ),
            {"project_id": project_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO decision_revisions "
                "(decision_id, version, content, is_current, created_at) "
                "VALUES (1, 1, 'decision previa a M8', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        memory_rows = connection.execute(
            text("SELECT id, status, category, category_locked FROM memories")
        ).fetchall()
        decision_rows = connection.execute(
            text("SELECT id, subject, category, category_locked FROM decisions")
        ).fetchall()

    assert len(memory_rows) == 1
    assert memory_rows[0].id == 1
    assert memory_rows[0].status == "current"
    assert memory_rows[0].category is None
    assert memory_rows[0].category_locked == 0

    assert len(decision_rows) == 1
    assert decision_rows[0].id == 1
    assert decision_rows[0].subject == "asunto previo a M8"
    assert decision_rows[0].category is None
    assert decision_rows[0].category_locked == 0


_M18B_PREVIOUS_HEAD_REVISION = "71bb52f6cc2b"  # head immediately before M18b's criticality column


@pytest.mark.integration
def test_upgrade_head_adds_criticality_column_to_memories_and_decisions(tmp_path: Path) -> None:
    """M18b, ADR-126: one new column on both tables after upgrading to head,
    purely additive — mirrors the M8 category migration test above."""
    database_path = tmp_path / "sirius.db"

    command.upgrade(_alembic_config(database_path), "head")

    inspector = inspect(build_engine(database_path))
    memory_columns = {c["name"] for c in inspector.get_columns("memories")}
    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    assert "criticality" in memory_columns
    assert "criticality" in decision_columns


@pytest.mark.integration
def test_downgrade_to_previous_head_removes_only_the_criticality_column(tmp_path: Path) -> None:
    """M18b: downgrading past this migration removes only ``criticality``
    from ``memories`` and ``decisions``; ``category``/``category_locked``
    (added by the earlier M8 migration this one revises) are unaffected."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "head")
    command.downgrade(config, _M18B_PREVIOUS_HEAD_REVISION)

    inspector = inspect(build_engine(database_path))
    memory_columns = {c["name"] for c in inspector.get_columns("memories")}
    decision_columns = {c["name"] for c in inspector.get_columns("decisions")}
    assert "criticality" not in memory_columns
    assert "criticality" not in decision_columns
    assert memory_columns == {
        "id",
        "status",
        "subject_key",
        "project_id",
        "created_at",
        "updated_at",
        "category",
        "category_locked",
    }
    assert decision_columns == {
        "id",
        "subject",
        "project_id",
        "status",
        "supersedes_decision_id",
        "created_at",
        "updated_at",
        "category",
        "category_locked",
    }


@pytest.mark.integration
def test_upgrading_from_previous_head_preserves_rows_and_backfills_criticality(
    tmp_path: Path,
) -> None:
    """M18b compatibility: a base created before this migration existed
    (still at the previous head) upgrades to the new head without losing any
    existing memory or decision; ``criticality`` backfills to ``NULL`` —
    "nadie la ha marcado" (ADR-126)."""
    database_path = tmp_path / "sirius.db"
    config = _alembic_config(database_path)
    command.upgrade(config, _M18B_PREVIOUS_HEAD_REVISION)

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
                "VALUES (1, 1, 'recuerdo previo a M18b', 'manual', 1, :now)"
            ),
            {"now": now},
        )
        project_id = connection.execute(
            text(
                "INSERT INTO projects "
                "(name, objective, current_state, next_step, is_active, status, created_at, "
                "updated_at) VALUES ('Sirius 0.1', '', '', '', 1, 'active', :now, :now)"
            ),
            {"now": now},
        ).lastrowid
        connection.execute(
            text(
                "INSERT INTO decisions (id, subject, project_id, status, created_at, updated_at) "
                "VALUES (1, 'asunto previo a M18b', :project_id, 'approved', :now, :now)"
            ),
            {"project_id": project_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO decision_revisions "
                "(decision_id, version, content, is_current, created_at) "
                "VALUES (1, 1, 'decision previa a M18b', 1, :now)"
            ),
            {"now": now},
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        memory_rows = connection.execute(
            text("SELECT id, status, criticality FROM memories")
        ).fetchall()
        decision_rows = connection.execute(
            text("SELECT id, subject, criticality FROM decisions")
        ).fetchall()

    assert len(memory_rows) == 1
    assert memory_rows[0].id == 1
    assert memory_rows[0].status == "current"
    assert memory_rows[0].criticality is None

    assert len(decision_rows) == 1
    assert decision_rows[0].id == 1
    assert decision_rows[0].subject == "asunto previo a M18b"
    assert decision_rows[0].criticality is None
