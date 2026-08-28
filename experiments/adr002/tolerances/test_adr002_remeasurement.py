"""Pruebas propias de la remedicion 02B.

    uv run pytest experiments/adr002 -q

Verifican el ARNES de la remedicion, no los umbrales: que el ciclo se
repite de verdad sobre copias limpias, que el minimo de repeticiones y de
sesiones se hace cumplir en ejecucion, y que la evidencia publicada
declara su alcance LAB-LINUX sin trasladarse a Windows.

Una medicion no puede fallar aqui por ser lenta. Lo que si puede fallar
es que la restitucion no sea identica o que el integrity-check no pase:
esas dos no admiten margen.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from experiments.adr002.tolerances import corpus, remeasurement
from experiments.adr002.tolerances.run_remeasurement import (
    ARRASTRADAS,
    ARTIFACTS_DIR,
    FICHERO_V01,
    FICHERO_V02,
)


@pytest.fixture(scope="module")
def base_referencia() -> Path:
    database_path, _ids = corpus.corpus_de_referencia("adr002_remed_test_")
    return database_path


# --------------------------------------------------------------------------
# Minimos exigidos por el 02B, comprobados en ejecucion.
# --------------------------------------------------------------------------


def test_el_ciclo_rechaza_menos_de_treinta_repeticiones(base_referencia: Path) -> None:
    with pytest.raises(remeasurement.EvidenciaInsuficienteError):
        remeasurement.medir_ciclo_repetido(
            base_referencia, repeticiones=remeasurement.CICLOS_MINIMOS - 1
        )


def test_las_sesiones_rechazan_menos_de_cinco(base_referencia: Path) -> None:
    ids = corpus.CorpusIds(
        conversation_id=1,
        proyecto_activo_id=1,
        proyecto_ajeno_id=2,
        memoria_unica_id=1,
        memoria_no_reportable_id=2,
        memoria_ajena_id=3,
        memorias_vigentes=499,
        memorias_frecuentes=200,
        mensajes=5_000,
        decisiones_aprobadas=50,
    )

    with pytest.raises(remeasurement.EvidenciaInsuficienteError):
        remeasurement.medir_sesiones(
            base_referencia, ids, sesiones=remeasurement.SESIONES_MINIMAS - 1
        )


def test_los_minimos_del_paquete_02b_son_los_declarados() -> None:
    assert remeasurement.CICLOS_MINIMOS == 30
    assert remeasurement.SESIONES_MINIMAS == 5


# --------------------------------------------------------------------------
# El ciclo se repite de verdad, sobre copias limpias.
# --------------------------------------------------------------------------


def test_el_ciclo_no_altera_la_base_de_referencia(base_referencia: Path) -> None:
    """Cada repeticion trabaja sobre una copia: la base original debe
    conservar sus indices intactos al terminar."""
    antes = _objetos_fts(base_referencia)

    remeasurement.medir_ciclo_repetido(base_referencia, repeticiones=30, warmup=1)

    assert _objetos_fts(base_referencia) == antes
    assert antes != []


def test_el_ciclo_registra_distribucion_completa_por_operacion(
    base_referencia: Path,
) -> None:
    resultado = remeasurement.medir_ciclo_repetido(base_referencia, repeticiones=30, warmup=1)

    for clave in ("borrado", "construccion_desde_canon", "reconstruccion_desde_canon"):
        distribucion = resultado[clave]
        assert distribucion["n"] == 30
        assert distribucion["min_ms"] <= distribucion["p50_ms"] <= distribucion["p95_ms"]
        assert distribucion["p95_ms"] <= distribucion["p99_ms"] <= distribucion["max_ms"]
        assert distribucion["resolucion_p99"]


def test_la_restitucion_identica_y_el_integrity_check_son_del_cien_por_cien(
    base_referencia: Path,
) -> None:
    """Estas dos no admiten margen: son la puerta 5 de ADR-002."""
    resultado = remeasurement.medir_ciclo_repetido(base_referencia, repeticiones=30, warmup=1)
    tasas = resultado["tasas_de_exito"]

    for clave in (
        "borrado_completo",
        "sin_rastro_de_sombras",
        "construccion_filas_identicas",
        "reconstruccion_filas_identicas",
        "integrity_check_ok",
    ):
        assert tasas[clave]["tasa"] == 1.0, f"{clave}: {tasas[clave]}"
    assert resultado["todas_las_comprobaciones_al_100"] is True
    assert resultado["repeticiones_con_fallo"] == []


def test_el_rebuild_interno_se_registra_solo_como_observacion(
    base_referencia: Path,
) -> None:
    """No puede presentarse como reconstruccion desde el canon."""
    resultado = remeasurement.medir_ciclo_repetido(base_referencia, repeticiones=30, warmup=1)
    observacion = resultado["observacion_rebuild_interno"]

    assert "advertencia" in observacion
    assert "no desde memory_revisions" in observacion["advertencia"]
    assert "OBSERVACION" in observacion["advertencia"]


def _objetos_fts(database_path: Path) -> list[str]:
    connection = sqlite3.connect(str(database_path))
    try:
        return [
            str(nombre)
            for (nombre,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE 'knowledge\\_fts%' ESCAPE '\\' "
                "OR name LIKE 'message\\_fts%' ESCAPE '\\' ORDER BY name"
            ).fetchall()
        ]
    finally:
        connection.close()


# --------------------------------------------------------------------------
# Evidencia publicada: alcance y conservacion del v0.1.
# --------------------------------------------------------------------------


def test_el_artefacto_v01_se_conserva_sin_modificar() -> None:
    v01 = ARTIFACTS_DIR / FICHERO_V01
    if not v01.exists():
        pytest.skip("el paquete 02 todavia no se ha ejecutado en este arbol")

    payload = json.loads(v01.read_text(encoding="utf-8"))

    assert payload["estado"] == "PROPUESTO"
    assert "escenarios" in payload
    assert payload["corpus"]["mensajes"] == 5_000


def test_la_remedicion_declara_alcance_lab_linux_y_windows_pendiente() -> None:
    destino = ARTIFACTS_DIR / FICHERO_V02
    if not destino.exists():
        pytest.skip("el runner de remedicion todavia no se ha ejecutado")

    payload = json.loads(destino.read_text(encoding="utf-8"))

    assert payload["entorno"]["alcance"] == "LAB-LINUX"
    assert "LAB-LINUX" in payload["alcance"]
    windows = payload["alcance"]["ACEPTACION-WINDOWS"]
    assert windows.startswith("PENDIENTE")
    assert "Ninguna cifra absoluta" in windows
    assert "traslada automaticamente a Windows" in windows
    assert "aceptacion_windows" in payload["no_medido"]


def test_la_remedicion_arrastra_literalmente_la_evidencia_valida_del_02() -> None:
    """Lo que el 02B no corrige debe copiarse, no reejecutarse."""
    v01_path = ARTIFACTS_DIR / FICHERO_V01
    v02_path = ARTIFACTS_DIR / FICHERO_V02
    if not (v01_path.exists() and v02_path.exists()):
        pytest.skip("faltan artefactos de alguna de las dos rondas")

    v01 = json.loads(v01_path.read_text(encoding="utf-8"))
    v02 = json.loads(v02_path.read_text(encoding="utf-8"))
    arrastrada = v02["evidencia_arrastrada_del_paquete_02"]

    for clave in ARRASTRADAS:
        assert arrastrada[clave] == v01["escenarios"][clave], clave
    assert v02["conserva_sin_modificar"] == FICHERO_V01


def test_la_remedicion_publica_las_dos_correcciones_de_metodo() -> None:
    destino = ARTIFACTS_DIR / FICHERO_V02
    if not destino.exists():
        pytest.skip("el runner de remedicion todavia no se ha ejecutado")

    remedidos = json.loads(destino.read_text(encoding="utf-8"))["escenarios_remedidos"]
    ciclo = remedidos["E-CICLO-30_borrado_construccion_reconstruccion"]
    sesiones = remedidos["E-SESIONES-5_variacion_entre_ejecuciones"]

    assert ciclo["repeticiones"] >= remeasurement.CICLOS_MINIMOS
    assert ciclo["todas_las_comprobaciones_al_100"] is True
    assert sesiones["sesiones"] >= remeasurement.SESIONES_MINIMAS
    assert len(sesiones["por_sesion"]) == sesiones["sesiones"]
    assert sesiones["variacion_entre_sesiones"]["peor_variacion_relativa_observada"] is not None
    assert "MISMO PROCESO" in sesiones["limite_declarado"]


def test_las_sesiones_publicadas_son_estables_en_orden_y_conjunto() -> None:
    destino = ARTIFACTS_DIR / FICHERO_V02
    if not destino.exists():
        pytest.skip("el runner de remedicion todavia no se ha ejecutado")

    payload = json.loads(destino.read_text(encoding="utf-8"))
    resumen = payload["escenarios_remedidos"]["E-SESIONES-5_variacion_entre_ejecuciones"][
        "estabilidad_entre_sesiones"
    ]["resumen"]

    assert resumen["orden_estable_entre_sesiones"] is True
    assert resumen["conjunto_estable_entre_sesiones"] is True
