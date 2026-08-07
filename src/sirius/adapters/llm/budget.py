"""Budget guard for the OpenAI adapter.

DR-018 ("Presupuesto operativo") defines a *monthly* operating envelope (20
USD, warn at 15 USD) computed from real provider usage, with blocking
"antes de enviar" (before sending). A monthly cap that resets every time the
process restarts would not actually be monthly, so accumulated spend is
persisted via an injected ``LLMUsageRepository`` (the minimal persistence
DR-018 requires) keyed by the current UTC year-month; it survives restarts
and rolls over automatically once the month changes. When no repository is
injected (e.g. tests, or fake-provider mode where no budget is ever checked),
the tracker falls back to a process-lifetime in-memory counter.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BudgetPolicy:
    """Pricing and thresholds from DR-018 (subject to external revision).

    Las dos tarifas de audio se añaden para Model Studio: una sesión de
    grabación suma una transcripción y una síntesis por turno además del coste
    de texto. Sin ellas el gasto de audio no se apuntaría en ninguna parte y el
    tope mensual dejaría de proteger de verdad (hallazgo MS-A04). El precio
    vive aquí, en un solo sitio, y no repartido por cada adaptador.
    """

    monthly_limit_usd: float = 20.0
    warn_threshold_usd: float = 15.0
    input_cost_usd_per_million_tokens: float = 2.50
    output_cost_usd_per_million_tokens: float = 15.0
    transcription_cost_usd_per_minute: float = 0.003
    speech_cost_usd_per_million_characters: float = 15.0


class LLMUsageRepository(Protocol):
    """Persists accumulated spend per UTC year-month (e.g. ``"2026-07"``)."""

    def get_spent_usd(self, year_month: str) -> float:
        """Return the spend recorded so far for that month, or 0.0 if none."""
        ...

    def add_spent_usd(self, year_month: str, amount_usd: float) -> None:
        """Add ``amount_usd`` to that month's running total."""
        ...


def _current_year_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


class BudgetTracker:
    """Tracks estimated spend and blocks new requests once the limit is reached."""

    def __init__(
        self,
        policy: BudgetPolicy | None = None,
        usage_repository: LLMUsageRepository | None = None,
    ) -> None:
        self._policy = policy or BudgetPolicy()
        self._usage_repository = usage_repository
        self._in_memory_spent_usd = 0.0
        self._lock = threading.Lock()

    @property
    def spent_usd(self) -> float:
        """Spend recorded for the current UTC month (persisted if a repository was given)."""
        if self._usage_repository is None:
            with self._lock:
                return self._in_memory_spent_usd
        return self._usage_repository.get_spent_usd(_current_year_month())

    def has_remaining_budget(self) -> bool:
        """Return whether a new request may be sent (checked before sending)."""
        return self.spent_usd < self._policy.monthly_limit_usd

    def is_near_limit(self) -> bool:
        return self.spent_usd >= self._policy.warn_threshold_usd

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record the real usage of a completed request against the budget."""
        self._record_cost(
            input_tokens / 1_000_000 * self._policy.input_cost_usd_per_million_tokens
            + output_tokens / 1_000_000 * self._policy.output_cost_usd_per_million_tokens
        )

    def record_transcription(self, audio_seconds: float) -> None:
        """Apunta el coste de transcribir ``audio_seconds`` de voz.

        Suma al MISMO total mensual que el texto, sin tabla nueva ni migración:
        el repositorio guarda dólares por mes y es indiferente a su origen. Por
        eso ``has_remaining_budget()`` no cambia y el bloqueo previo al envío
        pasa a cubrir también el audio.
        """
        minutes = max(0.0, audio_seconds) / 60.0
        self._record_cost(minutes * self._policy.transcription_cost_usd_per_minute)

    def record_speech(self, character_count: int) -> None:
        """Apunta el coste de sintetizar ``character_count`` caracteres."""
        characters = max(0, character_count)
        self._record_cost(
            characters / 1_000_000 * self._policy.speech_cost_usd_per_million_characters
        )

    def _record_cost(self, cost_usd: float) -> None:
        if self._usage_repository is None:
            with self._lock:
                self._in_memory_spent_usd += cost_usd
            return
        self._usage_repository.add_spent_usd(_current_year_month(), cost_usd)
