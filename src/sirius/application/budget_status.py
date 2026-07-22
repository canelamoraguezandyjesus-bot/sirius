"""Read-only monthly budget status for the observable surface (B7c; RF-030,
PA-018; DR-018).

The **blocking** behaviour when the monthly limit is reached already exists
in ``OpenAIResponsesProvider``/``BudgetTracker``
(``sirius.adapters.llm.budget``, never reimplemented here). What was missing
is a *non-blocking* early warning once spend approaches the limit but sending
is still allowed. ``application`` may never import ``sirius.adapters``
(``test_application_boundaries.py``), so this use case does not depend on
``BudgetTracker``/``BudgetPolicy`` directly; instead it depends on the
minimal ``LLMSpendReader`` Protocol below, which
``SqliteLLMUsageRepository`` already satisfies structurally — the
composition root wires this use case to the very same repository instance
``BudgetTracker`` reads from, so both always agree on the current month's
spend.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

__all__ = ["BudgetStatus", "GetBudgetStatusUseCase", "LLMSpendReader"]


class LLMSpendReader(Protocol):
    """Reads accumulated LLM spend for a UTC year-month (e.g. ``"2026-07"``)."""

    def get_spent_usd(self, year_month: str) -> float:
        """Return the spend recorded so far for that month, or 0.0 if none."""
        ...


def _current_year_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    """Snapshot of this month's spend against DR-018's configured envelope."""

    spent_usd: float
    warn_threshold_usd: float
    monthly_limit_usd: float
    is_near_limit: bool


class GetBudgetStatusUseCase:
    """Reports whether this month's spend is close to the configured limit.

    ``warn_threshold_usd``/``monthly_limit_usd`` are handed in by the
    composition root, sourced from the same ``BudgetPolicy``/provider
    settings the OpenAI adapter's own tracker uses — this use case never
    invents or adjusts DR-018's thresholds.
    """

    def __init__(
        self,
        usage_repository: LLMSpendReader,
        *,
        warn_threshold_usd: float,
        monthly_limit_usd: float,
    ) -> None:
        self._usage_repository = usage_repository
        self._warn_threshold_usd = warn_threshold_usd
        self._monthly_limit_usd = monthly_limit_usd

    def get_status(self) -> BudgetStatus:
        spent_usd = self._usage_repository.get_spent_usd(_current_year_month())
        return BudgetStatus(
            spent_usd=spent_usd,
            warn_threshold_usd=self._warn_threshold_usd,
            monthly_limit_usd=self._monthly_limit_usd,
            is_near_limit=spent_usd >= self._warn_threshold_usd,
        )
