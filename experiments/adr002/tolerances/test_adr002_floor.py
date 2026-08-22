"""Pruebas de la preinscripcion del suelo de medicion (ADR002-TOL-209, fase A).

Todo es sintetico o doble controlado. **Ninguna prueba ejecuta la corrida
real del suelo**, ninguna escribe artefactos y ninguna toca el repositorio.

Cada prueba negativa corresponde a una condicion de la matriz bloqueante
del paquete de trabajo 05.
"""

from __future__ import annotations

import ast
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.tolerances import floor_probes as sondas
from experiments.adr002.tolerances import floor_protocol as fp
from experiments.adr002.tolerances import run_floor
from experiments.adr002.tolerances import schema_floor_v0_1 as esquema

# --------------------------------------------------------------------------
# Utilidades sinteticas
# --------------------------------------------------------------------------


def medida(
    sonda: str,
    pid: int,
    p50: int,
    p95: int,
    *,
    n: int = fp.N_SONDA_F,
) -> fp.MedidaSonda:
    return fp.MedidaSonda(
        sonda=sonda,
        pid=pid,
        n=n,
        warmup_descartado=fp.WARMUP_SONDA_F,
        p50=p50,
        p95=p95,
        p99=p95,
        minimo=p50,
        maximo=p95,
        media_truncada=(p50 + p95) // 2,
    )


def medidas_validas(
    *,
    p50_por_pid: Sequence[int] = (1000, 1010, 1020, 1030, 1040),
    p95_por_pid: Sequence[int] = (2000, 2020, 2040, 2060, 2080),
) -> list[fp.MedidaSonda]:
    """Cinco procesos por cada una de las tres sondas normativas."""
    return [
        medida(sonda, 100 + indice, p50_por_pid[indice], p95_por_pid[indice])
        for sonda in fp.F_NORMATIVO
        for indice in range(len(p50_por_pid))
    ]


def _vector(base: int, n: int = fp.N_SONDA_F) -> list[int]:
    """Vector crudo determinista, sin multiplos uniformes de 100 ns."""
    return [base + (indice * 7) % 23 for indice in range(n)]


def documento_valido() -> dict[str, Any]:
    """Documento minimo conforme, construido a partir de las formulas."""
    lista_sondas: list[dict[str, Any]] = []
    for sonda in fp.F_NORMATIVO:
        for indice in range(fp.PROCESOS_MINIMOS):
            muestras = _vector(1000 + 10 * indice)
            ordenadas = sorted(muestras)
            lista_sondas.append(
                {
                    "sonda": sonda,
                    "pid": 100 + indice,
                    "n": len(muestras),
                    "warmup_descartado": fp.WARMUP_SONDA_F,
                    "muestras_ns": muestras,
                    "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
                    "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
                    "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
                    "min_ns": ordenadas[0],
                    "max_ns": ordenadas[-1],
                    "media_truncada_ns": sum(ordenadas) // len(ordenadas),
                    "resolucion_percentil": fp.resolucion_percentil(len(muestras)),
                }
            )

    convertidas = [
        medida(
            str(entrada["sonda"]),
            int(entrada["pid"]),
            int(entrada["p50_ns"]),
            int(entrada["p95_ns"]),
        )
        for entrada in lista_sondas
    ]
    derivacion = fp.derivar(convertidas)

    return {
        "documento": "Suelo de medicion LAB-LINUX para ADR002-TOL-209",
        "version_esquema": fp.VERSION_ESQUEMA,
        "estado": fp.ESTADO,
        "protocolo": fp.PROTOCOLO,
        "preinscripcion": {
            "commit_a": "0" * 40,
            "head_en_ejecucion": "0" * 40,
            "blobs_preinscritos": {r: "a" * 40 for r in fp.ARCHIVOS_PREINSCRITOS},
            "blob_arnes": "b" * 40,
            "blobs_corpus_congelado": dict(fp.BLOBS_CORPUS_CONGELADO),
            "blob_protocolo": fp.BLOB_PROTOCOLO_APROBADO,
        },
        "entorno": {
            "captura_inicial": {"boot_id": "boot-1"},
            "captura_final": {"boot_id": "boot-1"},
            "boot_id": "boot-1",
            "carga_por_proceso": {str(100 + i): [0.1] for i in range(fp.PROCESOS_MINIMOS)},
            "incidencias": [],
        },
        "procesos": [{"pid": 100 + i} for i in range(fp.PROCESOS_MINIMOS)],
        "sondas": lista_sondas,
        "diagnosticos": {nombre: {"presente": True} for nombre in fp.DIAGNOSTICOS},
        "controles_internos": dict.fromkeys(fp.CONTROLES_BLOQUEANTES, True),
        "derivacion": {
            "sm_ns": derivacion.sm,
            "b50_ns": derivacion.b50,
            "b95_ns": derivacion.b95,
            "b_ns": derivacion.b,
            "u_ns": derivacion.u,
            "m": fp.MARGEN_M,
            "descomposicion_b": fp.descomposicion_b(convertidas),
        },
        # Coherente por construccion con SM y U derivados: los minimos se
        # eligen por encima de SM (no dominada) y el regimen se recomputa
        # con la misma regla que aplica el validador.
        "regimenes_por_percentil": [
            {
                "magnitud": "ejemplo",
                "p50": fp.regimen_de_percentil(derivacion.sm + 1, derivacion.u),
                "p95": fp.regimen_de_percentil(derivacion.sm + 2, derivacion.u),
                "min_p50_ns": derivacion.sm + 1,
                "min_p95_ns": derivacion.sm + 2,
            }
        ],
        "clasificacion_diagnostica_linea_base": {
            "fuente": run_floor.RUTA_LINEA_BASE,
            "magnitudes": [
                {
                    "magnitud": "escenario_sintetico.capa",
                    "min_p50_ns": derivacion.sm + 1,
                    "min_p95_ns": derivacion.sm + 2,
                }
            ],
        },
        "custodia": {
            "diff_preinscritos_vacio": True,
            "sha_a_es_ancestro": True,
            "reverificada_tras_medir": True,
            "head": "0" * 40,
        },
        "no_autoriza": {"limite_duro_tol_107": False, "aprobacion_tol_209": False},
    }


class CustodiaDoble:
    """Doble controlado del entorno de custodia. No toca ningun repositorio."""

    def __init__(
        self,
        contenidos: Mapping[str, bytes],
        *,
        head: str = "H",
        ancestro: bool = True,
        existe: bool = True,
        limpio: bool = True,
        diff_vacio: bool = True,
        blobs_en_commit: Mapping[str, str] | None = None,
    ) -> None:
        self.contenidos = dict(contenidos)
        self._head = head
        self._ancestro = ancestro
        self._existe = existe
        self._limpio = limpio
        self._diff_vacio = diff_vacio
        # Por defecto el commit registra exactamente lo que hay en el
        # "arbol" del doble: cada prueba negativa lo desalinea a proposito.
        self._blobs_en_commit = (
            {r: fp.blob_git(d) for r, d in contenidos.items()}
            if blobs_en_commit is None
            else dict(blobs_en_commit)
        )

    def entorno(self) -> fp.EntornoCustodia:
        def leer(ruta: str) -> bytes:
            if ruta not in self.contenidos:
                raise OSError(ruta)
            return self.contenidos[ruta]

        return fp.EntornoCustodia(
            leer_bytes=leer,
            es_ancestro=lambda _a, _d: self._ancestro,
            existe_commit=lambda _s: self._existe,
            head=lambda: self._head,
            arbol_limpio=lambda: self._limpio,
            diff_vacio=lambda _a, _b, _r: self._diff_vacio,
            blob_en_commit=lambda _s, ruta: self._blobs_en_commit.get(ruta),
        )


def contenidos_custodia() -> dict[str, bytes]:
    rutas = [
        *fp.ARCHIVOS_PREINSCRITOS,
        fp.ARCHIVO_ARNES_HEREDADO,
        *fp.BLOBS_CORPUS_CONGELADO,
    ]
    return {ruta: f"contenido de {ruta}".encode() for ruta in rutas}


def blobs_de(contenidos: Mapping[str, bytes]) -> dict[str, str]:
    return {ruta: fp.blob_git(datos) for ruta, datos in contenidos.items()}


# --------------------------------------------------------------------------
# 1 · nearest-rank sin interpolacion
# --------------------------------------------------------------------------


def test_percentil_es_siempre_una_muestra_observada() -> None:
    muestras = [10, 20, 30, 40, 100]
    for num, den in ((1, 2), (19, 20), (99, 100)):
        assert fp.percentil_ns(muestras, num, den) in muestras


def test_percentil_no_interpola_entre_dos_muestras() -> None:
    # Con interpolacion lineal el P50 de [10, 20] seria 15: valor nunca observado.
    assert fp.percentil_ns([10, 20], 1, 2) == 10


def test_percentil_p99_con_n_100_es_la_peor_muestra() -> None:
    muestras = list(range(1, 101))
    assert fp.percentil_ns(muestras, 99, 100) == 99
    assert fp.resolucion_percentil(100).startswith("con n=100")


def test_percentil_rechaza_fraccion_invalida() -> None:
    with pytest.raises(ValueError, match="fraccion invalida"):
        fp.percentil_ns([1, 2, 3], 3, 2)


# --------------------------------------------------------------------------
# 2 · SM, B50, B95, B y U exactos
# --------------------------------------------------------------------------


def test_sm_b50_b95_b_y_u_exactos() -> None:
    medidas = medidas_validas()
    assert fp.calcular_sm(medidas) == 2080
    assert fp.calcular_b50(medidas) == 40
    assert fp.calcular_b95(medidas) == 80
    assert fp.calcular_b(medidas) == 80
    assert fp.calcular_u(80) == 400


def test_b_es_max_de_b50_y_b95_cuando_domina_p50() -> None:
    medidas = medidas_validas(
        p50_por_pid=(1000, 1100, 1200, 1300, 1500), p95_por_pid=(2000, 2010, 2020, 2030, 2040)
    )
    assert fp.calcular_b50(medidas) == 500
    assert fp.calcular_b95(medidas) == 40
    assert fp.calcular_b(medidas) == 500


def test_derivacion_completa_es_coherente() -> None:
    derivacion = fp.derivar(medidas_validas())
    assert derivacion.b == max(derivacion.b50, derivacion.b95)
    assert derivacion.u == fp.FACTOR_U * derivacion.b
    assert derivacion.m == 1


def test_u_no_admite_b_negativa() -> None:
    with pytest.raises(ValueError, match="B no puede ser negativa"):
        fp.calcular_u(-1)


# --------------------------------------------------------------------------
# 3 · m fijo igual a 1  ·  23 · U distinta de 5B rechazada
# --------------------------------------------------------------------------


def test_margen_es_exactamente_uno() -> None:
    assert fp.MARGEN_M == 1
    assert fp.FACTOR_U == 5


def test_esquema_rechaza_margen_distinto_de_uno() -> None:
    doc = documento_valido()
    doc["derivacion"]["m"] = 2
    assert any("m debe ser 1" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_u_distinta_de_cinco_b() -> None:
    doc = documento_valido()
    doc["derivacion"]["u_ns"] = int(doc["derivacion"]["b_ns"]) * 4 + 1
    assert any("U debe ser" in f for f in esquema.fallos_suelo_medicion(doc))


# --------------------------------------------------------------------------
# 4 · continuidad en U
# --------------------------------------------------------------------------


@pytest.mark.parametrize("b", [1, 7, 80, 1234])
def test_continuidad_exacta_de_los_permisos_en_u(b: int) -> None:
    """En M = U el permiso relativo y el absoluto coinciden exactamente."""
    u = fp.calcular_u(b)
    for delta in range(0, 2 * b + 2):
        relativo = fp.pasa_relativo(u, u + delta)
        absoluto = fp.pasa_absoluto(u, u + delta, b)
        assert relativo == absoluto, f"discontinuidad en delta={delta}"


def test_criterio_relativo_es_aritmetica_entera_exacta() -> None:
    assert fp.pasa_relativo(100, 120) is True
    assert fp.pasa_relativo(100, 121) is False
    assert fp.pasa_relativo(0, 10) is False


# --------------------------------------------------------------------------
# 5 y 6 · F contiene exactamente tres sondas; diagnosticos excluidos
# --------------------------------------------------------------------------


def test_f_contiene_exactamente_tres_sondas() -> None:
    assert fp.F_NORMATIVO == (fp.SONDA_VACIA, fp.SONDA_SQLITE_0, fp.SONDA_SQLITE_1)
    assert len(fp.F_NORMATIVO) == 3
    assert fp.comprobar_composicion_f(fp.F_NORMATIVO) == ()


@pytest.mark.parametrize("intruso", list(fp.DIAGNOSTICOS))
def test_diagnosticos_no_pueden_entrar_en_f(intruso: str) -> None:
    fallos = fp.comprobar_composicion_f([*fp.F_NORMATIVO, intruso])
    assert fallos


def test_fts5_y_rank_no_pueden_entrar_en_f() -> None:
    assert fp.comprobar_composicion_f([*fp.F_NORMATIVO, "fts5_cero"])
    assert fp.comprobar_composicion_f([*fp.F_NORMATIVO, "rank_completo"])


def test_derivacion_rechaza_sondas_ajenas_a_f() -> None:
    contaminadas = [*medidas_validas(), medida("fts5_cero", 100, 5, 6)]
    with pytest.raises(fp.SondaFueraDeFError):
        fp.calcular_b(contaminadas)


# --------------------------------------------------------------------------
# 7 y 8 · SQL permitido por clave primaria; construcciones prohibidas
# --------------------------------------------------------------------------


def test_sql_de_sonda_por_clave_primaria_es_valido() -> None:
    assert (
        fp.fallos_sql_de_sonda(
            sondas.SQL_SONDA_SQLITE,
            tabla_canonica=sondas.TABLA_CANONICA,
            columna_pk=sondas.COLUMNA_PK,
        )
        == ()
    )
    sondas.comprobar_sql_de_sonda()


def test_tabla_canonica_elegida_no_es_fts_ni_sombra() -> None:
    assert sondas.TABLA_CANONICA == "memory_revisions"
    assert sondas.COLUMNA_PK == "id"
    assert not sondas.TABLA_CANONICA.endswith("_fts")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id FROM memory_revisions WHERE content LIKE ?",
        "SELECT id FROM knowledge_fts WHERE knowledge_fts MATCH ?",
        "SELECT id FROM memory_revisions JOIN memories ON 1 WHERE id = ?",
        "SELECT id FROM memory_revisions WHERE id = ? ORDER BY id",
        "SELECT count(*) FROM memory_revisions WHERE id = ?",
        "SELECT max(id) FROM memory_revisions WHERE id = ?",
        "SELECT id FROM memory_revisions_content WHERE id = ?",
        "SELECT id FROM memory_revisions WHERE id = ? GROUP BY id",
        "SELECT bm25(knowledge_fts) FROM knowledge_fts WHERE id = ?",
    ],
)
def test_sql_prohibido_es_rechazado(sql: str) -> None:
    fallos = fp.fallos_sql_de_sonda(
        sql, tabla_canonica=sondas.TABLA_CANONICA, columna_pk=sondas.COLUMNA_PK
    )
    assert fallos


def test_sql_sin_filtro_por_clave_primaria_es_rechazado() -> None:
    fallos = fp.fallos_sql_de_sonda(
        "SELECT id FROM memory_revisions",
        tabla_canonica=sondas.TABLA_CANONICA,
        columna_pk=sondas.COLUMNA_PK,
    )
    assert any("clave primaria" in f for f in fallos)


def test_sql_sobre_otra_tabla_es_rechazado() -> None:
    fallos = fp.fallos_sql_de_sonda(
        "SELECT id FROM messages WHERE id = ?",
        tabla_canonica=sondas.TABLA_CANONICA,
        columna_pk=sondas.COLUMNA_PK,
    )
    assert any("tabla canonica" in f for f in fallos)


# --------------------------------------------------------------------------
# 9 y 10 · menos de cinco procesos; PIDs repetidos
# --------------------------------------------------------------------------


def test_menos_de_cinco_procesos_es_rechazado_en_la_derivacion() -> None:
    pocas = [medida(s, 100 + i, 1000, 2000) for s in fp.F_NORMATIVO for i in range(4)]
    with pytest.raises(fp.ProcesosInsuficientesError):
        fp.calcular_b(pocas)


def test_pids_repetidos_no_cuentan_como_procesos_independientes() -> None:
    repetidos = [medida(s, 100, 1000, 2000) for s in fp.F_NORMATIVO for _ in range(5)]
    with pytest.raises(fp.ProcesosInsuficientesError):
        fp.calcular_sm(repetidos)


def test_esquema_rechaza_pids_repetidos() -> None:
    doc = documento_valido()
    doc["procesos"] = [{"pid": 100} for _ in range(fp.PROCESOS_MINIMOS)]
    assert any("PIDs repetidos" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_menos_de_cinco_procesos() -> None:
    doc = documento_valido()
    doc["procesos"] = [{"pid": 100 + i} for i in range(3)]
    assert any("el minimo es 5" in f for f in esquema.fallos_suelo_medicion(doc))


def test_evaluar_magnitud_exige_cinco_sesiones() -> None:
    with pytest.raises(fp.ProcesosInsuficientesError):
        fp.evaluar_magnitud([10, 11, 12], [20, 21, 22], sm=1, b=5, u=25)


# --------------------------------------------------------------------------
# 11, 12, 13 · warm-up mezclado, redondeo, filtrado o n incoherente
# --------------------------------------------------------------------------


def test_el_warmup_se_descarta_y_no_entra_en_el_vector() -> None:
    llamadas: list[int] = []

    def contar() -> None:
        llamadas.append(1)

    muestras = sondas.medir_ns(contar, n=30, warmup=7)
    assert len(muestras) == 30
    assert len(llamadas) == 37


def test_esquema_rechaza_warmup_negativo() -> None:
    doc = documento_valido()
    doc["sondas"][0]["warmup_descartado"] = -1
    assert any("warmup_descartado invalido" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_muestras_redondeadas() -> None:
    doc = documento_valido()
    muestras = [1000 + 100 * i for i in range(fp.N_SONDA_F)]
    ordenadas = sorted(muestras)
    doc["sondas"][0].update(
        {
            "muestras_ns": muestras,
            "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
            "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
            "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
            "min_ns": ordenadas[0],
            "max_ns": ordenadas[-1],
        }
    )
    assert any("redondeado" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_n_incoherente_con_el_vector() -> None:
    doc = documento_valido()
    doc["sondas"][0]["n"] = 7
    assert any("longitud del vector" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_vector_ausente_o_vacio() -> None:
    doc = documento_valido()
    doc["sondas"][0]["muestras_ns"] = []
    assert any("vacio" in f for f in esquema.fallos_suelo_medicion(doc))

    otro = documento_valido()
    del otro["sondas"][0]["muestras_ns"]
    assert any("sin campo muestras_ns" in f for f in esquema.fallos_suelo_medicion(otro))


def test_esquema_rechaza_percentil_que_no_es_nearest_rank() -> None:
    doc = documento_valido()
    doc["sondas"][0]["p50_ns"] = int(doc["sondas"][0]["p50_ns"]) + 1
    assert any("nearest-rank" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_n_por_debajo_del_minimo() -> None:
    doc = documento_valido()
    recortado = list(doc["sondas"][0]["muestras_ns"])[:30]
    ordenadas = sorted(recortado)
    doc["sondas"][0].update(
        {
            "muestras_ns": recortado,
            "n": len(recortado),
            "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
            "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
            "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
            "min_ns": ordenadas[0],
            "max_ns": ordenadas[-1],
        }
    )
    assert any("por debajo del minimo" in f for f in esquema.fallos_suelo_medicion(doc))


# --------------------------------------------------------------------------
# 14 y 15 · carga o entorno ausentes; cambio de boot_id
# --------------------------------------------------------------------------


@pytest.mark.parametrize("campo", list(esquema.CAMPOS_ENTORNO))
def test_esquema_rechaza_entorno_incompleto(campo: str) -> None:
    doc = documento_valido()
    del doc["entorno"][campo]
    assert any(campo in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_cambio_de_boot_id() -> None:
    doc = documento_valido()
    doc["entorno"]["captura_final"] = {"boot_id": "boot-2"}
    assert any("boot_id cambio" in f for f in esquema.fallos_suelo_medicion(doc))


# --------------------------------------------------------------------------
# 16 y 17 · busy-spin y comprobacion 1x/2x
# --------------------------------------------------------------------------


def test_duplicacion_detecta_escalado_correcto() -> None:
    assert sondas.escala_con_el_trabajo(100, 200) is True
    assert sondas.escala_con_el_trabajo(100, 210) is True


def test_duplicacion_detecta_arnes_dominante() -> None:
    # El corchete domina: doblar el trabajo apenas mueve la medida.
    assert sondas.escala_con_el_trabajo(100, 105) is False
    assert sondas.escala_con_el_trabajo(0, 200) is False


def test_control_busy_spin_fallido_bloquea() -> None:
    estado = dict.fromkeys(fp.CONTROLES_BLOQUEANTES, True)
    estado["busy_spin_estable"] = False
    assert not fp.evaluar_controles(estado).valido


def test_control_duplicacion_fallido_bloquea() -> None:
    estado = dict.fromkeys(fp.CONTROLES_BLOQUEANTES, True)
    estado["duplicacion_1x_2x"] = False
    assert "duplicacion_1x_2x" in fp.evaluar_controles(estado).fallos


def test_busy_spin_rechaza_vueltas_no_positivas() -> None:
    with pytest.raises(ValueError, match="vueltas debe ser positivo"):
        sondas.diagnostico_busy_spin(vueltas=0, n=1, warmup=0)


# --------------------------------------------------------------------------
# 18 · guarda SM anterior al regimen
# --------------------------------------------------------------------------


def test_guarda_sm_actua_antes_de_seleccionar_regimen() -> None:
    """min P95 < SM: NO_EVALUABLE aunque los minimos superasen U."""
    veredicto = fp.evaluar_magnitud([1000] * 5, [2000, 2000, 2000, 2000, 2000], sm=5000, b=10, u=50)
    assert veredicto.dominada_por_instrumento is True
    assert veredicto.resultado == fp.NO_EVALUABLE
    assert veredicto.por_percentil == ()
    assert fp.registro_por_percentil(veredicto) == fp.NO_EVALUABLE


def test_sin_guarda_sm_la_magnitud_si_se_clasifica() -> None:
    veredicto = fp.evaluar_magnitud([1000] * 5, [2000] * 5, sm=100, b=10, u=50)
    assert veredicto.dominada_por_instrumento is False
    assert len(veredicto.por_percentil) == 2


# --------------------------------------------------------------------------
# 19, 20, 21 · regimen por percentil, invariante y combinacion imposible
# --------------------------------------------------------------------------


def test_p50_y_p95_pueden_caer_en_regimenes_distintos() -> None:
    veredicto = fp.evaluar_magnitud(
        [100, 101, 102, 103, 104], [500, 505, 510, 515, 520], sm=50, b=60, u=300
    )
    regimenes = {v.percentil: v.regimen for v in veredicto.por_percentil}
    assert regimenes["P50"] == fp.REGIMEN_ABSOLUTO
    assert regimenes["P95"] == fp.REGIMEN_RELATIVO
    assert fp.registro_por_percentil(veredicto) == "P50: absoluto · P95: relativo"


def test_invariante_min_p95_mayor_o_igual_que_min_p50() -> None:
    with pytest.raises(fp.InvarianteVioladoError, match="invariante violado"):
        fp.evaluar_magnitud([900] * 5, [100, 200, 300, 400, 500], sm=1, b=10, u=50)


def test_combinacion_p50_relativo_p95_absoluto_es_imposible() -> None:
    """No puede construirse con datos coherentes; el esquema tambien la rechaza."""
    doc = documento_valido()
    doc["regimenes_por_percentil"] = [
        {
            "magnitud": "imposible",
            "p50": fp.REGIMEN_RELATIVO,
            "p95": fp.REGIMEN_ABSOLUTO,
            "min_p50_ns": 1000,
            "min_p95_ns": 2000,
        }
    ]
    assert any("combinacion imposible" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_invariante_violado() -> None:
    doc = documento_valido()
    doc["regimenes_por_percentil"][0].update({"min_p50_ns": 3000, "min_p95_ns": 1000})
    assert any("invariante violado" in f for f in esquema.fallos_suelo_medicion(doc))


def test_las_tres_combinaciones_validas_son_admisibles() -> None:
    ambos_absolutos = fp.evaluar_magnitud([10] * 5, [20] * 5, sm=1, b=5, u=1000)
    mixto = fp.evaluar_magnitud(
        [100, 101, 102, 103, 104], [500, 505, 510, 515, 520], sm=1, b=60, u=300
    )
    ambos_relativos = fp.evaluar_magnitud([1000] * 5, [2000] * 5, sm=1, b=5, u=25)
    assert [v.regimen for v in ambos_absolutos.por_percentil] == ["absoluto", "absoluto"]
    assert [v.regimen for v in mixto.por_percentil] == ["absoluto", "relativo"]
    assert [v.regimen for v in ambos_relativos.por_percentil] == ["relativo", "relativo"]


def test_veredicto_global_exige_que_pasen_los_dos_percentiles() -> None:
    fallando_p95 = fp.evaluar_magnitud([10] * 5, [20, 20, 20, 20, 400], sm=1, b=5, u=100000)
    assert fallando_p95.resultado == "INVALIDA"
    pasando = fp.evaluar_magnitud([10] * 5, [20] * 5, sm=1, b=5, u=100000)
    assert pasando.resultado == "VALIDA"


# --------------------------------------------------------------------------
# 22 · B unica y diagnostico B50/B95
# --------------------------------------------------------------------------


def test_esquema_exige_descomposicion_de_b() -> None:
    doc = documento_valido()
    del doc["derivacion"]["descomposicion_b"]
    assert any("descomposicion_b" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_dos_bandas_normativas() -> None:
    doc = documento_valido()
    doc["derivacion"]["banda_absoluta_secundaria"] = 5
    assert any("dos bandas normativas" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_b_distinta_de_max_b50_b95() -> None:
    doc = documento_valido()
    doc["derivacion"]["b_ns"] = int(doc["derivacion"]["b_ns"]) + 1
    assert any("B debe ser max" in f for f in esquema.fallos_suelo_medicion(doc))


# --------------------------------------------------------------------------
# 24 y 25 · B ajustada por clasificacion historica; FTS5 no afecta B ni U
# --------------------------------------------------------------------------


def test_b_no_depende_de_ninguna_cifra_historica() -> None:
    """No existe techo historico preinscrito: B sale solo de F."""
    fuente = Path(fp.__file__).read_text(encoding="utf-8")
    assert "0.0661" not in fuente
    assert "0,0661" not in fuente
    assert "66100" not in fuente


def test_b_cambia_solo_si_cambian_las_sondas_de_f() -> None:
    base = fp.derivar(medidas_validas())
    otra = fp.derivar(
        medidas_validas(
            p50_por_pid=(1000, 1010, 1020, 1030, 1040),
            p95_por_pid=(2000, 2020, 2040, 2060, 2080),
        )
    )
    assert base == otra


def test_fts5_no_puede_alterar_b_ni_u() -> None:
    contaminadas = [*medidas_validas(), medida("fts5_muchos", 999, 10**9, 2 * 10**9)]
    with pytest.raises(fp.SondaFueraDeFError):
        fp.derivar(contaminadas)


# --------------------------------------------------------------------------
# 26 · puerto fuera de F
# --------------------------------------------------------------------------


def test_el_puerto_es_diagnostico_y_no_pertenece_a_f() -> None:
    assert fp.DIAG_PUERTO in fp.DIAGNOSTICOS
    assert fp.DIAG_PUERTO not in fp.F_NORMATIVO
    assert fp.comprobar_composicion_f([*fp.F_NORMATIVO, fp.DIAG_PUERTO])


def test_sobrecoste_del_puerto_se_mide_con_invocable_inyectado() -> None:
    llamadas: list[str] = []
    muestras = sondas.diagnostico_sobrecoste_puerto(
        lambda consulta: llamadas.append(consulta), "termino", n=3, warmup=1
    )
    assert len(muestras) == 3
    assert len(llamadas) == 4


# --------------------------------------------------------------------------
# 27 y 28 · excepcion -> NO_EVALUABLE; control bloqueante -> sin valores
# --------------------------------------------------------------------------


def test_control_ausente_cuenta_como_fallido() -> None:
    assert not fp.evaluar_controles({}).valido
    assert set(fp.evaluar_controles({}).fallos) == set(fp.CONTROLES_BLOQUEANTES)


def test_todos_los_controles_validos_no_producen_fallos() -> None:
    assert fp.evaluar_controles(dict.fromkeys(fp.CONTROLES_BLOQUEANTES, True)).valido


def test_esquema_no_admite_valores_con_controles_fallidos() -> None:
    doc = documento_valido()
    doc["controles_internos"]["carga_registrada"] = False
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("controles bloqueantes fallidos" in f for f in fallos)


def test_sonda_sqlite_con_filas_inesperadas_lanza() -> None:
    with pytest.raises(ValueError, match="filas_esperadas"):
        sondas.sonda_sqlite(
            sondas.FixtureSqlite(conexion=None, clave_existente=1, clave_inexistente=2),  # type: ignore[arg-type]
            filas_esperadas=2,
            n=1,
            warmup=0,
        )


# --------------------------------------------------------------------------
# 29 a 34 · custodia A -> D
# --------------------------------------------------------------------------


def test_custodia_valida_no_produce_fallos() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    doble = CustodiaDoble(contenidos)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert fallos == ()


def test_custodia_rechaza_commit_de_preinscripcion_inexistente() -> None:
    contenidos = contenidos_custodia()
    doble = CustodiaDoble(contenidos, existe=False)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos=blobs_de(contenidos),
        blob_arnes="x" * 40,
    )
    assert fallos == ("commit de preinscripcion inexistente",)


def test_custodia_rechaza_sha_a_que_no_es_ancestro() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    doble = CustodiaDoble(contenidos, ancestro=False)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("no es ancestro" in f for f in fallos)


def test_custodia_detecta_blob_preinscrito_alterado() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    alterado = fp.ARCHIVOS_PREINSCRITOS[1]
    contenidos[alterado] = b"contenido manipulado"
    doble = CustodiaDoble(contenidos)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any(alterado in f and "alterado" in f for f in fallos)


def test_custodia_detecta_harness_alterado() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    contenidos[fp.ARCHIVO_ARNES_HEREDADO] = b"arnes manipulado"
    doble = CustodiaDoble(contenidos)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("arnes heredado alterado" in f for f in fallos)


def test_custodia_detecta_blob_congelado_alterado() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    congelado = next(iter(fp.BLOBS_CORPUS_CONGELADO))
    contenidos[congelado] = b"corpus manipulado"
    doble = CustodiaDoble(contenidos)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("blob congelado alterado" in f for f in fallos)


def test_custodia_detecta_diff_no_vacio_en_ficheros_de_a() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    doble = CustodiaDoble(contenidos, diff_vacio=False)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("diff no vacio" in f for f in fallos)


def test_custodia_detecta_blobs_preinscritos_ausentes() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    incompletos = {r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS[:3]}
    doble = CustodiaDoble(contenidos)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos=incompletos,
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("blobs preinscritos ausentes" in f for f in fallos)


def test_blob_git_coincide_con_git_hash_object(tmp_path: Path) -> None:
    """El calculo del blob debe ser el de Git, comprobado contra git real."""
    fichero = tmp_path / "muestra.txt"
    fichero.write_bytes(b"contenido de prueba\n")
    esperado = subprocess.run(
        ["git", "hash-object", str(fichero)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert fp.blob_git(fichero.read_bytes()) == esperado


# --------------------------------------------------------------------------
# 35 a 38 · importacion sin efectos, --execute, arbol sucio, salida existente
# --------------------------------------------------------------------------


def test_importar_run_floor_no_tiene_efectos_secundarios() -> None:
    """Importar no mide: el plan es puro y no hay estado global de medicion."""
    plan = run_floor.plan_de_corrida()
    assert plan.procesos == fp.PROCESOS_MINIMOS
    assert plan.sondas_normativas == fp.F_NORMATIVO
    assert set(plan.orden) == set(fp.F_NORMATIVO)


def test_ejecucion_sin_execute_es_rechazada(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_floor.main([]) == run_floor.CODIGO_SIN_EXECUTE
    assert "no mide sin --execute" in capsys.readouterr().out


def test_execute_sin_commit_ni_output_es_rechazado(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_floor.main(["--execute"]) == run_floor.CODIGO_BLOQUEADO
    assert "--preinscription-commit" in capsys.readouterr().out


def test_plan_no_mide_y_es_imprimible(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_floor.main(["--plan"]) == run_floor.CODIGO_OK
    salida = capsys.readouterr().out
    assert "sondas normativas (F)" in salida
    assert "U = 5 * B" in salida


def test_precondiciones_rechazan_arbol_sucio() -> None:
    contenidos = contenidos_custodia()
    doble = CustodiaDoble(contenidos, limpio=False)
    fallos = fp.verificar_precondiciones_ejecucion(doble.entorno(), sha_a="A", salida_existe=False)
    assert any("sucio" in f for f in fallos)


def test_precondiciones_rechazan_salida_existente() -> None:
    contenidos = contenidos_custodia()
    doble = CustodiaDoble(contenidos, head="A")
    fallos = fp.verificar_precondiciones_ejecucion(doble.entorno(), sha_a="A", salida_existe=True)
    assert any("ya existe" in f for f in fallos)


def test_precondiciones_rechazan_head_distinto_del_commit_a() -> None:
    contenidos = contenidos_custodia()
    doble = CustodiaDoble(contenidos, head="OTRO")
    fallos = fp.verificar_precondiciones_ejecucion(doble.entorno(), sha_a="A", salida_existe=False)
    assert any("distinto del commit de preinscripcion" in f for f in fallos)


def test_precondiciones_rechazan_commit_inexistente() -> None:
    contenidos = contenidos_custodia()
    doble = CustodiaDoble(contenidos, existe=False)
    fallos = fp.verificar_precondiciones_ejecucion(doble.entorno(), sha_a="A", salida_existe=False)
    assert any("no existe" in f for f in fallos)


def test_comprobar_precondiciones_agrega_custodia_y_entorno() -> None:
    contenidos = contenidos_custodia()
    contenidos[f"docs/architecture/{fp.PROTOCOLO}"] = b"protocolo manipulado"
    doble = CustodiaDoble(contenidos, head="A")
    resultado = run_floor.comprobar_precondiciones(
        doble.entorno(), sha_a="A", salida=Path("/inexistente/salida.json"), salida_existe=False
    )
    assert not resultado.permite_medir
    assert any("protocolo aprobado ha sido modificado" in f for f in resultado.fallos)


# --------------------------------------------------------------------------
# Esquema: secciones, negaciones y etiquetas prohibidas
# --------------------------------------------------------------------------


def test_documento_valido_no_produce_fallos() -> None:
    assert esquema.fallos_suelo_medicion(documento_valido()) == []


@pytest.mark.parametrize("seccion", list(esquema.SECCIONES_OBLIGATORIAS))
def test_esquema_exige_todas_las_secciones(seccion: str) -> None:
    doc = documento_valido()
    del doc[seccion]
    assert any(seccion in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_exige_negar_el_limite_duro_y_la_aprobacion() -> None:
    doc = documento_valido()
    doc["no_autoriza"]["limite_duro_tol_107"] = True
    assert any(
        "limite_duro_tol_107 debe ser False" in f for f in esquema.fallos_suelo_medicion(doc)
    )

    otro = documento_valido()
    del otro["no_autoriza"]["aprobacion_tol_209"]
    assert any("aprobacion_tol_209" in f for f in esquema.fallos_suelo_medicion(otro))


def test_esquema_rechaza_la_etiqueta_de_tol_207() -> None:
    doc = documento_valido()
    doc["clasificacion_entorno"] = "ENVOLVENTE_REPRODUCIBLE"
    assert any("ENVOLVENTE_REPRODUCIBLE" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_protocolo_distinto_del_aprobado() -> None:
    doc = documento_valido()
    doc["protocolo"] = "OTRO_PROTOCOLO_v9.md"
    assert any("no es el aprobado" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_blob_de_protocolo_alterado() -> None:
    doc = documento_valido()
    doc["preinscripcion"]["blob_protocolo"] = "f" * 40
    assert any("blob del protocolo" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_blob_congelado_alterado() -> None:
    doc = documento_valido()
    ruta = next(iter(fp.BLOBS_CORPUS_CONGELADO))
    doc["preinscripcion"]["blobs_corpus_congelado"][ruta] = "0" * 40
    assert any("blob congelado alterado" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_exige_los_cuatro_diagnosticos() -> None:
    doc = documento_valido()
    del doc["diagnosticos"][fp.DIAG_BUSY_SPIN]
    assert any(fp.DIAG_BUSY_SPIN in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_exige_clasificacion_diagnostica_de_la_linea_base() -> None:
    doc = documento_valido()
    del doc["clasificacion_diagnostica_linea_base"]
    assert any("clasificacion diagnostica" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_diagnosticos_dentro_de_f() -> None:
    doc = documento_valido()
    intruso = dict(doc["sondas"][0])
    intruso["sonda"] = fp.DIAG_PUERTO
    doc["sondas"].append(intruso)
    assert any("diagnosticos dentro de F" in f for f in esquema.fallos_suelo_medicion(doc))


def test_esquema_rechaza_custodia_incumplida() -> None:
    doc = documento_valido()
    doc["custodia"]["diff_preinscritos_vacio"] = False
    assert any("diff en los ficheros preinscritos" in f for f in esquema.fallos_suelo_medicion(doc))


# --------------------------------------------------------------------------
# Orden round-robin y constantes preinscritas
# --------------------------------------------------------------------------


def test_orden_es_round_robin_y_no_por_bloques() -> None:
    orden = list(sondas.orden_round_robin(fp.F_NORMATIVO, 3))
    assert orden == list(fp.F_NORMATIVO) * 3
    assert orden[:3] == list(fp.F_NORMATIVO)


def test_orden_rechaza_rondas_no_positivas() -> None:
    with pytest.raises(ValueError, match="rondas debe ser positivo"):
        list(sondas.orden_round_robin(fp.F_NORMATIVO, 0))


def test_constantes_preinscritas_de_la_sonda_de_reloj() -> None:
    assert fp.N_SONDA_RELOJ == 100_000
    assert fp.WARMUP_SONDA_RELOJ == 1_000
    assert fp.N_SONDA_F == 100
    assert fp.PROCESOS_MINIMOS == 5
    assert fp.SEMILLA == 20260726


def test_medir_ns_rechaza_parametros_invalidos() -> None:
    with pytest.raises(ValueError, match="n debe ser positivo"):
        sondas.medir_ns(lambda: None, n=0, warmup=0)
    with pytest.raises(ValueError, match="warm-up no puede ser negativo"):
        sondas.medir_ns(lambda: None, n=1, warmup=-1)


def test_los_seis_ficheros_preinscritos_estan_declarados() -> None:
    assert len(fp.ARCHIVOS_PREINSCRITOS) == 6
    for ruta in fp.ARCHIVOS_PREINSCRITOS:
        assert (run_floor.RAIZ_REPOSITORIO / ruta).exists(), ruta


# --------------------------------------------------------------------------
# Recorrido extremo a extremo sintetico: main() --execute con dependencias
# inyectadas recorre el MISMO camino de produccion que la fase D real:
# precondiciones -> ejecutor -> sondas -> controles -> derivacion ->
# documento -> validacion -> escritura atomica -> relectura y revalidacion.
# Nada mide de verdad: procesos, entorno, sondas y linea base son dobles.
# --------------------------------------------------------------------------

SHA_E2E = "1234abcd" * 5


def _vector_sintetico(pid: int, sonda: str, n: int = fp.N_SONDA_F) -> list[int]:
    """Vector crudo determinista: ints, no multiplos uniformes de 100 ns."""
    base = 50_000 + 137 * (pid % 100) + 11 * len(sonda)
    return [base + (indice * 7) % 23 for indice in range(n)]


def _resultado_proceso_sintetico(pid: int) -> dict[str, Any]:
    return {
        "pid": pid,
        "sondas": {
            nombre: {
                "muestras_ns": _vector_sintetico(pid, nombre),
                "warmup_descartado": fp.WARMUP_SONDA_F,
            }
            for nombre in fp.F_NORMATIVO
        },
        "reloj": {
            "n": 1000,
            "warmup_descartado": 100,
            "p50_ns": 41,
            "p95_ns": 43,
            "p99_ns": 47,
            "min_ns": 40,
            "max_ns": 47,
            "deltas_distintos_ns": [40, 41, 42, 43, 47],
            "min_no_nulo_ns": 40,
        },
        "busy_spin": {
            "vueltas": fp.VUELTAS_BUSY_SPIN,
            "p50_inicio_ns": 500_003,
            "p50_mitad_ns": 500_021,
            "p50_final_ns": 500_007,
        },
        "duplicacion": {
            "vueltas_1x": fp.VUELTAS_BUSY_SPIN,
            "vueltas_2x": 2 * fp.VUELTAS_BUSY_SPIN,
            "p50_1x_ns": 500_003,
            "p50_2x_ns": 1_000_101,
        },
        "puerto": {
            "n": fp.N_DIAGNOSTICO,
            "warmup_descartado": fp.WARMUP_DIAGNOSTICO,
            "p50_ns": 900_001,
            "p95_ns": 950_003,
            "p99_ns": 990_007,
            "min_ns": 850_009,
            "max_ns": 990_007,
        },
        "cargas": [0.41, 0.44, 0.42],
        "incidencias": [],
        "filtrado_aplicado": False,
        "warmup_mezclado": False,
    }


def _linea_base_sintetica() -> dict[str, Any]:
    """Estructura minima con la misma forma que la evidencia versionada."""
    return {
        "escenarios_remedidos": {
            "E-SESIONES-5_variacion_entre_ejecuciones": {
                "variacion_entre_sesiones": {
                    "escenario_sintetico": {
                        "capa_lenta__p50_ms": {
                            "valores_por_sesion": [100.0, 100.5, 101.0, 100.2, 100.8]
                        },
                        "capa_lenta__p95_ms": {
                            "valores_por_sesion": [120.0, 121.0, 122.0, 120.5, 121.5]
                        },
                    }
                }
            }
        }
    }


def _custodia_e2e() -> fp.EntornoCustodia:
    """Custodia que lee el arbol real (solo lectura) y fija HEAD = SHA_E2E.

    ``blob_en_commit`` simula un commit que registra exactamente el
    contenido del arbol: es el caso conforme. Las pruebas negativas lo
    desalinean para comprobar que la comparacion NO es tautologica.
    """
    raiz = run_floor.RAIZ_REPOSITORIO

    def leer(ruta: str) -> bytes:
        return (raiz / ruta).read_bytes()

    return fp.EntornoCustodia(
        leer_bytes=leer,
        es_ancestro=lambda _a, _d: True,
        existe_commit=lambda _s: True,
        head=lambda: SHA_E2E,
        arbol_limpio=lambda: True,
        diff_vacio=lambda _a, _b, _r: True,
        blob_en_commit=lambda _s, ruta: fp.blob_git(leer(ruta)),
    )


def _deps_e2e(
    *,
    resultados: Sequence[Mapping[str, Any]] | None = None,
    ejecutor: Any = None,
    boot_id_final: str = "boot-e2e",
) -> run_floor.DependenciasCorrida:
    listado: list[Mapping[str, Any]] = (
        [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
        if resultados is None
        else list(resultados)
    )

    def ejecutor_por_defecto(_plan: run_floor.PlanCorrida) -> list[Mapping[str, Any]]:
        return listado

    def capturar(etapa: str) -> dict[str, Any]:
        boot = "boot-e2e" if etapa == "inicial" else boot_id_final
        return {"etapa": etapa, "boot_id": boot, "carga": 0.4}

    return run_floor.DependenciasCorrida(
        entorno_custodia=_custodia_e2e(),
        ejecutor=ejecutor_por_defecto if ejecutor is None else ejecutor,
        capturar_entorno=capturar,
        cargar_linea_base=_linea_base_sintetica,
    )


def _main_e2e(salida: Path, deps: run_floor.DependenciasCorrida) -> int:
    return run_floor.main(
        ["--execute", "--preinscription-commit", SHA_E2E, "--output", str(salida)],
        dependencias=deps,
    )


def test_e2e_recorrido_completo_produce_json_valido(tmp_path: Path) -> None:
    """main() --execute recorre el camino completo y publica un JSON valido."""
    salida = tmp_path / "suelo_medicion_e2e.json"
    assert _main_e2e(salida, _deps_e2e()) == run_floor.CODIGO_OK
    assert salida.exists()

    releido = json.loads(salida.read_text(encoding="utf-8"))
    assert esquema.fallos_suelo_medicion(releido) == []

    # La derivacion publicada coincide exactamente con las formulas
    # preinscritas aplicadas a los vectores sinteticos inyectados.
    medidas = [
        medida(
            str(entrada["sonda"]),
            int(entrada["pid"]),
            int(entrada["p50_ns"]),
            int(entrada["p95_ns"]),
        )
        for entrada in releido["sondas"]
    ]
    esperada = fp.derivar(medidas)
    derivacion = releido["derivacion"]
    assert derivacion["sm_ns"] == esperada.sm
    assert derivacion["b50_ns"] == esperada.b50
    assert derivacion["b95_ns"] == esperada.b95
    assert derivacion["b_ns"] == esperada.b == max(esperada.b50, esperada.b95)
    assert derivacion["u_ns"] == esperada.u == fp.FACTOR_U * esperada.b
    assert derivacion["m"] == 1

    # Los blobs preinscritos publicados son los del arbol real.
    for ruta, blob in releido["preinscripcion"]["blobs_preinscritos"].items():
        contenido = (run_floor.RAIZ_REPOSITORIO / ruta).read_bytes()
        assert blob == fp.blob_git(contenido), ruta

    assert releido["preinscripcion"]["commit_a"] == SHA_E2E
    assert all(releido["controles_internos"].values())
    assert releido["regimenes_por_percentil"], "clasificacion diagnostica vacia"
    assert releido["no_autoriza"]["aprobacion_tol_209"] is False
    assert releido["no_autoriza"]["limite_duro_tol_107"] is False


def test_e2e_segunda_ejecucion_con_salida_existente_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    assert _main_e2e(salida, _deps_e2e()) == run_floor.CODIGO_OK
    contenido_original = salida.read_bytes()
    assert _main_e2e(salida, _deps_e2e()) == run_floor.CODIGO_BLOQUEADO
    assert salida.read_bytes() == contenido_original


def test_e2e_con_cuatro_procesos_bloquea_sin_escribir(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(4)]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_con_pids_repetidos_bloquea_sin_escribir(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001) for _ in range(fp.PROCESOS_MINIMOS)]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_duplicacion_fallida_bloquea_sin_escribir(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    resultados[2]["duplicacion"]["p50_2x_ns"] = resultados[2]["duplicacion"]["p50_1x_ns"]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_busy_spin_con_deriva_monotona_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    resultados[0]["busy_spin"].update(
        {"p50_inicio_ns": 500_000, "p50_mitad_ns": 600_000, "p50_final_ns": 700_000}
    )
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_cambio_de_boot_id_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    deps = _deps_e2e(boot_id_final="boot-distinto")
    assert _main_e2e(salida, deps) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_vector_redondeado_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    redondeado = [50_000 + 100 * i for i in range(fp.N_SONDA_F)]
    resultados[1]["sondas"][fp.SONDA_VACIA]["muestras_ns"] = redondeado
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_vector_incompleto_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    resultados[3]["sondas"][fp.SONDA_SQLITE_0]["muestras_ns"] = _vector_sintetico(
        9004, fp.SONDA_SQLITE_0
    )[:30]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_ejecutor_que_lanza_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"

    def ejecutor_roto(_plan: run_floor.PlanCorrida) -> list[Mapping[str, Any]]:
        msg = "proceso hijo murio"
        raise RuntimeError(msg)

    assert _main_e2e(salida, _deps_e2e(ejecutor=ejecutor_roto)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_resultado_sin_clave_obligatoria_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    del resultados[0]["reloj"]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_precondicion_fallida_no_llega_a_medir(tmp_path: Path) -> None:
    """Con arbol sucio, el ejecutor inyectado NUNCA llega a invocarse."""
    salida = tmp_path / "suelo.json"
    invocado: list[bool] = []

    def ejecutor_espia(_plan: run_floor.PlanCorrida) -> list[Mapping[str, Any]]:
        invocado.append(True)
        return []

    deps = _deps_e2e(ejecutor=ejecutor_espia)
    custodia_sucia = fp.EntornoCustodia(
        leer_bytes=deps.entorno_custodia.leer_bytes,
        es_ancestro=deps.entorno_custodia.es_ancestro,
        existe_commit=deps.entorno_custodia.existe_commit,
        head=deps.entorno_custodia.head,
        arbol_limpio=lambda: False,
        diff_vacio=deps.entorno_custodia.diff_vacio,
        blob_en_commit=deps.entorno_custodia.blob_en_commit,
    )
    deps_sucias = run_floor.DependenciasCorrida(
        entorno_custodia=custodia_sucia,
        ejecutor=deps.ejecutor,
        capturar_entorno=deps.capturar_entorno,
        cargar_linea_base=deps.cargar_linea_base,
    )
    assert _main_e2e(salida, deps_sucias) == run_floor.CODIGO_BLOQUEADO
    assert not invocado
    assert not salida.exists()


def test_worker_sin_execute_no_mide(capsys: pytest.CaptureFixture[str]) -> None:
    """El worker interno tambien queda detras de la guarda --execute."""
    assert run_floor.main(["--worker"]) == run_floor.CODIGO_SIN_EXECUTE
    assert "no mide sin --execute" in capsys.readouterr().out


def test_escritura_atomica_no_deja_temporales(tmp_path: Path) -> None:
    salida = tmp_path / "anidado" / "suelo.json"
    run_floor.escribir_json_atomico(salida, {"a": 1})
    assert json.loads(salida.read_text(encoding="utf-8")) == {"a": 1}
    residuos = [p for p in salida.parent.iterdir() if p.name != salida.name]
    assert residuos == []


def test_clasificar_linea_base_con_evidencia_versionada_real() -> None:
    """La clasificacion diagnostica funciona sobre el artefacto real."""
    datos = run_floor.cargar_linea_base_real()
    entradas = run_floor.clasificar_linea_base(datos, sm=50_000, b=70_000, u=350_000)
    assert len(entradas) == 6  # 3 escenarios x 2 capas
    for entrada in entradas:
        assert entrada["min_p95_ns"] >= entrada["min_p50_ns"]
        assert "registro" in entrada
    # Con U = 0,35 ms, rank() (~120 ms) queda en relativo en ambos percentiles.
    rank = [e for e in entradas if "rank" in e["magnitud"]]
    assert rank
    assert all(e.get("p50") == fp.REGIMEN_RELATIVO for e in rank)
    assert all(e.get("p95") == fp.REGIMEN_RELATIVO for e in rank)


def test_controles_desde_resultados_todo_valido() -> None:
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    captura = {"etapa": "x", "boot_id": "boot-e2e", "carga": 0.4}
    controles = run_floor.evaluar_controles_desde_resultados(
        resultados, captura_inicial=captura, captura_final=captura, custodia_ok=True
    )
    assert set(controles) == set(fp.CONTROLES_BLOQUEANTES)
    assert all(controles.values())


def test_controles_no_confian_en_flags_del_proceso() -> None:
    """Los flags declarados se cruzan con los datos, no se aceptan solos."""
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    resultados[0]["filtrado_aplicado"] = True
    captura = {"etapa": "x", "boot_id": "boot-e2e", "carga": 0.4}
    controles = run_floor.evaluar_controles_desde_resultados(
        resultados, captura_inicial=captura, captura_final=captura, custodia_ok=True
    )
    assert controles["sin_filtrado"] is False


def _controles_de(resultados: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    captura = {"etapa": "x", "boot_id": "boot-e2e", "carga": 0.4}
    return run_floor.evaluar_controles_desde_resultados(
        resultados, captura_inicial=captura, captura_final=captura, custodia_ok=True
    )


def test_warmup_se_recomputa_aunque_el_worker_declare_lo_contrario() -> None:
    """Un worker que miente sobre el warm-up no supera el control.

    Regresion del invariante 8: ``warmup_separado`` se derivaba solo del
    flag ``warmup_mezclado``, de modo que declarar 0 descartadas con el
    flag en False pasaba pese a que el plan preinscrito exige 5.
    """
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    for nombre in fp.F_NORMATIVO:
        resultados[0]["sondas"][nombre]["warmup_descartado"] = 0
    assert resultados[0]["warmup_mezclado"] is False, "el worker declara no haber mezclado"
    assert _controles_de(resultados)["warmup_separado"] is False


def test_forma_del_vector_se_publica_como_diagnostico(tmp_path: Path) -> None:
    """El artefacto publica la cardinalidad del vector para el auditor.

    El filtrado silencioso (recortar la cola y repadear) NO se convierte en
    control bloqueante: es indistinguible de un suelo cuantizado por la
    resolucion del reloj sin evidencia adicional. Se publica la forma del
    vector para que un auditor lo evalue. Limitacion declarada en el §8.
    """
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    mediana = 50_000
    resultados[1]["sondas"][fp.SONDA_SQLITE_0]["muestras_ns"] = [mediana] * 80 + [
        mediana + i for i in range(1, 21)
    ]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_OK
    releido = json.loads(salida.read_text(encoding="utf-8"))
    sospechosa = next(
        e for e in releido["sondas"] if e["pid"] == 9002 and e["sonda"] == fp.SONDA_SQLITE_0
    )
    assert sospechosa["repeticion_maxima"] == 80
    assert sospechosa["valores_distintos"] == 21
    # Toda entrada publica ambos diagnosticos, no solo la sospechosa.
    for entrada in releido["sondas"]:
        assert "valores_distintos" in entrada
        assert "repeticion_maxima" in entrada


def test_e2e_worker_que_miente_sobre_el_warmup_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    for nombre in fp.F_NORMATIVO:
        resultados[2]["sondas"][nombre]["warmup_descartado"] = 0
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


# --------------------------------------------------------------------------
# Regresiones de la revision adversarial de la fase A
# --------------------------------------------------------------------------


def test_los_cinco_modulos_preinscritos_parsean() -> None:
    """Guarda contra sintaxis invalida en cualquier modulo congelado.

    Se comprueba con ``ast.parse`` sobre el fichero del arbol, no con una
    importacion: una importacion puede resolverse desde bytecode cacheado
    y ocultar que el fuente congelado no compila.
    """
    for ruta in fp.ARCHIVOS_PREINSCRITOS:
        if not ruta.endswith(".py"):
            continue
        fuente = (run_floor.RAIZ_REPOSITORIO / ruta).read_text(encoding="utf-8")
        ast.parse(fuente, filename=ruta)


def test_pid_no_entero_es_rechazado_y_no_silencia_la_recomputacion() -> None:
    """Un campo con tipo manipulado no puede desactivar la recomputacion.

    Antes de esta guarda, publicar ``pid`` como cadena hacia que la
    reconstruccion de medidas devolviese ``None`` y la recomputacion de
    SM/B/U se omitiese por completo: bastaba para publicar una derivacion
    arbitraria (por ejemplo todo a cero) con validacion en verde.
    """
    doc = documento_valido()
    for entrada in doc["sondas"]:
        entrada["pid"] = str(entrada["pid"])
    doc["derivacion"].update({"sm_ns": 0, "b50_ns": 0, "b95_ns": 0, "b_ns": 0, "u_ns": 0})
    doc["derivacion"]["descomposicion_b"] = {s: {"b50_ns": 0, "b95_ns": 0} for s in fp.F_NORMATIVO}
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("pid debe ser un entero" in f for f in fallos)
    assert any("no verificable" in f for f in fallos)


@pytest.mark.parametrize(
    "campo", ["p50_ns", "p95_ns", "p99_ns", "min_ns", "max_ns", "media_truncada_ns"]
)
def test_percentil_no_entero_es_rechazado(campo: str) -> None:
    doc = documento_valido()
    doc["sondas"][0][campo] = float(doc["sondas"][0][campo])
    assert any("debe ser un entero" in f for f in esquema.fallos_suelo_medicion(doc))


def test_derivacion_incoherente_con_las_sondas_es_rechazada() -> None:
    doc = documento_valido()
    doc["derivacion"]["b_ns"] = int(doc["derivacion"]["b_ns"])
    doc["derivacion"]["b50_ns"] = 0
    doc["derivacion"]["b95_ns"] = 0
    doc["derivacion"]["b_ns"] = 0
    doc["derivacion"]["u_ns"] = 0
    assert any("recomputacion" in f for f in esquema.fallos_suelo_medicion(doc))


@pytest.mark.parametrize("valor", [0, None, "", "si", 1])
def test_control_que_no_sea_true_estricto_es_fallido(valor: object) -> None:
    """0, None o cadena no pueden colarse como control satisfecho."""
    doc = documento_valido()
    doc["controles_internos"]["carga_registrada"] = valor
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("controles bloqueantes fallidos" in f for f in fallos)


def test_head_al_publicar_distinto_del_commit_a_es_rechazado() -> None:
    doc = documento_valido()
    doc["custodia"]["head"] = "f" * 40
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("difiere del commit de" in f for f in fallos)


def test_custodia_sin_reverificacion_tras_medir_es_rechazada() -> None:
    doc = documento_valido()
    del doc["custodia"]["reverificada_tras_medir"]
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("no se reverifico despues de medir" in f for f in fallos)


def test_head_en_ejecucion_distinto_de_commit_a_es_rechazado() -> None:
    doc = documento_valido()
    doc["preinscripcion"]["head_en_ejecucion"] = "e" * 40
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("head_en_ejecucion difiere" in f for f in fallos)


def test_escritura_atomica_nunca_sobrescribe(tmp_path: Path) -> None:
    """Cierra la ventana TOCTOU: si la salida aparece, no se destruye."""
    salida = tmp_path / "suelo.json"
    salida.write_text("PREEXISTENTE", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_floor.escribir_json_atomico(salida, {"a": 1})
    assert salida.read_text(encoding="utf-8") == "PREEXISTENTE"
    residuos = [p for p in tmp_path.iterdir() if p.name != salida.name]
    assert residuos == []


def test_e2e_head_que_cambia_durante_la_medicion_bloquea(tmp_path: Path) -> None:
    """La custodia se reverifica tras medir: un HEAD movido bloquea."""
    salida = tmp_path / "suelo.json"
    deps = _deps_e2e()
    heads = [SHA_E2E, SHA_E2E, "c0ffee11" * 5]

    def head_movil() -> str:
        return heads.pop(0) if len(heads) > 1 else heads[0]

    custodia_movil = fp.EntornoCustodia(
        leer_bytes=deps.entorno_custodia.leer_bytes,
        es_ancestro=deps.entorno_custodia.es_ancestro,
        existe_commit=deps.entorno_custodia.existe_commit,
        head=head_movil,
        arbol_limpio=lambda: True,
        diff_vacio=lambda _a, _b, _r: True,
        blob_en_commit=deps.entorno_custodia.blob_en_commit,
    )
    deps_movil = run_floor.DependenciasCorrida(
        entorno_custodia=custodia_movil,
        ejecutor=deps.ejecutor,
        capturar_entorno=deps.capturar_entorno,
        cargar_linea_base=deps.cargar_linea_base,
    )
    assert _main_e2e(salida, deps_movil) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_salida_que_aparece_durante_la_medicion_no_se_destruye(tmp_path: Path) -> None:
    """La ruta de salida aparece MIENTRAS se mide: se bloquea sin destruirla.

    Regresion del bloqueante en que el manejador de error borraba el
    fichero ajeno que ``os.link`` acababa de proteger: la correccion TOCTOU
    habia sustituido «sobrescribir en silencio» por «destruir en silencio».
    """
    salida = tmp_path / "suelo.json"
    deps = _deps_e2e()
    ajeno = b'{"evidencia": "de otra corrida"}'

    def ejecutor_que_crea_la_salida(plan: run_floor.PlanCorrida) -> list[Mapping[str, Any]]:
        salida.write_bytes(ajeno)
        return list(deps.ejecutor(plan))

    deps_colision = run_floor.DependenciasCorrida(
        entorno_custodia=deps.entorno_custodia,
        ejecutor=ejecutor_que_crea_la_salida,
        capturar_entorno=deps.capturar_entorno,
        cargar_linea_base=deps.cargar_linea_base,
    )
    assert _main_e2e(salida, deps_colision) == run_floor.CODIGO_BLOQUEADO
    assert salida.read_bytes() == ajeno, "se destruyo evidencia ajena"
    residuos = [p for p in tmp_path.iterdir() if p.name != salida.name]
    assert residuos == []


def test_custodia_no_es_tautologica_contra_el_commit() -> None:
    """El blob del arbol se compara contra lo que registra el commit A.

    Sin esta comparacion independiente, calcular el blob leyendo el arbol y
    volver a compararlo con el mismo arbol nunca detectaria una alteracion.
    """
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    alterado = fp.ARCHIVOS_PREINSCRITOS[2]
    # El arbol y los blobs declarados coinciden entre si, pero el commit
    # registra OTRO contenido para ese fichero.
    doble = CustodiaDoble(
        contenidos,
        blobs_en_commit={**blobs, alterado: fp.blob_git(b"lo que el commit registraba")},
    )
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("difiere del commit de preinscripcion" in f and alterado in f for f in fallos)


def test_custodia_detecta_fichero_no_registrado_en_el_commit() -> None:
    contenidos = contenidos_custodia()
    blobs = blobs_de(contenidos)
    ausente = fp.ARCHIVOS_PREINSCRITOS[0]
    sin_ese = {r: b for r, b in blobs.items() if r != ausente}
    doble = CustodiaDoble(contenidos, blobs_en_commit=sin_ese)
    fallos = fp.verificar_custodia(
        doble.entorno(),
        sha_a="A",
        blobs_preinscritos={r: blobs[r] for r in fp.ARCHIVOS_PREINSCRITOS},
        blob_arnes=blobs[fp.ARCHIVO_ARNES_HEREDADO],
        blobs_congelados={r: blobs[r] for r in fp.BLOBS_CORPUS_CONGELADO},
    )
    assert any("no registrado en el commit" in f for f in fallos)


def test_blob_en_commit_real_coincide_con_git() -> None:
    """El proveedor real usa git como fuente de verdad independiente."""
    entorno = run_floor.entorno_custodia_real()
    ruta = "experiments/adr002/tolerances/harness.py"
    esperado = subprocess.run(
        ["git", "rev-parse", f"HEAD:{ruta}"],
        cwd=str(run_floor.RAIZ_REPOSITORIO),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert entorno.blob_en_commit("HEAD", ruta) == esperado
    assert entorno.blob_en_commit("HEAD", "ruta/que/no/existe.py") is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("min_ns", float("nan")),
        ("max_ns", float("inf")),
        ("pid", [1, 2]),
        ("pid", {"a": 1}),
        ("n", "100"),
        ("media_truncada_ns", None),
        ("sonda", 7),
    ],
)
def test_validador_es_total_ante_valores_manipulados(campo: str, valor: object) -> None:
    """El validador NUNCA lanza: devuelve fallos ante cualquier valor JSON.

    Un validador que lanzase dejaria de ser guarda: quien lo invoca no
    obtendria veredicto y un artefacto manipulado quedaria sin evaluar.
    """
    doc = documento_valido()
    doc["sondas"][3][campo] = valor
    fallos = esquema.fallos_suelo_medicion(doc)
    assert fallos
    assert not any("validacion abortada" in f for f in fallos), fallos


def test_validador_no_lanza_con_procesos_malformados() -> None:
    doc = documento_valido()
    doc["procesos"] = [{"pid": [1]}, {"pid": None}, "texto", 7, {"pid": 3}]
    fallos = esquema.fallos_suelo_medicion(doc)
    assert fallos
    assert not any("validacion abortada" in f for f in fallos), fallos


def test_validador_convierte_fallo_interno_en_fallo_de_validacion() -> None:
    """La red de seguridad existe y no enmascara documentos conformes."""

    class Explosivo(dict[str, Any]):
        def get(self, *_a: Any, **_k: Any) -> Any:
            msg = "boom"
            raise RuntimeError(msg)

    fallos = esquema.fallos_suelo_medicion(Explosivo())
    assert any("validacion abortada" in f for f in fallos)


def _entrada_regimen(doc: dict[str, Any]) -> dict[str, Any]:
    entrada: dict[str, Any] = doc["regimenes_por_percentil"][0]
    return entrada


def test_regimen_declarado_se_recomputa_contra_u() -> None:
    """Declarar un regimen que no salga de aplicar U invalida el artefacto."""
    doc = documento_valido()
    entrada = _entrada_regimen(doc)
    u = int(doc["derivacion"]["u_ns"])
    sm = int(doc["derivacion"]["sm_ns"])
    # Minimos por encima de SM (no dominada) y por encima de U: el regimen
    # correcto es relativo en ambos, pero se declara absoluto.
    entrada.update(
        {
            "min_p50_ns": max(sm, u) + 10,
            "min_p95_ns": max(sm, u) + 20,
            "p50": fp.REGIMEN_ABSOLUTO,
            "p95": fp.REGIMEN_ABSOLUTO,
        }
    )
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("corresponde 'relativo'" in f for f in fallos), fallos


def test_guarda_sm_no_es_eludible_en_el_artefacto() -> None:
    """min P95 < SM obliga a NO_EVALUABLE tambien a nivel de artefacto."""
    doc = documento_valido()
    sm = int(doc["derivacion"]["sm_ns"])
    _entrada_regimen(doc).update(
        {
            "min_p50_ns": sm - 20,
            "min_p95_ns": sm - 10,
            "p50": fp.REGIMEN_RELATIVO,
            "p95": fp.REGIMEN_RELATIVO,
        }
    )
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("guarda de dominancia se eludio" in f for f in fallos), fallos


def test_no_evaluable_no_es_comodin_universal() -> None:
    """Declarar NO_EVALUABLE no desactiva invariante ni regimenes."""
    doc = documento_valido()
    doc["regimenes_por_percentil"] = [
        {
            "magnitud": "comodin",
            "resultado": fp.NO_EVALUABLE,
            "p50": "inventado",
            "p95": None,
            "min_p50_ns": 5000,
            "min_p95_ns": 1,
        }
    ]
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("invariante violado" in f for f in fallos), fallos
    assert any("no puede publicar regimen" in f for f in fallos), fallos


def test_no_evaluable_debe_estar_justificado_por_sm() -> None:
    doc = documento_valido()
    sm = int(doc["derivacion"]["sm_ns"])
    doc["regimenes_por_percentil"] = [
        {
            "magnitud": "injustificada",
            "resultado": fp.NO_EVALUABLE,
            "min_p50_ns": sm + 100,
            "min_p95_ns": sm + 200,
        }
    ]
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("sin que min_s P95" in f for f in fallos), fallos


def test_muestras_negativas_son_rechazadas() -> None:
    """Una duracion medida con reloj monotonico no puede ser negativa."""
    doc = documento_valido()
    negativas = [-1_000_000 - i for i in range(fp.N_SONDA_F)]
    ordenadas = sorted(negativas)
    doc["sondas"][0].update(
        {
            "muestras_ns": negativas,
            "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
            "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
            "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
            "min_ns": ordenadas[0],
            "max_ns": ordenadas[-1],
            "media_truncada_ns": sum(ordenadas) // len(ordenadas),
        }
    )
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("muestras negativas" in f for f in fallos), fallos


def test_incidencias_registradas_impiden_publicar() -> None:
    """Una sonda que no midio la forma declarada no puede publicar B ni U."""
    doc = documento_valido()
    doc["entorno"]["incidencias"] = ["SQLite_0_filas devolvio filas"]
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("incidencias registradas" in f for f in fallos), fallos


@pytest.mark.parametrize("mutacion", ["ausente", "nulo"])
def test_head_de_publicacion_es_obligatorio(mutacion: str) -> None:
    """Un HEAD ausente no puede ser mas permisivo que un HEAD distinto."""
    doc = documento_valido()
    if mutacion == "ausente":
        del doc["custodia"]["head"]
    else:
        doc["custodia"]["head"] = None
    doc["preinscripcion"]["commit_a"] = "dead" * 10
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("falta el HEAD de publicacion" in f for f in fallos), fallos


def test_head_en_ejecucion_es_obligatorio() -> None:
    doc = documento_valido()
    doc["preinscripcion"].pop("head_en_ejecucion", None)
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("falta head_en_ejecucion" in f for f in fallos), fallos


def test_e2e_incidencia_en_una_sonda_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    resultados[2]["incidencias"] = ["SQLite_1_fila no devolvio exactamente una fila"]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_muestras_negativas_bloquean(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    resultados = [_resultado_proceso_sintetico(9001 + i) for i in range(fp.PROCESOS_MINIMOS)]
    resultados[0]["sondas"][fp.SONDA_VACIA]["muestras_ns"] = [
        -1000 - i for i in range(fp.N_SONDA_F)
    ]
    assert _main_e2e(salida, _deps_e2e(resultados=resultados)) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


@pytest.mark.parametrize("etapa", ["inicial", "final"])
def test_e2e_captura_de_entorno_que_lanza_bloquea(tmp_path: Path, etapa: str) -> None:
    """Una dependencia que lanza produce CODIGO_BLOQUEADO, no una traza."""
    salida = tmp_path / "suelo.json"
    deps = _deps_e2e()

    def capturar(e: str) -> Mapping[str, Any]:
        if e == etapa:
            msg = f"/proc ilegible en etapa {e}"
            raise OSError(msg)
        return deps.capturar_entorno(e)

    deps_roto = run_floor.DependenciasCorrida(
        entorno_custodia=deps.entorno_custodia,
        ejecutor=deps.ejecutor,
        capturar_entorno=capturar,
        cargar_linea_base=deps.cargar_linea_base,
    )
    assert _main_e2e(salida, deps_roto) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_custodia_que_lanza_bloquea(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    deps = _deps_e2e()

    def arbol_que_estalla() -> bool:
        msg = "git status fallo: index file smaller than expected"
        raise run_floor.EjecucionBloqueadaError(msg)

    custodia = fp.EntornoCustodia(
        leer_bytes=deps.entorno_custodia.leer_bytes,
        es_ancestro=deps.entorno_custodia.es_ancestro,
        existe_commit=deps.entorno_custodia.existe_commit,
        head=deps.entorno_custodia.head,
        arbol_limpio=arbol_que_estalla,
        diff_vacio=deps.entorno_custodia.diff_vacio,
        blob_en_commit=deps.entorno_custodia.blob_en_commit,
    )
    deps_roto = run_floor.DependenciasCorrida(
        entorno_custodia=custodia,
        ejecutor=deps.ejecutor,
        capturar_entorno=deps.capturar_entorno,
        cargar_linea_base=deps.cargar_linea_base,
    )
    assert _main_e2e(salida, deps_roto) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()


def test_e2e_revalidacion_fallida_borra_el_artefacto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cobertura del paso de relectura y revalidacion tras escribir.

    Se fuerza que el documento releido NO valide: el artefacto ya escrito
    debe eliminarse y la corrida devolver CODIGO_BLOQUEADO.
    """
    salida = tmp_path / "suelo.json"
    llamadas: list[int] = []
    original = esquema.fallos_suelo_medicion

    def validador(doc: Mapping[str, Any]) -> list[str]:
        llamadas.append(1)
        if len(llamadas) >= 2:  # la segunda llamada es la revalidacion
            return ["fallo inyectado en la revalidacion"]
        return original(doc)

    monkeypatch.setattr(esquema, "fallos_suelo_medicion", validador)
    assert _main_e2e(salida, _deps_e2e()) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists(), "la revalidacion fallida debe eliminar el artefacto"
    assert len(llamadas) >= 2
    assert list(tmp_path.iterdir()) == []


def test_e2e_documento_invalido_no_llega_a_escribirse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cobertura de la validacion previa a la escritura."""
    salida = tmp_path / "suelo.json"
    monkeypatch.setattr(
        esquema,
        "fallos_suelo_medicion",
        lambda _doc: ["fallo inyectado antes de escribir"],
    )
    assert _main_e2e(salida, _deps_e2e()) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()
    assert list(tmp_path.iterdir()) == []


def test_resolucion_percentil_usa_el_rango_real_sin_coma_flotante() -> None:
    """El ordinal publicado debe coincidir con el rango nearest-rank real.

    Con ``floor(0.99 * n)`` habia un off-by-one para todo n multiplo de 100
    —justo los tamanos preinscritos— y el artefacto afirmaba ser el maximo
    sin serlo.
    """
    for n in (30, 99, 100, 101, 150, 200, 1000, 100_000):
        muestras = list(range(1, n + 1))
        p99 = fp.percentil_ns(muestras, 99, 100)
        ordinal_real = n - muestras.index(p99)
        texto = fp.resolucion_percentil(n)
        if ordinal_real == 1:
            assert "coincide con el maximo observado" in texto, (n, texto)
        else:
            assert f"la {ordinal_real}.a peor muestra" in texto, (n, texto)


def test_resolucion_percentil_con_n_100_no_afirma_ser_el_maximo() -> None:
    texto = fp.resolucion_percentil(fp.N_SONDA_F)
    assert "2.a peor muestra" in texto
    assert "coincide con el maximo" not in texto


@pytest.mark.parametrize(
    ("ruta", "clave"),
    [
        ("doc", "version_esquema"),
        ("doc", "protocolo"),
        ("preinscripcion", "blob_protocolo"),
    ],
)
def test_null_explicito_no_absuelve_la_identidad(ruta: str, clave: str) -> None:
    """Un `null` no puede ser mas permisivo que un valor distinto."""
    doc = documento_valido()
    destino: dict[str, Any] = doc if ruta == "doc" else doc[ruta]
    destino[clave] = None
    assert esquema.fallos_suelo_medicion(doc), f"{ruta}.{clave} = null quedo absuelto"


def test_regimenes_vacios_no_pueden_borrar_el_veredicto() -> None:
    doc = documento_valido()
    doc["regimenes_por_percentil"] = []
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("regimenes_por_percentil vacio" in f for f in fallos), fallos


@pytest.mark.parametrize("valor", [None, {}, {"magnitudes": []}, {"magnitudes": "x"}])
def test_clasificacion_diagnostica_no_puede_vaciarse(valor: object) -> None:
    """Borrar la divulgacion de la linea base debe ser detectable."""
    doc = documento_valido()
    doc["clasificacion_diagnostica_linea_base"] = valor
    assert esquema.fallos_suelo_medicion(doc)


def test_warmup_distinto_del_preinscrito_es_rechazado() -> None:
    """Un artefacto no puede contradecir su propio plan de warm-up."""
    doc = documento_valido()
    doc["sondas"][0]["warmup_descartado"] = 0
    fallos = esquema.fallos_suelo_medicion(doc)
    assert any("difiere del preinscrito" in f for f in fallos), fallos


def test_temporal_no_eliminable_se_denuncia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un residuo en disco nunca queda en silencio.

    Si el temporal no se puede borrar, la corrida no puede seguir
    afirmando que no publico nada: se denuncia y falla.
    """
    salida = tmp_path / "suelo.json"
    real_unlink = Path.unlink

    def unlink_que_falla(self: Path, *a: Any, **k: Any) -> None:
        if self.name.endswith(".tmp"):
            msg = "operacion no permitida"
            raise PermissionError(msg)
        real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink_que_falla)
    with pytest.raises(run_floor.ResiduoNoEliminableError, match="no eliminable"):
        run_floor.escribir_json_atomico(salida, {"a": 1})


def test_e2e_temporal_no_eliminable_bloquea(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    salida = tmp_path / "suelo.json"
    real_unlink = Path.unlink

    def unlink_que_falla(self: Path, *a: Any, **k: Any) -> None:
        if self.name.endswith(".tmp"):
            msg = "operacion no permitida"
            raise PermissionError(msg)
        real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink_que_falla)
    assert _main_e2e(salida, _deps_e2e()) == run_floor.CODIGO_BLOQUEADO


def test_e2e_artefacto_invalido_no_eliminable_se_denuncia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si el artefacto invalido sobrevive, el veredicto lo dice."""
    salida = tmp_path / "suelo.json"
    llamadas: list[int] = []
    original = esquema.fallos_suelo_medicion

    def validador(doc: Mapping[str, Any]) -> list[str]:
        llamadas.append(1)
        return ["fallo inyectado"] if len(llamadas) >= 2 else original(doc)

    real_unlink = Path.unlink

    def unlink_selectivo(self: Path, *a: Any, **k: Any) -> None:
        if self.name == salida.name:
            msg = "operacion no permitida"
            raise PermissionError(msg)
        real_unlink(self, *a, **k)

    monkeypatch.setattr(esquema, "fallos_suelo_medicion", validador)
    monkeypatch.setattr(Path, "unlink", unlink_selectivo)
    codigo, fallos = run_floor.ejecutar_corrida(
        sha_a=SHA_E2E, salida=salida, dependencias=_deps_e2e()
    )
    assert codigo == run_floor.CODIGO_BLOQUEADO
    assert any("ATENCION" in f and "no eliminable" in f for f in fallos), fallos


def test_e2e_arbol_sucio_tras_medir_bloquea(tmp_path: Path) -> None:
    """Si el arbol se ensucia durante la corrida, no se publica nada."""
    salida = tmp_path / "suelo.json"
    deps = _deps_e2e()
    llamadas: list[int] = []

    def limpio_solo_al_principio() -> bool:
        llamadas.append(1)
        return len(llamadas) <= 1

    custodia = fp.EntornoCustodia(
        leer_bytes=deps.entorno_custodia.leer_bytes,
        es_ancestro=deps.entorno_custodia.es_ancestro,
        existe_commit=deps.entorno_custodia.existe_commit,
        head=deps.entorno_custodia.head,
        arbol_limpio=limpio_solo_al_principio,
        diff_vacio=deps.entorno_custodia.diff_vacio,
        blob_en_commit=deps.entorno_custodia.blob_en_commit,
    )
    deps_sucias = run_floor.DependenciasCorrida(
        entorno_custodia=custodia,
        ejecutor=deps.ejecutor,
        capturar_entorno=deps.capturar_entorno,
        cargar_linea_base=deps.cargar_linea_base,
    )
    assert _main_e2e(salida, deps_sucias) == run_floor.CODIGO_BLOQUEADO
    assert not salida.exists()
