"""Pruebas de la preinscripcion de la banda envolvente (TOL-209, paquete 07).

Se congelan junto al metodo, ANTES de medir. Cubren:

1. las funciones puras del protocolo y las PROPIEDADES DEMOSTRABLES del
   metodo: envolvente monotona, banda no decreciente, cruce dentro de su
   intervalo y continuidad exacta en ``U``;
2. la reutilizacion congelada de las sondas del paquete 06;
3. el recorrido COMPLETO del orquestador, de extremo a extremo, con
   dependencias inyectadas y datos sinteticos: ninguna prueba mide;
4. el validador, contra un catalogo de mutaciones.

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
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.tolerances import envelope_protocol as ep
from experiments.adr002.tolerances import floor_scale_probes as sondas
from experiments.adr002.tolerances import run_envelope as corrida
from experiments.adr002.tolerances import schema_envelope_v0_1 as esquema

RAIZ = Path(__file__).resolve().parents[3]

SHA_FICTICIO = "0" * 40
PIDS: tuple[int, ...] = tuple(9001 + i for i in range(ep.PROCESOS_MINIMOS))

#: ``D(s) = 180 * isqrt(s)``: creciente, luego su envolvente coincide con
#: ella. La condicion ``5 D(s) <= s`` se cumple desde ``s >= 25 * 180^2``,
#: es decir desde 810 000 ns: el primer escalon sostenido es 1 ms y el cruce
#: cae en 900 000 ns, DENTRO del intervalo (500 us, 1 ms].
FACTOR_DISPERSION = 180
COSTE_CPU_NS = 345_000
COSTE_CANON_NS = 52_000
TAIL_BASE = 100


# --------------------------------------------------------------------------
# Datos sinteticos
# --------------------------------------------------------------------------


def dispersion_creciente(escala_ns: int) -> int:
    """Ley por defecto: creciente y con razon decreciente."""
    return FACTOR_DISPERSION * math.isqrt(escala_ns)


def dispersion_insostenible(escala_ns: int) -> int:
    """Ley con ``D(s) = s/2``: ningun escalon sostiene la condicion."""
    return escala_ns // 2


def dispersion_solo_el_ultimo(escala_ns: int) -> int:
    """Ley constante que solo deja sostenible el ultimo escalon.

    ``5 * 150 ms = 750 ms``: cabe en 1 s pero no en 500 ms.
    """
    del escala_ns
    return 150_000_000


def _vector(base: int, cola: int, n: int) -> list[int]:
    """Vector con P50 en ``base + 3`` y P95 en ``base + cola``."""
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
        "p50_ns": ep.percentil_ns(ordenadas, 1, 2),
        "p95_ns": ep.percentil_ns(ordenadas, 19, 20),
        "p99_ns": ep.percentil_ns(ordenadas, 99, 100),
        "min_ns": ordenadas[0],
        "max_ns": ordenadas[-1],
    }


def calibraciones_sinteticas() -> dict[str, sondas.Calibracion]:
    """Calibracion ficticia coherente: el P50 de las muestras es el coste."""

    def _muestras(coste: int) -> tuple[int, ...]:
        return tuple(coste + (i - 10) for i in range(ep.MUESTRAS_CALIBRACION))

    return {
        ep.FAMILIA_CPU: sondas.Calibracion(
            familia=ep.FAMILIA_CPU,
            unidades_referencia=ep.UNIDADES_REFERENCIA[ep.FAMILIA_CPU],
            coste_referencia_ns=COSTE_CPU_NS,
            muestras=_muestras(COSTE_CPU_NS),
        ),
        ep.FAMILIA_CANON: sondas.Calibracion(
            familia=ep.FAMILIA_CANON,
            unidades_referencia=ep.UNIDADES_REFERENCIA[ep.FAMILIA_CANON],
            coste_referencia_ns=COSTE_CANON_NS,
            muestras=_muestras(COSTE_CANON_NS),
        ),
    }


def plan_sintetico() -> corrida.PlanCorrida:
    return corrida.plan_de_corrida(corrida.plan_de_unidades(calibraciones_sinteticas()))


def resultado_sintetico(
    plan: corrida.PlanCorrida,
    indice: int,
    ley: Callable[[int], int] = dispersion_creciente,
) -> dict[str, Any]:
    """Resultado crudo de un proceso, sin medir nada."""
    ultimo = ep.PROCESOS_MINIMOS - 1
    escalas: dict[str, dict[str, Any]] = {familia: {} for familia in ep.FAMILIAS}
    for familia in ep.FAMILIAS:
        for escala in ep.ESCALERA_NS:
            objetivo = ley(escala)
            if familia == ep.FAMILIA_CPU:
                objetivo //= 2
            cola = TAIL_BASE + objetivo * indice // ultimo
            entrada = _entrada_cruda(escala, cola, ep.n_para_escala(escala), ep.WARMUP_ESCALA)
            entrada["unidades"] = plan.unidades[familia][escala]
            escalas[familia][str(escala)] = entrada

    unitarias = {
        ep.SONDA_VACIA: _entrada_cruda(
            130, 20 + 60 * indice // ultimo, ep.N_UNITARIA, ep.WARMUP_UNITARIA
        ),
        ep.SONDA_CANON_0: _entrada_cruda(
            4_700, TAIL_BASE + 11_000 * indice // ultimo, ep.N_UNITARIA, ep.WARMUP_UNITARIA
        ),
        ep.SONDA_CANON_1: _entrada_cruda(
            5_100, TAIL_BASE + 12_000 * indice // ultimo, ep.N_UNITARIA, ep.WARMUP_UNITARIA
        ),
    }

    return {
        "pid": PIDS[indice],
        "escalas": escalas,
        "unitarias": unitarias,
        "referencia": {
            "vueltas": ep.VUELTAS_REFERENCIA,
            "p50_inicio_ns": 345_000 + indice,
            "p50_mitad_ns": 345_050 + indice,
            "p50_final_ns": 345_020 + indice,
        },
        "unidades": corrida.unidades_a_json(plan.unidades),
        "cargas": [0.5, 0.6, 0.55],
        "incidencias": [],
        "filtrado_aplicado": False,
        "warmup_mezclado": False,
    }


def resultados_sinteticos(
    plan: corrida.PlanCorrida, ley: Callable[[int], int] = dispersion_creciente
) -> list[Mapping[str, Any]]:
    return [resultado_sintetico(plan, i, ley) for i in range(ep.PROCESOS_MINIMOS)]


def entorno_de_prueba(
    *,
    limpio: bool = True,
    ancestro: bool = True,
    diff_vacio: bool = True,
    head: str = SHA_FICTICIO,
    sobrescribir: Mapping[str, bytes] | None = None,
    blob_en_commit_divergente: bool = False,
) -> ep.EntornoCustodia:
    """Custodia sobre el repositorio real, con las decisiones inyectadas."""
    extra = dict(sobrescribir or {})

    def leer_bytes(ruta: str) -> bytes:
        if ruta in extra:
            return extra[ruta]
        return (RAIZ / ruta).read_bytes()

    def blob_en_commit(_sha: str, ruta: str) -> str | None:
        if blob_en_commit_divergente:
            return "f" * 40
        return ep.blob_git(leer_bytes(ruta))

    return ep.EntornoCustodia(
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
    entorno: ep.EntornoCustodia | None = None,
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
        datos = json.loads((RAIZ / ep.RUTA_LINEA_BASE).read_text(encoding="utf-8"))
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
    salida = tmp_path / "envolvente.json"
    codigo = corrida.main(
        ["--execute", "--preinscription-commit", SHA_FICTICIO, "--output", str(salida)],
        dependencias=dependencias_de_prueba(**kwargs),
    )
    assert codigo == corrida.CODIGO_OK
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


@pytest.fixture(scope="module")
def artefacto(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    return documento_producido(tmp_path_factory.mktemp("envolvente"))


@pytest.fixture(scope="module")
def artefacto_no_evaluable(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    plan = plan_sintetico()
    return documento_producido(
        tmp_path_factory.mktemp("envolvente_no_evaluable"),
        resultados=resultados_sinteticos(plan, dispersion_insostenible),
    )


def envolvente_de_ley(ley: Callable[[int], int]) -> ep.Envolvente:
    """Envolvente construida directamente de una ley, sin pasar por medidas."""
    dispersiones = tuple(ley(s) for s in ep.ESCALERA_NS)
    acumulado: list[int] = []
    peor = 0
    for valor in dispersiones:
        peor = max(peor, valor)
        acumulado.append(peor)
    return ep.Envolvente(dispersiones=dispersiones, envolvente=tuple(acumulado))


# --------------------------------------------------------------------------
# Escalera, percentiles y constantes
# --------------------------------------------------------------------------


def test_la_escalera_amplia_la_del_paquete_06_hasta_un_segundo() -> None:
    assert len(ep.ESCALERA_NS) == 16
    assert list(ep.ESCALERA_NS) == sorted(ep.ESCALERA_NS)
    assert ep.ESCALERA_NS[-3:] == (200_000_000, 500_000_000, 1_000_000_000)
    for escala in ep.ESCALERA_NS:
        assert escala % ep.FACTOR_U == 0
    for escala in ep.ESCALERA_NS:
        assert ep.n_para_escala(escala) % ep.RONDAS_ROUND_ROBIN == 0


def test_once_sesiones_independientes() -> None:
    assert ep.PROCESOS_MINIMOS == 11
    assert ep.PROCESOS_MINIMOS % 2 == 1, "impar para que el P50 entre procesos sea real"


def test_percentil_no_interpola_y_usa_techo() -> None:
    ordenadas = list(range(1, 101))
    assert ep.percentil_ns(ordenadas, 1, 2) == 50
    assert ep.percentil_ns(ordenadas, 19, 20) == 95
    assert ep.percentil_ns(ordenadas, 99, 100) == 99
    with pytest.raises(ValueError, match="fraccion invalida"):
        ep.percentil_ns([1, 2, 3], 3, 2)
    with pytest.raises(ValueError, match="no hay muestras"):
        ep.percentil_ns([], 1, 2)


def test_resolucion_percentil_coherente_con_el_rango() -> None:
    for n in (30, 100, 300):
        rango = max(1, -(-99 * n // 100))
        peores = n - rango + 1
        texto = ep.resolucion_percentil(n)
        if peores <= 1:
            assert "maximo observado" in texto
        else:
            assert f"{peores}.a peor" in texto
    with pytest.raises(ValueError, match="n debe ser positivo"):
        ep.resolucion_percentil(0)


def test_unidades_para_escala_redondea_al_entero_mas_cercano() -> None:
    assert ep.unidades_para_escala(100, unidades_referencia=10, coste_referencia_ns=100) == 10
    assert ep.unidades_para_escala(104, unidades_referencia=10, coste_referencia_ns=100) == 10
    assert ep.unidades_para_escala(106, unidades_referencia=10, coste_referencia_ns=100) == 11
    assert ep.unidades_para_escala(1, unidades_referencia=10, coste_referencia_ns=10_000) == 1
    with pytest.raises(ValueError, match="calibracion invalida"):
        ep.unidades_para_escala(100, unidades_referencia=0, coste_referencia_ns=100)


# --------------------------------------------------------------------------
# Envolvente monotona
# --------------------------------------------------------------------------


def test_la_envolvente_es_el_maximo_acumulado() -> None:
    envolvente = envolvente_de_ley(lambda s: 1 if s == ep.ESCALERA_NS[3] else 0)
    assert envolvente.envolvente[:3] == (0, 0, 0)
    assert all(v == 1 for v in envolvente.envolvente[3:])


def test_la_envolvente_es_monotona_aunque_la_curva_no_lo_sea() -> None:
    """La curva D(s) medida NO es monotona: la del paquete 06 lo demostro."""
    medida = [6404, 6640, 5346, 56498, 46720, 330419, 274175, 964694]
    medida += [1553846, 2388363, 5041895, 18425838, 15982352, 30_000_000, 20_000_000, 40_000_000]
    envolvente = ep.Envolvente(tuple(medida), tuple())
    acumulado: list[int] = []
    peor = 0
    for valor in medida:
        peor = max(peor, valor)
        acumulado.append(peor)
    envolvente = ep.Envolvente(tuple(medida), tuple(acumulado))
    assert not all(a <= b for a, b in pairwise(medida)), "la curva medida no es monotona"
    assert envolvente.es_monotona()
    assert envolvente.cubre_el_suelo()


def test_la_banda_toma_siempre_el_escalon_superior() -> None:
    envolvente = envolvente_de_ley(dispersion_creciente)
    for indice, escala in enumerate(ep.ESCALERA_NS):
        assert envolvente.banda(escala) == envolvente.envolvente[indice]
    # Cualquier magnitud del tramo recibe el valor del escalon SUPERIOR.
    assert envolvente.banda(ep.ESCALERA_NS[0] - 1) == envolvente.envolvente[0]
    assert envolvente.banda(ep.ESCALERA_NS[0] + 1) == envolvente.envolvente[1]
    assert envolvente.banda(1) == envolvente.envolvente[0]


def test_la_banda_no_esta_definida_por_encima_del_ultimo_escalon() -> None:
    """Y no hace falta: esa magnitud vive siempre en regimen relativo."""
    envolvente = envolvente_de_ley(dispersion_creciente)
    with pytest.raises(ep.EscaleraInvalidaError, match="por encima del ultimo escalon"):
        envolvente.banda(ep.ESCALERA_NS[-1] + 1)
    with pytest.raises(ValueError, match="magnitud debe ser positiva"):
        envolvente.banda(0)


def test_la_banda_nunca_se_estrecha_al_crecer_la_magnitud() -> None:
    """Es la propiedad que cierra M-03; una lectura directa de D la rompe."""
    envolvente = envolvente_de_ley(dispersion_creciente)
    assert ep.banda_no_decreciente(envolvente)

    # Con la curva medida sin envolver, la banda SI se estrecharia.
    cruda = ep.Envolvente(
        dispersiones=tuple(range(len(ep.ESCALERA_NS))),
        envolvente=tuple(reversed(range(len(ep.ESCALERA_NS)))),
    )
    assert not cruda.es_monotona()
    assert not ep.banda_no_decreciente(cruda)


# --------------------------------------------------------------------------
# El cruce
# --------------------------------------------------------------------------


def test_el_cruce_cae_dentro_del_intervalo_de_su_escalon() -> None:
    """Demostracion del docstring de ``resolver_cruce``, comprobada."""
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    assert cruce.evaluable
    indice = cruce.indice_escalon
    assert indice is not None
    inferior = 0 if indice == 0 else ep.ESCALERA_NS[indice - 1]
    assert cruce.u is not None
    assert inferior < cruce.u <= ep.ESCALERA_NS[indice]


def test_el_umbral_no_tiene_por_que_ser_un_escalon() -> None:
    """Es la diferencia con el paquete 06, donde U era un escalon medido."""
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    assert cruce.u == 900_000
    assert cruce.u not in ep.ESCALERA_NS
    assert cruce.indice_escalon == ep.ESCALERA_NS.index(1_000_000)


def test_la_continuidad_en_el_umbral_es_exacta_y_derivada() -> None:
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    assert cruce.u is not None
    assert cruce.b_en_u is not None
    assert ep.continuidad_exacta(cruce)
    # m * B(U) == 0,20 * U, sin resto y sin postular m.
    assert ep.MARGEN_M * cruce.b_en_u * ep.OBJETIVO_RELATIVO_DEN == (
        ep.OBJETIVO_RELATIVO_NUM * cruce.u
    )
    assert cruce.envolvente.banda(cruce.u) == cruce.b_en_u
    assert cruce.u == ep.FACTOR_U * cruce.b_en_u


def test_el_cruce_exige_sostenerse_en_todos_los_escalones_superiores() -> None:
    """Un cruce aislado no puede adelantar el umbral."""

    def ley(escala: int) -> int:
        if escala == 50_000:
            return 1_000  # 5*1000 <= 50000: sostenible en solitario
        return dispersion_creciente(escala)

    cruce = ep.resolver_cruce(envolvente_de_ley(ley))
    assert cruce.evaluable
    assert cruce.indice_escalon == ep.ESCALERA_NS.index(1_000_000)


def test_sin_ningun_escalon_sostenido_el_resultado_es_no_evaluable() -> None:
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_insostenible))
    assert not cruce.evaluable
    assert cruce.u is None
    assert cruce.b_en_u is None
    assert cruce.motivo_no_evaluable is not None
    assert cruce.motivo_no_evaluable.startswith(ep.MOTIVO_SIN_CRUCE)
    assert not ep.continuidad_exacta(cruce)


def test_un_cruce_en_el_borde_superior_es_no_evaluable() -> None:
    """Sin escala medida posterior, el cruce no puede confirmarse."""
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_solo_el_ultimo))
    assert not cruce.evaluable
    assert cruce.motivo_no_evaluable is not None
    assert cruce.motivo_no_evaluable.startswith(ep.MOTIVO_BORDE_SUPERIOR)
    assert cruce.indice_escalon == len(ep.ESCALERA_NS) - 1


def test_las_confirmaciones_son_todos_los_escalones_por_encima() -> None:
    """Con ``CONFIRMACIONES_MINIMAS = 1``, el control de borde ya lo implica.

    Se comprueba la identidad para que un endurecimiento futuro de la
    constante tenga sobre que morder, y se publica el recuento.
    """
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    assert cruce.indice_escalon is not None
    assert cruce.confirmaciones == len(ep.ESCALERA_NS) - 1 - cruce.indice_escalon
    assert cruce.confirmaciones >= ep.CONFIRMACIONES_MINIMAS


def test_el_cruce_recupera_el_metodo_del_paquete_06_si_d_es_constante() -> None:
    """Con ``D`` constante, ``E = D`` y ``U = 5 D``: el punto fijo anterior."""
    constante = 40_000
    cruce = ep.resolver_cruce(envolvente_de_ley(lambda _s: constante))
    assert cruce.u == ep.FACTOR_U * constante
    assert cruce.b_en_u == constante


def test_sostenible_en_escalon_es_exacto_en_su_frontera() -> None:
    assert ep.sostenible_en_escalon(200, 1_000) is True
    assert ep.sostenible_en_escalon(201, 1_000) is False


def test_razon_por_mil_no_usa_coma_flotante() -> None:
    assert ep.razon_por_mil(200, 1_000) == 200
    assert ep.razon_por_mil(0, 1_000) == 0
    with pytest.raises(ValueError, match="escala debe ser positiva"):
        ep.razon_por_mil(1, 0)


def test_la_envolvente_evita_la_asimetria_en_el_caso_ordinario() -> None:
    """Con una curva creciente, ninguna banda baja del 20 % de su escalon.

    El maximo acumulado arrastra hacia arriba los escalones bajos, que son
    justamente los que no sostienen la condicion y por tanto tienen
    ``E(s) > 0,20 s``.
    """
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    filas = ep.holgura_por_escalon(cruce)
    assert len(filas) == len(ep.ESCALERA_NS)
    estrictos = [
        f["escala_ns"] for f in filas if f["bajo_el_umbral"] and not f["banda_al_menos_el_objetivo"]
    ]
    assert estrictos == []


def test_la_holgura_denuncia_la_asimetria_cuando_existe() -> None:
    """Un pico tardio deja escalones bajos con banda menor que su 20 %.

    Suelo diminuto hasta 100 us, un pico de 30 ms en 200 us y nada mayor: el
    cruce se va a 150 ms, y la banda de 100 us —1 us— queda muy por debajo
    del 20 % de 100 us. Es alcanzable, porque cubre el suelo medido, pero es
    una asimetria y el diagnostico la publica en vez de disimularla.
    """

    def ley(escala: int) -> int:
        if escala < 200_000:
            return 1_000
        if escala == 200_000:
            return 30_000_000
        return 1_000

    cruce = ep.resolver_cruce(envolvente_de_ley(ley))
    assert cruce.u == 150_000_000
    filas = ep.holgura_por_escalon(cruce)
    estrictos = [
        f["escala_ns"] for f in filas if f["bajo_el_umbral"] and not f["banda_al_menos_el_objetivo"]
    ]
    assert 100_000 in estrictos, "la asimetria existe y debe publicarse, no disimularse"
    # Y sigue siendo alcanzable: la banda cubre el suelo medido en ese escalon.
    assert cruce.envolvente.cubre_el_suelo()


# --------------------------------------------------------------------------
# Dispersion, cobertura y SM
# --------------------------------------------------------------------------


def medidas_de_ley(ley: Callable[[int], int]) -> list[ep.MedidaEscala]:
    medidas: list[ep.MedidaEscala] = []
    ultimo = ep.PROCESOS_MINIMOS - 1
    for escala in ep.ESCALERA_NS:
        for indice, pid in enumerate(PIDS):
            valor = escala + ley(escala) * indice // ultimo
            for familia in ep.FAMILIAS:
                p95 = valor if familia == ep.FAMILIA_CANON else escala
                medidas.append(
                    ep.MedidaEscala(
                        familia=familia,
                        escala_ns=escala,
                        unidades=10,
                        pid=pid,
                        n=ep.n_para_escala(escala),
                        warmup_descartado=ep.WARMUP_ESCALA,
                        p50=escala,
                        p95=p95,
                        p99=p95,
                        minimo=escala,
                        maximo=p95,
                        media_truncada=escala,
                    )
                )
    return medidas


def test_la_dispersion_toma_el_peor_caso_entre_familias_y_percentiles() -> None:
    medidas = medidas_de_ley(dispersion_creciente)
    for escala in ep.ESCALERA_NS:
        peor = ep.dispersion_de_escala(medidas, escala)
        assert peor == ep.dispersion_de_familia(medidas, ep.FAMILIA_CANON, escala, "p95")
    with pytest.raises(ValueError, match="percentil no normativo"):
        ep.dispersion_de_familia(medidas, ep.FAMILIA_CPU, ep.ESCALERA_NS[0], "p99")


def test_la_cobertura_exige_once_procesos_por_familia_y_escala() -> None:
    medidas = medidas_de_ley(dispersion_creciente)
    recortadas = [m for m in medidas if not (m.escala_ns == 100_000 and m.pid == PIDS[-1])]
    with pytest.raises(ep.ProcesosInsuficientesError):
        ep.construir_envolvente(recortadas)


def test_la_cobertura_rechaza_familias_y_escalas_ajenas() -> None:
    medidas = medidas_de_ley(dispersion_creciente)
    intrusa = ep.MedidaEscala(
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
    with pytest.raises(ep.SondaNoNeutralError):
        ep.construir_envolvente([*medidas, intrusa])

    ajena = ep.MedidaEscala(
        familia=ep.FAMILIA_CPU,
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
    with pytest.raises(ep.EscaleraInvalidaError, match="escalas ajenas"):
        ep.construir_envolvente([*medidas, ajena])


def unitarias_sinteticas() -> list[ep.MedidaUnitaria]:
    medidas: list[ep.MedidaUnitaria] = []
    for sonda in ep.SONDAS_UNITARIAS:
        for indice, pid in enumerate(PIDS):
            p95 = 5_000 + 1_000 * indice
            medidas.append(
                ep.MedidaUnitaria(
                    sonda=sonda,
                    pid=pid,
                    n=ep.N_UNITARIA,
                    warmup_descartado=ep.WARMUP_UNITARIA,
                    p50=5_000,
                    p95=p95,
                    p99=p95,
                    minimo=5_000,
                    maximo=p95,
                    media_truncada=5_000,
                )
            )
    return medidas


def test_sm_es_el_peor_p95_y_exige_las_tres_sondas() -> None:
    medidas = unitarias_sinteticas()
    assert ep.calcular_sm(medidas) == max(m.p95 for m in medidas)
    sin_una = [m for m in medidas if m.sonda != ep.SONDA_CANON_0]
    with pytest.raises(ep.EscaleraInvalidaError, match="faltan sondas unitarias"):
        ep.calcular_sm(sin_una)
    recortada = [m for m in medidas if not (m.sonda == ep.SONDA_VACIA and m.pid == PIDS[0])]
    with pytest.raises(ep.ProcesosInsuficientesError):
        ep.calcular_sm(recortada)


# --------------------------------------------------------------------------
# Regimen, banda y veredicto
# --------------------------------------------------------------------------


def test_los_tres_regimenes_posibles_y_la_banda_que_aplica() -> None:
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    assert cruce.u == 900_000
    sm = 1_000

    absoluto = ep.evaluar_magnitud([100_000] * 11, [150_000] * 11, sm=sm, cruce=cruce)
    assert [v.regimen for v in absoluto.por_percentil] == ["absoluto", "absoluto"]
    # La banda de una magnitud de 100 us es la envolvente en ese escalon.
    assert absoluto.por_percentil[0].banda_ns == cruce.envolvente.banda(100_000)

    mixto = ep.evaluar_magnitud([800_000] * 11, [1_000_000] * 11, sm=sm, cruce=cruce)
    assert [v.regimen for v in mixto.por_percentil] == ["absoluto", "relativo"]
    assert mixto.por_percentil[1].banda_ns is None

    relativo = ep.evaluar_magnitud([2_000_000] * 11, [2_100_000] * 11, sm=sm, cruce=cruce)
    assert [v.regimen for v in relativo.por_percentil] == ["relativo", "relativo"]


def test_la_guarda_de_instrumento_va_antes_del_regimen() -> None:
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    veredicto = ep.evaluar_magnitud([1_000] * 11, [2_000] * 11, sm=21_000, cruce=cruce)
    assert veredicto.dominada_por_instrumento
    assert veredicto.resultado == ep.NO_EVALUABLE
    assert veredicto.por_percentil == ()
    assert ep.registro_por_percentil(veredicto) == ep.NO_EVALUABLE


def test_no_se_clasifica_sin_umbral_resuelto() -> None:
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_insostenible))
    with pytest.raises(ep.InvarianteVioladoError, match="sin umbral resuelto"):
        ep.evaluar_magnitud([1] * 11, [2] * 11, sm=0, cruce=cruce)


def test_el_invariante_de_percentiles_se_hace_cumplir() -> None:
    cruce = ep.resolver_cruce(envolvente_de_ley(dispersion_creciente))
    with pytest.raises(ep.InvarianteVioladoError, match="invariante violado"):
        ep.evaluar_magnitud([500_000] * 11, [400_000] * 11, sm=1, cruce=cruce)
    with pytest.raises(ValueError, match="incoherente"):
        ep.evaluar_magnitud([1] * 11, [2] * 10, sm=0, cruce=cruce)
    with pytest.raises(ValueError, match="faltan percentiles"):
        ep.evaluar_magnitud([], [], sm=0, cruce=cruce)


def test_criterios_relativo_y_absoluto_en_sus_fronteras() -> None:
    assert ep.pasa_relativo(1_000, 1_200) is True
    assert ep.pasa_relativo(1_000, 1_201) is False
    assert ep.pasa_relativo(0, 0) is False
    assert ep.pasa_absoluto(1_000, 1_200, 200) is True
    assert ep.pasa_absoluto(1_000, 1_201, 200) is False


# --------------------------------------------------------------------------
# Controles, progresion y deriva
# --------------------------------------------------------------------------


def test_los_controles_fallan_cerrado() -> None:
    completo = dict.fromkeys(ep.CONTROLES_BLOQUEANTES, True)
    assert ep.evaluar_controles(completo).valido
    for control in ep.CONTROLES_BLOQUEANTES:
        ausente = {k: v for k, v in completo.items() if k != control}
        assert ep.evaluar_controles(ausente).fallos == (control,)
    for valor in (1, "si", None, 0):
        alterado = {**completo, "pids_distintos": valor}
        assert "pids_distintos" in ep.evaluar_controles(alterado).fallos  # type: ignore[arg-type]


def test_escala_progresa_con_tolerancia_de_un_tercio() -> None:
    assert ep.escala_progresa(1_000, 10_000, 2_000, 20_000) is True
    assert ep.escala_progresa(1_000, 10_000, 1_000, 20_000) is False
    assert ep.escala_progresa(1_000, 10_000, 2_666, 20_000) is True
    assert ep.escala_progresa(1_000, 10_000, 2_667, 20_000) is False
    assert ep.escala_progresa(0, 10_000, 1_000, 20_000) is False


def test_progresion_solo_exigible_sin_cuantizacion_relevante() -> None:
    assert ep.progresion_exigible(ep.UNIDADES_MINIMAS_PROGRESION, 100) is True
    assert ep.progresion_exigible(1, 100) is False


def test_referencia_estable_solo_denuncia_deriva_monotona_y_excesiva() -> None:
    assert ep.referencia_estable(100, 110, 105) is True
    assert ep.referencia_estable(100, 110, 120) is True
    assert ep.referencia_estable(100, 120, 140) is False
    assert ep.referencia_estable(0, 1, 2) is False


def test_calibracion_en_banda_en_sus_fronteras() -> None:
    assert ep.calibracion_en_banda(500, 1_000) is True
    assert ep.calibracion_en_banda(499, 1_000) is False
    assert ep.calibracion_en_banda(2_000, 1_000) is True
    assert ep.calibracion_en_banda(2_001, 1_000) is False


# --------------------------------------------------------------------------
# Custodia
# --------------------------------------------------------------------------


def blobs_reales() -> dict[str, str]:
    return {ruta: ep.blob_git((RAIZ / ruta).read_bytes()) for ruta in ep.ARCHIVOS_PREINSCRITOS}


def heredados_reales() -> dict[str, str]:
    return {ruta: ep.blob_git((RAIZ / ruta).read_bytes()) for ruta in ep.ARCHIVOS_HEREDADOS}


def test_blob_git_coincide_con_git_hash_object() -> None:
    ruta = "experiments/adr002/tolerances/envelope_protocol.py"
    esperado = subprocess.run(
        ["git", "hash-object", ruta],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert ep.blob_git((RAIZ / ruta).read_bytes()) == esperado


def test_custodia_completa_no_encuentra_fallos() -> None:
    assert (
        ep.verificar_custodia(
            entorno_de_prueba(),
            sha_a=SHA_FICTICIO,
            blobs_preinscritos=blobs_reales(),
            blobs_heredados=heredados_reales(),
        )
        == ()
    )


def test_custodia_denuncia_commit_inexistente() -> None:
    entorno = ep.EntornoCustodia(
        leer_bytes=lambda ruta: (RAIZ / ruta).read_bytes(),
        es_ancestro=lambda _a, _b: True,
        existe_commit=lambda _sha: False,
        head=lambda: SHA_FICTICIO,
        arbol_limpio=lambda: True,
        diff_vacio=lambda _a, _b, _rutas: True,
        blob_en_commit=lambda _s, ruta: ep.blob_git((RAIZ / ruta).read_bytes()),
    )
    assert ep.verificar_custodia(
        entorno,
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    ) == ("commit de preinscripcion inexistente",)


def test_custodia_denuncia_no_ancestro_y_diff_no_vacio() -> None:
    fallos = ep.verificar_custodia(
        entorno_de_prueba(ancestro=False, diff_vacio=False),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    )
    assert any("no es ancestro" in f for f in fallos)
    assert any("diff no vacio" in f for f in fallos)


def test_custodia_usa_una_fuente_de_verdad_independiente_del_arbol() -> None:
    fallos = ep.verificar_custodia(
        entorno_de_prueba(blob_en_commit_divergente=True),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    )
    assert any("difiere del commit de preinscripcion" in f for f in fallos)


def test_custodia_denuncia_modulo_heredado_alterado() -> None:
    fallos = ep.verificar_custodia(
        entorno_de_prueba(),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados={ruta: "0" * 40 for ruta in ep.ARCHIVOS_HEREDADOS},
    )
    assert any("blob heredado distinto del preinscrito" in f for f in fallos)


def test_custodia_denuncia_evidencias_anteriores_alteradas() -> None:
    for ruta in ep.EVIDENCIAS_ANTERIORES:
        alterada = entorno_de_prueba(sobrescribir={ruta: b"{}"})
        fallos = ep.fallos_evidencias_anteriores(alterada)
        assert any("alterada" in f and ruta in f for f in fallos), ruta


def test_custodia_denuncia_registro_o_protocolo_alterados() -> None:
    for ruta in (
        f"docs/architecture/{ep.REGISTRO}",
        f"docs/architecture/{ep.PROTOCOLO}",
        ep.RUTA_LINEA_BASE,
    ):
        alterado = entorno_de_prueba(sobrescribir={ruta: b"cambiado"})
        fallos = ep.fallos_documentos_de_referencia(alterado)
        assert any("alterado" in f and ruta in f for f in fallos), ruta
    assert ep.fallos_documentos_de_referencia(entorno_de_prueba()) == ()


def test_precondiciones_de_ejecucion_fallan_cerrado() -> None:
    limpio = entorno_de_prueba()
    assert (
        ep.verificar_precondiciones_ejecucion(limpio, sha_a=SHA_FICTICIO, salida_existe=False) == ()
    )
    sucio = entorno_de_prueba(limpio=False)
    assert "arbol de trabajo sucio" in ep.verificar_precondiciones_ejecucion(
        sucio, sha_a=SHA_FICTICIO, salida_existe=False
    )
    desviado = entorno_de_prueba(head="a" * 40)
    fallos = ep.verificar_precondiciones_ejecucion(
        desviado, sha_a=SHA_FICTICIO, salida_existe=False
    )
    assert any("distinto del commit de preinscripcion" in f for f in fallos)
    assert "la ruta de salida ya existe" in ep.verificar_precondiciones_ejecucion(
        limpio, sha_a=SHA_FICTICIO, salida_existe=True
    )


# --------------------------------------------------------------------------
# Sondas heredadas del paquete 06, sin tocar
# --------------------------------------------------------------------------


def test_las_sondas_se_heredan_congeladas_del_paquete_06() -> None:
    for ruta, blob in ep.ARCHIVOS_HEREDADOS.items():
        assert ep.blob_git((RAIZ / ruta).read_bytes()) == blob, ruta
    assert "experiments/adr002/tolerances/floor_scale_probes.py" in ep.ARCHIVOS_HEREDADOS


def test_las_familias_y_sondas_son_neutrales() -> None:
    assert ep.comprobar_neutralidad([*ep.FAMILIAS, *ep.SONDAS_UNITARIAS]) == ()
    for nombre in ("busqueda_fts5", "orden_por_rank", "puntuacion_bm25", "ADR002-C"):
        assert ep.comprobar_neutralidad([nombre]) != ()
    assert sondas.fallos_sql_de_sonda(sondas.SQL_SONDA_CANON) == ()


def test_ninguna_cadena_sql_heredada_toca_fts_ni_rank() -> None:
    ruta = RAIZ / "experiments/adr002/tolerances/floor_scale_probes.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    troceados: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.JoinedStr):
            troceados.update(id(hijo) for hijo in ast.walk(nodo) if hijo is not nodo)
    consultas: list[str] = []
    for nodo in ast.walk(arbol):
        if id(nodo) in troceados or not isinstance(nodo, ast.Constant | ast.JoinedStr):
            continue
        if isinstance(nodo, ast.Constant) and not isinstance(nodo.value, str):
            continue
        texto = ast.unparse(nodo)
        if "select" in texto.lower():
            consultas.append(texto)
    assert consultas
    for consulta in consultas:
        minusculas = consulta.lower()
        assert sondas.TABLA_CANONICA in minusculas or "tabla_canonica" in minusculas
        for prohibido in ("fts", "match", "rank", "bm25", "embedding", "vector"):
            assert prohibido not in minusculas, consulta


def test_el_orden_es_round_robin_sobre_los_pares_de_la_escalera() -> None:
    pares = ep.pares_de_escalera()
    assert len(pares) == len(ep.FAMILIAS) * len(ep.ESCALERA_NS)
    orden = list(sondas.orden_round_robin(pares, ep.RONDAS_ROUND_ROBIN))
    assert len(orden) == len(pares) * ep.RONDAS_ROUND_ROBIN
    assert orden[: len(pares)] == list(pares)
    assert [familia for familia, _ in orden[: len(ep.FAMILIAS)]] == list(ep.FAMILIAS)


# --------------------------------------------------------------------------
# El orquestador no mide sin autorizacion
# --------------------------------------------------------------------------


def test_sin_execute_no_mide_nada(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main([]) == corrida.CODIGO_SIN_EXECUTE
    assert "no mide sin --execute" in capsys.readouterr().out


def test_el_plan_se_imprime_sin_medir(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main(["--plan"]) == corrida.CODIGO_OK
    salida = capsys.readouterr().out
    assert str(ep.PROCESOS_MINIMOS) in salida
    assert str(len(ep.CONTROLES_BLOQUEANTES)) in salida


def test_execute_sin_commit_ni_salida_se_bloquea(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main(["--execute"]) == corrida.CODIGO_BLOQUEADO
    assert "--preinscription-commit" in capsys.readouterr().out


def test_worker_sin_unidades_se_bloquea(capsys: pytest.CaptureFixture[str]) -> None:
    assert corrida.main(["--execute", "--worker"]) == corrida.CODIGO_BLOQUEADO
    assert "la cantidad de trabajo la fija el padre" in capsys.readouterr().out


def test_unidades_desde_json_falla_cerrado() -> None:
    plan = corrida.unidades_a_json(plan_sintetico().unidades)
    assert corrida.unidades_desde_json(plan)[ep.FAMILIA_CPU][10_000] > 0
    with pytest.raises(corrida.EjecucionBloqueadaError, match="debe ser un objeto"):
        corrida.unidades_desde_json([])
    with pytest.raises(corrida.EjecucionBloqueadaError, match="no trae la familia"):
        corrida.unidades_desde_json({ep.FAMILIA_CPU: plan[ep.FAMILIA_CPU]})
    roto = deepcopy(plan)
    roto[ep.FAMILIA_CANON]["10000"] = 0
    with pytest.raises(corrida.EjecucionBloqueadaError, match="unidades invalidas"):
        corrida.unidades_desde_json(roto)


def test_el_plan_de_unidades_cubre_la_escalera_de_dieciseis() -> None:
    plan = corrida.plan_de_unidades(calibraciones_sinteticas())
    assert set(plan) == set(ep.FAMILIAS)
    for familia in ep.FAMILIAS:
        assert set(plan[familia]) == set(ep.ESCALERA_NS)
        assert all(v >= 1 for v in plan[familia].values())
    with pytest.raises(corrida.EjecucionBloqueadaError, match="faltan calibraciones"):
        corrida.plan_de_unidades({ep.FAMILIA_CPU: calibraciones_sinteticas()[ep.FAMILIA_CPU]})


# --------------------------------------------------------------------------
# Recorrido completo de extremo a extremo (sin medir)
# --------------------------------------------------------------------------


def test_recorrido_completo_produce_un_artefacto_valido(artefacto: dict[str, Any]) -> None:
    assert esquema.fallos_banda_envolvente(artefacto) == []
    assert artefacto["version_esquema"] == ep.VERSION_ESQUEMA
    assert artefacto["estado"] == ep.ESTADO_EVIDENCIA
    assert artefacto["no_autoriza"]["aprobacion_tol_209"] is False


def test_el_artefacto_publica_el_cruce_esperado(artefacto: dict[str, Any]) -> None:
    der = artefacto["derivacion"]
    assert der["resultado"] == "RESUELTO"
    assert der["u_ns"] == 900_000
    assert der["b_en_u_ns"] == 180_000
    assert der["u_ns"] not in ep.ESCALERA_NS, "U no tiene por que ser un escalon"
    assert der["intervalo_del_cruce_ns"] == [500_000, 1_000_000]
    assert der["confirmaciones_posteriores"] >= ep.CONFIRMACIONES_MINIMAS
    assert der["motivo_no_evaluable"] is None


def test_el_cruce_se_reproduce_desde_cero(artefacto: dict[str, Any]) -> None:
    """Recomputacion independiente desde los vectores crudos publicados."""
    dispersiones: list[int] = []
    for escala in ep.ESCALERA_NS:
        peor = 0
        for familia in ep.FAMILIAS:
            for clave in ("p50_ns", "p95_ns"):
                valores = [
                    int(e[clave])
                    for e in artefacto["escalas"]
                    if e["familia"] == familia and e["escala_ns"] == escala
                ]
                peor = max(peor, max(valores) - min(valores))
        dispersiones.append(peor)

    envolvente: list[int] = []
    acumulado = 0
    for valor in dispersiones:
        acumulado = max(acumulado, valor)
        envolvente.append(acumulado)
    assert envolvente == sorted(envolvente), "la envolvente es monotona"

    sostenibles = [5 * e <= s for e, s in zip(envolvente, ep.ESCALERA_NS, strict=True)]
    k = next(i for i in range(len(ep.ESCALERA_NS)) if all(sostenibles[i:]))
    assert artefacto["derivacion"]["u_ns"] == 5 * envolvente[k]
    assert artefacto["derivacion"]["b_en_u_ns"] == envolvente[k]
    for fila, dispersion, envuelta in zip(
        artefacto["derivacion"]["curva"], dispersiones, envolvente, strict=True
    ):
        assert fila["dispersion_ns"] == dispersion
        assert fila["envolvente_ns"] == envuelta


def test_todos_los_controles_bloqueantes_pasan(artefacto: dict[str, Any]) -> None:
    controles = artefacto["controles_internos"]
    assert set(controles) == set(ep.CONTROLES_BLOQUEANTES)
    assert all(controles[c] is True for c in ep.CONTROLES_BLOQUEANTES)
    assert len(ep.CONTROLES_BLOQUEANTES) == 23


def test_el_artefacto_cita_las_evidencias_anteriores_intactas(artefacto: dict[str, Any]) -> None:
    citadas = artefacto["preinscripcion"]["blobs_evidencias_anteriores"]
    assert citadas == dict(ep.EVIDENCIAS_ANTERIORES)
    assert len(citadas) == 4
    for ruta, blob in ep.EVIDENCIAS_ANTERIORES.items():
        assert ep.blob_git((RAIZ / ruta).read_bytes()) == blob, ruta
    assert artefacto["custodia"]["evidencias_anteriores_intactas"] is True
    assert artefacto["metodo"]["no_sustituye_evidencia"] is True


def test_la_banda_publicada_de_cada_magnitud_sale_de_la_envolvente(
    artefacto: dict[str, Any],
) -> None:
    envolvente = {f["escala_ns"]: f["envolvente_ns"] for f in artefacto["derivacion"]["curva"]}
    u = artefacto["derivacion"]["u_ns"]
    for entrada in artefacto["regimenes_por_percentil"]:
        if entrada.get("resultado") == ep.NO_EVALUABLE:
            continue
        for percentil, clave_banda in (("p50", "banda_p50_ns"), ("p95", "banda_p95_ns")):
            minimo = entrada[f"min_{percentil}_ns"]
            if minimo >= u:
                assert entrada[percentil] == ep.REGIMEN_RELATIVO
                assert entrada[clave_banda] is None
            else:
                assert entrada[percentil] == ep.REGIMEN_ABSOLUTO
                escalon = next(s for s in ep.ESCALERA_NS if s >= minimo)
                assert entrada[clave_banda] == envolvente[escalon]


def test_la_banda_del_artefacto_nunca_se_estrecha(artefacto: dict[str, Any]) -> None:
    curva = artefacto["derivacion"]["curva"]
    valores = [f["envolvente_ns"] for f in curva]
    assert valores == sorted(valores)
    assert artefacto["controles_internos"]["banda_no_decreciente"] is True


def test_las_dos_listas_de_veredicto_son_la_misma(artefacto: dict[str, Any]) -> None:
    assert (
        artefacto["clasificacion_diagnostica_linea_base"]["magnitudes"]
        == artefacto["regimenes_por_percentil"]
    )


def test_no_se_publica_ningun_valor_si_el_arbol_esta_sucio(tmp_path: Path) -> None:
    salida = tmp_path / "envolvente.json"
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=salida,
        dependencias=dependencias_de_prueba(entorno=entorno_de_prueba(limpio=False)),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("sucio" in f for f in fallos)
    assert not salida.exists()


def test_no_se_sobrescribe_una_salida_existente(tmp_path: Path) -> None:
    salida = tmp_path / "envolvente.json"
    salida.write_text("evidencia ajena", encoding="utf-8")
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO, salida=salida, dependencias=dependencias_de_prueba()
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("ya existe" in f for f in fallos)
    assert salida.read_text(encoding="utf-8") == "evidencia ajena"


def test_una_evidencia_anterior_alterada_bloquea_la_corrida(tmp_path: Path) -> None:
    ruta = "artifacts/adr002_tolerances/suelo_medicion_v0.2.json"
    entorno = entorno_de_prueba(sobrescribir={ruta: b"[]"})
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "envolvente.json",
        dependencias=dependencias_de_prueba(entorno=entorno),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("evidencia anterior alterada" in f for f in fallos)


def test_el_registro_alterado_bloquea_la_corrida(tmp_path: Path) -> None:
    entorno = entorno_de_prueba(sobrescribir={f"docs/architecture/{ep.REGISTRO}": b"fila cambiada"})
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "envolvente.json",
        dependencias=dependencias_de_prueba(entorno=entorno),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("documento de referencia alterado" in f for f in fallos)


def test_un_boot_id_distinto_bloquea_la_corrida(tmp_path: Path) -> None:
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "envolvente.json",
        dependencias=dependencias_de_prueba(boot_final="otro-boot"),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("boot_id_estable" in f for f in fallos)


def test_unidades_distintas_entre_procesos_bloquean_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    escala = str(ep.ESCALERA_NS[-1])
    resultados[2]["escalas"][ep.FAMILIA_CPU][escala]["unidades"] += 1
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "envolvente.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("unidades_identicas" in f for f in fallos)


def test_una_incidencia_registrada_bloquea_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    resultados[3]["incidencias"] = ["canon_1_fila no devolvio exactamente una fila"]
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "envolvente.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("sin_filtrado" in f for f in fallos)


def test_deriva_intraproceso_bloquea_la_corrida(tmp_path: Path) -> None:
    plan = plan_sintetico()
    resultados = [deepcopy(dict(r)) for r in resultados_sinteticos(plan)]
    resultados[1]["referencia"] = {
        "vueltas": ep.VUELTAS_REFERENCIA,
        "p50_inicio_ns": 300_000,
        "p50_mitad_ns": 360_000,
        "p50_final_ns": 450_000,
    }
    codigo, fallos = corrida.ejecutar_corrida(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "envolvente.json",
        dependencias=dependencias_de_prueba(resultados=resultados),
    )
    assert codigo == corrida.CODIGO_BLOQUEADO
    assert any("estabilidad_intraproceso" in f for f in fallos)


def test_un_ejecutor_que_falla_no_deja_artefacto(tmp_path: Path) -> None:
    salida = tmp_path / "envolvente.json"

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


def test_la_escritura_no_destruye_un_fichero_ajeno(tmp_path: Path) -> None:
    salida = tmp_path / "envolvente.json"
    salida.write_text("evidencia ajena", encoding="utf-8")
    with pytest.raises(FileExistsError):
        corrida.escribir_json_atomico(salida, {"a": 1})
    assert salida.read_text(encoding="utf-8") == "evidencia ajena"
    assert list(tmp_path.iterdir()) == [salida]


def test_la_escritura_rechaza_valores_no_json(tmp_path: Path) -> None:
    salida = tmp_path / "envolvente.json"
    with pytest.raises(ValueError, match="Out of range float"):
        corrida.escribir_json_atomico(salida, {"a": float("nan")})
    assert not salida.exists()
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------
# NO_EVALUABLE de extremo a extremo
# --------------------------------------------------------------------------


def test_una_corrida_sin_cruce_publica_no_evaluable_sin_inventar_nada(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = artefacto_no_evaluable
    assert esquema.fallos_banda_envolvente(doc) == []
    der = doc["derivacion"]
    assert der["resultado"] == ep.NO_EVALUABLE
    assert der["u_ns"] is None
    assert der["b_en_u_ns"] is None
    assert ep.MOTIVO_SIN_CRUCE in der["motivo_no_evaluable"]
    assert all(not fila["sostenible"] for fila in der["curva"])
    for entrada in doc["regimenes_por_percentil"]:
        assert entrada["resultado"] == ep.NO_EVALUABLE
        assert entrada["motivo"] == ep.MOTIVO_UMBRAL_NO_RESUELTO
    controles = doc["controles_internos"]
    fallidos = [c for c in ep.CONTROLES_BLOQUEANTES if controles[c] is not True]
    assert fallidos == list(ep.CONTROLES_QUE_EXIGEN_UMBRAL)


def test_el_validador_exige_motivo_cuando_no_hay_cruce(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = deepcopy(artefacto_no_evaluable)
    doc["derivacion"]["motivo_no_evaluable"] = ""
    assert any("motivo explicito" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_publicar_u_sin_cruce(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = deepcopy(artefacto_no_evaluable)
    doc["derivacion"]["u_ns"] = 900_000
    doc["derivacion"]["b_en_u_ns"] = 180_000
    doc["derivacion"]["resultado"] = "RESUELTO"
    assert any(
        "no coincide con el cruce recomputado" in f for f in esquema.fallos_banda_envolvente(doc)
    )


def test_no_evaluable_no_absuelve_otros_controles(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = deepcopy(artefacto_no_evaluable)
    doc["controles_internos"]["custodia_verificada"] = False
    assert any(
        "no absuelve controles bloqueantes" in f for f in esquema.fallos_banda_envolvente(doc)
    )


def test_sin_umbral_no_se_puede_declarar_la_continuidad(
    artefacto_no_evaluable: dict[str, Any],
) -> None:
    doc = deepcopy(artefacto_no_evaluable)
    doc["controles_internos"]["continuidad_exacta_en_u"] = True
    assert any(
        "no puede declararse satisfecho sin umbral" in f
        for f in esquema.fallos_banda_envolvente(doc)
    )


# --------------------------------------------------------------------------
# Validador: mutaciones
# --------------------------------------------------------------------------


def _mutado(artefacto: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(artefacto))


def test_el_validador_es_total_y_nunca_lanza() -> None:
    basuras: tuple[Any, ...] = (None, [], "texto", 3, {"documento": object()})
    for basura in basuras:
        assert esquema.fallos_banda_envolvente(basura)


def test_el_validador_exige_todas_las_secciones(artefacto: dict[str, Any]) -> None:
    for seccion in esquema.SECCIONES_OBLIGATORIAS:
        doc = _mutado(artefacto)
        del doc[seccion]
        assert any(seccion in f for f in esquema.fallos_banda_envolvente(doc)), seccion


def test_el_validador_rechaza_identidad_alterada(artefacto: dict[str, Any]) -> None:
    for campo, valor in (
        ("version_esquema", "otra"),
        ("protocolo", "otro.md"),
        ("registro", "otro.md"),
        ("paquete", "otro"),
        ("estado", "APROBADO"),
    ):
        doc = _mutado(artefacto)
        doc[campo] = valor
        assert esquema.fallos_banda_envolvente(doc), campo


def test_el_validador_rechaza_una_u_inventada(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["u_ns"] = 700_000
    assert any(
        "no coincide con el cruce recomputado" in f for f in esquema.fallos_banda_envolvente(doc)
    )


def test_el_validador_rechaza_una_envolvente_maquillada(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["curva"][0]["envolvente_ns"] = 1
    assert any("curva no coincide" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_una_banda_por_magnitud_maquillada(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    for entrada in doc["regimenes_por_percentil"]:
        if entrada.get("banda_p95_ns") is not None:
            entrada["banda_p95_ns"] += 1
            break
    else:  # pragma: no cover - la clasificacion siempre trae una absoluta
        pytest.skip("no hay magnitudes en regimen absoluto")
    assert any("la envolvente da" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_un_percentil_incoherente(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["p95_ns"] += 1
    assert any("p95_ns publicado" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_muestras_negativas_o_recortadas(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["muestras_ns"][0] = -1
    assert any("negativas" in f for f in esquema.fallos_banda_envolvente(doc))
    doc = _mutado(artefacto)
    doc["escalas"][0]["muestras_ns"] = doc["escalas"][0]["muestras_ns"][:10]
    assert esquema.fallos_banda_envolvente(doc)


def test_el_validador_exige_once_procesos_por_escala(artefacto: dict[str, Any]) -> None:
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
    assert any("procesos distintos" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_unidades_divergentes(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["escalas"][0]["unidades"] += 1
    assert any("no son equivalentes" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_una_calibracion_incoherente(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["calibracion"][ep.FAMILIA_CPU]["coste_referencia_ns"] = COSTE_CPU_NS * 2
    assert any(
        "no salen de la calibracion publicada" in f for f in esquema.fallos_banda_envolvente(doc)
    )
    doc = _mutado(artefacto)
    doc["calibracion"][ep.FAMILIA_CANON]["muestras_ns"][10] += 5
    assert any("no es el P50 de sus muestras" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_un_sm_maquillado(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["sm_ns"] = 1
    assert any("sm_ns" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_un_regimen_a_conveniencia(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    for entrada in doc["regimenes_por_percentil"]:
        if entrada.get("p95") == ep.REGIMEN_ABSOLUTO:
            entrada["p95"] = ep.REGIMEN_RELATIVO
            break
    assert any("corresponde" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_eludir_la_guarda_de_instrumento(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["derivacion"]["sm_ns"] = 10**12
    assert any("guarda de dominancia se eludio" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_publicar_con_controles_fallidos(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["controles_internos"]["custodia_verificada"] = False
    assert any("controles bloqueantes fallidos" in f for f in esquema.fallos_banda_envolvente(doc))
    doc = _mutado(artefacto)
    del doc["controles_internos"]["banda_no_decreciente"]
    assert any("control bloqueante ausente" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_negaciones_alteradas(artefacto: dict[str, Any]) -> None:
    assert len(esquema.NEGACIONES_OBLIGATORIAS) == 7
    for clave in esquema.NEGACIONES_OBLIGATORIAS:
        doc = _mutado(artefacto)
        doc["no_autoriza"][clave] = True
        assert any(clave in f for f in esquema.fallos_banda_envolvente(doc))
        doc = _mutado(artefacto)
        del doc["no_autoriza"][clave]
        assert any(clave in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_custodia_incompleta(artefacto: dict[str, Any]) -> None:
    for clave in (
        "diff_preinscritos_vacio",
        "sha_a_es_ancestro",
        "reverificada_tras_medir",
        "evidencias_anteriores_intactas",
        "registro_actualizado_intacto",
    ):
        doc = _mutado(artefacto)
        doc["custodia"][clave] = False
        assert esquema.fallos_banda_envolvente(doc), clave


def test_el_validador_exige_forma_de_sha(artefacto: dict[str, Any]) -> None:
    for ruta, valor in (
        (("preinscripcion", "commit_a"), ""),
        (("preinscripcion", "head_en_ejecucion"), "no-es-un-sha"),
        (("custodia", "head"), "0" * 39),
    ):
        doc = _mutado(artefacto)
        doc[ruta[0]][ruta[1]] = valor
        assert any("SHA" in f for f in esquema.fallos_banda_envolvente(doc)), ruta


def test_el_validador_rechaza_blobs_de_referencia_alterados(artefacto: dict[str, Any]) -> None:
    for campo in ("blob_protocolo", "blob_registro", "blob_linea_base"):
        doc = _mutado(artefacto)
        doc["preinscripcion"][campo] = "0" * 40
        assert esquema.fallos_banda_envolvente(doc), campo
    doc = _mutado(artefacto)
    doc["preinscripcion"]["blobs_evidencias_anteriores"] = {}
    assert any("blobs_evidencias_anteriores" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_pids_ajenos(artefacto: dict[str, Any]) -> None:
    for seccion in ("escalas", "sondas_unitarias"):
        doc = _mutado(artefacto)
        doc[seccion][0]["pid"] = 12345
        assert any(
            "no son los procesos declarados" in f for f in esquema.fallos_banda_envolvente(doc)
        ), seccion


def test_el_validador_rechaza_una_tabla_de_progresion_inventada(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    fila = doc["diagnosticos"][ep.DIAG_PROGRESION]["por_proceso"][0]["filas"][0]
    fila["p50_menor_ns"] *= 3
    fila["p50_mayor_ns"] *= 3
    assert any("no coincide con la recomputada" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_recomputa_la_holgura(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["diagnosticos"][ep.DIAG_HOLGURA]["por_escalon"][0]["banda_ns"] += 1
    assert any(
        "holgura_de_banda.por_escalon no coincide" in f
        for f in esquema.fallos_banda_envolvente(doc)
    )


def test_el_validador_rechaza_deriva_publicada_como_estable(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["diagnosticos"][ep.DIAG_REFERENCIA]["por_proceso"][0] = {
        "vueltas": ep.VUELTAS_REFERENCIA,
        "p50_inicio_ns": 100,
        "p50_mitad_ns": 200,
        "p50_final_ns": 300,
    }
    assert any("deriva o throttling" in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_incidencias_y_cargas_ausentes(artefacto: dict[str, Any]) -> None:
    doc = _mutado(artefacto)
    doc["entorno"]["incidencias"] = ["algo raro"]
    assert any("incidencias" in f for f in esquema.fallos_banda_envolvente(doc))
    doc = _mutado(artefacto)
    doc["entorno"]["carga_por_proceso"] = {}
    assert any(
        "no cubre exactamente los procesos declarados" in f
        for f in esquema.fallos_banda_envolvente(doc)
    )


def test_el_validador_fija_la_cita_historica_de_los_paquetes_anteriores(
    artefacto: dict[str, Any],
) -> None:
    contraste = artefacto["contraste_metodos_anteriores"]
    assert contraste["u_paquete_05_ns"] == 48_790
    assert contraste["b_paquete_05_ns"] == 9_758
    assert contraste["u_paquete_06_ns"] == 100_000_000
    assert contraste["b_paquete_06_ns"] == 20_000_000
    for campo in ("u_paquete_05_ns", "b_paquete_06_ns"):
        doc = _mutado(artefacto)
        doc["contraste_metodos_anteriores"][campo] += 1
        assert any(campo in f for f in esquema.fallos_banda_envolvente(doc))


def test_el_validador_rechaza_un_plan_que_no_es_el_preinscrito(
    artefacto: dict[str, Any],
) -> None:
    for campo, valor in (
        ("procesos", 5),
        ("rondas", 2),
        ("semilla", 1),
        ("warmup_por_escala", 0),
        ("n_unitaria", 99),
        ("escalera_ns", [1, 2]),
        ("orden", []),
    ):
        doc = _mutado(artefacto)
        doc["plan"][campo] = valor
        assert esquema.fallos_banda_envolvente(doc), campo


def test_el_validador_rechaza_importar_una_clasificacion_de_tol_207(
    artefacto: dict[str, Any],
) -> None:
    doc = _mutado(artefacto)
    doc["clasificacion_entorno"] = "ENVOLVENTE_REPRODUCIBLE"
    assert any("TOL-207" in f for f in esquema.fallos_banda_envolvente(doc))


# --------------------------------------------------------------------------
# Integridad de la preinscripcion
# --------------------------------------------------------------------------


def test_los_seis_ficheros_preinscritos_existen_y_parsean() -> None:
    assert len(ep.ARCHIVOS_PREINSCRITOS) == 6
    for ruta in ep.ARCHIVOS_PREINSCRITOS:
        completa = RAIZ / ruta
        assert completa.is_file(), ruta
        if completa.suffix == ".py":
            ast.parse(completa.read_text(encoding="utf-8"), filename=str(completa))


def test_este_fichero_esta_entre_los_preinscritos() -> None:
    relativa = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    assert relativa in ep.ARCHIVOS_PREINSCRITOS


def test_el_acta_de_gobierno_esta_preinscrita() -> None:
    acta = "docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md"
    assert acta in ep.ARCHIVOS_PREINSCRITOS
    assert (RAIZ / acta).is_file()


def test_las_cuatro_evidencias_anteriores_siguen_intactas() -> None:
    assert len(ep.EVIDENCIAS_ANTERIORES) == 4
    for ruta, blob in ep.EVIDENCIAS_ANTERIORES.items():
        completa = RAIZ / ruta
        assert completa.is_file(), ruta
        assert ep.blob_git(completa.read_bytes()) == blob, ruta


def test_los_documentos_de_referencia_estan_intactos() -> None:
    assert ep.fallos_documentos_de_referencia(entorno_de_prueba()) == ()
    for ruta, blob in ep.BLOBS_CORPUS_CONGELADO.items():
        assert ep.blob_git((RAIZ / ruta).read_bytes()) == blob, ruta


def test_importar_los_modulos_no_mide_ni_escribe(tmp_path: Path) -> None:
    guion = (
        f"import sys; sys.path.insert(0, {str(RAIZ)!r});"
        "from experiments.adr002.tolerances import envelope_protocol,"
        " run_envelope, schema_envelope_v0_1;"
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
