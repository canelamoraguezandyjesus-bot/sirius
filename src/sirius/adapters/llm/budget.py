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
from contextlib import contextmanager
from dataclasses import dataclass, field
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


@dataclass
class ReservaPresupuesto:
    """El resguardo de una admisión (H-30): importe estimado y si ya se soltó."""

    importe_usd: float
    liquidada: bool = field(default=False)


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
        self._reservado_usd = 0.0

    @property
    def spent_usd(self) -> float:
        """Spend recorded for the current UTC month (persisted if a repository was given)."""
        if self._usage_repository is None:
            with self._lock:
                return self._in_memory_spent_usd
        return self._usage_repository.get_spent_usd(_current_year_month())

    def has_remaining_budget(self) -> bool:
        """Return whether a new request may be sent (checked before sending).

        DESDE H-30 esto es el AVISO, no la puerta: la admisión real es
        :meth:`reservar`, que es atómica y cuenta lo que ya está en vuelo.
        Comprobar aquí y gastar después son dos operaciones, y dos peticiones
        concurrentes al borde del tope pasaban las dos (auditoría #396).
        """
        return self.spent_usd < self._policy.monthly_limit_usd

    # --- H-30: la admisión es una reserva atómica -------------------------

    def reservar(self, estimado_usd: float) -> ReservaPresupuesto | None:
        """Admitir (o no) una petición, contando lo que ya está EN VUELO.

        La regla, en dos mitades y con su porqué:

        - Sin nada en vuelo, la admisión es EXACTAMENTE la de siempre
          (``spent < limit``): una petición sola con remanente positivo entra
          aunque su estimado exceda el remanente, igual que DR-018 venía
          admitiendo. La reserva protege de la concurrencia; no endurece el
          pacto (criterio de parada (b) de la nota de arranque).
        - Con reservas vivas, la nueva tiene que demostrar que CABE JUNTA:
          ``spent + en_vuelo + estimado <= limit``. Es lo que impide que dos
          peticiones al borde del tope se cuelen las dos leyendo el mismo
          saldo.

        Devuelve la reserva admitida, o ``None`` si no hay sitio. Atómico
        bajo el candado del tracker: la lectura del gastado y el alta de la
        reserva ocurren sin que otra admisión se intercale. Cubre EL PROCESO
        (la aplicación de escritorio es uno, y texto y voz conviven ahí);
        cubrir varios procesos sería una reserva en el repositorio y se
        declara como límite, no se finge.
        """
        with self._lock:
            gastado = (
                self._in_memory_spent_usd
                if self._usage_repository is None
                else self._usage_repository.get_spent_usd(_current_year_month())
            )
            if self._reservado_usd == 0.0:
                admitida = gastado < self._policy.monthly_limit_usd
            else:
                admitida = (
                    gastado + self._reservado_usd + estimado_usd <= self._policy.monthly_limit_usd
                )
            if not admitida:
                return None
            reserva = ReservaPresupuesto(importe_usd=max(0.0, estimado_usd))
            self._reservado_usd += reserva.importe_usd
            return reserva

    def _soltar(self, reserva: ReservaPresupuesto) -> None:
        with self._lock:
            if reserva.liquidada:
                return
            reserva.liquidada = True
            self._reservado_usd = max(0.0, self._reservado_usd - reserva.importe_usd)

    @contextmanager
    def reserva(self, estimado_usd: float):  # type: ignore[no-untyped-def]
        """La reserva con la soltura garantizada.

        El coste REAL lo apuntan los ``record_*`` de siempre, DENTRO del
        ``with`` y con sus unidades naturales; la salida suelta la reserva
        -pase lo que pase-, así que una petición reventada no apunta coste ni
        deja el sitio bloqueado. Una sola forma para los tres carriles: no hay
        segunda API de asiento que pueda divergir de la primera.
        """
        admitida = self.reservar(estimado_usd)
        try:
            yield admitida
        finally:
            if admitida is not None:
                self._soltar(admitida)

    # --- Los costes como funciones puras de la política, para los estimados ---

    def costo_texto_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1_000_000 * self._policy.input_cost_usd_per_million_tokens
            + output_tokens / 1_000_000 * self._policy.output_cost_usd_per_million_tokens
        )

    def costo_transcripcion_usd(self, audio_seconds: float) -> float:
        return max(0.0, audio_seconds) / 60.0 * self._policy.transcription_cost_usd_per_minute

    def costo_sintesis_usd(self, character_count: int) -> float:
        return (
            max(0, character_count)
            / 1_000_000
            * self._policy.speech_cost_usd_per_million_characters
        )

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
