"""SQLite-backed LLM usage ledger: monthly spend must survive a restart."""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.llm.budget import BudgetPolicy, BudgetTracker
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_llm_usage_repository import (
    build_sqlite_llm_usage_repository,
)


def _prepare(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


@pytest.mark.integration
def test_get_spent_usd_is_zero_for_a_month_with_no_recorded_usage(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare(database_path)
    repository = build_sqlite_llm_usage_repository(database_path)

    assert repository.get_spent_usd("2026-07") == 0.0


@pytest.mark.integration
def test_add_spent_usd_accumulates_within_the_same_month(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare(database_path)
    repository = build_sqlite_llm_usage_repository(database_path)

    repository.add_spent_usd("2026-07", 1.5)
    repository.add_spent_usd("2026-07", 2.5)

    assert repository.get_spent_usd("2026-07") == 4.0


@pytest.mark.integration
def test_spend_is_tracked_separately_per_month(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare(database_path)
    repository = build_sqlite_llm_usage_repository(database_path)

    repository.add_spent_usd("2026-06", 10.0)
    repository.add_spent_usd("2026-07", 1.0)

    assert repository.get_spent_usd("2026-06") == 10.0
    assert repository.get_spent_usd("2026-07") == 1.0


@pytest.mark.integration
def test_spend_survives_reopening_the_store(tmp_path: Path) -> None:
    """A monthly cap that reset on every restart would not be meaningfully
    monthly (DR-018): a brand-new repository instance against the same
    database must see prior spend, simulating the app being closed and
    reopened.
    """
    database_path = tmp_path / "sirius.db"
    _prepare(database_path)
    first_repository = build_sqlite_llm_usage_repository(database_path)
    first_repository.add_spent_usd("2026-07", 5.0)

    reopened_repository = build_sqlite_llm_usage_repository(database_path)

    assert reopened_repository.get_spent_usd("2026-07") == 5.0


@pytest.mark.integration
def test_budget_tracker_with_a_repository_survives_a_new_instance(tmp_path: Path) -> None:
    """End-to-end: BudgetTracker itself, wired to the SQLite repository,
    reports the same spend after being rebuilt fresh (simulating a restart).
    """
    database_path = tmp_path / "sirius.db"
    _prepare(database_path)
    policy = BudgetPolicy(input_cost_usd_per_million_tokens=1_000_000.0)

    first_tracker = BudgetTracker(
        policy, usage_repository=build_sqlite_llm_usage_repository(database_path)
    )
    first_tracker.record_usage(input_tokens=3, output_tokens=0)

    second_tracker = BudgetTracker(
        policy, usage_repository=build_sqlite_llm_usage_repository(database_path)
    )

    assert second_tracker.spent_usd == 3.0
