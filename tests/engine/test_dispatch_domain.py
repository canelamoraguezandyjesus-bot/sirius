"""``orden_enlazada``: la referencia de la orden del propietario en la evidencia (C2, #240)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO, orden_enlazada
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item


def _work_item(*, evidencia: tuple[str, ...] = ()) -> WorkItem:
    base = create_work_item(
        work_id="WI-ORDEN-0001",
        peticion_original="implementa X",
        objetivo="objetivo de prueba",
        contexto_origen=("incidencia:240",),
        entregable="entregable de prueba",
        criterio_terminado="criterio de prueba",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
    )
    return dataclasses.replace(base, evidencia=evidencia)


def test_sin_evidencia_no_hay_orden_enlazada() -> None:
    assert orden_enlazada(_work_item(evidencia=())) is None


def test_evidencia_sin_marcador_no_cuenta_como_orden() -> None:
    work_item = _work_item(evidencia=("diario:episodio-1", "pr:https://example.invalid/pr/1"))
    assert orden_enlazada(work_item) is None


def test_marcador_sin_referencia_no_cuenta_como_orden() -> None:
    work_item = _work_item(evidencia=(MARCADOR_ORDEN_PROPIETARIO,))
    assert orden_enlazada(work_item) is None


def test_marcador_con_espacios_sin_referencia_no_cuenta() -> None:
    work_item = _work_item(evidencia=(f"{MARCADOR_ORDEN_PROPIETARIO}   ",))
    assert orden_enlazada(work_item) is None


def test_evidencia_con_marcador_devuelve_la_referencia() -> None:
    referencia = "https://github.com/acme/repo/issues/241#issuecomment-987654321"
    work_item = _work_item(evidencia=(f"{MARCADOR_ORDEN_PROPIETARIO}{referencia}",))
    assert orden_enlazada(work_item) == referencia


def test_se_queda_con_la_primera_entrada_marcada() -> None:
    work_item = _work_item(
        evidencia=(
            f"{MARCADOR_ORDEN_PROPIETARIO}primera",
            f"{MARCADOR_ORDEN_PROPIETARIO}segunda",
        )
    )
    assert orden_enlazada(work_item) == "primera"
