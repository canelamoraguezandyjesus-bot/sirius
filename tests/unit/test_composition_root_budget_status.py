"""Unit tests for the composition root's B7c budget-status wiring.

Confirms ``get_budget_status_use_case`` is built with DR-018's fixed 20/15
USD envelope by default, and — the coherence requirement from the issue —
reads the *same* year-month-keyed spend the OpenAI adapter's own
``BudgetTracker`` would read, through the same ``LLMUsageRepository``
instance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_llm_usage_repository import (
    build_sqlite_llm_usage_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.budget_status import GetBudgetStatusUseCase
from sirius.composition_root import build_conversation_dependencies


def _current_year_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def test_build_conversation_dependencies_wires_the_budget_status_use_case(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.get_budget_status_use_case, GetBudgetStatusUseCase)


def test_budget_status_defaults_to_dr018s_envelope_with_no_recorded_spend(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    status = dependencies.get_budget_status_use_case.get_status()

    assert status.spent_usd == 0.0
    assert status.warn_threshold_usd == 15.0
    assert status.monthly_limit_usd == 20.0
    assert status.is_near_limit is False


def test_budget_status_reads_the_same_repository_the_openai_providers_tracker_writes_to(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    # Simulates real recorded spend for the current month, written through a
    # fresh repository instance against the same database file — exactly how
    # BudgetTracker.record_usage would persist it after a real send.
    build_sqlite_llm_usage_repository(database_path).add_spent_usd(_current_year_month(), 16.0)

    status = dependencies.get_budget_status_use_case.get_status()

    assert status.spent_usd == 16.0
    assert status.is_near_limit is True
