"""Unit tests for BudgetTracker's in-memory fallback (no repository injected)."""

from __future__ import annotations

from sirius.adapters.llm.budget import BudgetPolicy, BudgetTracker


def test_has_remaining_budget_when_nothing_spent() -> None:
    tracker = BudgetTracker(BudgetPolicy(monthly_limit_usd=20.0))

    assert tracker.has_remaining_budget() is True
    assert tracker.is_near_limit() is False


def test_record_usage_computes_cost_from_the_policy() -> None:
    policy = BudgetPolicy(
        input_cost_usd_per_million_tokens=2.0, output_cost_usd_per_million_tokens=4.0
    )
    tracker = BudgetTracker(policy)

    tracker.record_usage(input_tokens=1_000_000, output_tokens=1_000_000)

    assert tracker.spent_usd == 6.0


def test_is_near_limit_once_the_warn_threshold_is_reached() -> None:
    policy = BudgetPolicy(warn_threshold_usd=1.0, input_cost_usd_per_million_tokens=1_000_000.0)
    tracker = BudgetTracker(policy)

    tracker.record_usage(input_tokens=1, output_tokens=0)

    assert tracker.is_near_limit() is True


def test_has_remaining_budget_becomes_false_once_the_monthly_limit_is_hit() -> None:
    policy = BudgetPolicy(monthly_limit_usd=1.0, input_cost_usd_per_million_tokens=1_000_000.0)
    tracker = BudgetTracker(policy)

    tracker.record_usage(input_tokens=1, output_tokens=0)

    assert tracker.has_remaining_budget() is False


def test_without_a_repository_spend_does_not_survive_a_new_instance() -> None:
    """The in-memory fallback is explicitly process-local: a fresh tracker
    (simulating a restart) starts back at zero. Persistence across restarts
    requires injecting a repository (see test_sqlite_llm_usage_repository.py).
    """
    policy = BudgetPolicy(input_cost_usd_per_million_tokens=1_000_000.0)
    first_tracker = BudgetTracker(policy)
    first_tracker.record_usage(input_tokens=1, output_tokens=0)

    second_tracker = BudgetTracker(policy)

    assert second_tracker.spent_usd == 0.0
