"""Preinscripcion normativa del suelo multiescala (ADR002-TOL-209, sucesor).

Este modulo se congela ANTES de medir. Sustituye el METODO de determinacion
de ``B`` y ``U`` del paquete 05 sin invalidar su evidencia, que se conserva
intacta y cuyo blob este modulo verifica.

No mide nada. No abre ficheros. No ejecuta nada al importarse.

POR QUE EXISTE UN SUCESOR
=========================

El paquete 05 derivo ``B`` de la dispersion absoluta observada en UNA sola
escala —la mas barata alcanzable, ~21 us— y despues resolvio ``U = B / 0,20``.
Esa derivacion presupone, sin decirlo, que la dispersion absoluta del suelo
es CONSTANTE frente a la magnitud medida. La evidencia versionada la refuta:
la razon dispersion/magnitud decrece de forma monotona al crecer la escala
(0,455 a 21 us; 0,33-0,36 entre 188 y 736 us; 0,12-0,16 a 126 ms). Medir el
suelo solo en la escala mas barata produce por tanto una ``B`` minuscula y
una ``U`` minuscula.

El resultado contradice al Registro v0.4, que en la fila ``ADR002-TOL-107``
dice literalmente, sobre magnitudes de 0,14-1,0 ms: «un 36 % son 0,27 ms
absolutos — es el suelo de medicion, no inestabilidad del sistema. **A esa
escala la comparacion debe hacerse en valor absoluto**». Con ``U = 48,79 us``
esas magnitudes caen en regimen RELATIVO: exactamente lo contrario.

La misma fila exige que el fundamento del umbral sea «el suelo de medicion
medido del entorno». El defecto del paquete 05 no fue medir mal: fue medir
el suelo en un solo punto y extrapolarlo como si fuese plano.

METODO SUCESOR: PUNTO FIJO MULTIESCALA
======================================

En lugar de suponer ``D`` constante y despejar ``U``, se mide ``D(s)`` a
trece escalas y se resuelve el punto fijo

    D(U) / U <= 0,20    con    B := U / 5

sobre una escalera de escalas NOMINALES preinscritas. ``U`` es la escala
medida mas pequena desde la cual la condicion se sostiene para ella y para
todas las escalas mayores; nunca un valor interpolado. Es la misma
disciplina que el §4.1 del protocolo impone a los percentiles, aplicada a
la seleccion de escala.

Derivacion del criterio, desde el proposito declarado de TOL-107: el
regimen absoluto existe porque por debajo de cierta magnitud un criterio
relativo del 20 % exige lo imposible —el propio suelo excede ese 20 %—.
Luego el umbral es, por definicion, la magnitud desde la que el 20 %
relativo es alcanzable: ``D(M) <= 0,20 M``. Y ``B`` es ``0,20 U`` porque en
``M = U`` los dos regimenes deben coincidir; con ``m = 1``, ``m * B`` iguala
exactamente el ``20 %`` de la frontera.

El factor ``0,20`` NO se elige aqui: es el objetivo relativo ya congelado
del Registro v0.4 (fila TOL-107). El metodo sucesor no lo toca. Tampoco
toca ``m = 1``, unico valor que preserva la continuidad exacta.

Si ``D`` fuese constante, el punto fijo devuelve ``U = 5 * D``, es decir el
metodo del paquete 05 como caso particular. El sucesor lo generaliza, no lo
contradice.

QUE HACE QUE ``D(s)`` NO SE PROMEDIE HASTA DESAPARECER
=====================================================

``D(s)`` se construye como ``max - min`` de un percentil ENTRE PROCESOS
independientes, no como desviacion dentro de un proceso. Lo que separa a
dos procesos equivalentes son diferencias sistematicas —estado de cache,
frecuencia, afinidad, poblacion de la page cache— comunes a todo el trabajo
de la ventana medida, y por tanto proporcionales a ella. El promediado
interno solo cancela el jitter independiente por unidad de trabajo. Por eso
la construccion del §6.1 del protocolo, que es exactamente esta, mide lo
que TOL-107 llama «variacion entre ejecuciones equivalentes» y no la
disuelve al crecer la escala.

NEUTRALIDAD
===========

Ninguna sonda usa FTS5, ``rank()`` ni operacion propia de ningun candidato.
Las dos familias son:

- ``cpu``: trabajo aritmetico puro en el interprete;
- ``canon``: consultas por clave primaria sobre la tabla canonica de ADR-001.

``D(s)`` es el PEOR caso entre familias y entre P50 y P95: un suelo
subestimado exigiria lo imposible, de modo que la direccion conservadora es
la unica admisible.

Las magnitudes historicas de FTS5 y ``rank()`` se emplean UNICAMENTE como
contraste diagnostico posterior, jamas para determinar ``B`` ni ``U``.

Fuentes normativas: protocolo aprobado (blob
``c298a6b804309a78062f79b6341adfea2374ce56``) §2, §3, §4, §5, §6, §7, §8;
Registro v0.4 fila ``ADR002-TOL-107`` y §9.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

# --------------------------------------------------------------------------
# Identidad
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "suelo-multiescala-0.1"
ESTADO: Final = "PROPUESTO · PREINSCRIPCION SUCESORA"
ESTADO_EVIDENCIA: Final = "PROPUESTO · SUELO MULTIESCALA MEDIDO — NO APRUEBA TOL-209"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_06_TOL209_SUELO_MULTIESCALA_v0.1"
PROTOCOLO: Final = "SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md"
BLOB_PROTOCOLO_APROBADO: Final = "c298a6b804309a78062f79b6341adfea2374ce56"

RUTA_LINEA_BASE: Final = "artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json"

#: Evidencia del metodo anterior. Se CONSERVA intacta: el sucesor no la
#: borra ni la reescribe, solo corrige el metodo de determinacion de B y U.
#: Los blobs se comprueban byte a byte en cada corrida.
EVIDENCIA_ANTERIOR: Final = "artifacts/adr002_tolerances/suelo_medicion_v0.1.json"
INFORME_ANTERIOR: Final = "artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md"

BLOBS_EVIDENCIA_ANTERIOR: Final[Mapping[str, str]] = {
    EVIDENCIA_ANTERIOR: "899ecee82bf0c62408b43c732fbbb49304eea119",
    INFORME_ANTERIOR: "e2b075499f89f71a49c33325298ae9f4bc1f7076",
}

#: Valores publicados por el metodo anterior. Se citan como HECHO historico
#: verificable, jamas como referencia normativa: el sucesor no los usa para
#: nada salvo para explicar por que existe.
U_ANTERIOR_NS: Final = 48_790
B_ANTERIOR_NS: Final = 9_758

ARCHIVOS_PREINSCRITOS: Final[tuple[str, ...]] = (
    ("docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_06_TOL209_SUELO_MULTIESCALA_v0.1.md"),
    "experiments/adr002/tolerances/floor_scale_probes.py",
    "experiments/adr002/tolerances/floor_scale_protocol.py",
    "experiments/adr002/tolerances/run_floor_scale.py",
    "experiments/adr002/tolerances/schema_floor_scale_v0_1.py",
    "experiments/adr002/tolerances/test_adr002_floor_scale.py",
)

#: Participan por importacion sin ser ficheros nuevos: su blob se registra
#: igual, porque un cambio en ellos cambiaria lo que se mide.
ARCHIVOS_HEREDADOS: Final[Mapping[str, str]] = {
    "experiments/adr002/tolerances/corpus.py": "90c5118e045676d29998182de60a88a1a2b62443",
}

BLOBS_CORPUS_CONGELADO: Final[Mapping[str, str]] = {
    "experiments/adr002/benchmark/conformance_corpus_v0_4.json": (
        "c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48"
    ),
    "experiments/adr002/benchmark/cases_v0_4.json": "072753b96f4162fe88ce9c96660296349225c7be",
    "experiments/adr002/benchmark/references_v0_4.json": (
        "3fc9a63705144bf543266de129e17a17ab31c568"
    ),
    "experiments/adr002/benchmark/pdp_cases_v0_3.json": "2eee45a04dee3d72f52ad00dfd46023d7c5e2199",
    "experiments/adr002/benchmark/pdp_harness_rules_v0_2.json": (
        "86e4f4ea6b4af3d445ec0f71c9772b46751a202b"
    ),
    "experiments/adr002/benchmark/performance_corpus_v0_2.json": (
        "4e9e2746e49b158a43eda7826b47c78c41b36e90"
    ),
    "experiments/adr002/benchmark/benchmark_manifest_v0_4.json": (
        "fa9a2f2b5d8d65aed811f039b2b279c5350d2132"
    ),
}

# --------------------------------------------------------------------------
# Escalera nominal preinscrita
# --------------------------------------------------------------------------
#
# Progresion 1-2-5 sobre cuatro ordenes de magnitud, de 10 us a 100 ms.
# Trece escalones. El rango se fija para abarcar con margen todas las
# magnitudes que la evidencia versionada de la linea base publica (0,14 ms a
# 128 ms), sin que ninguna de ellas determine escala alguna: son escalas de
# trabajo sintetico neutral.
#
# Se elige 1-2-5 y no una decada por escalon porque ``U`` es una escala
# MEDIDA: la resolucion de la escalera es la resolucion de ``U``. Una
# escalera por decadas dejaria a ``U`` con un factor 10 de indeterminacion.
#
# Cada escala es multiplo de 5 para que ``B = U / 5`` sea exacto en enteros.

ESCALERA_NS: Final[tuple[int, ...]] = (
    10_000,  # 10 us
    20_000,
    50_000,
    100_000,  # 100 us
    200_000,
    500_000,
    1_000_000,  # 1 ms
    2_000_000,
    5_000_000,
    10_000_000,  # 10 ms
    20_000_000,
    50_000_000,
    100_000_000,  # 100 ms
)

FAMILIA_CPU: Final = "cpu"
FAMILIA_CANON: Final = "canon"
FAMILIAS: Final[tuple[str, ...]] = (FAMILIA_CPU, FAMILIA_CANON)

#: Sondas de suelo unitario: dan SM, el nivel del instrumento. Se conservan
#: del paquete 05 porque su significado no estaba en discusion.
SONDA_VACIA: Final = "D_vacia"
SONDA_CANON_0: Final = "canon_0_filas"
SONDA_CANON_1: Final = "canon_1_fila"
SONDAS_UNITARIAS: Final[tuple[str, ...]] = (SONDA_VACIA, SONDA_CANON_0, SONDA_CANON_1)

#: Diagnosticos publicados. Ninguno modifica B ni U.
DIAG_REFERENCIA: Final = "referencia_intraproceso"
DIAG_PROGRESION: Final = "progresion_por_escala"
DIAG_CURVA: Final = "curva_dispersion"
DIAGNOSTICOS: Final[tuple[str, ...]] = (DIAG_REFERENCIA, DIAG_PROGRESION, DIAG_CURVA)

#: Nombres que jamas pueden aparecer en una sonda normativa.
PROHIBIDOS_EN_SONDAS: Final[tuple[str, ...]] = (
    "fts",
    "fts5",
    "rank",
    "bm25",
    "knowledge_fts",
    "message_fts",
    "embedding",
    "vector",
    "adr002-a",
    "adr002-b",
    "adr002-c",
    "adr002-d",
)

# --------------------------------------------------------------------------
# Repeticiones, sesiones y calibracion
# --------------------------------------------------------------------------

#: §3.2: 100 repeticiones cuando el coste es bajo; §3.1: 30 como minimo.
UMBRAL_COSTE_BAJO_NS: Final = 1_000_000
N_COSTE_BAJO: Final = 100
N_COSTE_ALTO: Final = 30
WARMUP_ESCALA: Final = 5

N_UNITARIA: Final = 100
WARMUP_UNITARIA: Final = 5

#: §3.3: al menos cinco sesiones independientes. Aqui, procesos distintos.
PROCESOS_MINIMOS: Final = 5

#: §5.3: semilla del corpus de rendimiento congelado.
SEMILLA: Final = 20260726

#: §5.2 aplicado a sondas: rondas intercaladas, nunca bloques completos.
#: Divide exactamente tanto a 100 como a 30.
RONDAS_ROUND_ROBIN: Final = 5

#: Calibracion: muestras para estimar el coste de la cantidad de referencia
#: de cada familia. La calibracion la hace el proceso PADRE una sola vez y
#: la misma cantidad de trabajo se impone a todos los hijos: TOL-107 mide la
#: variacion entre ejecuciones EQUIVALENTES, y dos ejecuciones que resuelven
#: cantidades de trabajo distintas no son equivalentes.
MUESTRAS_CALIBRACION: Final = 21
WARMUP_CALIBRACION: Final = 5

#: Cantidad de referencia por familia, en unidades de trabajo de la familia.
UNIDADES_REFERENCIA: Final[Mapping[str, int]] = {
    FAMILIA_CPU: 10_000,
    FAMILIA_CANON: 10,
}

#: Tolerancia de calibracion. La magnitud observada de una escala debe caer
#: en [s/2, 2s]. Fuera de banda, la escala se declara mal calibrada y la
#: corrida falla cerrado: no se recalibra al gusto tras ver resultados.
CALIBRACION_MIN_NUM: Final = 1
CALIBRACION_MIN_DEN: Final = 2
CALIBRACION_MAX_FACTOR: Final = 2

#: La comprobacion de progresion solo es exigible donde la cuantizacion del
#: numero entero de unidades es despreciable. Con menos de diez unidades,
#: redondear introduce hasta un 50 % de error en la propia escala nominal y
#: la comprobacion denunciaria un artefacto de la calibracion, no un defecto
#: del instrumento. Se publica la tabla completa; se exige donde procede.
UNIDADES_MINIMAS_PROGRESION: Final = 10

#: Tolerancia de progresion: 1/3. NO puede ser 1/2. El escalon minimo de la
#: escalera es un factor 2, y «el tiempo no crece en absoluto» produce
#: exactamente un desvio del 50 % del valor esperado: con tolerancia 1/2 ese
#: caso —el que la comprobacion existe para denunciar— pasaria justo en la
#: frontera. Con 1/3 un escalon de factor 2 exige una razon medida en
#: [1,33x, 2,67x], holgura sobrada frente al 5 % de error que la cuantizacion
#: puede introducir cuando la progresion es exigible.
TOLERANCIA_PROGRESION_NUM: Final = 1
TOLERANCIA_PROGRESION_DEN: Final = 3

#: Deriva o throttling dentro de un proceso: mismo criterio del paquete 05.
TOLERANCIA_DERIVA_NUM: Final = 3
TOLERANCIA_DERIVA_DEN: Final = 10
VUELTAS_REFERENCIA: Final = 10_000
N_REFERENCIA: Final = 100
WARMUP_REFERENCIA: Final = 5

# --------------------------------------------------------------------------
# Formulas vinculantes
# --------------------------------------------------------------------------

#: Objetivo relativo congelado del Registro v0.4 (fila TOL-107), expresado
#: como fraccion exacta. NO se elige aqui.
OBJETIVO_RELATIVO_NUM: Final = 1
OBJETIVO_RELATIVO_DEN: Final = 5

#: Decision del paquete 05, conservada: unico valor que preserva continuidad.
MARGEN_M: Final = 1

#: B = U / FACTOR_U y U = FACTOR_U * B. Relacion identica a la del paquete
#: 05; lo que cambia es COMO se determina el punto fijo.
FACTOR_U: Final = OBJETIVO_RELATIVO_DEN

REGIMEN_RELATIVO: Final = "relativo"
REGIMEN_ABSOLUTO: Final = "absoluto"
NO_EVALUABLE: Final = "NO_EVALUABLE"


class PercentilInterpoladoError(ValueError):
    """Se intento obtener un percentil por interpolacion (§4.1, §8.5)."""


class SondaNoNeutralError(ValueError):
    """Una sonda normativa nombra FTS5, rank() o un candidato."""


class ProcesosInsuficientesError(ValueError):
    """Menos de cinco procesos independientes (§3.3)."""


class EscaleraInvalidaError(ValueError):
    """La escalera medida no cubre las escalas preinscritas."""


def percentil_ns(ordenadas: Sequence[int], fraccion_num: int, fraccion_den: int) -> int:
    """Percentil por rango mas cercano sobre enteros en nanosegundos.

    Nunca interpola: devuelve siempre una muestra realmente observada
    (§4.1). La fraccion se pasa como par de enteros para que el rango no
    dependa de la representacion binaria de un ``float``.
    """
    if not ordenadas:
        msg = "no hay muestras"
        raise ValueError(msg)
    if fraccion_den <= 0 or fraccion_num <= 0 or fraccion_num > fraccion_den:
        msg = f"fraccion invalida: {fraccion_num}/{fraccion_den}"
        raise ValueError(msg)
    n = len(ordenadas)
    rango = max(1, -(-fraccion_num * n // fraccion_den))
    return ordenadas[min(n - 1, rango - 1)]


def p50_ns(muestras: Sequence[int]) -> int:
    """P50 nearest-rank."""
    return percentil_ns(sorted(muestras), 1, 2)


def p95_ns(muestras: Sequence[int]) -> int:
    """P95 nearest-rank."""
    return percentil_ns(sorted(muestras), 19, 20)


def p99_ns(muestras: Sequence[int]) -> int:
    """P99 nearest-rank."""
    return percentil_ns(sorted(muestras), 99, 100)


def resolucion_percentil(n: int) -> str:
    """Que puede afirmar honestamente un P99 con ``n`` muestras (§4.3, §4.4).

    El ordinal se deriva con la misma aritmetica entera de techo que
    ``percentil_ns``, sin coma flotante.
    """
    if n <= 0:
        msg = "n debe ser positivo"
        raise ValueError(msg)
    rango = max(1, -(-99 * n // 100))
    peores = n - rango + 1
    if peores <= 1:
        return (
            f"con n={n}, el P99 por rango mas cercano coincide con el maximo observado; "
            f"acota la cola, no la caracteriza"
        )
    return f"con n={n}, el P99 corresponde a la {peores}.a peor muestra observada"


def n_para_escala(escala_ns: int) -> int:
    """Repeticiones exigidas por el §3.1/§3.2 segun el coste de la escala."""
    return N_COSTE_BAJO if escala_ns <= UMBRAL_COSTE_BAJO_NS else N_COSTE_ALTO


def pares_de_escalera() -> tuple[tuple[str, int], ...]:
    """Orden canonico ``(familia, escala)``: familias intercaladas por escala."""
    return tuple((familia, escala) for escala in ESCALERA_NS for familia in FAMILIAS)


def comprobar_neutralidad(nombres: Sequence[str]) -> tuple[str, ...]:
    """Ninguna sonda normativa puede nombrar FTS5, rank() ni un candidato."""
    fallos: list[str] = []
    for nombre in nombres:
        minusculas = nombre.lower()
        for prohibido in PROHIBIDOS_EN_SONDAS:
            if prohibido in minusculas:
                fallos.append(f"sonda no neutral: {nombre} contiene '{prohibido}'")
    return tuple(dict.fromkeys(fallos))


def unidades_para_escala(
    escala_ns: int, *, unidades_referencia: int, coste_referencia_ns: int
) -> int:
    """Cuantas unidades de trabajo aproximan la escala nominal ``escala_ns``.

    Redondeo al entero mas cercano en aritmetica entera exacta; nunca menos
    de una unidad. La cuantizacion resultante se declara y se comprueba con
    ``calibracion_en_banda``.
    """
    if unidades_referencia <= 0 or coste_referencia_ns <= 0 or escala_ns <= 0:
        msg = "calibracion invalida: cantidades y costes deben ser positivos"
        raise ValueError(msg)
    numerador = escala_ns * unidades_referencia
    return max(1, (2 * numerador + coste_referencia_ns) // (2 * coste_referencia_ns))


# --------------------------------------------------------------------------
# Medidas
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MedidaEscala:
    """Percentiles de una (familia, escala) en un proceso. Enteros en ns."""

    familia: str
    escala_ns: int
    unidades: int
    pid: int
    n: int
    warmup_descartado: int
    p50: int
    p95: int
    p99: int
    minimo: int
    maximo: int
    media_truncada: int


@dataclass(frozen=True, slots=True)
class MedidaUnitaria:
    """Percentiles de una sonda de suelo unitario en un proceso."""

    sonda: str
    pid: int
    n: int
    warmup_descartado: int
    p50: int
    p95: int
    p99: int
    minimo: int
    maximo: int
    media_truncada: int


def _pids(medidas: Sequence[MedidaEscala], familia: str, escala: int) -> set[int]:
    return {m.pid for m in medidas if m.familia == familia and m.escala_ns == escala}


def comprobar_cobertura(medidas: Sequence[MedidaEscala]) -> None:
    """Toda (familia, escala) preinscrita debe tener >=5 procesos distintos."""
    fallos = comprobar_neutralidad([m.familia for m in medidas])
    if fallos:
        raise SondaNoNeutralError(str(list(fallos)))
    familias = {m.familia for m in medidas}
    if familias - set(FAMILIAS):
        msg = f"familias ajenas a la preinscripcion: {sorted(familias - set(FAMILIAS))}"
        raise EscaleraInvalidaError(msg)
    escalas = {m.escala_ns for m in medidas}
    if escalas - set(ESCALERA_NS):
        msg = f"escalas ajenas a la escalera: {sorted(escalas - set(ESCALERA_NS))}"
        raise EscaleraInvalidaError(msg)
    for escala in ESCALERA_NS:
        for familia in FAMILIAS:
            pids = _pids(medidas, familia, escala)
            if not pids:
                msg = f"falta la sonda {familia}@{escala} ns"
                raise EscaleraInvalidaError(msg)
            if len(pids) < PROCESOS_MINIMOS:
                msg = (
                    f"{familia}@{escala} ns: {len(pids)} procesos distintos; "
                    f"el minimo es {PROCESOS_MINIMOS}"
                )
                raise ProcesosInsuficientesError(msg)


def dispersion_de_familia(
    medidas: Sequence[MedidaEscala], familia: str, escala_ns: int, percentil: str
) -> int:
    """``max - min`` entre procesos de un percentil de una (familia, escala)."""
    if percentil not in ("p50", "p95"):
        msg = f"percentil no normativo: {percentil}"
        raise ValueError(msg)
    seleccion = [m for m in medidas if m.familia == familia and m.escala_ns == escala_ns]
    if not seleccion:
        msg = f"falta la sonda {familia}@{escala_ns} ns"
        raise EscaleraInvalidaError(msg)
    valores = [int(getattr(m, percentil)) for m in seleccion]
    return max(valores) - min(valores)


def dispersion_de_escala(medidas: Sequence[MedidaEscala], escala_ns: int) -> int:
    """``D(s)``: peor dispersion absoluta entre procesos en la escala ``s``.

    Peor caso sobre las dos familias y sobre P50 y P95, con la misma
    construccion de peor par que el §6.1 del protocolo, pero en valor
    absoluto en lugar de razon. El peor caso es la unica direccion admisible:
    un suelo subestimado exige a los candidatos lo que el entorno no permite.
    """
    peor = 0
    for familia in FAMILIAS:
        for percentil in ("p50", "p95"):
            peor = max(peor, dispersion_de_familia(medidas, familia, escala_ns, percentil))
    return peor


def sostenible_en_escala(dispersion_ns: int, escala_ns: int) -> bool:
    """``D(s) / s <= 0,20`` en aritmetica entera exacta."""
    return OBJETIVO_RELATIVO_DEN * dispersion_ns <= OBJETIVO_RELATIVO_NUM * escala_ns


def razon_por_mil(dispersion_ns: int, escala_ns: int) -> int:
    """``D(s) / s`` en milesimas, truncado. Entero: el artefacto no usa coma flotante."""
    if escala_ns <= 0:
        msg = "la escala debe ser positiva"
        raise ValueError(msg)
    return 1000 * dispersion_ns // escala_ns


@dataclass(frozen=True, slots=True)
class PuntoFijo:
    """Resultado de resolver el punto fijo sobre la escalera medida."""

    dispersiones: tuple[tuple[int, int], ...]
    sostenibles: tuple[tuple[int, bool], ...]
    u: int | None
    b: int | None
    m: int
    motivo_no_evaluable: str | None

    @property
    def evaluable(self) -> bool:
        return self.u is not None and self.b is not None


def resolver_punto_fijo(medidas: Sequence[MedidaEscala]) -> PuntoFijo:
    """Resuelve ``U`` y ``B`` sobre la escalera preinscrita.

    ``U`` es la escala medida mas pequena desde la cual la condicion
    ``5 * D(s) <= s`` se cumple para ella y para TODAS las escalas mayores.
    Exigir la monotonia evita adoptar un cruce accidental: si la condicion
    se cumple en una escala y falla en una mayor, el ruido no decrece con la
    escala y el punto fijo no esta determinado.

    ``B := U / FACTOR_U``, exacto porque cada escala es multiplo de 5. Asi
    ``B`` iguala el 20 % de la frontera —continuidad exacta con el regimen
    relativo en ``M = U``— y a la vez cubre el ruido demostrado en esa
    escala, porque la condicion de seleccion garantiza ``D(U) <= U / 5``.

    Si ninguna escala satisface la condicion de forma sostenida, devuelve
    ``NO_EVALUABLE`` sin inventar ningun valor.
    """
    comprobar_cobertura(medidas)

    dispersiones = tuple((s, dispersion_de_escala(medidas, s)) for s in ESCALERA_NS)
    sostenibles = tuple((s, sostenible_en_escala(d, s)) for s, d in dispersiones)
    mapa = dict(sostenibles)

    elegida: int | None = None
    for indice, escala in enumerate(ESCALERA_NS):
        if all(mapa[mayor] for mayor in ESCALERA_NS[indice:]):
            elegida = escala
            break

    if elegida is None:
        fallidas = [s for s, ok in sostenibles if not ok]
        motivo = (
            "ninguna escala medida sostiene D(s) <= s/5 para ella y todas las mayores; "
            f"escalas que fallan: {fallidas}"
        )
        return PuntoFijo(
            dispersiones=dispersiones,
            sostenibles=sostenibles,
            u=None,
            b=None,
            m=MARGEN_M,
            motivo_no_evaluable=motivo,
        )

    if elegida % FACTOR_U != 0:  # pragma: no cover - la escalera es multiplo de 5
        msg = f"escala {elegida} no es multiplo de {FACTOR_U}: B no seria exacto"
        raise EscaleraInvalidaError(msg)

    return PuntoFijo(
        dispersiones=dispersiones,
        sostenibles=sostenibles,
        u=elegida,
        b=elegida // FACTOR_U,
        m=MARGEN_M,
        motivo_no_evaluable=None,
    )


def banda_cubre_el_suelo(punto: PuntoFijo) -> bool:
    """``D(s) <= m * B`` para toda escala medida por debajo de ``U``.

    En el regimen absoluto el criterio es ``(max - min) <= m * B``. Si el
    propio suelo excediera esa banda en alguna escala del regimen absoluto,
    el criterio seria inalcanzable tambien alli y la puerta exigiria lo
    imposible. Con ``D`` no decreciente la condicion se cumple por
    construccion —``D(s) <= D(U) <= U/5 = B``—; la comprobacion existe para
    denunciar una escalera no monotona en vez de publicarla en silencio.
    """
    if punto.b is None or punto.u is None:
        return False
    limite = MARGEN_M * punto.b
    return all(d <= limite for s, d in punto.dispersiones if s <= punto.u)


def calcular_sm(unitarias: Sequence[MedidaUnitaria]) -> int:
    """``SM``: nivel maximo del instrumento. Guarda de dominancia; no define U.

    Se conserva del paquete 05: es el peor P95 de las sondas de suelo
    unitario sobre todos los procesos.
    """
    fallos = comprobar_neutralidad([m.sonda for m in unitarias])
    if fallos:
        raise SondaNoNeutralError(str(list(fallos)))
    presentes = {m.sonda for m in unitarias}
    faltan = sorted(s for s in SONDAS_UNITARIAS if s not in presentes)
    if faltan:
        msg = f"faltan sondas unitarias: {faltan}"
        raise EscaleraInvalidaError(msg)
    intrusas = sorted(s for s in presentes if s not in SONDAS_UNITARIAS)
    if intrusas:
        msg = f"sondas unitarias ajenas: {intrusas}"
        raise EscaleraInvalidaError(msg)
    for sonda in SONDAS_UNITARIAS:
        pids = {m.pid for m in unitarias if m.sonda == sonda}
        if len(pids) < PROCESOS_MINIMOS:
            msg = f"{sonda}: {len(pids)} procesos distintos; el minimo es {PROCESOS_MINIMOS}"
            raise ProcesosInsuficientesError(msg)
    return max(m.p95 for m in unitarias)


# --------------------------------------------------------------------------
# Seleccion de regimen: identica al paquete 05
# --------------------------------------------------------------------------


def pasa_relativo(minimo: int, maximo: int) -> bool:
    """``(max - min) / min <= 0,20`` en aritmetica entera exacta."""
    if minimo <= 0:
        return False
    return OBJETIVO_RELATIVO_DEN * (maximo - minimo) <= OBJETIVO_RELATIVO_NUM * minimo


def pasa_absoluto(minimo: int, maximo: int, b: int) -> bool:
    """``(max - min) <= m * B``, con ``m = 1``."""
    return (maximo - minimo) <= MARGEN_M * b


def regimen_de_percentil(minimo_del_percentil: int, u: int) -> str:
    """RELATIVO si ``min_s p(s) >= U``; ABSOLUTO en caso contrario."""
    return REGIMEN_RELATIVO if minimo_del_percentil >= u else REGIMEN_ABSOLUTO


@dataclass(frozen=True, slots=True)
class VeredictoPercentil:
    """Regimen y resultado de un percentil concreto."""

    percentil: str
    minimo: int
    maximo: int
    regimen: str
    pasa: bool


@dataclass(frozen=True, slots=True)
class VeredictoMagnitud:
    """Veredicto completo de una magnitud sobre sus sesiones."""

    dominada_por_instrumento: bool
    resultado: str
    por_percentil: tuple[VeredictoPercentil, ...]


class InvarianteVioladoError(ValueError):
    """``min_s P95 < min_s P50`` o combinacion P50 relativo / P95 absoluto."""


def evaluar_magnitud(
    p50_por_sesion: Sequence[int],
    p95_por_sesion: Sequence[int],
    *,
    sm: int,
    b: int,
    u: int,
) -> VeredictoMagnitud:
    """Guarda ``SM`` primero, despues regimen por percentil. Orden normativo."""
    if not p50_por_sesion or not p95_por_sesion:
        msg = "faltan percentiles por sesion"
        raise ValueError(msg)
    if len(p50_por_sesion) != len(p95_por_sesion):
        msg = "numero de sesiones incoherente entre P50 y P95"
        raise ValueError(msg)
    if len(p50_por_sesion) < PROCESOS_MINIMOS:
        msg = f"{len(p50_por_sesion)} sesiones; el minimo es {PROCESOS_MINIMOS}"
        raise ProcesosInsuficientesError(msg)

    min50, max50 = min(p50_por_sesion), max(p50_por_sesion)
    min95, max95 = min(p95_por_sesion), max(p95_por_sesion)

    if min95 < min50:
        msg = f"invariante violado: min_s P95 ({min95}) < min_s P50 ({min50})"
        raise InvarianteVioladoError(msg)

    if min95 < sm:
        return VeredictoMagnitud(
            dominada_por_instrumento=True,
            resultado=NO_EVALUABLE,
            por_percentil=(),
        )

    reg50 = regimen_de_percentil(min50, u)
    reg95 = regimen_de_percentil(min95, u)
    if reg50 == REGIMEN_RELATIVO and reg95 == REGIMEN_ABSOLUTO:
        msg = "combinacion imposible: P50 relativo con P95 absoluto"
        raise InvarianteVioladoError(msg)

    def _evaluar(nombre: str, minimo: int, maximo: int, regimen: str) -> VeredictoPercentil:
        pasa = (
            pasa_relativo(minimo, maximo)
            if regimen == REGIMEN_RELATIVO
            else pasa_absoluto(minimo, maximo, b)
        )
        return VeredictoPercentil(
            percentil=nombre, minimo=minimo, maximo=maximo, regimen=regimen, pasa=pasa
        )

    v50 = _evaluar("P50", min50, max50, reg50)
    v95 = _evaluar("P95", min95, max95, reg95)
    return VeredictoMagnitud(
        dominada_por_instrumento=False,
        resultado="VALIDA" if (v50.pasa and v95.pasa) else "INVALIDA",
        por_percentil=(v50, v95),
    )


def registro_por_percentil(veredicto: VeredictoMagnitud) -> str:
    """Cadena para el campo unico ``Regimen aplicable`` de la ficha aprobada."""
    if veredicto.dominada_por_instrumento:
        return NO_EVALUABLE
    return " · ".join(f"{v.percentil}: {v.regimen}" for v in veredicto.por_percentil)


# --------------------------------------------------------------------------
# Controles internos preinscritos
# --------------------------------------------------------------------------

CONTROLES_BLOQUEANTES: Final[tuple[str, ...]] = (
    "procesos_independientes",
    "pids_distintos",
    "escalera_completa",
    "unidades_identicas",
    "calibracion_en_banda",
    "carga_registrada",
    "boot_id_estable",
    "captura_ambiental_presente",
    "estabilidad_intraproceso",
    "progresion_por_escala",
    "banda_cubre_el_suelo",
    "vectores_crudos_completos",
    "sin_muestras_negativas",
    "sin_filtrado",
    "warmup_separado",
    "sin_redondeo_previo",
    "sondas_neutrales",
    "evidencia_anterior_intacta",
    "custodia_verificada",
)


@dataclass(frozen=True, slots=True)
class ResultadoControles:
    """Resultado agregado de los controles internos preinscritos."""

    fallos: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.fallos


def evaluar_controles(estado: Mapping[str, bool]) -> ResultadoControles:
    """Falla cerrado: un control ausente o distinto de ``True`` es fallido."""
    fallos = tuple(c for c in CONTROLES_BLOQUEANTES if estado.get(c) is not True)
    return ResultadoControles(fallos=fallos)


def calibracion_en_banda(observado_ns: int, nominal_ns: int) -> bool:
    """La magnitud observada debe caer en ``[s/2, 2s]``, en enteros."""
    if observado_ns <= 0 or nominal_ns <= 0:
        return False
    minimo_ok = observado_ns * CALIBRACION_MIN_DEN >= nominal_ns * CALIBRACION_MIN_NUM
    maximo_ok = observado_ns <= nominal_ns * CALIBRACION_MAX_FACTOR
    return minimo_ok and maximo_ok


def escala_progresa(p50_menor: int, escala_menor: int, p50_mayor: int, escala_mayor: int) -> bool:
    """El tiempo medido debe crecer con la escala nominal, no con el corchete.

    Sustituye la comprobacion 1x/2x del paquete 05 por su version
    multiescala y con razon arbitraria: al pasar de ``escala_menor`` a
    ``escala_mayor``, el tiempo medido debe acercarse al mismo factor.
    Comparacion exacta en enteros, sin division:

        |p50_mayor * s_menor - p50_menor * s_mayor| * DEN
            <= p50_menor * s_mayor * NUM

    Tolerancia preinscrita de 1/3: con 1/2, un tiempo que no crece en
    absoluto pasaria justo en la frontera del escalon minimo de factor 2.
    """
    if p50_menor <= 0 or escala_menor <= 0 or escala_mayor <= 0:
        return False
    esperado = p50_menor * escala_mayor
    desvio = abs(p50_mayor * escala_menor - esperado)
    return desvio * TOLERANCIA_PROGRESION_DEN <= esperado * TOLERANCIA_PROGRESION_NUM


def progresion_exigible(unidades_menor: int, unidades_mayor: int) -> bool:
    """La progresion solo se exige donde la cuantizacion es despreciable."""
    return (
        unidades_menor >= UNIDADES_MINIMAS_PROGRESION
        and unidades_mayor >= UNIDADES_MINIMAS_PROGRESION
    )


def referencia_estable(p50_inicio: int, p50_mitad: int, p50_final: int) -> bool:
    """Criterio preinscrito de deriva o throttling dentro de un proceso.

    Inestable si el P50 del trabajo fijo de referencia crece de forma
    estrictamente monotona entre inicio, mitad y final Y el crecimiento
    total supera la tolerancia preinscrita. Aritmetica entera exacta.
    """
    if min(p50_inicio, p50_mitad, p50_final) <= 0:
        return False
    monotono = p50_inicio < p50_mitad < p50_final
    crecimiento_excesivo = (
        p50_final - p50_inicio
    ) * TOLERANCIA_DERIVA_DEN > p50_inicio * TOLERANCIA_DERIVA_NUM
    return not (monotono and crecimiento_excesivo)


# --------------------------------------------------------------------------
# Custodia. Funciones puras e inyectables.
# --------------------------------------------------------------------------


def blob_git(contenido: bytes) -> str:
    """SHA-1 del objeto blob de Git para ``contenido``."""
    cabecera = f"blob {len(contenido)}\0".encode()
    return hashlib.sha1(cabecera + contenido, usedforsecurity=False).hexdigest()


@dataclass(frozen=True, slots=True)
class EntornoCustodia:
    """Operaciones inyectadas para probar la custodia sin repositorio real.

    ``blob_en_commit`` es imprescindible: sin una fuente de verdad
    independiente del arbol de trabajo, comparar el blob del arbol contra
    uno calculado del mismo arbol seria tautologico.
    """

    leer_bytes: Callable[[str], bytes]
    es_ancestro: Callable[[str, str], bool]
    existe_commit: Callable[[str], bool]
    head: Callable[[], str]
    arbol_limpio: Callable[[], bool]
    diff_vacio: Callable[[str, str, Sequence[str]], bool]
    blob_en_commit: Callable[[str, str], str | None]


def fallos_evidencia_anterior(entorno: EntornoCustodia) -> tuple[str, ...]:
    """La evidencia del metodo anterior debe seguir byte a byte donde estaba.

    El sucesor corrige el metodo; no reescribe la historia. Comprobar solo
    la existencia del fichero no bastaria: una reescritura silenciosa lo
    dejaria presente y alterado.
    """
    fallos: list[str] = []
    for ruta, esperado in BLOBS_EVIDENCIA_ANTERIOR.items():
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"la evidencia anterior ha desaparecido o es ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(f"la evidencia anterior fue alterada: {ruta} ({observado} != {esperado})")
    return tuple(fallos)


def verificar_custodia(
    entorno: EntornoCustodia,
    *,
    sha_a: str,
    blobs_preinscritos: Mapping[str, str],
    blobs_heredados: Mapping[str, str],
    blobs_congelados: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Comprueba la cadena preinscripcion -> evidencia y devuelve los fallos."""
    fallos: list[str] = []
    congelados = dict(BLOBS_CORPUS_CONGELADO if blobs_congelados is None else blobs_congelados)

    if not entorno.existe_commit(sha_a):
        return ("commit de preinscripcion inexistente",)

    if not entorno.es_ancestro(sha_a, entorno.head()):
        fallos.append("el commit de preinscripcion no es ancestro de HEAD")

    faltan = [r for r in ARCHIVOS_PREINSCRITOS if r not in blobs_preinscritos]
    if faltan:
        fallos.append(f"blobs preinscritos ausentes: {sorted(faltan)}")

    def _comparar(ruta: str, esperado: str, etiqueta: str) -> None:
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"{etiqueta} ilegible: {ruta}")
            return
        if observado != esperado:
            fallos.append(f"{etiqueta} alterado: {ruta} ({observado} != {esperado})")

    def _comparar_contra_commit(ruta: str, etiqueta: str) -> None:
        """Fuente de verdad independiente: lo que el commit registra."""
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"{etiqueta} ilegible: {ruta}")
            return
        registrado = entorno.blob_en_commit(sha_a, ruta)
        if registrado is None:
            fallos.append(f"{etiqueta} no registrado en el commit de preinscripcion: {ruta}")
        elif observado != registrado:
            fallos.append(
                f"{etiqueta} difiere del commit de preinscripcion: {ruta} "
                f"(arbol {observado} != commit {registrado})"
            )

    for ruta, esperado in blobs_preinscritos.items():
        _comparar(ruta, esperado, "blob preinscrito")
        _comparar_contra_commit(ruta, "blob preinscrito")

    for ruta, esperado in ARCHIVOS_HEREDADOS.items():
        if ruta not in blobs_heredados:
            fallos.append(f"blob heredado ausente: {ruta}")
            continue
        if blobs_heredados[ruta] != esperado:
            fallos.append(f"blob heredado distinto del preinscrito: {ruta}")
        _comparar(ruta, esperado, "modulo heredado")
        _comparar_contra_commit(ruta, "modulo heredado")

    for ruta, esperado in congelados.items():
        _comparar(ruta, esperado, "blob congelado")

    fallos.extend(fallos_evidencia_anterior(entorno))

    if not entorno.diff_vacio(sha_a, entorno.head(), ARCHIVOS_PREINSCRITOS):
        fallos.append("diff no vacio en los ficheros preinscritos entre A y HEAD")

    return tuple(dict.fromkeys(fallos))


def verificar_precondiciones_ejecucion(
    entorno: EntornoCustodia,
    *,
    sha_a: str,
    salida_existe: bool,
) -> tuple[str, ...]:
    """Comprobaciones exigidas ANTES de medir. Falla cerrado."""
    fallos: list[str] = []
    if not entorno.arbol_limpio():
        fallos.append("arbol de trabajo sucio")
    if not entorno.existe_commit(sha_a):
        fallos.append("el commit de preinscripcion no existe")
    elif entorno.head() != sha_a:
        fallos.append(f"HEAD ({entorno.head()}) distinto del commit de preinscripcion ({sha_a})")
    if salida_existe:
        fallos.append("la ruta de salida ya existe")
    return tuple(fallos)
