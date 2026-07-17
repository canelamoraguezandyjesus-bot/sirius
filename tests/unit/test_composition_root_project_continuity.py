"""Unit tests for the composition root's project continuity wiring (B3b).

Confirms both project-related use cases share the same underlying
``ProjectRepository`` — no extra repository is built, and updating through
one use case is visible through the other without rebuilding composition.
"""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.composition_root import build_conversation_dependencies


def test_build_conversation_dependencies_wires_project_continuity_use_case(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.project_continuity_use_case, ProjectContinuityUseCase)


def test_initial_project_and_continuity_use_cases_share_the_same_project(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    dependencies.initial_project_use_case.create_initial_project("Mi Proyecto", "Objetivo")
    dependencies.project_continuity_use_case.update("estado", "bloqueo", "siguiente")

    summary = dependencies.project_continuity_use_case.get_summary()
    assert summary.name == "Mi Proyecto"
    assert summary.objective == "Objetivo"
    assert summary.current_state == "estado"
    assert summary.blockers == "bloqueo"
    assert summary.next_step == "siguiente"
