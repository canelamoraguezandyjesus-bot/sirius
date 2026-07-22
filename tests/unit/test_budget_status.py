"""Unit tests for GetBudgetStatusUseCase (B7c; RF-030, PA-018; DR-018)."""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.application.budget_status import BudgetStatus, GetBudgetStatusUseCase


class _FakeSpendReader:
    def __init__(self, spent_usd: float) -> None:
        self._spent_usd = spent_usd
        self.requested_year_months: list[str] = []

    def get_spent_usd(self, year_month: str) -> float:
        self.requested_year_months.append(year_month)
        return self._spent_usd


def test_spend_below_the_warn_threshold_is_not_near_limit() -> None:
    use_case = GetBudgetStatusUseCase(
        _FakeSpendReader(10.0), warn_threshold_usd=15.0, monthly_limit_usd=20.0
    )

    assert use_case.get_status() == BudgetStatus(
        spent_usd=10.0, warn_threshold_usd=15.0, monthly_limit_usd=20.0, is_near_limit=False
    )


def test_spend_at_the_warn_threshold_is_near_limit() -> None:
    use_case = GetBudgetStatusUseCase(
        _FakeSpendReader(15.0), warn_threshold_usd=15.0, monthly_limit_usd=20.0
    )

    assert use_case.get_status().is_near_limit is True


def test_spend_above_the_warn_threshold_and_below_the_limit_is_near_limit() -> None:
    use_case = GetBudgetStatusUseCase(
        _FakeSpendReader(18.0), warn_threshold_usd=15.0, monthly_limit_usd=20.0
    )

    assert use_case.get_status().is_near_limit is True


def test_zero_spend_never_reports_near_limit() -> None:
    """The simulated provider never records usage: spend stays at 0.0, so the
    warning must never appear regardless of the configured thresholds."""
    use_case = GetBudgetStatusUseCase(
        _FakeSpendReader(0.0), warn_threshold_usd=15.0, monthly_limit_usd=20.0
    )

    assert use_case.get_status().is_near_limit is False


def test_reads_the_current_utc_year_month_from_the_repository() -> None:
    reader = _FakeSpendReader(0.0)
    use_case = GetBudgetStatusUseCase(reader, warn_threshold_usd=15.0, monthly_limit_usd=20.0)

    use_case.get_status()

    assert reader.requested_year_months == [datetime.now(UTC).strftime("%Y-%m")]


def test_status_carries_through_the_configured_thresholds_unchanged() -> None:
    use_case = GetBudgetStatusUseCase(
        _FakeSpendReader(5.0), warn_threshold_usd=15.0, monthly_limit_usd=20.0
    )

    status = use_case.get_status()

    assert status.warn_threshold_usd == 15.0
    assert status.monthly_limit_usd == 20.0
