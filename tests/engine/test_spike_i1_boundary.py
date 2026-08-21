"""S3-P1, S3-P2, S3-P4 -- clasificador de bordes y tabla del spike I1 (incidencia #211).

Toda esta prueba corre sobre los fixtures congelados en
``experiments/work_engine_spike_i1/fixtures/`` -la misma forma que devuelve
la API real, capturada de mediciones reales sobre este repositorio (ver
``RESULTADOS.md``)-, nunca contra `gh` ni contra un reloj real: S3-P4 exige
que la sonda, sobre los mismos datos guardados, produzca siempre el mismo
resultado.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from experiments.work_engine_spike_i1 import boundary
from experiments.work_engine_spike_i1.boundary import (
    EstadoBorde,
    construir_tabla,
    observacion_desde_fixture,
)

_SPIKE_DIR = Path(__file__).resolve().parents[2] / "experiments" / "work_engine_spike_i1"
_FIXTURES_DIR = _SPIKE_DIR / "fixtures"

_BORDE_ESPERADO = {
    "cancelado": EstadoBorde.CANCELADO,
    "no_arrancado_perpetuo": EstadoBorde.NO_ARRANCADO,
    "no_arrancado_cancelado_sin_job": EstadoBorde.NO_ARRANCADO,
    "skipped": EstadoBorde.SKIPPED,
    "completado_exito": EstadoBorde.COMPLETADO_EXITO,
    "completado_fallo": EstadoBorde.COMPLETADO_FALLO,
}


def _cargar_todos() -> tuple[boundary.ObservacionRun, ...]:
    observaciones = []
    for nombre in sorted(_BORDE_ESPERADO):
        datos = json.loads((_FIXTURES_DIR / f"{nombre}.json").read_text(encoding="utf-8"))
        observaciones.append(observacion_desde_fixture(datos))
    return tuple(observaciones)


def test_los_seis_fixtures_existen_y_cubren_los_cuatro_bordes_exigidos() -> None:
    nombres = {p.stem for p in _FIXTURES_DIR.glob("*.json")}
    assert nombres == set(_BORDE_ESPERADO)
    bordes_cubiertos = set(_BORDE_ESPERADO.values())
    assert {
        EstadoBorde.CANCELADO,
        EstadoBorde.NO_ARRANCADO,
        EstadoBorde.SKIPPED,
        EstadoBorde.COMPLETADO_EXITO,
    } <= bordes_cubiertos


def test_cada_fixture_clasifica_al_borde_que_le_corresponde() -> None:
    for nombre, esperado in _BORDE_ESPERADO.items():
        datos = json.loads((_FIXTURES_DIR / f"{nombre}.json").read_text(encoding="utf-8"))
        obs = observacion_desde_fixture(datos)
        assert boundary.clasificar(obs) is esperado, nombre


def test_no_arrancado_nunca_se_confunde_con_completado_fallo() -> None:
    """El caso exacto que la incidencia pide poder distinguir (S3-P1, requisito 3)."""
    datos_no_arrancado = json.loads(
        (_FIXTURES_DIR / "no_arrancado_perpetuo.json").read_text(encoding="utf-8")
    )
    datos_fallo = json.loads((_FIXTURES_DIR / "completado_fallo.json").read_text(encoding="utf-8"))

    obs_no_arrancado = observacion_desde_fixture(datos_no_arrancado)
    obs_fallo = observacion_desde_fixture(datos_fallo)

    assert boundary.clasificar(obs_no_arrancado) is EstadoBorde.NO_ARRANCADO
    assert boundary.clasificar(obs_fallo) is EstadoBorde.COMPLETADO_FALLO
    assert boundary.clasificar(obs_no_arrancado) is not boundary.clasificar(obs_fallo)
    # La señal estructural que los separa: un run que falló ejecutando tuvo
    # un job de verdad con runner asignado; uno que no arrancó, no.
    assert obs_no_arrancado.total_jobs == 0
    assert obs_fallo.total_jobs == 1
    assert obs_fallo.job_runner_id is not None


def test_construir_tabla_es_determinista_sobre_los_mismos_fixtures() -> None:
    observaciones = _cargar_todos()

    tabla_1 = construir_tabla(observaciones)
    tabla_2 = construir_tabla(observaciones)

    assert tabla_1 == tabla_2
    assert len(tabla_1) == len(_BORDE_ESPERADO)


def test_tabla_incluye_una_fila_por_borde_exigido() -> None:
    observaciones = _cargar_todos()
    tabla = construir_tabla(observaciones)

    bordes_en_tabla = {fila.borde for fila in tabla}
    assert {
        EstadoBorde.CANCELADO,
        EstadoBorde.NO_ARRANCADO,
        EstadoBorde.SKIPPED,
        EstadoBorde.COMPLETADO_EXITO,
    } <= bordes_en_tabla


def test_logs_404_del_caso_no_arrancado_perpetuo_se_conserva_como_dato() -> None:
    """Un 404 al pedir los registros es un dato, no un error de la sonda."""
    datos = json.loads((_FIXTURES_DIR / "no_arrancado_perpetuo.json").read_text(encoding="utf-8"))
    obs = observacion_desde_fixture(datos)
    tabla = construir_tabla((obs,))

    assert tabla[0].logs_http == "404"
    assert tabla[0].borde is EstadoBorde.NO_ARRANCADO


def _sin_llamadas_a_reloj_real(modulo_path: Path) -> list[str]:
    """AST -no una búsqueda de texto-, mismo método que `tests/engine/test_boundary.py`
    usa para la frontera sirius/sirius_engine: hace la ausencia de reloj real
    comprobable por inspección del árbol sintáctico, no por convención."""
    arbol = ast.parse(modulo_path.read_text(encoding="utf-8"), filename=str(modulo_path))
    prohibidos = {
        ("datetime", "now"),
        ("time", "time"),
        ("time", "monotonic"),
        ("time", "perf_counter"),
    }
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            valor = nodo.func.value
            if isinstance(valor, ast.Name) and (valor.id, nodo.func.attr) in prohibidos:
                hallazgos.append(f"{valor.id}.{nodo.func.attr}() en línea {nodo.lineno}")
    return hallazgos


def test_boundary_py_no_contiene_ninguna_llamada_a_reloj_real() -> None:
    assert _sin_llamadas_a_reloj_real(_SPIKE_DIR / "boundary.py") == []


def test_probe_py_no_contiene_ninguna_llamada_a_reloj_real() -> None:
    assert _sin_llamadas_a_reloj_real(_SPIKE_DIR / "probe.py") == []
