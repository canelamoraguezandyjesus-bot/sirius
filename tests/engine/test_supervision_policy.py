"""Política de decisión del supervisor (C1-P5, incidencia #232).

Función pura: sin almacén, sin observador, sin reloj real -solo ``Run`` y
``SupervisorPolicy`` de entrada, ``SupervisionDecision`` de salida-.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sirius_engine.domain.run import Run, RunState
from sirius_engine.domain.supervision import (
    SupervisionDecision,
    SupervisorPolicy,
    decidir_politica,
)
from sirius_engine.domain.worker_ref import WorkerRef

_AHORA = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
_WORKER = WorkerRef(adapter="claude-code", perfil_ref="perfiles/prueba", perfil_version=1)
_WORKER_ALTERNATIVO = WorkerRef(adapter="codex", perfil_ref="perfiles/prueba", perfil_version=1)


def _run_perdido(*, intento: int, worker: WorkerRef = _WORKER) -> Run:
    """Un ``Run`` en ``FINISHED(LOST)`` con el ``intento`` pedido.

    Construido directamente (no vía el almacén): a ``decidir_politica`` solo
    le importan ``intento`` y ``worker``, así que un doble mínimo basta.
    """
    return Run(
        run_id=f"RUN-{intento}",
        work_id="WI-0001",
        paso="paso-1",
        worker=worker,
        work_package={},
        intento=intento,
        estado=RunState.FINISHED,
        deadline=_AHORA + timedelta(hours=1),
        created_at=_AHORA - timedelta(hours=1),
        updated_at=_AHORA,
    )


def test_primer_intento_perdido_se_reactiva() -> None:
    politica = SupervisorPolicy(max_reactivaciones=1, max_sustituciones=1)
    assert decidir_politica(_run_perdido(intento=1), policy=politica) is (
        SupervisionDecision.REACTIVATE
    )


def test_tras_agotar_reactivaciones_se_sustituye_si_hay_alternativa() -> None:
    politica = SupervisorPolicy(
        max_reactivaciones=1, max_sustituciones=1, worker_alternativo=_WORKER_ALTERNATIVO
    )
    assert decidir_politica(_run_perdido(intento=2), policy=politica) is (
        SupervisionDecision.SUBSTITUTE_WORKER
    )


def test_sin_worker_alternativo_configurado_se_escala_directamente() -> None:
    """No inventar una alternativa: sin ``worker_alternativo``, salta a ESCALATE."""
    politica = SupervisorPolicy(max_reactivaciones=1, max_sustituciones=1, worker_alternativo=None)
    assert decidir_politica(_run_perdido(intento=2), policy=politica) is (
        SupervisionDecision.ESCALATE
    )


def test_tras_agotar_reactivaciones_y_sustituciones_se_escala() -> None:
    politica = SupervisorPolicy(
        max_reactivaciones=1, max_sustituciones=1, worker_alternativo=_WORKER_ALTERNATIVO
    )
    # intento 1 reactiva, intento 2 sustituye, intento 3 ya sustituyó una vez: escala
    assert (
        decidir_politica(_run_perdido(intento=3, worker=_WORKER_ALTERNATIVO), policy=politica)
        is SupervisionDecision.ESCALATE
    )


def test_el_worker_alternativo_igual_al_actual_no_cuenta_como_alternativa() -> None:
    """Si el Run ya corre con el `worker_alternativo` configurado, sustituir sería un no-op."""
    politica = SupervisorPolicy(
        max_reactivaciones=1, max_sustituciones=1, worker_alternativo=_WORKER_ALTERNATIVO
    )
    assert (
        decidir_politica(_run_perdido(intento=2, worker=_WORKER_ALTERNATIVO), policy=politica)
        is SupervisionDecision.ESCALATE
    )


def test_decidir_politica_es_determinista_c1_p5() -> None:
    politica = SupervisorPolicy(worker_alternativo=_WORKER_ALTERNATIVO)
    run = _run_perdido(intento=2)
    assert decidir_politica(run, policy=politica) == decidir_politica(run, policy=politica)


def test_max_reactivaciones_no_puede_ser_negativo() -> None:
    with pytest.raises(ValueError):
        SupervisorPolicy(max_reactivaciones=-1)


def test_max_sustituciones_no_puede_ser_negativo() -> None:
    with pytest.raises(ValueError):
        SupervisorPolicy(max_sustituciones=-1)
