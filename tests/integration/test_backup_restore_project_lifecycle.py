"""B3c-specific integration test: backup and restoration must conserve the
full project lifecycle — every project, every revision, each project's
``current_revision_id`` pointer, the single-ACTIVE-project constraint, and
which project ``ContextBuilder`` picks up afterward.

The backup/restoration mechanism itself (``VACUUM INTO`` on create, an
atomic whole-file replace on restore) is schema-agnostic and already covered
generically by ``tests/integration/test_sqlite_backup_restore.py``; this
test exercises that same mechanism specifically against B3c's project
schema, since a defect there would silently lose project history without
any of the generic backup tests noticing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.backup.sqlite_backup_service import build_sqlite_backup_service
from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.models import ProjectModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import ContextBuilder
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.domain.project import ProjectStatus

_PASSWORD = "correct horse battery staple"


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "sirius.db"
    upgrade_to_head(path)
    return path


@pytest.fixture
def backups_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


@pytest.mark.integration
def test_backup_and_restore_conserve_the_full_project_lifecycle(
    database_path: Path, backups_dir: Path
) -> None:
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()

    # Project A: three revisions, then completed.
    project_a = project_repository.create_project(
        "A", "objetivo A", state_summary="estado A v1", blockers=(), next_step="paso A v1"
    )
    project_repository.append_revision(
        project_a.id,
        objective="objetivo A",
        state_summary="estado A v2",
        blockers=("b1",),
        next_step="paso A v2",
    )
    project_a_final = project_repository.append_revision(
        project_a.id,
        objective="objetivo A",
        state_summary="estado A v3",
        blockers=("b1", "b2"),
        next_step="paso A v3",
    )
    assert project_a_final.current_revision is not None
    project_repository.complete_active_project(project_a.id)

    # Project B: a single revision, left ACTIVE — the one project a backup
    # taken right now must restore as the sole active project.
    project_b = project_repository.create_project(
        "B", "objetivo B", state_summary="estado B v1", blockers=(), next_step="paso B v1"
    )

    backup_service = build_sqlite_backup_service(database_path, backups_dir)
    created = backup_service.create_backup(_PASSWORD)

    # Mutate after the backup was taken, so restoring it is verifiably not a
    # no-op: B gains a second revision that the restore must undo.
    project_repository.append_revision(
        project_b.id,
        objective="objetivo B",
        state_summary="estado B v2 (post-backup)",
        blockers=(),
        next_step="paso B v2",
    )
    project_repository.close()

    result = backup_service.restore_backup(created.path, _PASSWORD, confirmed=True)
    assert result.manifest == created.manifest

    restored_repository = build_sqlite_project_repository(database_path)

    # --- Project A: COMPLETED, all three revisions conserved, pointer intact.
    restored_a = restored_repository.get_project(project_a.id)
    assert restored_a is not None
    assert restored_a.status is ProjectStatus.COMPLETED
    assert restored_a.current_revision == project_a_final.current_revision

    a_history = restored_repository.list_project_revisions(project_a.id)
    assert [r.version for r in a_history] == [1, 2, 3]
    assert a_history[0].state_summary == "estado A v1"
    assert a_history[1].state_summary == "estado A v2"
    assert a_history[2].state_summary == "estado A v3"

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model_a = session.get(ProjectModel, project_a.id)
        assert model_a is not None
        assert model_a.current_revision_id == project_a_final.current_revision.id

    # --- Project B: ACTIVE, back to exactly its one pre-backup revision —
    # the post-backup mutation was genuinely undone, not just left alone.
    restored_b = restored_repository.get_project(project_b.id)
    assert restored_b is not None
    assert restored_b.status is ProjectStatus.ACTIVE
    assert restored_b.current_revision is not None
    assert restored_b.current_revision.version == 1
    assert restored_b.current_revision.state_summary == "estado B v1"

    b_history = restored_repository.list_project_revisions(project_b.id)
    assert [r.version for r in b_history] == [1]

    with session_scope(session_factory) as session:
        model_b = session.get(ProjectModel, project_b.id)
        assert model_b is not None
        assert model_b.current_revision_id == restored_b.current_revision.id

    # --- Único activo: B is the only ACTIVE project after restore.
    assert restored_repository.get_active_project() == restored_b

    # --- ContextBuilder resolves to B, and A never enters the context.
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=restored_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=restored_repository,
        memory_repository=memory_repository,
        conversation_repository=build_sqlite_conversation_repository(database_path),
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
    )

    context = context_builder.build("hola")

    assert context.project is not None
    assert context.project.id == project_b.id
    assert context.project.id != project_a.id
