"""Por qué el motor dentro de Actions TIENE que ejecutarse de una en una (D2, #296).

Esto no es un informe de defecto: es la **medición que justifica** el grupo de
concurrencia del workflow que aloja al motor, y la razón de que ADR-082 diga que
serializar dejó de ser una precaución para pasar a ser la única protección.

El mecanismo, dicho corto. ``DurableWorkEngineStore`` reproduce el diario **una
sola vez, al construirse**, y a partir de ahí mantiene en memoria el índice de
identificadores y el de claves de idempotencia. Dos almacenes construidos sobre
el mismo fichero tienen cada uno su copia, y **ninguno ve lo que anexa el otro**.
Sus dos defensas -«ese ``work_id`` ya existe» y «esa clave ya se sirvió»- son
comprobaciones contra esa memoria, así que las dos pasan.

En producción esas dos lecturas son dos runners de GitHub Actions. Aquí son dos
objetos en el mismo proceso, **a propósito**: el fallo no es la simultaneidad,
es que dos lecturas independientes del diario no se ven entre sí. Reproducirlo
sin carreras lo hace determinista -mismo resultado siempre, sin plazos ni
suerte- en vez de una prueba que unos días pasa y otros no. Este repositorio ya
pagó una de esas hoy mismo (H-15, #290).

Si alguna de estas pruebas empieza a fallar, NO se ajusta: significa que alguien
hizo el almacén seguro entre procesos, y entonces hay que revisar ADR-082 y
decidir si el grupo de concurrencia sigue haciendo falta.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.domain.errors import DuplicateIdError
from sirius_engine.domain.work_item import WorkItem, WorkItemClass

AHORA = datetime(2026, 8, 24, 2, 0, tzinfo=UTC)


def _crear(almacen: DurableWorkEngineStore, *, work_id: str, clave: str | None = None) -> WorkItem:
    """Una petición de trabajo cualquiera. Lo que importa es el `work_id`."""
    return almacen.create_work_item(
        work_id=work_id,
        peticion_original="implementa X",
        objetivo="objetivo de prueba",
        contexto_origen=("incidencia:296",),
        entregable="entregable de prueba",
        criterio_terminado="criterio de prueba",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=AHORA,
        idempotency_key=clave,
    )


def _registros(diario: Path) -> list[dict[str, Any]]:
    if not diario.exists():
        return []
    return [json.loads(linea) for linea in diario.read_text(encoding="utf-8").splitlines() if linea]


def _creaciones_de(diario: Path, work_id: str) -> list[dict[str, Any]]:
    return [
        r
        for r in _registros(diario)
        if r.get("kind") == "work_item_created" and r.get("aggregate_id") == work_id
    ]


# --- Primero: dentro de UNA invocación las defensas funcionan --------------
#
# Va antes a propósito. Sin esto, las pruebas de abajo no distinguirían «el
# almacén no cruza procesos» de «el almacén no protege nada», que son cosas muy
# distintas y solo una es cierta.


def test_un_solo_almacen_rechaza_el_identificador_repetido(tmp_path: Path) -> None:
    almacen = DurableWorkEngineStore(tmp_path / "diario.jsonl")
    _crear(almacen, work_id="WI-D2-0001")

    with pytest.raises(DuplicateIdError):
        _crear(almacen, work_id="WI-D2-0001")


def test_un_solo_almacen_respeta_la_clave_de_idempotencia(tmp_path: Path) -> None:
    diario = tmp_path / "diario.jsonl"
    almacen = DurableWorkEngineStore(diario)

    primero = _crear(almacen, work_id="WI-D2-0002", clave="orden-42")
    segundo = _crear(almacen, work_id="WI-D2-0002", clave="orden-42")

    assert primero == segundo, "la clave de idempotencia debe devolver el mismo WorkItem"
    assert len(_creaciones_de(diario, "WI-D2-0002")) == 1, "no debe anexar dos veces"


# --- Y ahora el peligro: dos lecturas independientes del mismo diario ------


def test_dos_almacenes_sobre_el_mismo_diario_crean_el_trabajo_dos_veces(tmp_path: Path) -> None:
    """La demostración: el identificador repetido NO se detecta entre lecturas.

    Los dos almacenes se construyen ANTES de que ninguno escriba, que es
    exactamente lo que ocurre cuando dos invocaciones del motor arrancan sobre
    el mismo commit. En producción esto son dos incidencias, dos ramas y dos PRs
    para una sola petición.
    """
    diario = tmp_path / "diario.jsonl"

    primero = DurableWorkEngineStore(diario)
    segundo = DurableWorkEngineStore(diario)  # lee el mismo diario, todavía vacío

    _crear(primero, work_id="WI-D2-0003")
    _crear(segundo, work_id="WI-D2-0003")  # no levanta DuplicateIdError

    creaciones = _creaciones_de(diario, "WI-D2-0003")
    assert len(creaciones) == 2, (
        "si esto deja de dar 2, alguien hizo el almacén seguro entre procesos: "
        "revisa ADR-082 y decide si el grupo de concurrencia sigue haciendo falta"
    )


def test_dos_almacenes_sobre_el_mismo_diario_ignoran_la_clave_de_idempotencia(
    tmp_path: Path,
) -> None:
    """La clave de idempotencia tampoco cruza: vive en el índice en memoria."""
    diario = tmp_path / "diario.jsonl"

    primero = DurableWorkEngineStore(diario)
    segundo = DurableWorkEngineStore(diario)

    _crear(primero, work_id="WI-D2-0004", clave="orden-77")
    _crear(segundo, work_id="WI-D2-0004", clave="orden-77")

    assert len(_creaciones_de(diario, "WI-D2-0004")) == 2, (
        "la misma clave de idempotencia servida dos veces: es lo que ADR-082 "
        "declara como el daño peor, porque ya ha escrito en GitHub"
    )


def test_los_dos_registros_comparten_numero_de_secuencia(tmp_path: Path) -> None:
    """Y el diario queda con dos registros distintos numerados igual.

    ``replay()`` no comprueba secuencias -no las menciona-, así que este diario
    se absorbe sin una sola queja. Es la mitad del defecto que no se ve.
    """
    diario = tmp_path / "diario.jsonl"

    primero = DurableWorkEngineStore(diario)
    segundo = DurableWorkEngineStore(diario)
    _crear(primero, work_id="WI-D2-0005")
    _crear(segundo, work_id="WI-D2-0005")

    secuencias = [r["sequence"] for r in _creaciones_de(diario, "WI-D2-0005")]
    assert secuencias == [1, 1], f"se esperaban dos registros numerados 1, hay {secuencias}"

    # Y el almacén los relee sin protestar: el diario corrupto pasa por bueno.
    assert len(DurableWorkEngineStore(diario).list_events()) == 2
