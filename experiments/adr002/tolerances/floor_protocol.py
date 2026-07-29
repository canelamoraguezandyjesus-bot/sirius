"""Preinscripcion normativa del suelo de medicion LAB-LINUX para ADR002-TOL-209.

Este modulo se congela ANTES de medir. Contiene las decisiones, las
constantes, las formulas y los criterios de validez e invalidez, de modo
que su commit sea anterior y verificable frente al commit de evidencia.

No mide nada. No abre ficheros. No ejecuta nada al importarse.

Fuentes normativas:

- ``SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md`` (APROBADO por
  ``SIRIUS_0.2_ADR_002_REGISTRO_TOLERANCIAS_APROBACION_v1.0.md`` §1.2),
  reglas 2.x, 3.x, 4.x, 5.x, 6.x, 7 y 8;
- ``SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md``, fila
  ``ADR002-TOL-107`` y §9;
- ``SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_05_TOL209_SUELO_v0.1.md``.

Toda magnitud temporal es un entero en NANOSEGUNDOS. No se convierte a
milisegundos, no se redondea y no se interpola en ningun punto de la
cadena que produce una cifra normativa.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

# --------------------------------------------------------------------------
# Identidad del artefacto
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "suelo-0.1"
ESTADO: Final = "PROPUESTO · PREINSCRIPCION"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_05_TOL209_SUELO_v0.1"
PROTOCOLO: Final = "SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md"

# Blob Git del protocolo aprobado, verificado en el commit 42b7a91 y
# registrado en el acta de aprobacion v1.0 §1 punto 2.
BLOB_PROTOCOLO_APROBADO: Final = "c298a6b804309a78062f79b6341adfea2374ce56"

# Los seis artefactos de la fase A. La ejecucion futura verifica que sus
# blobs coinciden con los registrados en el JSON de evidencia.
ARCHIVOS_PREINSCRITOS: Final[tuple[str, ...]] = (
    "docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_05_TOL209_SUELO_v0.1.md",
    "experiments/adr002/tolerances/floor_probes.py",
    "experiments/adr002/tolerances/floor_protocol.py",
    "experiments/adr002/tolerances/run_floor.py",
    "experiments/adr002/tolerances/schema_floor_v0_1.py",
    "experiments/adr002/tolerances/test_adr002_floor.py",
)

# Participa en el resultado por importacion (``percentil``), sin ser fichero
# nuevo de la fase A: su blob se registra igualmente.
ARCHIVO_ARNES_HEREDADO: Final = "experiments/adr002/tolerances/harness.py"

# Los siete congelables de ``SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md`` §2.
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
# Decision 8 · composicion normativa de F
# --------------------------------------------------------------------------

SONDA_VACIA: Final = "D_vacia"
SONDA_SQLITE_0: Final = "SQLite_0_filas"
SONDA_SQLITE_1: Final = "SQLite_1_fila"

#: Las tres sondas que derivan SM, B50, B95, B y U. Ninguna otra.
F_NORMATIVO: Final[tuple[str, ...]] = (SONDA_VACIA, SONDA_SQLITE_0, SONDA_SQLITE_1)

DIAG_RELOJ: Final = "lecturas_consecutivas_reloj"
DIAG_BUSY_SPIN: Final = "busy_spin_calibrado"
DIAG_DUPLICACION: Final = "comprobacion_1x_2x"
DIAG_PUERTO: Final = "sobrecoste_puerto_comun"

#: Diagnosticos. Nunca modifican B ni U (decision 8; matriz 41).
DIAGNOSTICOS: Final[tuple[str, ...]] = (
    DIAG_RELOJ,
    DIAG_BUSY_SPIN,
    DIAG_DUPLICACION,
    DIAG_PUERTO,
)

#: Nombres que jamas pueden aparecer en F.
PROHIBIDOS_EN_F: Final[tuple[str, ...]] = (
    *DIAGNOSTICOS,
    "fts5",
    "rank",
    "knowledge_fts",
    "message_fts",
)

# --------------------------------------------------------------------------
# Decision 2 · sonda de reloj, y repeticiones del §3 del protocolo
# --------------------------------------------------------------------------

#: §3.2: 100 repeticiones cuando el coste es bajo. Todas las sondas de F lo son.
N_SONDA_F: Final = 100
WARMUP_SONDA_F: Final = 5

#: Desviacion al alza declarada (§7 punto 4): 100 muestras no caracterizan un tick.
N_SONDA_RELOJ: Final = 100_000
WARMUP_SONDA_RELOJ: Final = 1_000

N_DIAGNOSTICO: Final = 100
WARMUP_DIAGNOSTICO: Final = 5

#: §3.3: al menos cinco sesiones independientes. Aqui, procesos distintos.
PROCESOS_MINIMOS: Final = 5

#: §5.3: sin aleatoriedad no sembrada. Semilla del corpus de rendimiento congelado.
SEMILLA: Final = 20260726

# --------------------------------------------------------------------------
# Formulas vinculantes
# --------------------------------------------------------------------------

#: Objetivo relativo congelado del Registro v0.4, fila TOL-107. Se expresa
#: como fraccion exacta para no introducir aritmetica de coma flotante.
OBJETIVO_RELATIVO_NUM: Final = 1
OBJETIVO_RELATIVO_DEN: Final = 5

#: Decision 3. Unico valor que conserva continuidad exacta en M = U.
MARGEN_M: Final = 1

#: U = B / 0,20 = 5 * B. Factor derivado, no configurable (matriz 18').
FACTOR_U: Final = OBJETIVO_RELATIVO_DEN

REGIMEN_RELATIVO: Final = "relativo"
REGIMEN_ABSOLUTO: Final = "absoluto"
NO_EVALUABLE: Final = "NO_EVALUABLE"


class PercentilInterpoladoError(ValueError):
    """Se intento obtener un percentil por interpolacion (§4.1, §8.5)."""


class SondaFueraDeFError(ValueError):
    """Un diagnostico intento entrar en el conjunto normativo F."""


class ProcesosInsuficientesError(ValueError):
    """Menos de cinco procesos independientes (§3.3)."""


def percentil_ns(ordenadas: Sequence[int], fraccion_num: int, fraccion_den: int) -> int:
    """Percentil por rango mas cercano sobre enteros en nanosegundos.

    Nunca interpola: devuelve siempre una muestra realmente observada
    (§4.1 del protocolo). La fraccion se pasa como par de enteros para
    que el rango no dependa de la representacion binaria de un ``float``.
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
    """Que puede afirmar honestamente un percentil con ``n`` muestras (§4.3, §4.4)."""
    if n < 100:
        return (
            f"con n={n}, el P99 por rango mas cercano coincide con el maximo observado; "
            f"acota la cola, no la caracteriza"
        )
    peores = max(1, n - math.floor(0.99 * n))
    return f"con n={n}, el P99 corresponde a la {peores}.a peor muestra observada"


@dataclass(frozen=True, slots=True)
class MedidaSonda:
    """Percentiles de una sonda en un proceso. Enteros en nanosegundos."""

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


def _valores(medidas: Iterable[MedidaSonda], sonda: str, atributo: str) -> list[int]:
    seleccion = [m for m in medidas if m.sonda == sonda]
    return [int(getattr(m, atributo)) for m in seleccion]


def _comprobar_f(medidas: Sequence[MedidaSonda]) -> None:
    presentes = {m.sonda for m in medidas}
    intrusos = sorted(s for s in presentes if s not in F_NORMATIVO)
    if intrusos:
        msg = f"sondas ajenas a F en una derivacion normativa: {intrusos}"
        raise SondaFueraDeFError(msg)
    faltan = sorted(s for s in F_NORMATIVO if s not in presentes)
    if faltan:
        msg = f"faltan sondas normativas de F: {faltan}"
        raise SondaFueraDeFError(msg)
    for sonda in F_NORMATIVO:
        pids = {m.pid for m in medidas if m.sonda == sonda}
        if len(pids) < PROCESOS_MINIMOS:
            msg = f"{sonda}: {len(pids)} procesos distintos; el minimo es {PROCESOS_MINIMOS}"
            raise ProcesosInsuficientesError(msg)


def calcular_sm(medidas: Sequence[MedidaSonda]) -> int:
    """SM = maximo, sobre X en F y s en S, de P95(X, s).

    Guarda de dominancia instrumental. NO define U.
    """
    _comprobar_f(medidas)
    return max(m.p95 for m in medidas)


def _dispersion(medidas: Sequence[MedidaSonda], atributo: str) -> int:
    peor = 0
    for sonda in F_NORMATIVO:
        valores = _valores(medidas, sonda, atributo)
        peor = max(peor, max(valores) - min(valores))
    return peor


def calcular_b50(medidas: Sequence[MedidaSonda]) -> int:
    """B50 = maximo, sobre X en F y pares de procesos, de |P50(X,s) - P50(X,s')|."""
    _comprobar_f(medidas)
    return _dispersion(medidas, "p50")


def calcular_b95(medidas: Sequence[MedidaSonda]) -> int:
    """B95 = maximo, sobre X en F y pares de procesos, de |P95(X,s) - P95(X,s')|."""
    _comprobar_f(medidas)
    return _dispersion(medidas, "p95")


def calcular_b(medidas: Sequence[MedidaSonda]) -> int:
    """B = max(B50, B95). Banda absoluta unica, compatible con la ficha aprobada."""
    return max(calcular_b50(medidas), calcular_b95(medidas))


def calcular_u(b: int) -> int:
    """U = B / 0,20 = 5 * B. Sin multiplicador configurable y sin busqueda de k_U."""
    if b < 0:
        msg = "B no puede ser negativa"
        raise ValueError(msg)
    return FACTOR_U * b


@dataclass(frozen=True, slots=True)
class DerivacionSuelo:
    """Resultado completo de la derivacion normativa, en nanosegundos."""

    sm: int
    b50: int
    b95: int
    b: int
    u: int
    m: int


def derivar(medidas: Sequence[MedidaSonda]) -> DerivacionSuelo:
    """Deriva SM, B50, B95, B, U y m desde las sondas de F exclusivamente."""
    b50 = calcular_b50(medidas)
    b95 = calcular_b95(medidas)
    b = max(b50, b95)
    return DerivacionSuelo(
        sm=calcular_sm(medidas),
        b50=b50,
        b95=b95,
        b=b,
        u=calcular_u(b),
        m=MARGEN_M,
    )


# --------------------------------------------------------------------------
# Orden de evaluacion: guarda SM, luego regimen por percentil
# --------------------------------------------------------------------------


def pasa_relativo(minimo: int, maximo: int) -> bool:
    """(max - min) / min <= 0,20, en aritmetica entera exacta."""
    if minimo <= 0:
        return False
    return OBJETIVO_RELATIVO_DEN * (maximo - minimo) <= OBJETIVO_RELATIVO_NUM * minimo


def pasa_absoluto(minimo: int, maximo: int, b: int) -> bool:
    """(max - min) <= m * B, con m = 1."""
    return (maximo - minimo) <= MARGEN_M * b


def regimen_de_percentil(minimo_del_percentil: int, u: int) -> str:
    """RELATIVO si min_s p(s) >= U; ABSOLUTO en caso contrario."""
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
    invariante_respetado: bool


class InvarianteVioladoError(ValueError):
    """min_s P95 < min_s P50, o combinacion P50 relativo / P95 absoluto."""


def evaluar_magnitud(
    p50_por_sesion: Sequence[int],
    p95_por_sesion: Sequence[int],
    *,
    sm: int,
    b: int,
    u: int,
) -> VeredictoMagnitud:
    """Aplica la guarda SM y despues el regimen por percentil, en ese orden.

    El orden es normativo (matriz 39): si la guarda se evaluase despues, una
    magnitud dominada por el instrumento podria clasificarse y publicarse
    como latencia antes de que la guarda actuase.
    """
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

    # PASO 1 · guarda de dominancia, antes de seleccionar regimen.
    if min95 < sm:
        return VeredictoMagnitud(
            dominada_por_instrumento=True,
            resultado=NO_EVALUABLE,
            por_percentil=(),
            invariante_respetado=True,
        )

    # PASO 2 y 3 · regimen y criterio, por percentil.
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

    # PASO 4 · veredicto global conjuntivo.
    valida = v50.pasa and v95.pasa
    return VeredictoMagnitud(
        dominada_por_instrumento=False,
        resultado="VALIDA" if valida else "INVALIDA",
        por_percentil=(v50, v95),
        invariante_respetado=True,
    )


def registro_por_percentil(veredicto: VeredictoMagnitud) -> str:
    """Cadena para el campo unico ``Regimen aplicable`` de la ficha aprobada.

    Refina el formato singular del §7 punto 9 del protocolo. Es una
    desviacion declarada de antemano (§7 punto 4), no una modificacion
    normativa: la plantilla no se toca y su blob no cambia.
    """
    if veredicto.dominada_por_instrumento:
        return NO_EVALUABLE
    return " · ".join(f"{v.percentil}: {v.regimen}" for v in veredicto.por_percentil)


# --------------------------------------------------------------------------
# Controles internos preinscritos (decision 7)
# --------------------------------------------------------------------------

CONTROLES_BLOQUEANTES: Final[tuple[str, ...]] = (
    "procesos_independientes",
    "pids_distintos",
    "carga_registrada",
    "boot_id_estable",
    "busy_spin_estable",
    "duplicacion_1x_2x",
    "vectores_crudos_completos",
    "sin_filtrado",
    "warmup_separado",
    "sin_redondeo_previo",
    "captura_ambiental_presente",
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
    """Falla cerrado: un control ausente cuenta como fallido.

    Si algun control bloqueante falla, la corrida no publica valores
    (matriz 33'). B nunca se rebaja para obtener una clasificacion de
    regimen mas conveniente (matriz 36).
    """
    fallos = tuple(c for c in CONTROLES_BLOQUEANTES if not estado.get(c, False))
    return ResultadoControles(fallos=fallos)


# --------------------------------------------------------------------------
# Custodia A -> D. Funciones puras, inyectables y probables sin medir.
# --------------------------------------------------------------------------


def blob_git(contenido: bytes) -> str:
    """SHA-1 del objeto blob de Git para ``contenido``."""
    cabecera = f"blob {len(contenido)}\0".encode()
    return hashlib.sha1(cabecera + contenido, usedforsecurity=False).hexdigest()


@dataclass(frozen=True, slots=True)
class EntornoCustodia:
    """Operaciones inyectadas para poder probar la custodia sin repositorio real."""

    leer_bytes: Callable[[str], bytes]
    es_ancestro: Callable[[str, str], bool]
    existe_commit: Callable[[str], bool]
    head: Callable[[], str]
    arbol_limpio: Callable[[], bool]
    diff_vacio: Callable[[str, str, Sequence[str]], bool]


def verificar_custodia(
    entorno: EntornoCustodia,
    *,
    sha_a: str,
    blobs_preinscritos: Mapping[str, str],
    blob_arnes: str,
    blobs_congelados: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Comprueba la cadena A -> D completa y devuelve la lista de fallos.

    Pasos, en el orden exigido por el paquete de trabajo §9:
    existencia de A, ancestria sobre HEAD, blobs de los seis ficheros,
    blob de ``harness.py``, blobs congelados y diff vacio.
    """
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

    for ruta, esperado in blobs_preinscritos.items():
        _comparar(ruta, esperado, "blob preinscrito")

    _comparar(ARCHIVO_ARNES_HEREDADO, blob_arnes, "arnes heredado")

    for ruta, esperado in congelados.items():
        _comparar(ruta, esperado, "blob congelado")

    if not entorno.diff_vacio(sha_a, entorno.head(), ARCHIVOS_PREINSCRITOS):
        fallos.append("diff no vacio en los ficheros preinscritos entre A y HEAD")

    return tuple(fallos)


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


# --------------------------------------------------------------------------
# Guarda del SQL de las sondas de F
# --------------------------------------------------------------------------

_PROHIBIDO_SQL: Final[Mapping[str, str]] = {
    r"\blike\b": "LIKE",
    r"\bmatch\b": "MATCH",
    r"\bjoin\b": "JOIN",
    r"\border\s+by\b": "ORDER BY",
    r"\bgroup\s+by\b": "GROUP BY",
    r"\bcount\s*\(": "agregacion count()",
    r"\bsum\s*\(": "agregacion sum()",
    r"\bavg\s*\(": "agregacion avg()",
    r"\bmin\s*\(": "agregacion min()",
    r"\bmax\s*\(": "agregacion max()",
    r"\btotal\s*\(": "agregacion total()",
    r"\bgroup_concat\s*\(": "agregacion group_concat()",
    r"\brank\s*\(": "funcion de ranking rank()",
    r"\bbm25\s*\(": "funcion de ranking bm25()",
    r"\w*_fts\b": "tabla FTS",
    r"\bfts\d\b": "modulo FTS",
    r"\w*_content\b": "tabla sombra",
    r"\w*_docsize\b": "tabla sombra",
    r"\w*_idx\b": "tabla sombra",
    r"\w*_config\b": "tabla sombra",
    r"\w*_data\b": "tabla sombra",
}


def fallos_sql_de_sonda(sql: str, *, tabla_canonica: str, columna_pk: str) -> tuple[str, ...]:
    """Rechaza toda construccion prohibida en las sondas SQLite de F.

    Exige ademas que la consulta sea un ``SELECT`` sobre la tabla canonica
    declarada y filtre por su clave primaria con parametro enlazado.
    """
    fallos: list[str] = []
    texto = " ".join(sql.split()).lower()

    for patron, etiqueta in _PROHIBIDO_SQL.items():
        if re.search(patron, texto):
            fallos.append(f"construccion prohibida en sonda de F: {etiqueta}")

    if not texto.startswith("select "):
        fallos.append("la sonda debe ser un SELECT")
    if f" from {tabla_canonica.lower()} " not in f"{texto} ":
        fallos.append(f"la sonda debe consultar la tabla canonica {tabla_canonica}")
    if not re.search(rf"\bwhere\b\s+{re.escape(columna_pk.lower())}\s*=\s*\?", texto):
        fallos.append(f"la sonda debe filtrar por clave primaria {columna_pk} con parametro")

    return tuple(dict.fromkeys(fallos))


def comprobar_composicion_f(nombres: Sequence[str]) -> tuple[str, ...]:
    """F debe contener exactamente las tres sondas normativas."""
    fallos: list[str] = []
    if tuple(nombres) != F_NORMATIVO:
        fallos.append(f"F debe ser exactamente {list(F_NORMATIVO)}; se recibio {list(nombres)}")
    for nombre in nombres:
        minusculas = nombre.lower()
        for prohibido in PROHIBIDOS_EN_F:
            if prohibido.lower() in minusculas:
                fallos.append(f"sonda prohibida en F: {nombre}")
    return tuple(dict.fromkeys(fallos))
