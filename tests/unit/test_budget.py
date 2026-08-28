"""Unit tests for BudgetTracker's in-memory fallback (no repository injected)."""

from __future__ import annotations

import pytest

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


# --- Gasto de audio (Model Studio, hallazgo MS-A04) ---------------------


def test_transcription_cost_counts_against_the_same_monthly_total() -> None:
    """Sin tabla nueva ni migración: suma al mismo total que el texto."""
    tracker = BudgetTracker()

    tracker.record_usage(input_tokens=1_000_000, output_tokens=0)
    after_text = tracker.spent_usd
    tracker.record_transcription(audio_seconds=600.0)

    assert tracker.spent_usd > after_text


def test_speech_cost_counts_against_the_same_monthly_total() -> None:
    tracker = BudgetTracker()

    tracker.record_speech(character_count=100_000)

    assert tracker.spent_usd > 0.0


def test_audio_spend_can_exhaust_the_budget_and_block_sending() -> None:
    """SV-011 de verdad: si el audio no se apuntara, el tope nunca llegaría."""
    policy = BudgetPolicy(monthly_limit_usd=1.0, transcription_cost_usd_per_minute=0.5)
    tracker = BudgetTracker(policy=policy)

    assert tracker.has_remaining_budget()
    tracker.record_transcription(audio_seconds=120.0)

    assert not tracker.has_remaining_budget()


def test_negative_audio_quantities_never_refund_budget() -> None:
    """Una duración o un recuento absurdos no pueden devolver saldo."""
    tracker = BudgetTracker()
    tracker.record_speech(character_count=50_000)
    spent = tracker.spent_usd

    tracker.record_transcription(audio_seconds=-3600.0)
    tracker.record_speech(character_count=-1_000_000)

    assert tracker.spent_usd == spent


# --- H-30 (auditoría #396): comprobar y gastar en UNA operación ---------------


class _RepositorioEnMemoria:
    def __init__(self) -> None:
        self.total: dict[str, float] = {}

    def get_spent_usd(self, year_month: str) -> float:
        return self.total.get(year_month, 0.0)

    def add_spent_usd(self, year_month: str, amount_usd: float) -> None:
        self.total[year_month] = self.total.get(year_month, 0.0) + amount_usd


def _tracker_al_borde(remanente_usd: float) -> BudgetTracker:
    politica = BudgetPolicy(monthly_limit_usd=20.0)
    tracker = BudgetTracker(politica)
    # Dejar el mes gastado hasta que quede exactamente `remanente_usd`.
    tracker.record_usage(
        input_tokens=0,
        output_tokens=int((20.0 - remanente_usd) / 15.0 * 1_000_000),
    )
    return tracker


def test_h30_dos_reservas_que_juntas_exceden_no_pasan_las_dos() -> None:
    """La reproducción del informe, sin carrera de hilos: la admisión es una
    RESERVA atómica que cuenta lo en vuelo. Dos peticiones de ~3 USD con 4 de
    remanente: la primera entra, la segunda NO —antes, ambas leían «queda
    sitio» y se enviaban las dos—."""
    tracker = _tracker_al_borde(4.0)
    primera = tracker.reservar(3.0)
    segunda = tracker.reservar(3.0)
    assert primera is not None, "con remanente de sobra, la primera tenía que entrar"
    assert segunda is None, (
        "la segunda reserva entró con la primera aún en vuelo: el tope dejó de "
        "ser una cota, que es exactamente H-30"
    )


def test_h30_al_salir_del_with_la_reserva_se_suelta_y_el_coste_real_queda() -> None:
    """El asiento del coste real lo hacen los `record_*` de siempre DENTRO del
    `with`; la salida suelta la reserva. Coste real menor que el estimado: el
    sitio vuelve."""
    tracker = _tracker_al_borde(4.0)
    with tracker.reserva(3.0) as admitida:
        assert admitida is not None
        # 1 USD reales (a 15 USD/millón de tokens de salida).
        tracker.record_usage(input_tokens=0, output_tokens=int(1.0 / 15.0 * 1_000_000))
    assert tracker.spent_usd == pytest.approx(17.0, abs=1e-4)
    otra = tracker.reservar(2.5)
    assert otra is not None, "soltada la primera, el remanente real (~3.0) admite 2.5"


def test_h30_una_reserva_abandonada_no_puede_quedar_colgada() -> None:
    """Si la petición revienta, la reserva se suelta SIN apuntar coste: el
    camino con `with` lo garantiza incluso ante excepción."""
    tracker = _tracker_al_borde(4.0)
    with pytest.raises(RuntimeError), tracker.reserva(3.0) as admitida:
        assert admitida
        raise RuntimeError("la petición reventó a mitad")
    assert tracker.spent_usd == pytest.approx(16.0), "una petición rota apuntó coste"
    de_nuevo = tracker.reservar(3.0)
    assert de_nuevo is not None, "la reserva rota quedó colgada y bloquea el sitio"


def test_h30_una_peticion_sola_se_admite_con_la_regla_de_siempre() -> None:
    """Criterio de parada (b): con remanente > 0, UNA petición entra aunque su
    estimado exceda el remanente entero —igual que `has_remaining_budget`
    admitía hoy—. La reserva protege de la CONCURRENCIA, no endurece el pacto."""
    tracker = _tracker_al_borde(0.5)
    sola = tracker.reservar(3.0)
    assert sola is not None, (
        "una petición sola con remanente positivo quedó bloqueada: la reserva "
        "endureció el tope pactado en DR-018"
    )


def test_h30_los_tres_carriles_usan_la_misma_primitiva() -> None:
    """Pregunta 3 de la nota de arranque, comprobada sobre el CÓDIGO de los
    call sites de producción: los tres carriles admiten por `reserva(` y
    ninguno decide ya la admisión con `has_remaining_budget()` —que queda solo
    como aviso de cortesía (el micrófono) y para los indicadores—."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    proveedor = (raiz / "src/sirius/adapters/llm/openai_responses.py").read_text(encoding="utf-8")
    voz = (raiz / "src/sirius/application/studio_voice.py").read_text(encoding="utf-8")

    assert "with self._budget_tracker.reserva(" in proveedor, (
        "el carril de texto no admite por reserva"
    )
    # Se cuentan LÍNEAS de código, no apariciones: el docstring del propio
    # ayudante cita la llamada como ejemplo y una cuenta por subcadena lo
    # confundiría con un tercer carril (la familia vacua mordió aquí también).
    lineas_con_reserva = [
        linea for linea in voz.splitlines() if linea.strip().startswith("with self._reserva(")
    ]
    assert "def _reserva(" in voz, "los carriles de voz no admiten por reserva"
    assert len(lineas_con_reserva) == 2, f"transcripción Y síntesis, las dos: {lineas_con_reserva}"
    assert "has_remaining_budget" not in proveedor, (
        "el carril de texto sigue decidiendo la admisión con comprobar-y-gastar"
    )
