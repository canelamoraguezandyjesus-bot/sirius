"""Preinscripcion normativa de la banda envolvente (ADR002-TOL-209, paquete 07).

Este modulo se congela ANTES de medir. Materializa la decision de gobierno
recogida en ``SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0``:
``ADR002-TOL-107`` deja de usar una banda absoluta global y pasa a usar una
banda ``B(M)`` DEPENDIENTE DE LA MAGNITUD.

No mide nada. No abre ficheros. No ejecuta nada al importarse.

QUE CAMBIA RESPECTO DEL PAQUETE 06
==================================

El paquete 06 midio ``D(s)`` en trece escalas y resolvio el punto fijo
``5 D(U) <= U``, publicando UNA banda ``B = U / 5`` valida para toda
magnitud por debajo del umbral. Con ``U = 100 ms`` eso dio ``B = 20 ms``,
una banda casi no vinculante para una operacion de 0,2 ms. Ademas ``U``
quedo en el ultimo escalon medido, donde la clausula de monotonia no impone
nada.

El paquete 07 corrige las dos cosas:

1. la banda deja de ser un numero y pasa a ser una FUNCION de la magnitud,
   derivada de la envolvente monotona de la curva de suelo;
2. la escalera se amplia a 200 ms, 500 ms y 1 s, y el resultado es
   ``NO_EVALUABLE`` si el cruce cae en el tramo superior o si ninguna escala
   medida posterior confirma el regimen relativo.

Las once sesiones independientes —frente a cinco— responden a que ahora la
curva ENTERA es normativa, no un solo punto de ella.

DEFINICIONES VINCULANTES
========================

Sobre la escalera nominal preinscrita ``s_1 < ... < s_n``:

    D(s_i)  = peor (max - min) entre procesos, sobre familias y P50/P95
    E(s_i)  = max(D(s_1), ..., D(s_i))          envolvente monotona
    B(M)    = E(s_j)  con  j = min{ i : s_i >= M }   escalon superior

``E`` es no decreciente por construccion, de modo que ``B`` tambien lo es:
una magnitud mayor nunca recibe una banda mas estrecha. Es exactamente lo
que cierra el riesgo M-03 del Registro —«TOL-107 inaplicable y adverso para
candidatos rapidos»—, que una lectura directa de ``D(s)`` reabriria, porque
``D`` medida NO es monotona.

EL UMBRAL COMO CRUCE EXACTO
===========================

``U`` es el cruce entre la banda y el objetivo relativo:

    B(M) = 0,20 M     <=>     M = 5 E(s_j)

Sobre el escalon ``k`` elegido, ``U := 5 E(s_k)``. Se demuestra en
``resolver_cruce`` que ``s_(k-1) < U <= s_k``, de modo que ``B(U) = E(s_k)``
y por tanto

    m * B(U) = E(s_k) = U / 5 = 0,20 U        con m = 1

La continuidad en ``M = U`` es EXACTA y ya no se postula: se deriva. ``m = 1``
deja de ser una eleccion y pasa a ser la consecuencia de igualar los dos
regimenes en la frontera.

``U`` NO es un escalon de la escalera: es una funcion aritmetica exacta de
una dispersion MEDIDA (cinco veces la envolvente en el escalon elegido). No
tiene nada que ver con la interpolacion de percentiles que el §4.1 del
protocolo prohibe: alli se prohibe inventar una observacion que nunca
ocurrio; aqui se resuelve una ecuacion entre dos funciones preinscritas
cuyos parametros son todos observados.

Fuentes normativas: acta de gobierno de TOL-107 (banda dependiente de la
magnitud); protocolo aprobado (blob ``c298a6b8...``) §2, §3, §4, §5, §6, §7,
§8; Registro fila ``ADR002-TOL-107``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Final

# --------------------------------------------------------------------------
# Identidad
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "suelo-envolvente-0.1"
ESTADO: Final = "PROPUESTO · PREINSCRIPCION BANDA ENVOLVENTE"
ESTADO_EVIDENCIA: Final = "PROPUESTO · BANDA ENVOLVENTE MEDIDA — NO APRUEBA TOL-209"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1"
PROTOCOLO: Final = "SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md"
BLOB_PROTOCOLO_APROBADO: Final = "c298a6b804309a78062f79b6341adfea2374ce56"

REGISTRO: Final = "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md"
#: Blob del Registro DESPUES de la actualizacion de la fila TOL-107 que el
#: acta de gobierno autoriza. Se fija aqui para que una corrida no pueda
#: ejecutarse contra una fila distinta de la aprobada.
BLOB_REGISTRO_ACTUALIZADO: Final = "b499b573e2bb9918961248b05d6faa1b342c552b"

RUTA_LINEA_BASE: Final = "artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json"
BLOB_LINEA_BASE: Final = "f9f051332d9833fb7e10b27f4820849f00b6fe6c"

#: Evidencia de los metodos anteriores. Se CONSERVA intacta: el paquete 07
#: corrige el metodo, no reescribe observaciones. Los blobs se comprueban
#: byte a byte en cada corrida.
EVIDENCIAS_ANTERIORES: Final[Mapping[str, str]] = {
    "artifacts/adr002_tolerances/suelo_medicion_v0.1.json": (
        "899ecee82bf0c62408b43c732fbbb49304eea119"
    ),
    "artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md": (
        "e2b075499f89f71a49c33325298ae9f4bc1f7076"
    ),
    "artifacts/adr002_tolerances/suelo_medicion_v0.2.json": (
        "1d73fa363d6ca8e612e55adb270fbbf3e7540147"
    ),
    "artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.2_PROPUESTO.md": (
        "33f312dda5ba4e8dfea5d24acf5f0158ad7b4a64"
    ),
}

#: Valores publicados por los metodos anteriores. Cita historica verificable,
#: jamas referencia normativa.
U_PAQUETE_05_NS: Final = 48_790
B_PAQUETE_05_NS: Final = 9_758
U_PAQUETE_06_NS: Final = 100_000_000
B_PAQUETE_06_NS: Final = 20_000_000

ARCHIVOS_PREINSCRITOS: Final[tuple[str, ...]] = (
    "docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1.md",
    "docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md",
    "experiments/adr002/tolerances/envelope_protocol.py",
    "experiments/adr002/tolerances/run_envelope.py",
    "experiments/adr002/tolerances/schema_envelope_v0_1.py",
    "experiments/adr002/tolerances/test_adr002_envelope.py",
)

#: Modulos que participan por importacion sin ser ficheros nuevos. Las SONDAS
#: no cambian: lo que cambia es la derivacion. Reutilizarlas congeladas, en
#: vez de copiarlas, es lo que permite atribuir cualquier diferencia de
#: resultado al metodo y no al instrumento.
ARCHIVOS_HEREDADOS: Final[Mapping[str, str]] = {
    "experiments/adr002/tolerances/corpus.py": "90c5118e045676d29998182de60a88a1a2b62443",
    "experiments/adr002/tolerances/floor_scale_probes.py": (
        "07408093b7b0fb12837ec03abdfa9f4a6c384f70"
    ),
    "experiments/adr002/tolerances/floor_scale_protocol.py": (
        "aa6e6492e73608f496feda252f18436d8e80802e"
    ),
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
# Escalera nominal preinscrita: dieciseis escalones
# --------------------------------------------------------------------------
#
# Los trece del paquete 06 mas 200 ms, 500 ms y 1 s. La ampliacion no es
# cosmetica: con la escalera anterior el cruce cayo en el ultimo escalon, de
# modo que la clausula «y todas las escalas mayores» no impuso nada. Ahora
# hay tramo por encima donde confirmar —o desmentir— el regimen relativo.
#
# Progresion 1-2-5, cinco ordenes de magnitud. Todo escalon es multiplo de 5.

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
    200_000_000,
    500_000_000,
    1_000_000_000,  # 1 s
)

FAMILIA_CPU: Final = "cpu"
FAMILIA_CANON: Final = "canon"
FAMILIAS: Final[tuple[str, ...]] = (FAMILIA_CPU, FAMILIA_CANON)

SONDA_VACIA: Final = "D_vacia"
SONDA_CANON_0: Final = "canon_0_filas"
SONDA_CANON_1: Final = "canon_1_fila"
SONDAS_UNITARIAS: Final[tuple[str, ...]] = (SONDA_VACIA, SONDA_CANON_0, SONDA_CANON_1)

DIAG_REFERENCIA: Final = "referencia_intraproceso"
DIAG_PROGRESION: Final = "progresion_por_escala"
DIAG_ENVOLVENTE: Final = "curva_y_envolvente"
DIAG_HOLGURA: Final = "holgura_de_banda"
DIAGNOSTICOS: Final[tuple[str, ...]] = (
    DIAG_REFERENCIA,
    DIAG_PROGRESION,
    DIAG_ENVOLVENTE,
    DIAG_HOLGURA,
)

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

UMBRAL_COSTE_BAJO_NS: Final = 1_000_000
N_COSTE_BAJO: Final = 100
N_COSTE_ALTO: Final = 30
WARMUP_ESCALA: Final = 5

N_UNITARIA: Final = 100
WARMUP_UNITARIA: Final = 5

#: ONCE sesiones, no cinco. El §3.3 del protocolo exige cinco como MINIMO.
#: Con banda global bastaban: el ruido afectaba a un solo punto. Con banda
#: dependiente de la magnitud, cada escalon ruidoso es una tolerancia
#: ruidosa, y ``max - min`` sobre cinco observaciones lo fija un unico
#: proceso desafortunado. Once es impar, de modo que el P50 entre procesos
#: —publicado como diagnostico— cae en una observacion real.
PROCESOS_MINIMOS: Final = 11

SEMILLA: Final = 20260726
RONDAS_ROUND_ROBIN: Final = 5

MUESTRAS_CALIBRACION: Final = 21
WARMUP_CALIBRACION: Final = 5

UNIDADES_REFERENCIA: Final[Mapping[str, int]] = {
    FAMILIA_CPU: 10_000,
    FAMILIA_CANON: 10,
}

CALIBRACION_MIN_NUM: Final = 1
CALIBRACION_MIN_DEN: Final = 2
CALIBRACION_MAX_FACTOR: Final = 2

UNIDADES_MINIMAS_PROGRESION: Final = 10
TOLERANCIA_PROGRESION_NUM: Final = 1
TOLERANCIA_PROGRESION_DEN: Final = 3

TOLERANCIA_DERIVA_NUM: Final = 3
TOLERANCIA_DERIVA_DEN: Final = 10
VUELTAS_REFERENCIA: Final = 10_000
N_REFERENCIA: Final = 100
WARMUP_REFERENCIA: Final = 5

# --------------------------------------------------------------------------
# Formulas vinculantes
# --------------------------------------------------------------------------

OBJETIVO_RELATIVO_NUM: Final = 1
OBJETIVO_RELATIVO_DEN: Final = 5

#: Ya NO es una eleccion: es la consecuencia de igualar los dos regimenes en
#: la frontera. Con B(U) = U/5, ``m * B(U) = 0,20 U`` obliga a ``m = 1``.
MARGEN_M: Final = 1

FACTOR_U: Final = OBJETIVO_RELATIVO_DEN

#: Escalas medidas por encima de ``U`` que deben confirmar el regimen
#: relativo. Si no hay ninguna, el cruce esta en el borde y no se publica.
CONFIRMACIONES_MINIMAS: Final = 1

REGIMEN_RELATIVO: Final = "relativo"
REGIMEN_ABSOLUTO: Final = "absoluto"
NO_EVALUABLE: Final = "NO_EVALUABLE"

MOTIVO_SIN_CRUCE: Final = "sin_cruce_sostenido"
MOTIVO_BORDE_SUPERIOR: Final = "cruce_en_el_borde_superior"
MOTIVO_SIN_CONFIRMACION: Final = "sin_escala_posterior_que_confirme"
MOTIVO_DOMINADA: Final = "dominada_por_instrumento"
MOTIVO_UMBRAL_NO_RESUELTO: Final = "umbral_no_resuelto"


class SondaNoNeutralError(ValueError):
    """Una sonda normativa nombra FTS5, rank() o un candidato."""


class ProcesosInsuficientesError(ValueError):
    """Menos sesiones independientes de las exigidas (§3.3)."""


class EscaleraInvalidaError(ValueError):
    """La escalera medida no cubre las escalas preinscritas."""


class InvarianteVioladoError(ValueError):
    """Se violo un invariante demostrable del metodo."""


# --------------------------------------------------------------------------
# Percentiles: identicos a los paquetes anteriores
# --------------------------------------------------------------------------


def percentil_ns(ordenadas: Sequence[int], fraccion_num: int, fraccion_den: int) -> int:
    """Percentil por rango mas cercano sobre enteros en nanosegundos (§4.1)."""
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


def resolucion_percentil(n: int) -> str:
    """Que puede afirmar honestamente un P99 con ``n`` muestras (§4.3, §4.4)."""
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
    """Unidades de trabajo que aproximan la escala nominal, en enteros."""
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


def comprobar_cobertura(medidas: Sequence[MedidaEscala]) -> None:
    """Toda (familia, escala) preinscrita con al menos ``PROCESOS_MINIMOS``."""
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
            pids = {m.pid for m in medidas if m.familia == familia and m.escala_ns == escala}
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
    """``D(s)``: peor dispersion absoluta entre procesos en la escala ``s``."""
    peor = 0
    for familia in FAMILIAS:
        for percentil in ("p50", "p95"):
            peor = max(peor, dispersion_de_familia(medidas, familia, escala_ns, percentil))
    return peor


# --------------------------------------------------------------------------
# Envolvente monotona y banda dependiente de la magnitud
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Envolvente:
    """Curva ``D(s)`` medida y su envolvente monotona ``E(s)``.

    ``dispersiones`` y ``envolvente`` estan alineadas con ``ESCALERA_NS``.
    """

    dispersiones: tuple[int, ...]
    envolvente: tuple[int, ...]

    def banda(self, magnitud_ns: int) -> int:
        """``B(M) = E(s_j)`` con ``s_j`` el menor escalon ``>= M``.

        Direccion conservadora entre escalones: se toma el escalon SUPERIOR,
        cuyo valor de envolvente es mayor o igual. Tomar el inferior daria una
        banda mas estrecha que el suelo demostrado en el tramo.
        """
        if magnitud_ns <= 0:
            msg = "la magnitud debe ser positiva"
            raise ValueError(msg)
        for indice, escala in enumerate(ESCALERA_NS):
            if escala >= magnitud_ns:
                return self.envolvente[indice]
        msg = (
            f"magnitud {magnitud_ns} ns por encima del ultimo escalon "
            f"{ESCALERA_NS[-1]} ns: la banda no esta definida ahi, y no hace "
            f"falta porque esa magnitud vive en regimen relativo"
        )
        raise EscaleraInvalidaError(msg)

    def es_monotona(self) -> bool:
        """La envolvente no puede decrecer: es lo que cierra M-03."""
        return all(a <= b for a, b in pairwise(self.envolvente))

    def cubre_el_suelo(self) -> bool:
        """``E(s_i) >= D(s_i)`` en todo escalon, por construccion."""
        return all(e >= d for d, e in zip(self.dispersiones, self.envolvente, strict=False))


def construir_envolvente(medidas: Sequence[MedidaEscala]) -> Envolvente:
    """Calcula ``D(s)`` y su envolvente monotona ``E(s) = max acumulado``."""
    comprobar_cobertura(medidas)
    dispersiones = tuple(dispersion_de_escala(medidas, s) for s in ESCALERA_NS)
    acumulado: list[int] = []
    peor = 0
    for valor in dispersiones:
        peor = max(peor, valor)
        acumulado.append(peor)
    return Envolvente(dispersiones=dispersiones, envolvente=tuple(acumulado))


def sostenible_en_escalon(envolvente_ns: int, escala_ns: int) -> bool:
    """``5 E(s) <= s``: en ese escalon la banda ya cabe en el 20 % relativo."""
    return OBJETIVO_RELATIVO_DEN * envolvente_ns <= OBJETIVO_RELATIVO_NUM * escala_ns


def razon_por_mil(valor_ns: int, escala_ns: int) -> int:
    """Razon en milesimas, truncada. El artefacto no usa coma flotante."""
    if escala_ns <= 0:
        msg = "la escala debe ser positiva"
        raise ValueError(msg)
    return 1000 * valor_ns // escala_ns


@dataclass(frozen=True, slots=True)
class Cruce:
    """Resultado de resolver ``B(M) = 0,20 M`` sobre la escalera medida."""

    envolvente: Envolvente
    sostenibles: tuple[bool, ...]
    indice_escalon: int | None
    u: int | None
    b_en_u: int | None
    m: int
    confirmaciones: int
    motivo_no_evaluable: str | None

    @property
    def evaluable(self) -> bool:
        return self.u is not None and self.b_en_u is not None


def resolver_cruce(envolvente: Envolvente) -> Cruce:
    """Resuelve ``U`` como el cruce exacto entre ``B(M)`` y ``0,20 M``.

    ``k`` es el menor escalon que sostiene ``5 E(s_k) <= s_k`` y cuyos
    escalones superiores lo sostienen todos. Sobre el, ``U := 5 E(s_k)``.

    **Demostracion de que ``s_(k-1) < U <= s_k``** (con ``s_0 := 0``):

    - ``U = 5 E(s_k) <= s_k`` es la propia condicion de sostenibilidad;
    - si fuese ``U <= s_(k-1)``, entonces, como ``E`` no decrece,
      ``5 E(s_(k-1)) <= 5 E(s_k) = U <= s_(k-1)``, luego el escalon ``k-1``
      tambien seria sostenible y todos los superiores tambien lo serian,
      contradiciendo que ``k`` es el minimo.

    De ahi que ``B(U) = E(s_k) = U / 5``, y la continuidad en ``M = U`` sea
    exacta sin postular nada. ``U`` no es un escalon: es una consecuencia
    aritmetica exacta de una dispersion medida.

    Devuelve ``NO_EVALUABLE``, sin inventar ningun valor, si:

    - ningun escalon sostiene la condicion de forma sostenida;
    - el cruce cae en el tramo del ultimo escalon medido;
    - no queda al menos ``CONFIRMACIONES_MINIMAS`` escalas medidas por encima
      de ``U`` que confirmen el regimen relativo.
    """
    sostenibles = tuple(
        sostenible_en_escalon(e, s) for e, s in zip(envolvente.envolvente, ESCALERA_NS, strict=True)
    )

    elegido: int | None = None
    for indice in range(len(ESCALERA_NS)):
        if all(sostenibles[mayor] for mayor in range(indice, len(ESCALERA_NS))):
            elegido = indice
            break

    def _sin_cruce(motivo: str, indice: int | None = None) -> Cruce:
        return Cruce(
            envolvente=envolvente,
            sostenibles=sostenibles,
            indice_escalon=indice,
            u=None,
            b_en_u=None,
            m=MARGEN_M,
            confirmaciones=0,
            motivo_no_evaluable=motivo,
        )

    if elegido is None:
        fallidas = [s for s, ok in zip(ESCALERA_NS, sostenibles, strict=True) if not ok]
        return _sin_cruce(f"{MOTIVO_SIN_CRUCE}: escalones que fallan {fallidas}")

    if elegido == len(ESCALERA_NS) - 1:
        return _sin_cruce(
            f"{MOTIVO_BORDE_SUPERIOR}: el cruce cae en el tramo del ultimo escalon medido "
            f"({ESCALERA_NS[-1]} ns), donde ninguna escala posterior puede confirmarlo",
            elegido,
        )

    u = FACTOR_U * envolvente.envolvente[elegido]
    confirmaciones = sum(
        1
        for indice in range(elegido + 1, len(ESCALERA_NS))
        if sostenibles[indice] and ESCALERA_NS[indice] > u
    )
    if confirmaciones < CONFIRMACIONES_MINIMAS:
        return _sin_cruce(
            f"{MOTIVO_SIN_CONFIRMACION}: {confirmaciones} escalas medidas por encima de "
            f"U={u} ns confirman el regimen relativo; se exigen {CONFIRMACIONES_MINIMAS}",
            elegido,
        )

    # Los dos extremos del intervalo que la demostracion del docstring exige.
    inferior = 0 if elegido == 0 else ESCALERA_NS[elegido - 1]
    if not (inferior < u <= ESCALERA_NS[elegido]):  # pragma: no cover - demostrado
        msg = (
            f"invariante violado: U={u} fuera del intervalo "
            f"({inferior}, {ESCALERA_NS[elegido]}] del escalon elegido"
        )
        raise InvarianteVioladoError(msg)

    return Cruce(
        envolvente=envolvente,
        sostenibles=sostenibles,
        indice_escalon=elegido,
        u=u,
        b_en_u=envolvente.envolvente[elegido],
        m=MARGEN_M,
        confirmaciones=confirmaciones,
        motivo_no_evaluable=None,
    )


def continuidad_exacta(cruce: Cruce) -> bool:
    """``m * B(U) == 0,20 U`` sin resto. Se comprueba, no se supone."""
    if cruce.u is None or cruce.b_en_u is None:
        return False
    banda = cruce.envolvente.banda(cruce.u)
    if banda != cruce.b_en_u:
        return False
    return MARGEN_M * banda * OBJETIVO_RELATIVO_DEN == OBJETIVO_RELATIVO_NUM * cruce.u


def banda_no_decreciente(envolvente: Envolvente) -> bool:
    """``B`` nunca se estrecha al crecer la magnitud. Cierra M-03.

    Se comprueba sobre las magnitudes que pueden cambiar de escalon: los
    propios escalones y el punto inmediatamente posterior a cada uno.
    """
    magnitudes = [1]
    for escala in ESCALERA_NS[:-1]:
        magnitudes.extend((escala, escala + 1))
    magnitudes.append(ESCALERA_NS[-1])
    bandas = [envolvente.banda(m) for m in magnitudes]
    return all(a <= b for a, b in pairwise(bandas))


def holgura_por_escalon(cruce: Cruce) -> tuple[dict[str, int | bool], ...]:
    """Diagnostico: comparacion de ``m*B(s)`` con el ``20 %`` de cada escalon.

    Por debajo de ``U``, un escalon con ``m*B(s) < 0,20 s`` recibe un criterio
    absoluto MAS ESTRICTO que el objetivo relativo. No es inalcanzable —la
    banda cubre el suelo medido por construccion— pero es una asimetria real
    y se publica en lugar de disimularse. Ocurre solo en escalones que
    sostienen la condicion de forma aislada, sin sostenerla los superiores.
    """
    filas: list[dict[str, int | bool]] = []
    for indice, escala in enumerate(ESCALERA_NS):
        banda = MARGEN_M * cruce.envolvente.envolvente[indice]
        objetivo = OBJETIVO_RELATIVO_NUM * escala // OBJETIVO_RELATIVO_DEN
        filas.append(
            {
                "escala_ns": escala,
                "banda_ns": banda,
                "objetivo_relativo_ns": objetivo,
                "banda_al_menos_el_objetivo": banda >= objetivo,
                "bajo_el_umbral": cruce.u is not None and escala <= cruce.u,
            }
        )
    return tuple(filas)


def calcular_sm(unitarias: Sequence[MedidaUnitaria]) -> int:
    """``SM``: peor P95 de las sondas de suelo unitario. Guarda de dominancia."""
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
# Seleccion de regimen y criterio
# --------------------------------------------------------------------------


def pasa_relativo(minimo: int, maximo: int) -> bool:
    """``(max - min) / min <= 0,20`` en aritmetica entera exacta."""
    if minimo <= 0:
        return False
    return OBJETIVO_RELATIVO_DEN * (maximo - minimo) <= OBJETIVO_RELATIVO_NUM * minimo


def pasa_absoluto(minimo: int, maximo: int, banda: int) -> bool:
    """``(max - min) <= m * B(M)``, con ``M`` el minimo del percentil."""
    return (maximo - minimo) <= MARGEN_M * banda


def regimen_de_percentil(minimo_del_percentil: int, u: int) -> str:
    """RELATIVO si ``min_s p(s) >= U``; ABSOLUTO en caso contrario."""
    return REGIMEN_RELATIVO if minimo_del_percentil >= u else REGIMEN_ABSOLUTO


@dataclass(frozen=True, slots=True)
class VeredictoPercentil:
    """Regimen, banda aplicada y resultado de un percentil concreto."""

    percentil: str
    minimo: int
    maximo: int
    regimen: str
    banda_ns: int | None
    pasa: bool


@dataclass(frozen=True, slots=True)
class VeredictoMagnitud:
    """Veredicto completo de una magnitud sobre sus sesiones."""

    dominada_por_instrumento: bool
    resultado: str
    por_percentil: tuple[VeredictoPercentil, ...]


def evaluar_magnitud(
    p50_por_sesion: Sequence[int],
    p95_por_sesion: Sequence[int],
    *,
    sm: int,
    cruce: Cruce,
) -> VeredictoMagnitud:
    """Guarda ``SM`` primero, despues regimen y banda por percentil."""
    if not p50_por_sesion or not p95_por_sesion:
        msg = "faltan percentiles por sesion"
        raise ValueError(msg)
    if len(p50_por_sesion) != len(p95_por_sesion):
        msg = "numero de sesiones incoherente entre P50 y P95"
        raise ValueError(msg)
    if cruce.u is None:
        msg = "no se puede clasificar sin umbral resuelto"
        raise InvarianteVioladoError(msg)

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

    u = cruce.u
    reg50 = regimen_de_percentil(min50, u)
    reg95 = regimen_de_percentil(min95, u)
    if reg50 == REGIMEN_RELATIVO and reg95 == REGIMEN_ABSOLUTO:
        msg = "combinacion imposible: P50 relativo con P95 absoluto"
        raise InvarianteVioladoError(msg)

    def _evaluar(nombre: str, minimo: int, maximo: int, regimen: str) -> VeredictoPercentil:
        if regimen == REGIMEN_RELATIVO:
            return VeredictoPercentil(
                percentil=nombre,
                minimo=minimo,
                maximo=maximo,
                regimen=regimen,
                banda_ns=None,
                pasa=pasa_relativo(minimo, maximo),
            )
        banda = cruce.envolvente.banda(minimo)
        return VeredictoPercentil(
            percentil=nombre,
            minimo=minimo,
            maximo=maximo,
            regimen=regimen,
            banda_ns=banda,
            pasa=pasa_absoluto(minimo, maximo, banda),
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
    "envolvente_monotona",
    "envolvente_cubre_el_suelo",
    "banda_no_decreciente",
    "continuidad_exacta_en_u",
    "vectores_crudos_completos",
    "sin_muestras_negativas",
    "sin_filtrado",
    "warmup_separado",
    "sin_redondeo_previo",
    "sondas_neutrales",
    "evidencias_anteriores_intactas",
    "registro_actualizado_intacto",
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


#: Controles que presuponen un umbral resuelto y que, por tanto, un
#: ``NO_EVALUABLE`` legitimo no puede satisfacer.
CONTROLES_QUE_EXIGEN_UMBRAL: Final[tuple[str, ...]] = ("continuidad_exacta_en_u",)


def calibracion_en_banda(observado_ns: int, nominal_ns: int) -> bool:
    """La magnitud observada debe caer en ``[s/2, 2s]``, en enteros."""
    if observado_ns <= 0 or nominal_ns <= 0:
        return False
    minimo_ok = observado_ns * CALIBRACION_MIN_DEN >= nominal_ns * CALIBRACION_MIN_NUM
    maximo_ok = observado_ns <= nominal_ns * CALIBRACION_MAX_FACTOR
    return minimo_ok and maximo_ok


def escala_progresa(p50_menor: int, escala_menor: int, p50_mayor: int, escala_mayor: int) -> bool:
    """El tiempo medido debe crecer con la escala nominal, no con el corchete.

    Tolerancia 1/3: con 1/2, un tiempo que no crece pasaria justo en la
    frontera del escalon minimo de factor 2.
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
    """Criterio preinscrito de deriva o throttling dentro de un proceso."""
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
    """Operaciones inyectadas para probar la custodia sin repositorio real."""

    leer_bytes: Callable[[str], bytes]
    es_ancestro: Callable[[str, str], bool]
    existe_commit: Callable[[str], bool]
    head: Callable[[], str]
    arbol_limpio: Callable[[], bool]
    diff_vacio: Callable[[str, str, Sequence[str]], bool]
    blob_en_commit: Callable[[str, str], str | None]


def fallos_evidencias_anteriores(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Las evidencias v0.1 y v0.2 deben seguir byte a byte donde estaban."""
    fallos: list[str] = []
    for ruta, esperado in EVIDENCIAS_ANTERIORES.items():
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"evidencia anterior desaparecida o ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(f"evidencia anterior alterada: {ruta} ({observado} != {esperado})")
    return tuple(fallos)


def fallos_documentos_de_referencia(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Protocolo aprobado, Registro actualizado y linea base, intactos."""
    fallos: list[str] = []
    referencias = {
        f"docs/architecture/{PROTOCOLO}": BLOB_PROTOCOLO_APROBADO,
        f"docs/architecture/{REGISTRO}": BLOB_REGISTRO_ACTUALIZADO,
        RUTA_LINEA_BASE: BLOB_LINEA_BASE,
    }
    for ruta, esperado in referencias.items():
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"documento de referencia ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(f"documento de referencia alterado: {ruta} ({observado} != {esperado})")
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

    fallos.extend(fallos_documentos_de_referencia(entorno))
    fallos.extend(fallos_evidencias_anteriores(entorno))

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
