"""Pruebas propias del experimento de medicion de ADR-002.

Se ejecutan de forma independiente y NO forman parte de la suite de
Sirius 0.1: ``pyproject.toml`` fija ``testpaths = ["tests"]``, asi que
``uv run pytest`` no las recoge. Para lanzarlas:

    uv run pytest experiments/adr002 -q

Estas pruebas verifican el ARNES, no los umbrales. Una medicion no puede
fallar por ser lenta: eso seria fijar una tolerancia por la puerta de
atras, y las tolerancias las propone el Registro, no el codigo.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from experiments.adr002.tolerances import corpus, measurements
from experiments.adr002.tolerances.harness import (
    REPETICIONES_MINIMAS,
    RepeticionesInsuficientesError,
    medir,
    percentil,
)
from experiments.adr002.tolerances.run_measurements import ARTIFACTS_DIR, FICHERO

# --------------------------------------------------------------------------
# Arnes: percentiles, repeticiones minimas y reloj.
# --------------------------------------------------------------------------


def test_el_percentil_devuelve_siempre_una_muestra_observada() -> None:
    """Nearest-rank, nunca interpolado: un P99 interpolado podria dar un
    valor que nunca ocurrio, y el informe no debe afirmar eso."""
    muestras = [float(n) for n in range(1, 101)]

    for fraccion in (0.5, 0.95, 0.99):
        assert percentil(muestras, fraccion) in muestras


@pytest.mark.parametrize(
    ("fraccion", "esperado"),
    [(0.50, 50.0), (0.95, 95.0), (0.99, 99.0)],
)
def test_los_percentiles_conocidos_son_exactos(fraccion: float, esperado: float) -> None:
    muestras = [float(n) for n in range(1, 101)]

    assert percentil(muestras, fraccion) == esperado


def test_medir_rechaza_menos_repeticiones_de_las_exigidas() -> None:
    """El minimo del paquete 02 se hace cumplir en ejecucion, no solo en
    la documentacion."""
    with pytest.raises(RepeticionesInsuficientesError):
        medir(lambda: None, repeticiones=REPETICIONES_MINIMAS - 1, warmup=1)


def test_medir_descarta_el_warmup_y_lo_declara() -> None:
    llamadas: list[int] = []

    distribucion = medir(lambda: llamadas.append(1), repeticiones=REPETICIONES_MINIMAS, warmup=7)

    assert distribucion.warmup_descartado == 7
    assert distribucion.n == REPETICIONES_MINIMAS
    # Las llamadas totales incluyen el warm-up; las muestras, no.
    assert len(llamadas) == REPETICIONES_MINIMAS + 7


def test_la_resolucion_del_p99_se_declara_segun_el_numero_de_muestras() -> None:
    pocas = medir(lambda: None, repeticiones=30, warmup=0)
    muchas = medir(lambda: None, repeticiones=100, warmup=0)

    assert "coincide con el maximo observado" in pocas.resolucion_p99
    assert "peor muestra observada" in muchas.resolucion_p99


def test_los_percentiles_estan_ordenados() -> None:
    distribucion = medir(lambda: sum(range(50)), repeticiones=100, warmup=3)

    assert distribucion.min_ms <= distribucion.p50_ms <= distribucion.p95_ms
    assert distribucion.p95_ms <= distribucion.p99_ms <= distribucion.max_ms


# --------------------------------------------------------------------------
# Corpus: volumen de referencia y tokens de control.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def banco() -> measurements.Banco:
    creado = measurements.preparar_banco("adr002_test_")
    yield creado
    creado.cerrar()


def test_el_corpus_alcanza_el_volumen_de_referencia(banco: measurements.Banco) -> None:
    """5.000 mensajes y 500 recuerdos, exigidos por el §5.2 del paquete."""
    connection = sqlite3.connect(str(banco.database_path))
    try:
        mensajes = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        recuerdos = connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    finally:
        connection.close()

    assert mensajes == corpus.MENSAJES == 5_000
    assert recuerdos == corpus.RECUERDOS == 500


def test_el_esquema_procede_de_la_cadena_canonica_de_alembic(banco: measurements.Banco) -> None:
    connection = sqlite3.connect(str(banco.database_path))
    try:
        head = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        tablas = {
            fila[0]
            for fila in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        connection.close()

    assert head == "61be4bb269bf"
    assert {"knowledge_fts", "message_fts"}.issubset(tablas)


def test_los_tokens_de_control_se_comportan_como_el_experimento_supone(
    banco: measurements.Banco,
) -> None:
    """Sin este control, cada escenario podria estar midiendo otra cosa."""
    ausente = banco.busqueda.search_knowledge(corpus.TOKEN_AUSENTE)
    unico = banco.busqueda.search_knowledge(corpus.TOKEN_UNICO)
    frecuente = banco.busqueda.search_knowledge(corpus.TOKEN_FRECUENTE)
    no_reportable = banco.busqueda.search_knowledge(corpus.TOKEN_NO_REPORTABLE)

    assert len(ausente) == 0, "la ausencia real debe no existir en el indice"
    assert len(unico) == 1, "el token unico debe acertar exactamente una vez"
    assert len(frecuente) > 100, "el token frecuente debe acertar en muchos candidatos"
    assert len(no_reportable) == 1, "el contenido no reportable SI existe en el indice"


def test_el_contenido_no_reportable_no_sale_al_exterior(banco: measurements.Banco) -> None:
    """Existe en el indice pero esta archivado: la salida externa es vacia,
    igual que la de una ausencia real."""
    externa = banco.caso_de_uso.rank(corpus.TOKEN_NO_REPORTABLE)
    ausencia = banco.caso_de_uso.rank(corpus.TOKEN_AUSENTE)

    assert len(externa) == 0
    assert len(ausencia) == 0


# --------------------------------------------------------------------------
# Escenarios: forma de la evidencia, nunca umbrales.
# --------------------------------------------------------------------------


def test_la_estabilidad_de_orden_y_conjunto_se_mide_de_verdad(
    banco: measurements.Banco,
) -> None:
    resultado = measurements.medir_estabilidad(banco, repeticiones=REPETICIONES_MINIMAS)

    assert resultado["consulta_frecuente"]["tamano_del_resultado"] > 0
    assert resultado["resumen"]["orden_estable_en_todos_los_escenarios"] is True
    assert resultado["resumen"]["conjunto_estable_en_todos_los_escenarios"] is True


def test_la_indistinguibilidad_declara_modelo_de_amenaza_y_limites(
    banco: measurements.Banco,
) -> None:
    """El §6 del paquete lo exige expresamente: nada de presentar una
    prueba estadistica aislada como garantia."""
    resultado = measurements.medir_indistinguibilidad(banco)

    assert "modelo_de_amenaza" in resultado
    assert "limites" in resultado
    assert "no es una garantia criptografica" in resultado["limites"].lower()
    assert resultado["control_el_contenido_protegido_existe_en_el_indice"]["el_control_es_valido"]


def test_la_indistinguibilidad_compara_las_cuatro_dimensiones_exigidas(
    banco: measurements.Banco,
) -> None:
    """Estado, texto, conteo y tiempo por separado (§6 del paquete)."""
    resultado = measurements.medir_indistinguibilidad(banco)

    assert resultado["estado_externo"]["equivalentes"] is True
    assert resultado["texto_externo_equivalente"] is True
    assert resultado["conteo_externo_equivalente"] is True
    for capa in ("tiempo_recuperacion_completa", "tiempo_solo_indice_fts5"):
        for clave in ("diferencia_p50_ms", "diferencia_p95_ms", "diferencia_p99_ms"):
            assert clave in resultado[capa]


def test_el_borrado_hace_desaparecer_el_derivado_por_completo(
    banco: measurements.Banco,
) -> None:
    ciclo = measurements.medir_construccion_y_reconstruccion(banco.database_path)
    borrado = ciclo["E-BORRADO_desaparicion_del_derivado"]

    assert borrado["desaparicion_completa"] is True
    assert borrado["sin_rastro_de_sombras"] is True
    assert borrado["objetos_derivados_antes"] != []


def test_la_reconstruccion_desde_el_canon_restituye_el_indice(
    banco: measurements.Banco,
) -> None:
    """ADR-001 exige que todo derivado sea reconstruible desde la fuente
    canonica, no solo desde si mismo."""
    ciclo = measurements.medir_construccion_y_reconstruccion(banco.database_path)

    assert ciclo["E-CONSTRUCCION_inicial_desde_canon"]["filas_identicas_a_las_originales"] is True
    assert ciclo["E-RECONSTRUCCION"]["filas_identicas_a_las_originales"] is True
    assert all(v == "OK" for v in ciclo["E-RECONSTRUCCION"]["integrity_check"].values())


def test_el_tamano_se_mide_con_dbstat_y_se_compara_con_el_canon(
    banco: measurements.Banco,
) -> None:
    tamano = measurements.medir_tamano(banco.database_path)

    assert tamano["knowledge_fts_bytes"] > 0
    assert tamano["message_fts_bytes"] > 0
    assert tamano["canon_indexado_bytes"]["total_knowledge_fts"] > 0
    assert tamano["ratio_knowledge_fts_sobre_canon"] > 0


def test_la_fuga_de_ambito_persiste_al_volumen_de_referencia(
    banco: measurements.Banco,
) -> None:
    """Control ya medido en el trabajo 01, reejecutado a escala. Si algun
    dia deja de fugar, esta prueba lo delata."""
    fuga = measurements.medir_fuga_de_ambito(banco)

    assert fuga["hay_fuga"] is True
    assert fuga["resultados_de_proyecto_ajeno"] >= 1


# --------------------------------------------------------------------------
# Aislamiento: el experimento no toca nada productivo.
# --------------------------------------------------------------------------


def test_el_experimento_no_escribe_fuera_de_las_rutas_autorizadas() -> None:
    """La unica ruta de escritura del runner es artifacts/adr002_tolerances."""
    raiz = Path(__file__).resolve().parents[3]

    assert raiz / "artifacts" / "adr002_tolerances" == ARTIFACTS_DIR
    assert ARTIFACTS_DIR.is_relative_to(raiz / "artifacts")


def test_el_corpus_usa_ficheros_temporales_y_no_la_base_del_usuario(
    banco: measurements.Banco,
) -> None:
    import tempfile

    assert banco.database_path.is_relative_to(Path(tempfile.gettempdir()))


def test_las_mediciones_publicadas_declaran_entorno_y_metodologia() -> None:
    """Si el runner ya se ejecuto, su salida debe ser auditable."""
    destino = ARTIFACTS_DIR / FICHERO
    if not destino.exists():
        pytest.skip("el runner todavia no se ha ejecutado en este arbol")

    payload = json.loads(destino.read_text(encoding="utf-8"))

    for clave in ("python", "sqlite_biblioteca", "sqlalchemy", "alembic", "plataforma", "commit"):
        assert payload["entorno"][clave]
    assert payload["entorno"]["red"] == "no utilizada"
    assert payload["metodologia"]["reloj"].startswith("time.perf_counter_ns")
    assert payload["metodologia"]["repeticiones_minimas_exigidas"] == REPETICIONES_MINIMAS
    assert payload["corpus"]["mensajes"] == 5_000
    assert payload["corpus"]["recuerdos"] == 500
    assert "T1_a_T4" in payload["no_medido"]


def test_las_distribuciones_publicadas_cumplen_el_minimo_de_repeticiones() -> None:
    destino = ARTIFACTS_DIR / FICHERO
    if not destino.exists():
        pytest.skip("el runner todavia no se ha ejecutado en este arbol")

    payload = json.loads(destino.read_text(encoding="utf-8"))
    escenarios = payload["escenarios"]

    for nombre in (
        "E-LAT-0_cero_resultados",
        "E-LAT-1_un_resultado_exacto",
        "E-LAT-N_muchos_candidatos",
    ):
        for capa in ("solo_indice_fts5", "recuperacion_completa_rank"):
            distribucion = escenarios[nombre][capa]
            assert distribucion["n"] >= REPETICIONES_MINIMAS, f"{nombre}/{capa}"
            assert distribucion["p50_ms"] <= distribucion["p95_ms"] <= distribucion["p99_ms"]
