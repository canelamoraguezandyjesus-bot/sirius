"""Pruebas de la preinscripcion del suelo de medicion (ADR002-TOL-209, fase A).

Todo es sintetico o doble controlado. **Ninguna prueba ejecuta la corrida
real del suelo**, ninguna escribe artefactos y ninguna toca el repositorio.

Cada prueba negativa corresponde a una condicion de la matriz bloqueante
del paquete de trabajo 05.
"""

from __future__ import annotations

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
            "descomposicion_b": {s: {"b50_ns": 0, "b95_ns": 0} for s in fp.F_NORMATIVO},
        },
        "regimenes_por_percentil": [
            {
                "magnitud": "ejemplo",
                "p50": fp.REGIMEN_ABSOLUTO,
                "p95": fp.REGIMEN_ABSOLUTO,
                "min_p50_ns": 1000,
                "min_p95_ns": 2000,
            }
        ],
        "clasificacion_diagnostica_linea_base": {"fts5": "pendiente", "rank": "pendiente"},
        "custodia": {"diff_preinscritos_vacio": True, "sha_a_es_ancestro": True},
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
    ) -> None:
        self.contenidos = dict(contenidos)
        self._head = head
        self._ancestro = ancestro
        self._existe = existe
        self._limpio = limpio
        self._diff_vacio = diff_vacio

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
