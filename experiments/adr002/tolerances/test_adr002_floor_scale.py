"""Pruebas de la preinscripcion sucesora del suelo multiescala (TOL-209).

Se congelan junto al metodo, ANTES de medir. Cubren cuatro cosas:

1. las funciones puras del protocolo, con sus fronteras exactas en enteros;
2. las sondas, incluida su neutralidad respecto de FTS5, ``rank()`` y
   cualquier candidato;
3. el recorrido COMPLETO del orquestador, de extremo a extremo, con
   dependencias inyectadas y datos sinteticos: ninguna prueba mide;
4. el validador del artefacto, contra un catalogo de mutaciones que un
   artefacto manipulado podria intentar.

Ninguna prueba de este fichero ejecuta la medicion real ni escribe en
``artifacts/``.
"""

from __future__ import annotations

import ast
import json
import math
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.tolerances import floor_scale_probes as sondas
from experiments.adr002.tolerances import floor_scale_protocol as fp
from experiments.adr002.tolerances import run_floor_scale as corrida
from experiments.adr002.tolerances import schema_floor_scale_v0_1 as esquema

RAIZ = Path(__file__).resolve().parents[3]

SHA_FICTICIO = "0" * 40
PIDS: tuple[int, ...] = (9001, 9002, 9003, 9004, 9005)

#: ``D(s) = 180 * isqrt(s)``: crece con la escala y su razon D/s decrece,
#: igual que la evidencia versionada. Con esta ley el punto fijo cae en
#: 1 ms y ``B`` en 200 us, valores que ninguna prueba ajusta despues.
FACTOR_DISPERSION = 180
COSTE_CPU_NS = 300_000
COSTE_CANON_NS = 73_000
TAIL_BASE = 100


# --------------------------------------------------------------------------
# Datos sinteticos
# --------------------------------------------------------------------------


def dispersion_objetivo(escala_ns: int) -> int:
    """Dispersion sintetica de la escala, en nanosegundos."""
    return FACTOR_DISPERSION * math.isqrt(escala_ns)


def _vector(base: int, cola: int, n: int) -> list[int]:
    """Vector con P50 en ``base + 3`` y P95 en ``base + cola``.

    El cuerpo ocupa las posiciones bajas con valores en ``[base, base+6]`` y
    la cola las altas; ``cola`` debe superar 6 para que el P95 por rango mas
    cercano caiga en ella.
    """
    if cola <= 6:
        msg = "la cola debe superar el cuerpo"
        raise ValueError(msg)
    rango95 = max(1, -(-19 * n // 20))
    cima = n - rango95 + 1
    cuerpo = [base + (i % 7) for i in range(n - cima)]
    return [*cuerpo, *([base + cola] * cima)]


def _entrada_cruda(base: int, cola: int, n: int, warmup: int) -> dict[str, Any]:
    vector = _vector(base, cola, n)
    ordenadas = sorted(vector)
    return {
        "n": len(vector),
        "warmup_descartado": warmup,
        "muestras_ns": vector,
        "p50_ns": fp.percentil_ns(ordenadas, 1, 2),
        "p95_ns": fp.percentil_ns(ordenadas, 19, 20),
        "p99_ns": fp.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
    }


def calibraciones_sinteticas() -> dict[str, sondas.Calibracion]:
    """Calibracion ficticia coherente: el P50 de las muestras es el coste."""

    def _muestras(coste: int) -> tuple[int, ...]:
        return tuple(coste + (i - 10) for i in range(fp.MUESTRAS_CALIBRACION))

    return {
        fp.FAMILIA_CPU: sondas.Calibracion(
            familia=fp.FAMILIA_CPU,
            unidades_referencia=fp.UNIDADES_REFERENCIA[fp.FAMILIA_CPU],
            coste_referencia_ns=COSTE_CPU_NS,
            muestras=_muestras(COSTE_CPU_NS),
        ),
        fp.FAMILIA_CANON: sondas.Calibracion(
            familia=fp.FAMILIA_CANON,
            unidades_referencia=fp.UNIDADES_REFERENCIA[fp.FAMILIA_CANON],
            coste_referencia_ns=COSTE_CANON_NS,
            muestras=_muestras(COSTE_CANON_NS),
        ),
    }


def plan_sintetico() -> corrida.PlanCorrida:
    return corrida.plan_de_corrida(sondas.plan_de_unidades(calibraciones_sinteticas()))


def dispersion_insostenible(escala_ns: int) -> int:
    """Ley con ``D(s) = s/2``: ninguna escala sostiene ``5 D(s) <= s``."""
    return escala_ns // 2


def resultado_sintetico(
    plan: corrida.PlanCorrida,
    indice: int,
    ley: Callable[[int], int] = dispersion_objetivo,
) -> dict[str, Any]:
    """Resultado crudo de un proceso, sin medir nada."""
    escalas: dict[str, dict[str, Any]] = {familia: {} for familia in fp.FAMILIAS}
    for familia in fp.FAMILIAS:
        for escala in fp.ESCALERA_NS:
            objetivo = ley(escala)
            if familia == fp.FAMILIA_CPU:
                objetivo //= 2
            cola = TAIL_BASE + objetivo * indice // 4
            entrada = _entrada_cruda(escala, cola, fp.n_para_escala(escala), fp.WARMUP_ESCALA)
            entrada["unidades"] = plan.unidades[familia][escala]
            escalas[familia][str(escala)] = entrada

    unitarias = {
        fp.SONDA_VACIA: _entrada_cruda(
            130, 20 + 60 * indice // 4, fp.N_UNITARIA, fp.WARMUP_UNITARIA
        ),
        fp.SONDA_CANON_0: _entrada_cruda(
            6_900, TAIL_BASE + 13_000 * indice // 4, fp.N_UNITARIA, fp.WARMUP_UNITARIA
        ),
        fp.SONDA_CANON_1: _entrada_cruda(
            7_200, TAIL_BASE + 14_000 * indice // 4, fp.N_UNITARIA, fp.WARMUP_UNITARIA
        ),
    }

    return {
        "pid": PIDS[indice],
        "escalas": escalas,
        "unitarias": unitarias,
        "referencia": {
            "vueltas": fp.VUELTAS_REFERENCIA,
            "p50_inicio_ns": 300_000 + indice,
            "p50_mitad_ns": 300_050 + indice,
            "p50_final_ns": 300_020 + indice,
        },
        "unidades": corrida.unidades_a_json(plan.unidades),
        "cargas": [0.5, 0.6, 0.55],
        "incidencias": [],
        "filtrado_aplicado": False,
        "warmup_mezclado": False,
    }


def resultados_sinteticos(
    plan: corrida.PlanCorrida, ley: Callable[[int], int] = dispersion_objetivo
) -> list[Mapping[str, Any]]:
    return [resultado_sintetico(plan, indice, ley) for indice in range(len(PIDS))]


def entorno_de_prueba(
    *,
    limpio: bool = True,
    ancestro: bool = True,
    diff_vacio: bool = True,
    head: str = SHA_FICTICIO,
    sobrescribir: Mapping[str, bytes] | None = None,
    blob_en_commit_divergente: bool = False,
) -> fp.EntornoCustodia:
    """Custodia sobre el repositorio real, con las decisiones inyectadas.

    Lee los ficheros de verdad: asi los blobs preinscritos, heredados,
    congelados y de la evidencia anterior se comparan contra el arbol real y
    no contra un doble complaciente.
    """
    extra = dict(sobrescribir or {})

    def leer_bytes(ruta: str) -> bytes:
        if ruta in extra:
            return extra[ruta]
        return (RAIZ / ruta).read_bytes()

    def blob_en_commit(_sha: str, ruta: str) -> str | None:
        if blob_en_commit_divergente:
            return "f" * 40
        return fp.blob_git(leer_bytes(ruta))

    return fp.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=lambda _a, _b: ancestro,
        existe_commit=lambda _sha: True,
        head=lambda: head,
        arbol_limpio=lambda: limpio,
        diff_vacio=lambda _a, _b, _rutas: diff_vacio,
        blob_en_commit=blob_en_commit,
    )


def dependencias_de_prueba(
    *,
    entorno: fp.EntornoCustodia | None = None,
    resultados: Sequence[Mapping[str, Any]] | None = None,
    boot_inicial: str = "boot-de-prueba",
    boot_final: str = "boot-de-prueba",
) -> corrida.DependenciasCorrida:
    calibraciones = calibraciones_sinteticas()

    def _ejecutor(plan: corrida.PlanCorrida) -> Sequence[Mapping[str, Any]]:
        return resultados_sinteticos(plan) if resultados is None else resultados

    def _capturar(etapa: str) -> Mapping[str, Any]:
        return {
            "etapa": etapa,
            "boot_id": boot_inicial if etapa == "inicial" else boot_final,
            "carga": 0.5,
            "captura": {"etapa": etapa},
        }

    def _linea_base() -> Mapping[str, Any]:
        datos = json.loads((RAIZ / fp.RUTA_LINEA_BASE).read_text(encoding="utf-8"))
        assert isinstance(datos, dict)
        return datos

    return corrida.DependenciasCorrida(
        entorno_custodia=entorno_de_prueba() if entorno is None else entorno,
        calibrar=lambda: calibraciones,
        ejecutor=_ejecutor,
        capturar_entorno=_capturar,
        cargar_linea_base=_linea_base,
    )


def documento_producido(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    """Ejecuta el recorrido completo con dobles y devuelve el artefacto."""
    salida = tmp_path / "suelo.json"
    codigo = corrida.main(
        [
            "--execute",
            "--preinscription-commit",
            SHA_FICTICIO,
            "--output",
            str(salida),
        ],
        dependencias=dependencias_de_prueba(**kwargs),
    )
    assert codigo == corrida.CODIGO_OK
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


@pytest.fixture(scope="module")
def artefacto(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    return documento_producido(tmp_path_factory.mktemp("suelo"))


@pytest.fixture(scope="module")
def artefacto_no_evaluable(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Artefacto de una corrida donde ninguna escala sostiene la condicion."""
    plan = plan_sintetico()
    return documento_producido(
        tmp_path_factory.mktemp("suelo_no_evaluable"),
        resultados=resultados_sinteticos(plan, dispersion_insostenible),
    )


# --------------------------------------------------------------------------
# Percentiles y resolucion
# --------------------------------------------------------------------------


def test_percentil_no_interpola_nunca() -> None:
    muestras = [10, 20, 30, 40]
    assert fp.percentil_ns(sorted(muestras), 1, 2) in muestras
    assert fp.percentil_ns(sorted(muestras), 19, 20) in muestras


def test_percentil_usa_rango_mas_cercano_por_techo() -> None:
    ordenadas = list(range(1, 101))
    assert fp.percentil_ns(ordenadas, 1, 2) == 50
    assert fp.percentil_ns(ordenadas, 19, 20) == 95
    assert fp.percentil_ns(ordenadas, 99, 100) == 99


def test_percentil_rechaza_fracciones_invalidas() -> None:
    with pytest.raises(ValueError, match="fraccion invalida"):
        fp.percentil_ns([1, 2, 3], 3, 2)
    with pytest.raises(ValueError, match="fraccion invalida"):
        fp.percentil_ns([1, 2, 3], 0, 2)
    with pytest.raises(ValueError, match="no hay muestras"):
        fp.percentil_ns([], 1, 2)


def test_resolucion_percentil_usa_el_mismo_rango_que_percentil_ns() -> None:
    for n in (30, 99, 100, 200, 300):
        rango = max(1, -(-99 * n // 100))
        peores = n - rango + 1
        texto = fp.resolucion_percentil(n)
        if peores <= 1:
            assert "maximo observado" in texto
        else:
            assert f"{peores}.a peor" in texto


def test_resolucion_percentil_rechaza_n_no_positivo() -> None:
    with pytest.raises(ValueError, match="n debe ser positivo"):
        fp.resolucion_percentil(0)


def test_n_por_escala_sigue_el_protocolo() -> None:
    assert fp.n_para_escala(fp.UMBRAL_COSTE_BAJO_NS) == fp.N_COSTE_BAJO
    assert fp.n_para_escala(fp.UMBRAL_COSTE_BAJO_NS + 1) == fp.N_COSTE_ALTO
    for escala in fp.ESCALERA_NS:
        assert fp.n_para_escala(escala) % fp.RONDAS_ROUND_ROBIN == 0


def test_la_escalera_permite_b_exacta_y_esta_ordenada() -> None:
    assert list(fp.ESCALERA_NS) == sorted(fp.ESCALERA_NS)
    assert len(set(fp.ESCALERA_NS)) == len(fp.ESCALERA_NS)
    for escala in fp.ESCALERA_NS:
        assert escala % fp.FACTOR_U == 0


# --------------------------------------------------------------------------
# Calibracion y unidades
# --------------------------------------------------------------------------


def test_unidades_para_escala_redondea_al_entero_mas_cercano() -> None:
    # coste de 10 unidades = 100 ns  ->  1 unidad = 10 ns
    assert fp.unidades_para_escala(100, unidades_referencia=10, coste_referencia_ns=100) == 10
    assert fp.unidades_para_escala(104, unidades_referencia=10, coste_referencia_ns=100) == 10
    assert fp.unidades_para_escala(106, unidades_referencia=10, coste_referencia_ns=100) == 11
    # nunca menos de una unidad
    assert fp.unidades_para_escala(1, unidades_referencia=10, coste_referencia_ns=10_000) == 1


def test_unidades_para_escala_rechaza_calibracion_degenerada() -> None:
    with pytest.raises(ValueError, match="calibracion invalida"):
        fp.unidades_para_escala(100, unidades_referencia=0, coste_referencia_ns=100)
    with pytest.raises(ValueError, match="calibracion invalida"):
        fp.unidades_para_escala(100, unidades_referencia=10, coste_referencia_ns=0)


def test_calibracion_en_banda_en_sus_fronteras() -> None:
    assert fp.calibracion_en_banda(500, 1_000) is True
    assert fp.calibracion_en_banda(499, 1_000) is False
    assert fp.calibracion_en_banda(2_000, 1_000) is True
    assert fp.calibracion_en_banda(2_001, 1_000) is False
    assert fp.calibracion_en_banda(0, 1_000) is False


def test_plan_de_unidades_cubre_toda_la_escalera() -> None:
    plan = sondas.plan_de_unidades(calibraciones_sinteticas())
    assert set(plan) == set(fp.FAMILIAS)
    for familia in fp.FAMILIAS:
        assert set(plan[familia]) == set(fp.ESCALERA_NS)
        assert all(v >= 1 for v in plan[familia].values())


def test_plan_de_unidades_exige_todas_las_familias() -> None:
    incompleta = {fp.FAMILIA_CPU: calibraciones_sinteticas()[fp.FAMILIA_CPU]}
    with pytest.raises(sondas.SondaInvalidaError, match="faltan calibraciones"):
        sondas.plan_de_unidades(incompleta)


# --------------------------------------------------------------------------
# Punto fijo
# --------------------------------------------------------------------------


def medidas_con_ley(ley: Mapping[int, int]) -> list[fp.MedidaEscala]:
    """Medidas sinteticas con dispersion exacta ``ley[escala]`` por escala."""
    medidas: list[fp.MedidaEscala] = []
    for escala in fp.ESCALERA_NS:
        paso = ley[escala] // 4
        for indice, pid in enumerate(PIDS):
            valor = escala + paso * indice
            medidas.append(
                fp.MedidaEscala(
                    familia=fp.FAMILIA_CPU,
                    escala_ns=escala,
                    unidades=100,
                    pid=pid,
                    n=fp.n_para_escala(escala),
                    warmup_descartado=fp.WARMUP_ESCALA,
                    p50=escala,
                    p95=valor,
                    p99=valor,
                    minimo=escala,
                    maximo=valor,
                    media_truncada=escala,
                )
            )
            medidas.append(
                fp.MedidaEscala(
                    familia=fp.FAMILIA_CANON,
                    escala_ns=escala,
                    unidades=7,
                    pid=pid,
                    n=fp.n_para_escala(escala),
                    warmup_descartado=fp.WARMUP_ESCALA,
                    p50=escala,
                    p95=escala,
                    p99=escala,
                    minimo=escala,
                    maximo=escala,
                    media_truncada=escala,
                )
            )
    return medidas


def test_punto_fijo_elige_la_menor_escala_sostenida() -> None:
    ley = {escala: 4 * (dispersion_objetivo(escala) // 4) for escala in fp.ESCALERA_NS}
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert punto.evaluable
    assert punto.u == 1_000_000
    assert punto.b == 200_000
    assert punto.u == fp.FACTOR_U * (punto.b or 0)
    assert punto.m == fp.MARGEN_M
    assert punto.motivo_no_evaluable is None


def test_punto_fijo_exige_sostenerse_en_todas_las_escalas_mayores() -> None:
    # 100 us cumple la condicion, pero 200 us la rompe: el cruce es accidental
    # y no puede fijar el umbral.
    ley = {escala: 4 * (dispersion_objetivo(escala) // 4) for escala in fp.ESCALERA_NS}
    ley[100_000] = 4_000  # 5*4000 <= 100000: sostenible
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert punto.u == 1_000_000, "un cruce aislado no puede adelantar el umbral"


def test_punto_fijo_devuelve_no_evaluable_sin_inventar_valores() -> None:
    ley = {escala: 4 * (escala // 2) for escala in fp.ESCALERA_NS}
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert not punto.evaluable
    assert punto.u is None
    assert punto.b is None
    assert punto.motivo_no_evaluable is not None
    assert "ninguna escala" in punto.motivo_no_evaluable


def test_punto_fijo_recupera_el_metodo_anterior_si_d_es_constante() -> None:
    # Con D constante el punto fijo devuelve la menor escala >= 5*D, que es
    # exactamente lo que el paquete 05 calculaba como U = 5*B.
    constante = 4 * (40_000 // 4)
    ley = dict.fromkeys(fp.ESCALERA_NS, constante)
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert punto.u is not None
    assert punto.u >= fp.FACTOR_U * constante
    menores = [s for s in fp.ESCALERA_NS if s < punto.u]
    assert all(s < fp.FACTOR_U * constante for s in menores)


def test_sostenible_en_escala_es_exacto_en_su_frontera() -> None:
    assert fp.sostenible_en_escala(200, 1_000) is True
    assert fp.sostenible_en_escala(201, 1_000) is False


def test_razon_por_mil_no_usa_coma_flotante() -> None:
    assert fp.razon_por_mil(200, 1_000) == 200
    assert fp.razon_por_mil(1, 1_000) == 1
    assert fp.razon_por_mil(0, 1_000) == 0
    with pytest.raises(ValueError, match="escala debe ser positiva"):
        fp.razon_por_mil(1, 0)


def test_dispersion_de_escala_toma_el_peor_caso() -> None:
    ley = {escala: 4 * (dispersion_objetivo(escala) // 4) for escala in fp.ESCALERA_NS}
    medidas = medidas_con_ley(ley)
    for escala in fp.ESCALERA_NS:
        peor = fp.dispersion_de_escala(medidas, escala)
        cpu = fp.dispersion_de_familia(medidas, fp.FAMILIA_CPU, escala, "p95")
        canon = fp.dispersion_de_familia(medidas, fp.FAMILIA_CANON, escala, "p95")
        assert peor == max(cpu, canon)


def test_dispersion_rechaza_percentil_no_normativo() -> None:
    ley = dict.fromkeys(fp.ESCALERA_NS, 4)
    with pytest.raises(ValueError, match="percentil no normativo"):
        fp.dispersion_de_familia(medidas_con_ley(ley), fp.FAMILIA_CPU, fp.ESCALERA_NS[0], "p99")


def test_cobertura_exige_cinco_procesos_por_familia_y_escala() -> None:
    ley = {escala: 4 * (dispersion_objetivo(escala) // 4) for escala in fp.ESCALERA_NS}
    medidas = medidas_con_ley(ley)
    recortadas = [m for m in medidas if not (m.escala_ns == 100_000 and m.pid == PIDS[4])]
    with pytest.raises(fp.ProcesosInsuficientesError):
        fp.resolver_punto_fijo(recortadas)


def test_cobertura_rechaza_familias_y_escalas_ajenas() -> None:
    ley = {escala: 4 for escala in fp.ESCALERA_NS}
    medidas = medidas_con_ley(ley)
    intrusa = fp.MedidaEscala(
        familia="fts5",
        escala_ns=10_000,
        unidades=1,
        pid=PIDS[0],
        n=100,
        warmup_descartado=5,
        p50=1,
        p95=1,
        p99=1,
        minimo=1,
        maximo=1,
        media_truncada=1,
    )
    with pytest.raises(fp.SondaNoNeutralError):
        fp.resolver_punto_fijo([*medidas, intrusa])

    ajena = fp.MedidaEscala(
        familia=fp.FAMILIA_CPU,
        escala_ns=12_345,
        unidades=1,
        pid=PIDS[0],
        n=100,
        warmup_descartado=5,
        p50=1,
        p95=1,
        p99=1,
        minimo=1,
        maximo=1,
        media_truncada=1,
    )
    with pytest.raises(fp.EscaleraInvalidaError, match="escalas ajenas"):
        fp.resolver_punto_fijo([*medidas, ajena])


def test_banda_cubre_el_suelo_detecta_escalera_no_monotona() -> None:
    ley = {escala: 4 * (dispersion_objetivo(escala) // 4) for escala in fp.ESCALERA_NS}
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert fp.banda_cubre_el_suelo(punto) is True

    # Una dispersion enorme en una escala pequena deja el regimen absoluto sin
    # banda que lo cubra: el criterio seria inalcanzable alli.
    ley[200_000] = 4 * (900_000 // 4)
    roto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert roto.u == 1_000_000
    assert fp.banda_cubre_el_suelo(roto) is False


def test_banda_cubre_el_suelo_es_falsa_sin_punto_fijo() -> None:
    ley = {escala: 4 * (escala // 2) for escala in fp.ESCALERA_NS}
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert fp.banda_cubre_el_suelo(punto) is False


# --------------------------------------------------------------------------
# SM
# --------------------------------------------------------------------------


def unitarias_sinteticas(colas: Mapping[str, int] | None = None) -> list[fp.MedidaUnitaria]:
    alturas = dict(colas or {s: 20_000 for s in fp.SONDAS_UNITARIAS})
    medidas: list[fp.MedidaUnitaria] = []
    for sonda in fp.SONDAS_UNITARIAS:
        for indice, pid in enumerate(PIDS):
            p95 = 7_000 + alturas[sonda] * indice // 4
            medidas.append(
                fp.MedidaUnitaria(
                    sonda=sonda,
                    pid=pid,
                    n=fp.N_UNITARIA,
                    warmup_descartado=fp.WARMUP_UNITARIA,
                    p50=7_000,
                    p95=p95,
                    p99=p95,
                    minimo=7_000,
                    maximo=p95,
                    media_truncada=7_000,
                )
            )
    return medidas


def test_sm_es_el_peor_p95_de_las_sondas_unitarias() -> None:
    medidas = unitarias_sinteticas()
    assert fp.calcular_sm(medidas) == max(m.p95 for m in medidas)


def test_sm_exige_las_tres_sondas_y_cinco_procesos() -> None:
    medidas = unitarias_sinteticas()
    sin_una = [m for m in medidas if m.sonda != fp.SONDA_CANON_0]
    with pytest.raises(fp.EscaleraInvalidaError, match="faltan sondas unitarias"):
        fp.calcular_sm(sin_una)

    recortada = [m for m in medidas if not (m.sonda == fp.SONDA_VACIA and m.pid == PIDS[0])]
    with pytest.raises(fp.ProcesosInsuficientesError):
        fp.calcular_sm(recortada)


def test_sm_rechaza_sondas_ajenas_y_no_neutrales() -> None:
    medidas = unitarias_sinteticas()
    ajena = fp.MedidaUnitaria(
        sonda="otra_sonda",
        pid=PIDS[0],
        n=fp.N_UNITARIA,
        warmup_descartado=fp.WARMUP_UNITARIA,
        p50=1,
        p95=1,
        p99=1,
        minimo=1,
        maximo=1,
        media_truncada=1,
    )
    with pytest.raises(fp.EscaleraInvalidaError, match="sondas unitarias ajenas"):
        fp.calcular_sm([*medidas, ajena])

    no_neutral = fp.MedidaUnitaria(
        sonda="rank_completo",
        pid=PIDS[0],
        n=fp.N_UNITARIA,
        warmup_descartado=fp.WARMUP_UNITARIA,
        p50=1,
        p95=1,
        p99=1,
        minimo=1,
        maximo=1,
        media_truncada=1,
    )
    with pytest.raises(fp.SondaNoNeutralError):
        fp.calcular_sm([*medidas, no_neutral])


# --------------------------------------------------------------------------
# Regimen por percentil
# --------------------------------------------------------------------------


def test_los_tres_regimenes_posibles_y_solo_esos() -> None:
    u, b, sm = 1_000_000, 200_000, 21_000
    absoluto = fp.evaluar_magnitud([100_000] * 5, [150_000] * 5, sm=sm, b=b, u=u)
    assert [v.regimen for v in absoluto.por_percentil] == ["absoluto", "absoluto"]

    mixto = fp.evaluar_magnitud([900_000] * 5, [1_100_000] * 5, sm=sm, b=b, u=u)
    assert [v.regimen for v in mixto.por_percentil] == ["absoluto", "relativo"]

    relativo = fp.evaluar_magnitud([2_000_000] * 5, [2_100_000] * 5, sm=sm, b=b, u=u)
    assert [v.regimen for v in relativo.por_percentil] == ["relativo", "relativo"]


def test_la_guarda_de_instrumento_va_antes_del_regimen() -> None:
    veredicto = fp.evaluar_magnitud([1_000] * 5, [2_000] * 5, sm=21_000, b=200_000, u=1_000_000)
    assert veredicto.dominada_por_instrumento
    assert veredicto.resultado == fp.NO_EVALUABLE
    assert veredicto.por_percentil == ()
    assert fp.registro_por_percentil(veredicto) == fp.NO_EVALUABLE


def test_el_invariante_de_percentiles_se_hace_cumplir() -> None:
    with pytest.raises(fp.InvarianteVioladoError, match="invariante violado"):
        fp.evaluar_magnitud(
            [500_000, 500_000, 500_000, 500_000, 500_000],
            [400_000, 400_000, 400_000, 400_000, 400_000],
            sm=1,
            b=200_000,
            u=1_000_000,
        )


def test_evaluar_magnitud_exige_cinco_sesiones_coherentes() -> None:
    with pytest.raises(fp.ProcesosInsuficientesError):
        fp.evaluar_magnitud([1] * 4, [2] * 4, sm=0, b=1, u=1)
    with pytest.raises(ValueError, match="incoherente"):
        fp.evaluar_magnitud([1] * 5, [2] * 4, sm=0, b=1, u=1)
    with pytest.raises(ValueError, match="faltan percentiles"):
        fp.evaluar_magnitud([], [], sm=0, b=1, u=1)


def test_criterios_relativo_y_absoluto_en_sus_fronteras() -> None:
    assert fp.pasa_relativo(1_000, 1_200) is True
    assert fp.pasa_relativo(1_000, 1_201) is False
    assert fp.pasa_relativo(0, 0) is False
    assert fp.pasa_absoluto(1_000, 1_200, 200) is True
    assert fp.pasa_absoluto(1_000, 1_201, 200) is False


def test_la_continuidad_en_el_umbral_es_exacta() -> None:
    ley = {escala: 4 * (dispersion_objetivo(escala) // 4) for escala in fp.ESCALERA_NS}
    punto = fp.resolver_punto_fijo(medidas_con_ley(ley))
    assert punto.u is not None
    assert punto.b is not None
    # En M = U el criterio absoluto (m*B) y el relativo (20 % de M) coinciden.
    assert fp.MARGEN_M * punto.b == punto.u * fp.OBJETIVO_RELATIVO_NUM // fp.OBJETIVO_RELATIVO_DEN


# --------------------------------------------------------------------------
# Controles, progresion y deriva
# --------------------------------------------------------------------------


def test_los_controles_fallan_cerrado() -> None:
    completo = dict.fromkeys(fp.CONTROLES_BLOQUEANTES, True)
    assert fp.evaluar_controles(completo).valido

    for control in fp.CONTROLES_BLOQUEANTES:
        ausente = {k: v for k, v in completo.items() if k != control}
        assert fp.evaluar_controles(ausente).fallos == (control,)

    for valor in (1, "si", None, 0):
        alterado = {**completo, "pids_distintos": valor}
        assert "pids_distintos" in fp.evaluar_controles(alterado).fallos  # type: ignore[arg-type]


def test_escala_progresa_en_aritmetica_entera() -> None:
    # Del doble exacto: progresa.
    assert fp.escala_progresa(1_000, 10_000, 2_000, 20_000) is True
    # Tiempo plano frente a escala doble: es EXACTAMENTE el caso que la
    # comprobacion existe para denunciar, y con tolerancia 1/2 pasaria justo
    # en la frontera. Con 1/3 falla.
    assert fp.escala_progresa(1_000, 10_000, 1_000, 20_000) is False
    # Fronteras exactas de la tolerancia 1/3 sobre un escalon de factor 2.
    assert fp.escala_progresa(1_000, 10_000, 2_666, 20_000) is True
    assert fp.escala_progresa(1_000, 10_000, 2_667, 20_000) is False
    assert fp.escala_progresa(1_000, 10_000, 1_334, 20_000) is True
    assert fp.escala_progresa(1_000, 10_000, 1_333, 20_000) is False
    # Escalon de factor 2,5: tampoco pasa el tiempo plano.
    assert fp.escala_progresa(1_000, 20_000, 1_000, 50_000) is False
    assert fp.escala_progresa(1_000, 20_000, 2_500, 50_000) is True
    assert fp.escala_progresa(0, 10_000, 1_000, 20_000) is False


def test_progresion_solo_exigible_sin_cuantizacion_relevante() -> None:
    assert fp.progresion_exigible(fp.UNIDADES_MINIMAS_PROGRESION, 100) is True
    assert fp.progresion_exigible(1, 100) is False
    assert fp.progresion_exigible(100, fp.UNIDADES_MINIMAS_PROGRESION - 1) is False


def test_referencia_estable_solo_denuncia_deriva_monotona_y_excesiva() -> None:
    assert fp.referencia_estable(100, 110, 105) is True
    assert fp.referencia_estable(100, 110, 120) is True  # +20 %: dentro de tolerancia
    assert fp.referencia_estable(100, 120, 140) is False  # +40 % monotono
    assert fp.referencia_estable(0, 1, 2) is False


# --------------------------------------------------------------------------
# Custodia
# --------------------------------------------------------------------------


def test_blob_git_coincide_con_git_hash_object() -> None:
    ruta = "experiments/adr002/tolerances/floor_scale_protocol.py"
    esperado = subprocess.run(
        ["git", "hash-object", ruta],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert fp.blob_git((RAIZ / ruta).read_bytes()) == esperado


def blobs_reales() -> dict[str, str]:
    return {ruta: fp.blob_git((RAIZ / ruta).read_bytes()) for ruta in fp.ARCHIVOS_PREINSCRITOS}


def heredados_reales() -> dict[str, str]:
    return {ruta: fp.blob_git((RAIZ / ruta).read_bytes()) for ruta in fp.ARCHIVOS_HEREDADOS}


def test_custodia_completa_no_encuentra_fallos() -> None:
    assert (
        fp.verificar_custodia(
            entorno_de_prueba(),
            sha_a=SHA_FICTICIO,
            blobs_preinscritos=blobs_reales(),
            blobs_heredados=heredados_reales(),
        )
        == ()
    )


def test_custodia_denuncia_commit_inexistente() -> None:
    entorno = fp.EntornoCustodia(
        leer_bytes=lambda ruta: (RAIZ / ruta).read_bytes(),
        es_ancestro=lambda _a, _b: True,
        existe_commit=lambda _sha: False,
        head=lambda: SHA_FICTICIO,
        arbol_limpio=lambda: True,
        diff_vacio=lambda _a, _b, _rutas: True,
        blob_en_commit=lambda _s, ruta: fp.blob_git((RAIZ / ruta).read_bytes()),
    )
    assert fp.verificar_custodia(
        entorno,
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    ) == ("commit de preinscripcion inexistente",)


def test_custodia_denuncia_no_ancestro_y_diff_no_vacio() -> None:
    fallos = fp.verificar_custodia(
        entorno_de_prueba(ancestro=False, diff_vacio=False),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    )
    assert any("no es ancestro" in f for f in fallos)
    assert any("diff no vacio" in f for f in fallos)


def test_custodia_denuncia_blob_preinscrito_ausente_o_alterado() -> None:
    blobs = blobs_reales()
    ruta = fp.ARCHIVOS_PREINSCRITOS[1]
    sin_uno = {k: v for k, v in blobs.items() if k != ruta}
    fallos = fp.verificar_custodia(
        entorno_de_prueba(),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=sin_uno,
        blobs_heredados=heredados_reales(),
    )
    assert any("blobs preinscritos ausentes" in f for f in fallos)

    alterado = {**blobs, ruta: "0" * 40}
    fallos = fp.verificar_custodia(
        entorno_de_prueba(),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=alterado,
        blobs_heredados=heredados_reales(),
    )
    assert any("blob preinscrito alterado" in f for f in fallos)


def test_custodia_usa_una_fuente_de_verdad_independiente_del_arbol() -> None:
    fallos = fp.verificar_custodia(
        entorno_de_prueba(blob_en_commit_divergente=True),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    )
    assert any("difiere del commit de preinscripcion" in f for f in fallos)


def test_custodia_denuncia_modulo_heredado_alterado() -> None:
    fallos = fp.verificar_custodia(
        entorno_de_prueba(),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados={ruta: "0" * 40 for ruta in fp.ARCHIVOS_HEREDADOS},
    )
    assert any("blob heredado distinto del preinscrito" in f for f in fallos)


def test_custodia_denuncia_evidencia_anterior_alterada_o_ausente() -> None:
    alterada = entorno_de_prueba(sobrescribir={fp.EVIDENCIA_ANTERIOR: b"{}"})
    fallos = fp.fallos_evidencia_anterior(alterada)
    assert any("fue alterada" in f for f in fallos)

    def _leer(ruta: str) -> bytes:
        if ruta == fp.INFORME_ANTERIOR:
            raise FileNotFoundError(ruta)
        return (RAIZ / ruta).read_bytes()

    ausente = fp.EntornoCustodia(
        leer_bytes=_leer,
        es_ancestro=lambda _a, _b: True,
        existe_commit=lambda _sha: True,
        head=lambda: SHA_FICTICIO,
        arbol_limpio=lambda: True,
        diff_vacio=lambda _a, _b, _rutas: True,
        blob_en_commit=lambda _s, ruta: fp.blob_git((RAIZ / ruta).read_bytes()),
    )
    fallos = fp.fallos_evidencia_anterior(ausente)
    assert any("desaparecido" in f for f in fallos)


def test_precondiciones_de_ejecucion_fallan_cerrado() -> None:
    limpio = entorno_de_prueba()
    assert (
        fp.verificar_precondiciones_ejecucion(limpio, sha_a=SHA_FICTICIO, salida_existe=False) == ()
    )
    sucio = entorno_de_prueba(limpio=False)
    assert "arbol de trabajo sucio" in fp.verificar_precondiciones_ejecucion(
        sucio, sha_a=SHA_FICTICIO, salida_existe=False
    )
    desviado = entorno_de_prueba(head="a" * 40)
    fallos = fp.verificar_precondiciones_ejecucion(
        desviado, sha_a=SHA_FICTICIO, salida_existe=False
    )
    assert any("distinto del commit de preinscripcion" in f for f in fallos)
    assert "la ruta de salida ya existe" in fp.verificar_precondiciones_ejecucion(
        limpio, sha_a=SHA_FICTICIO, salida_existe=True
    )


# --------------------------------------------------------------------------
# Sondas: neutralidad y forma
# --------------------------------------------------------------------------


def test_las_familias_y_sondas_son_neutrales_por_nombre() -> None:
    assert fp.comprobar_neutralidad([*fp.FAMILIAS, *fp.SONDAS_UNITARIAS]) == ()


def test_la_neutralidad_detecta_nombres_prohibidos() -> None:
    for nombre in ("busqueda_fts5", "orden_por_rank", "puntuacion_bm25", "ADR002-C"):
        assert fp.comprobar_neutralidad([nombre]) != ()


def test_el_sql_de_la_sonda_canonica_es_neutral_y_por_clave_primaria() -> None:
    assert sondas.fallos_sql_de_sonda(sondas.SQL_SONDA_CANON) == ()
    sondas.comprobar_sql_de_sonda()


def test_el_sql_de_sonda_rechaza_consultas_no_neutrales() -> None:
    assert sondas.fallos_sql_de_sonda("SELECT rowid FROM knowledge_fts WHERE knowledge_fts MATCH ?")
    assert sondas.fallos_sql_de_sonda("SELECT id FROM memory_revisions ORDER BY id")
    assert sondas.fallos_sql_de_sonda("SELECT id FROM otra_tabla WHERE id = ?")


def test_ninguna_cadena_sql_del_modulo_de_sondas_toca_fts_ni_rank() -> None:
    """Comprobacion sobre el AST, no sobre el texto: los docstrings citan FTS5.

    Lo que no puede existir es una EXPRESION que se use como SQL y nombre
    FTS5, ``MATCH``, ``rank()`` o BM25. Se inspeccionan tanto las cadenas
    literales como las ``f``-cadenas, que el arbol descompone en trozos y que
    un recorrido ingenuo de ``ast.Constant`` dejaria pasar.
    """
    ruta = RAIZ / "experiments/adr002/tolerances/floor_scale_probes.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    # Una ``f``-cadena se descompone en trozos: sus ``Constant`` internos se
    # examinan como parte del conjunto, nunca sueltos.
    troceados: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.JoinedStr):
            troceados.update(id(hijo) for hijo in ast.walk(nodo) if hijo is not nodo)

    consultas: list[str] = []
    for nodo in ast.walk(arbol):
        if id(nodo) in troceados:
            continue
        if not isinstance(nodo, ast.Constant | ast.JoinedStr):
            continue
        if isinstance(nodo, ast.Constant) and not isinstance(nodo.value, str):
            continue
        texto = ast.unparse(nodo)
        if "select" in texto.lower():
            consultas.append(texto)
    assert consultas, "el modulo debe declarar al menos una consulta"
    for consulta in consultas:
        minusculas = consulta.lower()
        assert sondas.TABLA_CANONICA in minusculas or "tabla_canonica" in minusculas, consulta
        for prohibido in ("fts", "match", "rank", "bm25", "embedding", "vector"):
            assert prohibido not in minusculas, consulta
    # El valor efectivo del SQL normativo, ya interpolado, tambien se revisa.
    assert sondas.fallos_sql_de_sonda(sondas.SQL_SONDA_CANON) == ()


def test_girar_es_determinista_y_proporcional() -> None:
    assert sondas.girar(0) == 0
    assert sondas.girar(8) == sum(i & 7 for i in range(8))
    assert sondas.girar(16) == 2 * sondas.girar(8)
    with pytest.raises(ValueError, match="vueltas no puede ser negativo"):
        sondas.girar(-1)


def test_las_operaciones_exigen_unidades_positivas() -> None:
    with pytest.raises(ValueError, match="unidades debe ser positivo"):
        sondas.operacion_cpu(0)


def test_medir_ns_descarta_el_warmup_y_valida_argumentos() -> None:
    llamadas: list[int] = []

    def operacion() -> None:
        llamadas.append(1)

    muestras = sondas.medir_ns(operacion, n=4, warmup=3)
    assert len(muestras) == 4
    assert len(llamadas) == 7
    assert all(m >= 0 for m in muestras)
    with pytest.raises(ValueError, match="n debe ser positivo"):
        sondas.medir_ns(operacion, n=0, warmup=0)
    with pytest.raises(ValueError, match="warm-up no puede ser negativo"):
        sondas.medir_ns(operacion, n=1, warmup=-1)


def test_calibrar_familia_rechaza_familias_ajenas() -> None:
    with pytest.raises(sondas.SondaInvalidaError, match="familia ajena"):
        sondas.calibrar_familia(lambda: None, familia="fts5", unidades=1)


def test_el_orden_es_round_robin_y_no_por_bloques() -> None:
    pares = fp.pares_de_escalera()
    orden = list(sondas.orden_round_robin(pares, fp.RONDAS_ROUND_ROBIN))
    assert len(orden) == len(pares) * fp.RONDAS_ROUND_ROBIN
    assert orden[: len(pares)] == list(pares)
    # Las dos familias se intercalan dentro de cada escala.
    assert [familia for familia, _ in orden[: len(fp.FAMILIAS)]] == list(fp.FAMILIAS)
    with pytest.raises(ValueError, match="rondas debe ser positivo"):
        list(sondas.orden_round_robin(pares, 0))


def test_los_pares_de_la_escalera_cubren_todo_el_producto() -> None:
    pares = fp.pares_de_escalera()
    assert len(pares) == len(fp.FAMILIAS) * len(fp.ESCALERA_NS)
    assert set(pares) == {(f, s) for f in fp.FAMILIAS for s in fp.ESCALERA_NS}


# --------------------------------------------------------------------------
# El orquestador no mide sin autorizacion
# --------------------------------------------------------------------------


def test_sin_execute_no_mide_nada(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main([]) == corrida.CODIGO_SIN_EXECUTE
    assert "no mide sin --execute" in capsys.readouterr().out


def test_el_plan_se_imprime_sin_medir(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main(["--plan"]) == corrida.CODIGO_OK
    salida = capsys.readouterr().out
    assert str(fp.PROCESOS_MINIMOS) in salida
    assert str(len(fp.CONTROLES_BLOQUEANTES)) in salida


def test_execute_sin_commit_ni_salida_se_bloquea(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main(["--execute"]) == corrida.CODIGO_BLOQUEADO
    assert "--preinscription-commit" in capsys.readouterr().out


def test_worker_sin_unidades_se_bloquea(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main(["--execute", "--worker"]) == corrida.CODIGO_BLOQUEADO
    assert "la cantidad de trabajo la fija el padre" in capsys.readouterr().out


def test_unidades_desde_json_falla_cerrado() -> None:
    plan = corrida.unidades_a_json(plan_sintetico().unidades)
    assert corrida.unidades_desde_json(plan)[fp.FAMILIA_CPU][10_000] > 0

    with pytest.raises(corrida.EjecucionBloqueadaError, match="debe ser un objeto"):
        corrida.unidades_desde_json([])
    with pytest.raises(corrida.EjecucionBloqueadaError, match="no trae la familia"):
        corrida.unidades_desde_json({fp.FAMILIA_CPU: plan[fp.FAMILIA_CPU]})
    roto = deepcopy(plan)
    roto[fp.FAMILIA_CANON]["10000"] = 0
    with pytest.raises(corrida.EjecucionBloqueadaError, match="unidades invalidas"):
        corrida.unidades_desde_json(roto)


def test_plan_de_corrida_exige_unidades_completas() -> None:
    unidades = {f: dict(v) for f, v in plan_sintetico().unidades.items()}
    del unidades[fp.FAMILIA_CANON][fp.ESCALERA_NS[0]]
    with pytest.raises(corrida.EjecucionBloqueadaError, match="no cubre las escalas"):
        corrida.plan_de_corrida(unidades)
    with pytest.raises(corrida.EjecucionBloqueadaError, match="no cubre las familias"):
        corrida.plan_de_corrida({fp.FAMILIA_CPU: unidades[fp.FAMILIA_CPU]})


# --------------------------------------------------------------------------
# Recorrido completo de extremo a extremo (sin medir)
# --------------------------------------------------------------------------


def test_recorrido_completo_produce_un_artefacto_valido(artefacto: dict[str, Any]) -> None:
    assert esquema.fallos_suelo_multiescala(artefacto) == []
    assert artefacto["version_esquema"] == fp.VERSION_ESQUEMA
    assert artefacto["estado"] == fp.ESTADO_EVIDENCIA
    assert artefacto["no_autoriza"]["aprobacion_tol_209"] is False
    assert artefacto["no_autoriza"]["sustitucion_evidencia_anterior"] is False


def test_el_artefacto_publica_el_punto_fijo_esperado(artefacto: dict[str, Any]) -> None:
    derivacion = artefacto["derivacion"]
    assert derivacion["resultado"] == "RESUELTO"
    assert derivacion["u_ns"] == 1_000_000
    assert derivacion["b_ns"] == 200_000
    assert derivacion["m"] == fp.MARGEN_M
    assert derivacion["u_ns"] in fp.ESCALERA_NS
    assert derivacion["motivo_no_evaluable"] is None


def test_el_punto_fijo_se_reproduce_desde_cero(artefacto: dict[str, Any]) -> None:
    """Recomputacion independiente desde los vectores crudos publicados."""
    dispersiones: dict[int, int] = {}
    for escala in fp.ESCALERA_NS:
        peor = 0
        for familia in fp.FAMILIAS:
            for clave in ("p50_ns", "p95_ns"):
                valores = [
                    int(e[clave])
                    for e in artefacto["escalas"]
                    if e["familia"] == familia and e["escala_ns"] == escala
                ]
                peor = max(peor, max(valores) - min(valores))
        dispersiones[escala] = peor

    sostenidas = {s: 5 * d <= s for s, d in dispersiones.items()}
    esperada = next(
        s
        for indice, s in enumerate(fp.ESCALERA_NS)
        if all(sostenidas[mayor] for mayor in fp.ESCALERA_NS[indice:])
    )
    assert artefacto["derivacion"]["u_ns"] == esperada
    assert artefacto["derivacion"]["b_ns"] == esperada // 5
    for fila in artefacto["derivacion"]["dispersiones"]:
        assert fila["dispersion_ns"] == dispersiones[fila["escala_ns"]]


def test_todos_los_controles_bloqueantes_pasan(artefacto: dict[str, Any]) -> None:
    controles = artefacto["controles_internos"]
    assert set(controles) == set(fp.CONTROLES_BLOQUEANTES)
    assert all(controles[c] is True for c in fp.CONTROLES_BLOQUEANTES)


def test_el_artefacto_cita_la_evidencia_anterior_intacta(artefacto: dict[str, Any]) -> None:
    citados = artefacto["preinscripcion"]["blobs_evidencia_anterior"]
    assert citados == dict(fp.BLOBS_EVIDENCIA_ANTERIOR)
    for ruta, blob in fp.BLOBS_EVIDENCIA_ANTERIOR.items():
        assert fp.blob_git((RAIZ / ruta).read_bytes()) == blob
    assert artefacto["custodia"]["evidencia_anterior_intacta"] is True
    assert artefacto["metodo"]["no_sustituye_evidencia"] is True


def test_el_artefacto_no_usa_ninguna_magnitud_de_candidato_como_patron(
    artefacto: dict[str, Any],
) -> None:
    """FTS5 y ``rank()`` solo pueden aparecer como clasificacion diagnostica."""
    familias = {e["familia"] for e in artefacto["escalas"]}
    assert familias == set(fp.FAMILIAS)
    sondas_unitarias = {e["sonda"] for e in artefacto["sondas_unitarias"]}
    assert sondas_unitarias == set(fp.SONDAS_UNITARIAS)
    assert fp.comprobar_neutralidad(sorted(familias | sondas_unitarias)) == ()
    magnitudes = {e["magnitud"] for e in artefacto["regimenes_por_percentil"]}
    assert any("fts5" in m for m in magnitudes), "la clasificacion diagnostica debe publicarse"


def test_la_clasificacion_diagnostica_pone_submilisegundo_en_absoluto(
    artefacto: dict[str, Any],
) -> None:
    """Con el umbral sucesor, las magnitudes de 0,14-1,0 ms caen en absoluto.

    Es la comprobacion de coherencia con la fila TOL-107 del Registro, que
    dice literalmente que a esa escala la comparacion debe hacerse en valor
    absoluto. No se fuerza: se deriva del punto fijo resuelto.
    """
    u = artefacto["derivacion"]["u_ns"]
    for entrada in artefacto["regimenes_por_percentil"]:
        if entrada.get("resultado") == fp.NO_EVALUABLE:
            continue
        if entrada["min_p95_ns"] < u:
            assert entrada["p95"] == fp.REGIMEN_ABSOLUTO
        else:
            assert entrada["p95"] == fp.REGIMEN_RELATIVO


def test_las_dos_listas_de_veredicto_son_la_misma(artefacto: dict[str, Any]) -> None:
    assert (
        artefacto["clasificacion_diagnostica_linea_base"]["magnitudes"]
        == artefacto["regimenes_por_percentil"]
    )


def test_la_calibracion_publicada_deriva_las_unidades_medidas(artefacto: dict[str, Any]) -> None:
    for familia in fp.FAMILIAS:
        entrada = artefacto["calibracion"][familia]
        for escala in fp.ESCALERA_NS:
            esperado = fp.unidades_para_escala(
                escala,
                unidades_referencia=entrada["unidades_referencia"],
                coste_referencia_ns=entrada["coste_referencia_ns"],
            )
            assert entrada["unidades_por_escala"][str(escala)] == esperado
            medidas = {
                e["unidades"]
                for e in artefacto["escalas"]
                if e["familia"] == familia and e["escala_ns"] == escala
            }
            assert medidas == {esperado}


def test_no_se_publica_ningun_valor_si_el_arbol_esta_sucio(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=salida,
        dependencias=dependencias_de_prueba(entorno=entorno_de_prueba(limpio=False)),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("sucio" in f for f in fallos)
    assert not salida.exists()


def test_no_se_sobrescribe_una_salida_existente(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    salida.write_text("evidencia ajena", encoding="utf-8")
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO, salida=salida, dependencias=dependencias_de_prueba()
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("ya existe" in f for f in fallos)
    assert salida.read_text(encoding="utf-8") == "evidencia ajena"


def test_la_evidencia_anterior_alterada_bloquea_la_corrida(tmp_path: Path) -> None:
    entorno = entorno_de_prueba(sobrescribir={fp.EVIDENCIA_ANTERIOR: b"[]"})
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(entorno=entorno),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("evidencia anterior fue alterada" in f for f in fallos)


def test_un_boot_id_distinto_bloquea_la_corrida(tmp_path: Path) -> None:
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(boot_final="otro-boot"),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("boot_id_estable" in f for f in fallos)


def test_pids_repetidos_bloquean_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = resultados_sinteticos(plan)
    clonado = deepcopy(dict(resultados[1]))
    clonado["pid"] = resultados[0]["pid"]
    salida = tmp_path / "suelo.json"
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=salida,
        dependencias=dependencias_de_prueba(resultados=[resultados[0], clonado, *resultados[2:]]),
    )
    # Con un PID repetido la cobertura por (familia, escala) baja de cinco
    # procesos distintos: el punto fijo no llega a resolverse.
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("procesos distintos" in f for f in fallos)
    assert not salida.exists()


def test_el_control_de_pids_denuncia_la_repeticion() -> None:
    plan = plan_sintetico()
    resultados = resultados_sinteticos(plan)
    clonado = deepcopy(dict(resultados[1]))
    clonado["pid"] = resultados[0]["pid"]
    captura = {"boot_id": "b", "carga": 0.1}
    controles = corrida.evaluar_controles_desde_resultados(
        [resultados[0], clonado, *resultados[2:]],
        plan=plan,
        captura_inicial=captura,
        captura_final=captura,
        custodia_ok=True,
        evidencia_anterior_intacta=True,
        punto=fp.PuntoFijo((), (), None, None, fp.MARGEN_M, "sin resolver"),
    )
    assert controles["pids_distintos"] is False


def test_unidades_distintas_entre_procesos_bloquean_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    escala = str(fp.ESCALERA_NS[-1])
    resultados[2]["escalas"][fp.FAMILIA_CPU][escala]["unidades"] += 1
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("unidades_identicas" in f for f in fallos)


def test_una_escala_fuera_de_banda_bloquea_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    escala = fp.ESCALERA_NS[3]
    entrada = resultados[0]["escalas"][fp.FAMILIA_CPU][str(escala)]
    desplazado = 3 * escala
    entrada["muestras_ns"] = [v + desplazado for v in entrada["muestras_ns"]]
    ordenadas = sorted(entrada["muestras_ns"])
    entrada["p50_ns"] = fp.percentil_ns(ordenadas, 1, 2)
    entrada["p95_ns"] = fp.percentil_ns(ordenadas, 19, 20)
    entrada["p99_ns"] = fp.percentil_ns(ordenadas, 99, 100)
    entrada["min_ns"] = ordenadas[0]
    entrada["max_ns"] = ordenadas[-1]
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("calibracion_en_banda" in f for f in fallos)


def test_una_incidencia_registrada_bloquea_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    resultados[3]["incidencias"] = ["canon_1_fila no devolvio exactamente una fila"]
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("sin_filtrado" in f for f in fallos)


def test_un_resultado_sin_claves_bloquea_antes_de_derivar(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    del resultados[0]["referencia"]
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("sin la clave referencia" in f for f in fallos)


def test_deriva_intraproceso_bloquea_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    resultados[1]["referencia"] = {
        "vueltas": fp.VUELTAS_REFERENCIA,
        "p50_inicio_ns": 300_000,
        "p50_mitad_ns": 360_000,
        "p50_final_ns": 450_000,
    }
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "suelo.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("estabilidad_intraproceso" in f for f in fallos)


def test_un_ejecutor_que_falla_no_deja_artefacto(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"

    def _explota(_plan: corrida.PlanCorrida) -> Sequence[Mapping[str, Any]]:
        msg = "el hijo murio"
        raise corrida.EjecucionBloqueadaError(msg)

    base = dependencias_de_prueba()
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=salida,
        dependencias=corrida.DependenciasCorrida(
            entorno_custodia=base.entorno_custodia,
            calibrar=base.calibrar,
            ejecutor=_explota,
            capturar_entorno=base.capturar_entorno,
            cargar_linea_base=base.cargar_linea_base,
        ),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("ejecutor de procesos fallo" in f for f in fallos)
    assert not salida.exists()


def test_una_calibracion_que_falla_no_deja_artefacto(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"

    def _explota() -> Mapping[str, sondas.Calibracion]:
        msg = "calibracion degenerada"
        raise sondas.SondaInvalidaError(msg)

    base = dependencias_de_prueba()
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=salida,
        dependencias=corrida.DependenciasCorrida(
            entorno_custodia=base.entorno_custodia,
            calibrar=_explota,
            ejecutor=base.ejecutor,
            capturar_entorno=base.capturar_entorno,
            cargar_linea_base=base.cargar_linea_base,
        ),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("calibracion fallo" in f for f in fallos)
    assert not salida.exists()


def test_la_escritura_no_destruye_un_fichero_ajeno(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    salida.write_text("evidencia ajena", encoding="utf-8")
    with pytest.raises(FileExistsError):
        corrida.escribir_json_atomico(salida, {"a": 1})
    assert salida.read_text(encoding="utf-8") == "evidencia ajena"
    assert list(tmp_path.iterdir()) == [salida]


def test_la_escritura_rechaza_valores_no_json(tmp_path: Path) -> None:
    salida = tmp_path / "suelo.json"
    with pytest.raises(ValueError, match="Out of range float"):
        corrida.escribir_json_atomico(salida, {"a": float("nan")})
    assert not salida.exists()
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------
# Validador: mutaciones
# --------------------------------------------------------------------------


def _mutado(artefacto: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(artefacto))


def test_el_validador_es_total_y_nunca_lanza() -> None:
    basuras: tuple[Any, ...] = (None, [], "texto", 3, {"documento": object()})
    for basura in basuras:
        assert esquema.fallos_suelo_multiescala(basura)


def test_el_validador_exige_todas_las_secciones(artefacto: dict[str, Any]) -> None:
    for seccion in esquema.SECCIONES_OBLIGATORIAS:
        doc = _mutado(artefacto)
        del doc[seccion]
        fallos = esquema.fallos_suelo_multiescala(doc)
        assert any(seccion in f for f in fallos), seccion


def test_el_validador_rechaza_identidad_alterada(artefacto: dict[str, Any]) -> None:
    for campo, valor in (
        ("version_esquema", "otra"),
        ("protocolo", "otro.md"),
        ("paquete", "otro"),
        ("estado", "APROBADO"),
    ):
        doc = _mutado(artefacto)
        doc[campo] = valor
        assert esquema.fallos_suelo_multiescala(doc)


def test_el_validador_rechaza_una_u_interpolada(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["u_ns"] = 700_000
    doc["derivacion"]["b_ns"] = 140_000
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no coincide con el punto fijo recomputado" in f for f in fallos)


def test_el_validador_rechaza_una_b_que_no_sea_u_entre_cinco(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["b_ns"] = 300_000
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("U / 5" in f for f in fallos)


def test_el_validador_rechaza_un_margen_distinto_de_uno(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["m"] = 2
    assert any("m debe ser 1" in f for f in esquema.fallos_suelo_multiescala(doc))


def test_el_validador_rechaza_un_objetivo_relativo_distinto(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["objetivo_relativo"] = "1/4"
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("objetivo_relativo" in f for f in fallos)


def test_el_validador_rechaza_dispersiones_maquilladas(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["dispersiones"][0]["dispersion_ns"] = 1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("dispersiones no coincide" in f for f in fallos)


def test_el_validador_rechaza_un_percentil_incoherente(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["p95_ns"] = doc["escalas"][0]["p95_ns"] + 1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("p95_ns publicado" in f for f in fallos)


def test_el_validador_rechaza_un_vector_recortado(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["muestras_ns"] = doc["escalas"][0]["muestras_ns"][:10]
    assert esquema.fallos_suelo_multiescala(doc)


def test_el_validador_rechaza_muestras_negativas(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["muestras_ns"][0] = -1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("negativas" in f for f in fallos)


def test_el_validador_rechaza_un_vector_redondeado(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    entrada = doc["escalas"][0]
    escala = entrada["escala_ns"]
    entrada["muestras_ns"] = [escala + 100 * (i % 5) for i in range(entrada["n"])]
    ordenadas = sorted(entrada["muestras_ns"])
    entrada["p50_ns"] = fp.percentil_ns(ordenadas, 1, 2)
    entrada["p95_ns"] = fp.percentil_ns(ordenadas, 19, 20)
    entrada["p99_ns"] = fp.percentil_ns(ordenadas, 99, 100)
    entrada["min_ns"] = ordenadas[0]
    entrada["max_ns"] = ordenadas[-1]
    entrada["media_truncada_ns"] = sum(ordenadas) // len(ordenadas)
    entrada["valores_distintos"] = len(set(ordenadas))
    entrada["repeticion_maxima"] = max(ordenadas.count(v) for v in set(ordenadas))
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("redondeado" in f for f in fallos)


def test_el_validador_rechaza_una_familia_o_escala_ajena(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["familia"] = "fts5"
    assert any("familia ajena" in f for f in esquema.fallos_suelo_multiescala(doc))

    doc = _mutado(artefacto)
    doc["escalas"][0]["escala_ns"] = 12_345
    assert any("escala ajena" in f for f in esquema.fallos_suelo_multiescala(doc))


def test_el_validador_exige_cinco_procesos_por_escala(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    victima = doc["escalas"][0]
    doc["escalas"] = [
        e
        for e in doc["escalas"]
        if not (
            e["familia"] == victima["familia"]
            and e["escala_ns"] == victima["escala_ns"]
            and e["pid"] == victima["pid"]
        )
    ]
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("procesos distintos" in f for f in fallos)


def test_el_validador_rechaza_unidades_divergentes_entre_procesos(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["unidades"] += 1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no son equivalentes" in f for f in fallos)


def test_el_validador_rechaza_una_calibracion_que_no_deriva_las_unidades(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["calibracion"][fp.FAMILIA_CPU]["coste_referencia_ns"] = COSTE_CPU_NS * 2
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no salen de la calibracion publicada" in f for f in fallos)


def test_el_validador_rechaza_un_coste_que_no_es_el_p50_de_sus_muestras(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["calibracion"][fp.FAMILIA_CANON]["muestras_ns"][10] += 5
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no es el P50 de sus muestras" in f for f in fallos)


def test_el_validador_rechaza_un_sm_maquillado(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["sm_ns"] = 1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sm_ns" in f for f in fallos)


def test_el_validador_rechaza_un_regimen_declarado_a_conveniencia(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    for entrada in doc["regimenes_por_percentil"]:
        if entrada.get("p95") == fp.REGIMEN_ABSOLUTO:
            entrada["p95"] = fp.REGIMEN_RELATIVO
            break
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("corresponde" in f for f in fallos)


def test_el_validador_rechaza_la_combinacion_imposible(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    entrada = doc["regimenes_por_percentil"][0]
    entrada["p50"] = fp.REGIMEN_RELATIVO
    entrada["p95"] = fp.REGIMEN_ABSOLUTO
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("combinacion imposible" in f for f in fallos)


def test_el_validador_rechaza_eludir_la_guarda_de_instrumento(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["sm_ns"] = 10**12
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("guarda de dominancia se eludio" in f for f in fallos)


def test_el_validador_rechaza_un_veredicto_vacio(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["regimenes_por_percentil"] = []
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("vacio" in f for f in fallos)


def test_el_validador_rechaza_publicar_con_controles_fallidos(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["controles_internos"]["custodia_verificada"] = False
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("controles bloqueantes fallidos" in f for f in fallos)


def test_el_validador_rechaza_un_control_ausente(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    del doc["controles_internos"]["banda_cubre_el_suelo"]
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("control bloqueante ausente" in f for f in fallos)


def test_el_validador_rechaza_negaciones_alteradas(artefacto: dict[str, Any]) -> None:
    assert len(esquema.NEGACIONES_OBLIGATORIAS) == 7
    for clave in esquema.NEGACIONES_OBLIGATORIAS:
        doc = _mutado(artefacto)
        doc["no_autoriza"][clave] = True
        assert any(clave in f for f in esquema.fallos_suelo_multiescala(doc))
        doc = _mutado(artefacto)
        del doc["no_autoriza"][clave]
        assert any(clave in f for f in esquema.fallos_suelo_multiescala(doc))


def test_el_validador_exige_forma_de_sha_en_la_custodia(artefacto: dict[str, Any]) -> None:
    for ruta, valor in (
        (("preinscripcion", "commit_a"), ""),
        (("preinscripcion", "head_en_ejecucion"), "no-es-un-sha"),
        (("custodia", "head"), "0" * 39),
    ):
        doc = _mutado(artefacto)
        doc[ruta[0]][ruta[1]] = valor
        assert any("SHA" in f for f in esquema.fallos_suelo_multiescala(doc)), ruta

    doc = _mutado(artefacto)
    ruta_blob = fp.ARCHIVOS_PREINSCRITOS[0]
    doc["preinscripcion"]["blobs_preinscritos"][ruta_blob] = "no-es-un-blob"
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sin forma de blob Git" in f for f in fallos)


def test_el_validador_exige_que_los_pids_medidos_sean_los_declarados(
    artefacto: dict[str, Any],
) -> None:
    for seccion in ("escalas", "sondas_unitarias"):
        doc = _mutado(artefacto)
        doc[seccion][0]["pid"] = 12345
        fallos = esquema.fallos_suelo_multiescala(doc)
        assert any("no son los procesos declarados" in f for f in fallos), seccion

    doc = _mutado(artefacto)
    doc["procesos"][0]["pid"] = -1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("debe ser positivo" in f for f in fallos)


def test_el_validador_exige_carga_registrada_por_proceso(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["entorno"]["carga_por_proceso"] = {}
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no cubre exactamente los procesos declarados" in f for f in fallos)

    doc = _mutado(artefacto)
    doc["entorno"]["carga_por_proceso"][str(PIDS[0])] = []
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sin carga registrada" in f for f in fallos)

    doc = _mutado(artefacto)
    del doc["entorno"]["captura_inicial"]["carga"]
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sin carga del sistema" in f for f in fallos)


def test_el_validador_rechaza_una_tabla_de_progresion_inventada(
    artefacto: dict[str, Any],
) -> None:
    """La tabla no puede ser coherente solo consigo misma."""
    doc = _mutado(artefacto)
    fila = doc["diagnosticos"][fp.DIAG_PROGRESION]["por_proceso"][0]["filas"][0]
    # Coherente internamente: se mueven las dos magnitudes a la vez.
    fila["p50_menor_ns"] *= 3
    fila["p50_mayor_ns"] *= 3
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no coincide con la recomputada" in f for f in fallos)


def test_el_validador_exige_una_tabla_de_progresion_por_proceso(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["diagnosticos"][fp.DIAG_PROGRESION]["por_proceso"].pop()
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sin tabla para los procesos" in f for f in fallos)

    doc = _mutado(artefacto)
    doc["diagnosticos"][fp.DIAG_PROGRESION]["por_proceso"][0]["filas"].pop()
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("pares consecutivos de la escalera" in f for f in fallos)


def test_el_validador_recomputa_la_curva_de_dispersion(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["diagnosticos"][fp.DIAG_CURVA]["razon_por_mil"][0]["razon_por_mil"] += 1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("curva recomputada" in f for f in fallos)


def test_el_validador_exige_referencia_por_proceso_con_su_trabajo_fijo(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["diagnosticos"][fp.DIAG_REFERENCIA]["por_proceso"].pop()
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("entradas para 5 procesos" in f for f in fallos)

    doc = _mutado(artefacto)
    doc["diagnosticos"][fp.DIAG_REFERENCIA]["por_proceso"][0]["vueltas"] = 1
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("trabajo de referencia" in f for f in fallos)


def test_el_validador_fija_la_cita_historica_del_metodo_anterior(
    artefacto: dict[str, Any],
) -> None:
    contraste = artefacto["contraste_metodo_anterior"]
    assert contraste["u_anterior_ns"] == fp.U_ANTERIOR_NS == 48_790
    assert contraste["b_anterior_ns"] == fp.B_ANTERIOR_NS == 9_758
    for campo in ("u_anterior_ns", "b_anterior_ns"):
        doc = _mutado(artefacto)
        doc["contraste_metodo_anterior"][campo] += 1
        assert any(campo in f for f in esquema.fallos_suelo_multiescala(doc))


def test_el_validador_exige_capturas_etiquetadas_por_etapa(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["entorno"]["captura_final"]["etapa"] = "inicial"
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no se declara de la etapa final" in f for f in fallos)


def test_el_validador_rechaza_custodia_incompleta(artefacto: dict[str, Any]) -> None:
    for clave in (
        "diff_preinscritos_vacio",
        "sha_a_es_ancestro",
        "reverificada_tras_medir",
        "evidencia_anterior_intacta",
    ):
        doc = _mutado(artefacto)
        doc["custodia"][clave] = False
        assert esquema.fallos_suelo_multiescala(doc), clave


def test_el_validador_rechaza_una_evidencia_anterior_no_citada(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["preinscripcion"]["blobs_evidencia_anterior"] = {}
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("blobs_evidencia_anterior" in f for f in fallos)


def test_el_validador_rechaza_un_contraste_sin_explicacion(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["contraste_metodo_anterior"]["por_que_cambia"] = ""
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("por_que_cambia" in f for f in fallos)


def test_el_validador_rechaza_un_plan_que_no_es_el_preinscrito(artefacto: dict[str, Any]) -> None:
    for campo, valor in (
        ("procesos", 3),
        ("rondas", 2),
        ("semilla", 1),
        ("warmup_por_escala", 0),
        ("escalera_ns", [1, 2]),
        ("orden", []),
    ):
        doc = _mutado(artefacto)
        doc["plan"][campo] = valor
        assert esquema.fallos_suelo_multiescala(doc), campo


def test_el_validador_rechaza_progresion_maquillada(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    filas = doc["diagnosticos"][fp.DIAG_PROGRESION]["por_proceso"][0]["filas"]
    exigibles = [f for f in filas if f["exigible"]]
    assert exigibles, "la tabla debe contener filas exigibles"
    exigibles[0]["progresa"] = not exigibles[0]["progresa"]
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("progresa publicado" in f for f in fallos)


def test_el_validador_rechaza_deriva_publicada_como_estable(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["diagnosticos"][fp.DIAG_REFERENCIA]["por_proceso"][0] = {
        "vueltas": fp.VUELTAS_REFERENCIA,
        "p50_inicio_ns": 100,
        "p50_mitad_ns": 200,
        "p50_final_ns": 300,
    }
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("deriva o throttling" in f for f in fallos)


def test_el_validador_rechaza_incidencias_en_el_entorno(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["entorno"]["incidencias"] = ["algo raro"]
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("incidencias" in f for f in fallos)


def test_el_validador_rechaza_importar_una_clasificacion_de_tol_207(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["clasificacion_entorno"] = "ENVOLVENTE_REPRODUCIBLE"
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("TOL-207" in f for f in fallos)


def test_una_corrida_sin_punto_fijo_publica_no_evaluable_sin_inventar_nada(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = artefacto_no_evaluable
    assert esquema.fallos_suelo_multiescala(doc) == []
    derivacion = doc["derivacion"]
    assert derivacion["resultado"] == fp.NO_EVALUABLE
    assert derivacion["u_ns"] is None
    assert derivacion["b_ns"] is None
    assert "ninguna escala" in derivacion["motivo_no_evaluable"]
    assert all(not fila["sostenible"] for fila in derivacion["dispersiones"])
    # Sin umbral, ninguna magnitud se clasifica.
    for entrada in doc["regimenes_por_percentil"]:
        assert entrada["resultado"] == fp.NO_EVALUABLE
        assert entrada["motivo"] == "umbral_no_resuelto"
        assert "p50" not in entrada
    # El unico control que puede fallar es el que presupone el umbral.
    controles = doc["controles_internos"]
    assert controles["banda_cubre_el_suelo"] is False
    fallidos = [c for c in fp.CONTROLES_BLOQUEANTES if controles[c] is not True]
    assert fallidos == ["banda_cubre_el_suelo"]


def test_el_validador_exige_motivo_cuando_no_hay_punto_fijo(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = _mutado(artefacto_no_evaluable)
    doc["derivacion"]["motivo_no_evaluable"] = ""
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("motivo explicito" in f for f in fallos)


def test_el_validador_rechaza_publicar_u_sin_punto_fijo(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = _mutado(artefacto_no_evaluable)
    doc["derivacion"]["u_ns"] = 1_000_000
    doc["derivacion"]["b_ns"] = 200_000
    doc["derivacion"]["resultado"] = "RESUELTO"
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no coincide con el punto fijo recomputado" in f for f in fallos)


def test_no_evaluable_no_absuelve_otros_controles(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = _mutado(artefacto_no_evaluable)
    doc["controles_internos"]["custodia_verificada"] = False
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("no absuelve controles bloqueantes" in f for f in fallos)


def test_sin_banda_no_se_puede_declarar_que_la_banda_cubre(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = _mutado(artefacto_no_evaluable)
    doc["controles_internos"]["banda_cubre_el_suelo"] = True
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sin B no hay nada que cubra el suelo" in f for f in fallos)


def test_sin_umbral_no_se_puede_clasificar_ninguna_magnitud(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = _mutado(artefacto_no_evaluable)
    entrada = doc["regimenes_por_percentil"][0]
    entrada["resultado"] = "VALIDA"
    entrada["p50"] = fp.REGIMEN_ABSOLUTO
    entrada["p95"] = fp.REGIMEN_ABSOLUTO
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("sin umbral resuelto no se puede clasificar" in f for f in fallos)


def test_el_validador_rechaza_no_evaluable_con_punto_fijo_resuelto(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["resultado"] = fp.NO_EVALUABLE
    fallos = esquema.fallos_suelo_multiescala(doc)
    assert any("RESUELTO" in f for f in fallos)


# --------------------------------------------------------------------------
# Integridad de la preinscripcion
# --------------------------------------------------------------------------


def test_los_seis_ficheros_preinscritos_existen_y_parsean() -> None:
    assert len(fp.ARCHIVOS_PREINSCRITOS) == 6
    for ruta in fp.ARCHIVOS_PREINSCRITOS:
        completa = RAIZ / ruta
        assert completa.is_file(), ruta
        if completa.suffix == ".py":
            # ``ast.parse`` sobre el FICHERO, no una importacion: la cache de
            # bytecode puede ocultar un SyntaxError recien introducido.
            ast.parse(completa.read_text(encoding="utf-8"), filename=str(completa))


def test_este_fichero_esta_entre_los_preinscritos() -> None:
    relativa = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    assert relativa in fp.ARCHIVOS_PREINSCRITOS


def test_la_evidencia_anterior_sigue_en_su_sitio_y_sin_cambios() -> None:
    for ruta, blob in fp.BLOBS_EVIDENCIA_ANTERIOR.items():
        completa = RAIZ / ruta
        assert completa.is_file(), ruta
        assert fp.blob_git(completa.read_bytes()) == blob, ruta


def test_los_modulos_heredados_y_congelados_estan_intactos() -> None:
    for ruta, blob in fp.ARCHIVOS_HEREDADOS.items():
        assert fp.blob_git((RAIZ / ruta).read_bytes()) == blob, ruta
    for ruta, blob in fp.BLOBS_CORPUS_CONGELADO.items():
        assert fp.blob_git((RAIZ / ruta).read_bytes()) == blob, ruta


def test_el_protocolo_aprobado_esta_intacto() -> None:
    ruta = RAIZ / "docs/architecture" / fp.PROTOCOLO
    assert fp.blob_git(ruta.read_bytes()) == fp.BLOB_PROTOCOLO_APROBADO


def test_importar_los_modulos_no_mide_ni_escribe(tmp_path: Path) -> None:
    """Una importacion limpia no puede abrir ficheros ni cronometrar nada."""
    guion = (
        f"import sys; sys.path.insert(0, {str(RAIZ)!r});"
        "from experiments.adr002.tolerances import floor_scale_protocol,"
        " floor_scale_probes, run_floor_scale, schema_floor_scale_v0_1;"
        "print('ok')"
    )
    completado = subprocess.run(
        [sys.executable, "-c", guion],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completado.returncode == 0, completado.stderr
    assert completado.stdout.strip() == "ok"
    assert list(tmp_path.iterdir()) == []
