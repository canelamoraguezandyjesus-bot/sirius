"""Perfil de tolerancias P50/P95 (ADR002-TOL-209, paquete 08).

Materializa la decision de gobierno recogida en
``SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0``: ``TOL-107``
**separa P50 y P95** y cada percentil recibe su propia regla.

No mide nada. No abre ficheros. No ejecuta nada al importarse. **No hay
medicion nueva**: la fuente es el artefacto congelado ``suelo_medicion_v0.3``
y todo se deriva de sus vectores crudos de forma determinista.

POR QUE SE SEPARAN LOS DOS PERCENTILES
======================================

El paquete 07 devolvio ``NO_EVALUABLE`` porque exigia a **ambos** percentiles
el mismo objetivo relativo del 20 %. Su propia evidencia mostro que la
exigencia es asimetrica:

- el peor ``D50(s)/s`` sobre las 32 filas medidas es **0,158**: el centro de
  la distribucion cabe holgadamente en el 20 % a las dieciseis escalas;
- el peor ``D95(s)/s`` por escala **nunca baja de 0,252**: la cola no cabe en
  el 20 % en ningun punto de la escalera.

Tratarlos con la misma vara hacia inalcanzable una puerta que el centro si
cumple. La fila TOL-107 ya registraba el sintoma —variacion P95 de FTS5 del
32,9-36,4 %, sin objetivo relativo propuesto para FTS5— sin extraer la
consecuencia.

LAS DOS REGLAS
==============

**P50.** Conserva el objetivo relativo ``<= 20 %``. Se deriva ``D50(s)``, su
envolvente monotona ``E50(s)`` y el cruce ``U50 = 5 E50(s_k)``. Por debajo de
``U50`` se aplica ``B50(M) = E50(escalon superior)``; por encima, el 20 %
relativo. Por debajo de ``SM`` no se emite afirmacion de latencia.

**P95.** Deja de estar sujeto al objetivo relativo. Se evalua **en todo el
rango cubierto** contra ``B95(M) = E95(escalon superior)``. **No se crea
umbral relativo para P95.** Por debajo de ``SM`` o por encima de la mayor
escala medida, ``NO_EVALUABLE``.

En ambos casos, ``M`` es el **minimo entre sesiones del mismo percentil que
se evalua**: ``B50`` se consulta en ``min_s P50`` y ``B95`` en ``min_s P95``.

ONCE SESIONES, EXACTAMENTE
==========================

``(max - min)`` es un **rango**, y la esperanza de un rango crece con el
numero de observaciones. Comparar un rango de cinco sesiones contra una banda
construida con once no compara estabilidad: compara tamanos de muestra.

Por eso ``SESIONES_EXIGIDAS`` es exactamente **11**, tanto para construir las
bandas como para evaluar candidatos, y toda magnitud medida con otro numero
de sesiones se declara ``NO_COMPARABLE`` sin veredicto. Esta guarda alcanza
tambien a la linea base historica, medida con cinco sesiones: se publica como
contraste y **jamas como veredicto**.

La maquinaria de envolvente, escalon superior y cruce se **hereda congelada**
del paquete 07 (``envelope_protocol``): lo que cambia es la separacion por
percentil, no la aritmetica.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Final

from experiments.adr002.tolerances import envelope_protocol as ep

# --------------------------------------------------------------------------
# Identidad
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "perfil-tolerancias-0.1"
ESTADO: Final = "PROPUESTO · PERFIL DERIVADO — NO APRUEBA TOL-209"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_08_TOL209_PERFIL_TOLERANCIAS_v0.1"
ACTA: Final = "SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0.md"

#: Protocolo y Registro ACTUALIZADOS. Los anteriores no se tocan: sus blobs
#: los citan las evidencias v0.1, v0.2 y v0.3 ya publicadas.
PROTOCOLO: Final = "SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md"
REGISTRO: Final = "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md"
PROTOCOLO_ANTERIOR: Final = "SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md"
REGISTRO_ANTERIOR: Final = "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md"

#: Fuente unica del perfil: la evidencia congelada del paquete 07.
FUENTE: Final = "artifacts/adr002_tolerances/suelo_medicion_v0.3.json"
BLOB_FUENTE: Final = "7273264879ec0d45861160066555c1f08b5882bc"
COMMIT_FUENTE: Final = "561b47c9084122efad4fe256242caaced34e7518"

#: Evidencias que se conservan intactas. Se comprueban byte a byte.
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
    "artifacts/adr002_tolerances/suelo_medicion_v0.3.json": BLOB_FUENTE,
    "artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.3_PROPUESTO.md": (
        "2c4da11a2254db923c307f3449988892643d7d9e"
    ),
}

ARCHIVOS_PREINSCRITOS: Final[tuple[str, ...]] = (
    "docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_08_TOL209_PERFIL_TOLERANCIAS_v0.1.md",
    "docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md",
    "docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0.md",
    "docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md",
    "experiments/adr002/tolerances/derive_profile.py",
    "experiments/adr002/tolerances/profile_protocol.py",
    "experiments/adr002/tolerances/schema_profile_v0_1.py",
    "experiments/adr002/tolerances/test_adr002_profile.py",
)

#: Maquinaria heredada congelada del paquete 07. La aritmetica de envolvente,
#: escalon superior y cruce ya esta auditada: reutilizarla en vez de copiarla
#: es lo que permite atribuir cualquier diferencia a la separacion por
#: percentil y no a una reimplementacion.
ARCHIVOS_HEREDADOS: Final[Mapping[str, str]] = {
    "experiments/adr002/tolerances/envelope_protocol.py": (
        "afa4a7fe0191c9bc20e283d9f3ab297869c8faad"
    ),
}

# --------------------------------------------------------------------------
# Constantes vinculantes
# --------------------------------------------------------------------------

#: Escalera y familias: las del paquete 07, heredadas sin cambio.
ESCALERA_NS: Final[tuple[int, ...]] = ep.ESCALERA_NS
FAMILIAS: Final[tuple[str, ...]] = ep.FAMILIAS
SONDAS_UNITARIAS: Final[tuple[str, ...]] = ep.SONDAS_UNITARIAS

PERCENTIL_P50: Final = "P50"
PERCENTIL_P95: Final = "P95"
PERCENTILES: Final[tuple[str, ...]] = (PERCENTIL_P50, PERCENTIL_P95)

#: Objetivo relativo congelado del Registro. Aplica SOLO a P50.
OBJETIVO_RELATIVO_NUM: Final = ep.OBJETIVO_RELATIVO_NUM
OBJETIVO_RELATIVO_DEN: Final = ep.OBJETIVO_RELATIVO_DEN
FACTOR_U: Final = ep.FACTOR_U

#: Derivado, no elegido: unica solucion de igualar los dos regimenes de P50
#: en la frontera ``M = U50``.
MARGEN_M: Final = ep.MARGEN_M

#: Exactamente once. No "al menos": exactamente. Un rango de otro numero de
#: sesiones no es comparable con estas bandas.
SESIONES_EXIGIDAS: Final = 11

REGIMEN_RELATIVO: Final = ep.REGIMEN_RELATIVO
REGIMEN_ABSOLUTO: Final = ep.REGIMEN_ABSOLUTO
NO_EVALUABLE: Final = ep.NO_EVALUABLE
NO_COMPARABLE: Final = "NO_COMPARABLE"

VALIDA: Final = "VALIDA"
INVALIDA: Final = "INVALIDA"

MOTIVO_BAJO_SM: Final = "por_debajo_del_suelo_del_instrumento"
MOTIVO_SOBRE_ESCALERA: Final = "por_encima_de_la_mayor_escala_medida"
MOTIVO_SESIONES: Final = "numero_de_sesiones_distinto_del_exigido"
MOTIVO_SIN_U50: Final = "sin_cruce_p50_resuelto"


class PerfilInvalidoError(ValueError):
    """El perfil no se puede derivar de la fuente proporcionada."""


class InvarianteVioladoError(ValueError):
    """Se violo un invariante demostrable del metodo."""


# --------------------------------------------------------------------------
# Percentiles: heredados, por rango mas cercano
# --------------------------------------------------------------------------


def percentil_ns(ordenadas: Sequence[int], fraccion_num: int, fraccion_den: int) -> int:
    """Percentil por rango mas cercano (§4.1 del protocolo). Nunca interpola."""
    return ep.percentil_ns(ordenadas, fraccion_num, fraccion_den)


def p50_ns(muestras: Sequence[int]) -> int:
    """P50 nearest-rank."""
    return ep.p50_ns(muestras)


def p95_ns(muestras: Sequence[int]) -> int:
    """P95 nearest-rank."""
    return ep.p95_ns(muestras)


def razon_por_mil(valor_ns: int, escala_ns: int) -> int:
    """Razon en milesimas, truncada. El artefacto no usa coma flotante."""
    return ep.razon_por_mil(valor_ns, escala_ns)


def fraccion_por_mil(numerador: int, denominador: int) -> int:
    """``numerador / denominador`` en milesimas, truncado, en enteros."""
    if denominador <= 0:
        msg = "el denominador debe ser positivo"
        raise ValueError(msg)
    return 1000 * numerador // denominador


# --------------------------------------------------------------------------
# Observaciones de la fuente
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ObservacionEscala:
    """Un vector medido de una ``(familia, escala)`` en un proceso."""

    familia: str
    escala_ns: int
    pid: int
    p50: int
    p95: int


@dataclass(frozen=True, slots=True)
class ObservacionUnitaria:
    """Un vector medido de una sonda de suelo unitario en un proceso."""

    sonda: str
    pid: int
    p95: int


def comprobar_cobertura(observaciones: Sequence[ObservacionEscala]) -> None:
    """Toda ``(familia, escala)`` con EXACTAMENTE ``SESIONES_EXIGIDAS`` sesiones.

    Exactamente, no "al menos": la banda se construye con un rango, y un
    rango de otro tamano de muestra no es la misma magnitud estadistica.

    Se comprueban las TRES cosas que hacen falta para que ese "exactamente"
    signifique algo, y no solo dos:

    1. **once identificadores distintos** por ``(familia, escala)``;
    2. **once filas**, es decir **una sola observacion por sesion**: si una
       sesion aportase dos vectores al mismo par, el rango se tomaria sobre
       doce observaciones aunque los identificadores siguiesen siendo once, y
       la esperanza del rango ya no seria la de las bandas;
    3. **las mismas once sesiones en toda la escalera**: sin esto, "once
       sesiones completas independientes" no se hace cumplir en ningun punto
       y la envolvente podria mezclar poblaciones distintas escalon a escalon.
    """
    familias = {o.familia for o in observaciones}
    if familias - set(FAMILIAS):
        msg = f"familias ajenas: {sorted(familias - set(FAMILIAS))}"
        raise PerfilInvalidoError(msg)
    escalas = {o.escala_ns for o in observaciones}
    if escalas - set(ESCALERA_NS):
        msg = f"escalas ajenas a la escalera: {sorted(escalas - set(ESCALERA_NS))}"
        raise PerfilInvalidoError(msg)
    referencia: frozenset[int] | None = None
    for escala in ESCALERA_NS:
        for familia in FAMILIAS:
            filas = [o for o in observaciones if o.familia == familia and o.escala_ns == escala]
            pids = frozenset(o.pid for o in filas)
            if len(pids) != SESIONES_EXIGIDAS:
                msg = (
                    f"{familia}@{escala} ns: {len(pids)} sesiones distintas; "
                    f"se exigen exactamente {SESIONES_EXIGIDAS}"
                )
                raise PerfilInvalidoError(msg)
            if len(filas) != SESIONES_EXIGIDAS:
                msg = (
                    f"{familia}@{escala} ns: {len(filas)} observaciones para "
                    f"{len(pids)} sesiones; se exige una por sesion"
                )
                raise PerfilInvalidoError(msg)
            if referencia is None:
                referencia = pids
            elif pids != referencia:
                msg = (
                    f"{familia}@{escala} ns no lo midieron las mismas sesiones que el "
                    f"resto de la escalera"
                )
                raise PerfilInvalidoError(msg)


def dispersion_de_familia(
    observaciones: Sequence[ObservacionEscala], familia: str, escala_ns: int, percentil: str
) -> int:
    """``max - min`` entre sesiones del percentil de una ``(familia, escala)``."""
    if percentil not in PERCENTILES:
        msg = f"percentil no normativo: {percentil}"
        raise ValueError(msg)
    seleccion = [o for o in observaciones if o.familia == familia and o.escala_ns == escala_ns]
    if not seleccion:
        msg = f"falta la sonda {familia}@{escala_ns} ns"
        raise PerfilInvalidoError(msg)
    valores = [o.p50 if percentil == PERCENTIL_P50 else o.p95 for o in seleccion]
    return max(valores) - min(valores)


def dispersion_de_escala(
    observaciones: Sequence[ObservacionEscala], escala_ns: int, percentil: str
) -> int:
    """``D_p(s)``: peor dispersion del percentil ``p`` entre las dos familias.

    A diferencia del paquete 07, **no** se toma el peor caso sobre percentiles:
    cada percentil construye su propia curva. Esa es la separacion.
    """
    return max(
        dispersion_de_familia(observaciones, familia, escala_ns, percentil) for familia in FAMILIAS
    )


def construir_envolvente(
    observaciones: Sequence[ObservacionEscala], percentil: str
) -> ep.Envolvente:
    """``D_p(s)`` y su envolvente monotona ``E_p(s) = max acumulado``."""
    comprobar_cobertura(observaciones)
    dispersiones = tuple(dispersion_de_escala(observaciones, s, percentil) for s in ESCALERA_NS)
    acumulado: list[int] = []
    peor = 0
    for valor in dispersiones:
        peor = max(peor, valor)
        acumulado.append(peor)
    return ep.Envolvente(dispersiones=dispersiones, envolvente=tuple(acumulado))


def calcular_sm(unitarias: Sequence[ObservacionUnitaria]) -> int:
    """``SM``: peor P95 de las sondas de suelo unitario, sobre las 11 sesiones."""
    presentes = {o.sonda for o in unitarias}
    faltan = sorted(s for s in SONDAS_UNITARIAS if s not in presentes)
    if faltan:
        msg = f"faltan sondas unitarias: {faltan}"
        raise PerfilInvalidoError(msg)
    intrusas = sorted(s for s in presentes if s not in SONDAS_UNITARIAS)
    if intrusas:
        msg = f"sondas unitarias ajenas: {intrusas}"
        raise PerfilInvalidoError(msg)
    referencia: frozenset[int] | None = None
    for sonda in SONDAS_UNITARIAS:
        filas = [o for o in unitarias if o.sonda == sonda]
        pids = frozenset(o.pid for o in filas)
        if len(pids) != SESIONES_EXIGIDAS:
            msg = (
                f"{sonda}: {len(pids)} sesiones distintas; "
                f"se exigen exactamente {SESIONES_EXIGIDAS}"
            )
            raise PerfilInvalidoError(msg)
        if len(filas) != SESIONES_EXIGIDAS:
            msg = f"{sonda}: {len(filas)} observaciones para {len(pids)} sesiones"
            raise PerfilInvalidoError(msg)
        if referencia is None:
            referencia = pids
        elif pids != referencia:
            msg = f"{sonda} no lo midieron las mismas sesiones que el resto de las sondas"
            raise PerfilInvalidoError(msg)
    return max(o.p95 for o in unitarias)


def sesiones_de_la_fuente(
    observaciones: Sequence[ObservacionEscala], unitarias: Sequence[ObservacionUnitaria]
) -> frozenset[int]:
    """Identificadores de sesion presentes en TODA la fuente, escalas y sondas."""
    return frozenset({o.pid for o in observaciones} | {u.pid for u in unitarias})


# --------------------------------------------------------------------------
# El perfil
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Perfil:
    """Perfil de tolerancias derivado: una regla por percentil.

    ``cruce_p50`` es el cruce ``B50(M) = 0,20 M`` resuelto con la maquinaria
    heredada del paquete 07. ``envolvente_p95`` no tiene cruce: P95 se evalua
    en absoluto en todo el rango cubierto, por decision de gobierno.
    """

    sm_ns: int
    cruce_p50: ep.Cruce
    envolvente_p95: ep.Envolvente
    sesiones: int

    def __post_init__(self) -> None:
        """``sesiones`` no es un campo libre: solo hay un valor admisible.

        Sin esta comprobacion, un perfil construido a mano con otro numero
        haria que la guarda de ``evaluar_magnitud`` exigiese "lo que diga el
        perfil" en vez de los once que exige la regla 5.
        """
        if self.sesiones != SESIONES_EXIGIDAS:
            msg = (
                f"un perfil se construye con exactamente {SESIONES_EXIGIDAS} sesiones, "
                f"no con {self.sesiones}"
            )
            raise PerfilInvalidoError(msg)

    @property
    def u50_ns(self) -> int | None:
        return self.cruce_p50.u

    @property
    def b50_en_u50_ns(self) -> int | None:
        return self.cruce_p50.b_en_u

    @property
    def cubierto_hasta_ns(self) -> int:
        """Mayor escala medida. Por encima, P95 no tiene banda y es NO_EVALUABLE."""
        return ESCALERA_NS[-1]

    def banda_p50(self, magnitud_ns: int) -> int:
        """``B50(M) = E50(escalon superior)``."""
        return self.cruce_p50.envolvente.banda(magnitud_ns)

    def banda_p95(self, magnitud_ns: int) -> int:
        """``B95(M) = E95(escalon superior)``."""
        return self.envolvente_p95.banda(magnitud_ns)


def derivar_perfil(
    observaciones: Sequence[ObservacionEscala],
    unitarias: Sequence[ObservacionUnitaria],
) -> Perfil:
    """Deriva el perfil completo. Determinista: misma entrada, misma salida."""
    envolvente_p50 = construir_envolvente(observaciones, PERCENTIL_P50)
    envolvente_p95 = construir_envolvente(observaciones, PERCENTIL_P95)
    # Caso degenerado que la separacion por percentil hace alcanzable y el
    # paquete 07 no tenia: con D50(s_1) = 0 el cruce se resuelve en U50 = 0,
    # que la maquinaria heredada —demostrada para E(s_k) > 0— no admite. Se
    # denuncia con un error propio y legible en vez de propagar el invariante
    # violado de un modulo congelado que no se puede tocar.
    if envolvente_p50.envolvente[0] == 0:
        msg = (
            "dispersion P50 nula en el primer escalon: el cruce U50 degenera a 0 y este "
            "metodo no lo resuelve; con SM > 0 esa dispersion no se distingue de la "
            "resolucion del instrumento"
        )
        raise PerfilInvalidoError(msg)
    cruce_p50 = ep.resolver_cruce(envolvente_p50)
    return Perfil(
        sm_ns=calcular_sm(unitarias),
        cruce_p50=cruce_p50,
        envolvente_p95=envolvente_p95,
        sesiones=SESIONES_EXIGIDAS,
    )


# --------------------------------------------------------------------------
# Evaluacion de una magnitud
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VeredictoPercentil:
    """Veredicto de un percentil concreto de una magnitud."""

    percentil: str
    minimo: int
    maximo: int
    dispersion: int
    regimen: str | None
    banda_ns: int | None
    variacion_por_mil: int | None
    resultado: str
    motivo: str | None


@dataclass(frozen=True, slots=True)
class VeredictoMagnitud:
    """Veredicto agregado de una magnitud sobre sus dos percentiles."""

    sesiones: int
    p50: VeredictoPercentil
    p95: VeredictoPercentil
    resultado: str
    motivo: str | None


def pasa_relativo(minimo: int, maximo: int) -> bool:
    """``(max - min) / min <= 0,20`` en aritmetica entera exacta."""
    return ep.pasa_relativo(minimo, maximo)


def pasa_absoluto(minimo: int, maximo: int, banda: int) -> bool:
    """``(max - min) <= m * B(M)``."""
    return ep.pasa_absoluto(minimo, maximo, banda)


def _no_evaluable(percentil: str, minimo: int, maximo: int, motivo: str) -> VeredictoPercentil:
    return VeredictoPercentil(
        percentil=percentil,
        minimo=minimo,
        maximo=maximo,
        dispersion=maximo - minimo,
        regimen=None,
        banda_ns=None,
        variacion_por_mil=None,
        resultado=NO_EVALUABLE,
        motivo=motivo,
    )


def evaluar_p50(minimo: int, maximo: int, perfil: Perfil) -> VeredictoPercentil:
    """Regla de P50: relativo por encima de ``U50``, banda por debajo.

    Por debajo de ``SM`` no se emite afirmacion de latencia.
    """
    if minimo < perfil.sm_ns:
        return _no_evaluable(PERCENTIL_P50, minimo, maximo, MOTIVO_BAJO_SM)
    u50 = perfil.u50_ns
    if u50 is None:
        return _no_evaluable(PERCENTIL_P50, minimo, maximo, MOTIVO_SIN_U50)

    variacion = fraccion_por_mil(maximo - minimo, minimo) if minimo > 0 else None
    if minimo >= u50:
        return VeredictoPercentil(
            percentil=PERCENTIL_P50,
            minimo=minimo,
            maximo=maximo,
            dispersion=maximo - minimo,
            regimen=REGIMEN_RELATIVO,
            banda_ns=None,
            variacion_por_mil=variacion,
            resultado=VALIDA if pasa_relativo(minimo, maximo) else INVALIDA,
            motivo=None,
        )
    banda = perfil.banda_p50(minimo)
    return VeredictoPercentil(
        percentil=PERCENTIL_P50,
        minimo=minimo,
        maximo=maximo,
        dispersion=maximo - minimo,
        regimen=REGIMEN_ABSOLUTO,
        banda_ns=banda,
        variacion_por_mil=variacion,
        resultado=VALIDA if pasa_absoluto(minimo, maximo, banda) else INVALIDA,
        motivo=None,
    )


def evaluar_p95(minimo: int, maximo: int, perfil: Perfil) -> VeredictoPercentil:
    """Regla de P95: banda en TODO el rango cubierto. Sin umbral relativo.

    ``NO_EVALUABLE`` por debajo de ``SM`` o por encima de la mayor escala
    medida, donde la envolvente no esta definida.
    """
    if minimo < perfil.sm_ns:
        return _no_evaluable(PERCENTIL_P95, minimo, maximo, MOTIVO_BAJO_SM)
    if minimo > perfil.cubierto_hasta_ns:
        return _no_evaluable(PERCENTIL_P95, minimo, maximo, MOTIVO_SOBRE_ESCALERA)
    banda = perfil.banda_p95(minimo)
    return VeredictoPercentil(
        percentil=PERCENTIL_P95,
        minimo=minimo,
        maximo=maximo,
        dispersion=maximo - minimo,
        regimen=REGIMEN_ABSOLUTO,
        banda_ns=banda,
        variacion_por_mil=fraccion_por_mil(maximo - minimo, minimo) if minimo > 0 else None,
        resultado=VALIDA if pasa_absoluto(minimo, maximo, banda) else INVALIDA,
        motivo=None,
    )


def evaluar_magnitud(
    p50_por_sesion: Sequence[int],
    p95_por_sesion: Sequence[int],
    *,
    perfil: Perfil,
) -> VeredictoMagnitud:
    """Evalua una magnitud contra el perfil. Falla cerrado.

    La guarda de sesiones va PRIMERO: comparar un rango de ``n`` sesiones
    contra una banda construida con once no compara estabilidad, compara
    tamanos de muestra. Sin el mismo ``n``, no hay veredicto.
    """
    if not p50_por_sesion or not p95_por_sesion:
        msg = "faltan percentiles por sesion"
        raise ValueError(msg)
    if len(p50_por_sesion) != len(p95_por_sesion):
        msg = "numero de sesiones incoherente entre P50 y P95"
        raise ValueError(msg)

    sesiones = len(p50_por_sesion)
    min50, max50 = min(p50_por_sesion), max(p50_por_sesion)
    min95, max95 = min(p95_por_sesion), max(p95_por_sesion)

    if min95 < min50:
        msg = f"invariante violado: min_s P95 ({min95}) < min_s P50 ({min50})"
        raise InvarianteVioladoError(msg)

    if sesiones != SESIONES_EXIGIDAS:
        return VeredictoMagnitud(
            sesiones=sesiones,
            p50=_no_evaluable(PERCENTIL_P50, min50, max50, MOTIVO_SESIONES),
            p95=_no_evaluable(PERCENTIL_P95, min95, max95, MOTIVO_SESIONES),
            resultado=NO_COMPARABLE,
            motivo=MOTIVO_SESIONES,
        )

    v50 = evaluar_p50(min50, max50, perfil)
    v95 = evaluar_p95(min95, max95, perfil)
    return VeredictoMagnitud(
        sesiones=sesiones,
        p50=v50,
        p95=v95,
        resultado=agregar(v50, v95),
        motivo=None,
    )


def agregar(v50: VeredictoPercentil, v95: VeredictoPercentil) -> str:
    """Agrega los dos veredictos por percentil en el de la magnitud.

    Un percentil ``NO_EVALUABLE`` no emite afirmacion. La consecuencia se
    toma en la direccion conservadora, que es la unica compatible con
    "reparte la exigencia, no la relaja":

    - **basta un fallo** para que la magnitud falle: una afirmacion NEGATIVA
      se sostiene con un solo percentil que la respalde;
    - **hace falta que los dos sean evaluables y validos** para que la
      magnitud sea valida: una afirmacion POSITIVA de estabilidad sobre una
      magnitud cuya cola no se evaluo —por ejemplo por quedar por encima de
      la mayor escala medida, que es justo el caso que la regla de P95
      ordena declarar ``NO_EVALUABLE``— seria una afirmacion sin respaldo.
    """
    resultados = [v.resultado for v in (v50, v95)]
    if INVALIDA in resultados:
        return INVALIDA
    if NO_EVALUABLE in resultados:
        return NO_EVALUABLE
    return VALIDA


def registro_por_percentil(veredicto: VeredictoMagnitud) -> str:
    """Cadena para el campo unico ``Regimen aplicable`` de la ficha aprobada."""
    if veredicto.resultado == NO_COMPARABLE:
        return NO_COMPARABLE
    partes: list[str] = []
    for v in (veredicto.p50, veredicto.p95):
        partes.append(f"{v.percentil}: {v.regimen or v.resultado}")
    return " · ".join(partes)


# --------------------------------------------------------------------------
# Propiedades demostrables, comprobadas en ejecucion
# --------------------------------------------------------------------------


def bandas_no_decrecientes(perfil: Perfil) -> bool:
    """Ninguna de las dos bandas se estrecha al crecer la magnitud (M-03)."""
    return ep.banda_no_decreciente(perfil.cruce_p50.envolvente) and ep.banda_no_decreciente(
        perfil.envolvente_p95
    )


def envolventes_monotonas(perfil: Perfil) -> bool:
    """``E50`` y ``E95`` no decrecen."""
    return perfil.cruce_p50.envolvente.es_monotona() and perfil.envolvente_p95.es_monotona()


def envolventes_cubren_el_suelo(perfil: Perfil) -> bool:
    """``E_p(s_i) >= D_p(s_i)`` en todo escalon y para los dos percentiles."""
    return perfil.cruce_p50.envolvente.cubre_el_suelo() and perfil.envolvente_p95.cubre_el_suelo()


def continuidad_p50_exacta(perfil: Perfil) -> bool:
    """``m * B50(U50) = 0,20 U50`` sin resto."""
    return ep.continuidad_exacta(perfil.cruce_p50)


def p95_domina_a_p50(perfil: Perfil) -> bool:
    """``E95(s) >= E50(s)`` en todo escalon.

    No es un axioma: es una consecuencia de que, en cada sesion, el P95 no
    puede quedar por debajo del P50, y de que la evidencia lo confirma en las
    dieciseis escalas. Se comprueba, y si fallase se denunciaria en vez de
    suponerse: significaria que la cola es MAS estable que el centro, algo
    que invalidaria la lectura del perfil.
    """
    return all(
        e95 >= e50
        for e50, e95 in zip(
            perfil.cruce_p50.envolvente.envolvente,
            perfil.envolvente_p95.envolvente,
            strict=True,
        )
    )


def escalera_estrictamente_creciente() -> bool:
    """La escalera heredada sigue siendo estrictamente creciente."""
    return all(a < b for a, b in pairwise(ESCALERA_NS))


def p95_sin_umbral_relativo(perfil: Perfil) -> bool:
    """``evaluar_p95`` no aplica NINGUN criterio relativo. Se interroga, no se declara.

    Que el artefacto no publique un umbral solo cierra la puerta declarativa.
    Esta funcion cierra la operativa preguntandole al propio perfil, punto a
    punto del rango cubierto:

    1. **el regimen es siempre el absoluto**, nunca el relativo;
    2. **lo que vincula es la banda**: con dispersion exactamente ``B95(M)``
       la magnitud es valida y con un nanosegundo mas es invalida;
    3. **el 20 % no se aplica**: existe al menos un punto donde la magnitud
       valida del apartado 2 tiene una variacion relativa **superior** al
       20 %. Si hubiese umbral relativo, ahi saldria invalida.

    Sin el apartado 3 la comprobacion seria vacia: una banda siempre mas
    estrecha que el 20 % no permitiria distinguir un metodo del otro. Por eso
    la ausencia de ese punto devuelve ``False`` y bloquea, en vez de dar por
    bueno lo que no se ha podido demostrar.
    """
    demostrado = False
    for minimo in (perfil.sm_ns, *(s for s in ESCALERA_NS if s >= perfil.sm_ns)):
        banda = perfil.banda_p95(minimo)
        dentro = evaluar_p95(minimo, minimo + banda, perfil)
        fuera = evaluar_p95(minimo, minimo + banda + 1, perfil)
        if dentro.regimen != REGIMEN_ABSOLUTO or fuera.regimen != REGIMEN_ABSOLUTO:
            return False
        if dentro.resultado != VALIDA or fuera.resultado != INVALIDA:
            return False
        demostrado = demostrado or not pasa_relativo(minimo, minimo + banda)
    return demostrado


# --------------------------------------------------------------------------
# Controles internos preinscritos
# --------------------------------------------------------------------------

CONTROLES_BLOQUEANTES: Final[tuple[str, ...]] = (
    "fuente_intacta",
    "fuente_con_once_sesiones",
    "escalera_completa",
    "percentiles_recomputados",
    "envolventes_monotonas",
    "envolventes_cubren_el_suelo",
    "bandas_no_decrecientes",
    "continuidad_p50_exacta",
    "p95_no_mas_estable_que_p50",
    "sin_umbral_relativo_para_p95",
    "guarda_de_sesiones_activa",
    "evidencias_anteriores_intactas",
    "documentos_de_gobierno_intactos",
    "derivacion_determinista",
    "custodia_verificada",
)

#: Controles que presuponen un cruce P50 resuelto.
CONTROLES_QUE_EXIGEN_U50: Final[tuple[str, ...]] = ("continuidad_p50_exacta",)


@dataclass(frozen=True, slots=True)
class ResultadoControles:
    """Resultado agregado de los controles internos preinscritos."""

    fallos: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.fallos


def evaluar_controles(estado: Mapping[str, bool]) -> ResultadoControles:
    """Falla cerrado: un control ausente o distinto de ``True`` es fallido."""
    return ResultadoControles(
        fallos=tuple(c for c in CONTROLES_BLOQUEANTES if estado.get(c) is not True)
    )


# --------------------------------------------------------------------------
# Custodia. Se reutiliza el entorno inyectable del paquete 07.
# --------------------------------------------------------------------------

EntornoCustodia = ep.EntornoCustodia


def blob_git(contenido: bytes) -> str:
    """SHA-1 del objeto blob de Git para ``contenido``."""
    return ep.blob_git(contenido)


def fallos_evidencias_anteriores(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Las seis evidencias v0.1, v0.2 y v0.3 deben seguir byte a byte."""
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


def fallos_documentos_de_gobierno(entorno: EntornoCustodia) -> tuple[str, ...]:
    """El protocolo y el Registro ANTERIORES no se tocan.

    Sus blobs los citan las evidencias v0.1, v0.2 y v0.3 ya publicadas: si
    cambiasen, la custodia de esa evidencia dejaria de poder comprobarse. Por
    eso el paquete 08 publica versiones NUEVAS en vez de editarlas.
    """
    fallos: list[str] = []
    anteriores = {
        f"docs/architecture/{PROTOCOLO_ANTERIOR}": ep.BLOB_PROTOCOLO_APROBADO,
        f"docs/architecture/{REGISTRO_ANTERIOR}": ep.BLOB_REGISTRO_ACTUALIZADO,
    }
    for ruta, esperado in anteriores.items():
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"documento de gobierno anterior ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(
                f"documento de gobierno anterior alterado: {ruta} ({observado} != {esperado})"
            )
    return tuple(fallos)


def verificar_custodia(
    entorno: EntornoCustodia,
    *,
    sha_a: str,
    blobs_preinscritos: Mapping[str, str],
    blobs_heredados: Mapping[str, str],
) -> tuple[str, ...]:
    """Comprueba la cadena preinscripcion -> perfil y devuelve los fallos."""
    fallos: list[str] = []

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

    fallos.extend(fallos_documentos_de_gobierno(entorno))
    fallos.extend(fallos_evidencias_anteriores(entorno))

    if not entorno.diff_vacio(sha_a, entorno.head(), ARCHIVOS_PREINSCRITOS):
        fallos.append("diff no vacio en los ficheros preinscritos entre A y HEAD")

    return tuple(dict.fromkeys(fallos))


def verificar_precondiciones(
    entorno: EntornoCustodia, *, sha_a: str, salida_existe: bool
) -> tuple[str, ...]:
    """Comprobaciones exigidas ANTES de derivar. Falla cerrado."""
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
