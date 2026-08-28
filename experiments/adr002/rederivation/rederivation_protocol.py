"""Rederivacion de la linea base sobre el corpus congelado (TOL-208, paquete 10).

No mide. No abre ficheros. No ejecuta nada al importarse. **Este modulo NO
ejecuta T0**: preinscribe como se hara cuando exista la autorizacion.

QUE FALTA PARA CERRAR TOL-208
=============================

`ADR002-TOL-208` fija una regla de arranque en tres pasos, y **en ese orden**:

    1. congelar el corpus definitivo del benchmark   -> COMPLETADO (v0.4)
    2. ejecutar T0 sobre ese mismo corpus            -> pendiente
    3. rederivar la comparacion de linea base        -> pendiente

Los pasos 2 y 3 son lo unico que queda de las cinco puertas de arranque. Este
paquete los deja **preinscritos y ejecutables**, sin ejecutarlos.

POR QUE HAY QUE REDERIVAR Y NO REUTILIZAR
=========================================

La linea base historica se midio sobre el corpus 5.000/500 con **cinco**
sesiones. Las cifras vigentes de TOL-107 exigen **once**, y la regla 5 declara
`NO_COMPARABLE` cualquier rango obtenido con otro numero: `(max - min)` es un
rango y la esperanza de un rango crece con el tamano de la muestra.

De ahi que el perfil aprobado **no pueda pronunciarse** sobre FTS5 ni sobre
`rank()`. Rederivar no es repetir por gusto: es la unica via para que la linea
base vuelva a ser comparable, y es exactamente lo que el paso 3 ordena.

La linea base historica **no se remide ni se sustituye**: permanece congelada
con su head y sus ficheros. Lo que se produce es una medicion NUEVA sobre el
corpus definitivo, que se publica aparte.

LA GUARDA DE AUTORIZACION
=========================

Ejecutar T0 requiere **autorizacion expresa e independiente**, y ninguna acta
la ha dado. El recorrido lo comprueba contra el repositorio: sin el acta de
autorizacion presente, **se bloquea antes de tocar nada**. La guarda no es una
advertencia en un comentario: es una precondicion que falla cerrado.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.tolerances import profile_protocol as pp

# --------------------------------------------------------------------------
# Identidad
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "rederivacion-linea-base-0.1"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_10_TOL208_REDERIVACION_T0_v0.1"
PROTOCOLO: Final = pp.PROTOCOLO
REGISTRO: Final = pp.REGISTRO

#: Acta que autorizaria ejecutar T0. **No existe todavia**, y por eso el
#: recorrido se bloquea. Su ausencia es la guarda, no un comentario.
ACTA_DE_AUTORIZACION: Final = "SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md"

#: Actas de puerta que deben existir ANTES de rederivar. Sin protocolo comun
#: aprobado, las cifras no serian utilizables; sin ficha, la ejecucion no
#: seria utilizable como evidencia.
ACTAS_EXIGIDAS: Final[tuple[str, ...]] = (
    cp.ACTA_TOL_207,
    cp.ACTA_TOL_209,
    cp.ACTA_TOL_210,
)

#: Corpus definitivo congelado por el acta v0.4. La rederivacion se ejecuta
#: sobre EL MISMO corpus, o no es la rederivacion que TOL-208 ordena.
ACTA_CORPUS: Final = "SIRIUS_0.2_ADR_002_CONGELACION_CORPUS_v0.4_APROBADA.md"
CORPUS_CONGELADO: Final[Mapping[str, str]] = {
    "experiments/adr002/benchmark/conformance_corpus_v0_4.json": (
        "c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48"
    ),
    "experiments/adr002/benchmark/performance_corpus_v0_2.json": (
        "4e9e2746e49b158a43eda7826b47c78c41b36e90"
    ),
}

#: Linea base historica. Se conserva intacta: no se remide ni se sustituye.
LINEA_BASE_HISTORICA: Final = "artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json"
BLOB_LINEA_BASE: Final = "f9f051332d9833fb7e10b27f4820849f00b6fe6c"
SESIONES_LINEA_BASE_HISTORICA: Final = 5

#: Head de Alembic que identifica a T0 (Resolucion de la particion §3).
HEAD_T0: Final = "61be4bb269bf"
CANDIDATO: Final = cp.CONTROL

# --------------------------------------------------------------------------
# Plan de medicion, preinscrito
# --------------------------------------------------------------------------

#: Escenarios de la linea base historica. Se conservan **identicos** para que
#: la rederivacion sea comparable con lo que sustituye en funcion, no una
#: medicion distinta con el mismo nombre.
ESCENARIOS: Final[tuple[str, ...]] = (
    "cero_resultados",
    "un_resultado_exacto",
    "muchos_candidatos",
)

#: Las dos capas que la linea base separa: el indice lexico solo, y la
#: recuperacion completa con el barrido que RF-14 prohibe.
CAPAS: Final[tuple[str, ...]] = ("solo_indice_fts5", "recuperacion_completa_rank")

#: Exactamente once, por TOL-107 y el §3.3 del protocolo v0.2. No "al menos".
SESIONES_EXIGIDAS: Final = pp.SESIONES_EXIGIDAS
#: §3.1 y §3.2 del protocolo: 100 cuando el coste es bajo, y estas consultas
#: son de sub-milisegundo a decena de milisegundo.
REPETICIONES: Final = 100
REPETICIONES_MINIMAS: Final = cp.REPETICIONES_MINIMAS

MOTIVO_SIN_AUTORIZACION: Final = "ejecutar_t0_no_esta_autorizado"
MOTIVO_SIN_FICHA: Final = "t0_no_tiene_ficha_congelada"
MOTIVO_PUERTA_PENDIENTE: Final = "acta_de_puerta_ausente"
MOTIVO_CORPUS_ALTERADO: Final = "corpus_congelado_alterado"
MOTIVO_LINEA_BASE_ALTERADA: Final = "linea_base_historica_alterada"


# --------------------------------------------------------------------------
# Precondiciones. Todas se comprueban ANTES de medir, y fallan cerrado.
# --------------------------------------------------------------------------

EntornoCustodia = pp.EntornoCustodia


def blob_git(contenido: bytes) -> str:
    """SHA-1 del objeto blob de Git para ``contenido``."""
    return pp.blob_git(contenido)


def _existe(entorno: EntornoCustodia, ruta: str) -> bool:
    try:
        entorno.leer_bytes(ruta)
    except OSError:
        return False
    return True


def fallos_de_autorizacion(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Sin acta de autorizacion, no se ejecuta T0. Sin excepcion.

    Es la guarda que separa «preparado» de «ejecutado». Se comprueba contra el
    repositorio: la autorizacion es un documento que existe o no existe, no una
    bandera de linea de ordenes que cualquiera pueda pasar.
    """
    if not _existe(entorno, f"docs/architecture/{ACTA_DE_AUTORIZACION}"):
        return (
            f"{MOTIVO_SIN_AUTORIZACION}: falta {ACTA_DE_AUTORIZACION}. Ejecutar T0 exige "
            f"autorizacion expresa e independiente, y ninguna acta la ha dado",
        )
    return ()


def fallos_de_puertas(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Las actas de TOL-207, TOL-209 y TOL-210 deben existir."""
    return tuple(
        f"{MOTIVO_PUERTA_PENDIENTE}: falta {acta}"
        for acta in ACTAS_EXIGIDAS
        if not _existe(entorno, f"docs/architecture/{acta}")
    )


def fallos_de_corpus(entorno: EntornoCustodia) -> tuple[str, ...]:
    """El corpus congelado, byte a byte.

    Rederivar sobre otro corpus no es rederivar: es medir otra cosa. El
    §2 del acta de congelacion dice que un solo byte distinto invalida la
    congelacion de ese artefacto.
    """
    fallos: list[str] = []
    for ruta, esperado in CORPUS_CONGELADO.items():
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"{MOTIVO_CORPUS_ALTERADO}: {ruta} ilegible")
            continue
        if observado != esperado:
            fallos.append(f"{MOTIVO_CORPUS_ALTERADO}: {ruta} ({observado} != {esperado})")
    return tuple(fallos)


def fallos_de_linea_base(entorno: EntornoCustodia) -> tuple[str, ...]:
    """La linea base historica no se toca: se conserva y se cita."""
    try:
        observado = blob_git(entorno.leer_bytes(LINEA_BASE_HISTORICA))
    except OSError:
        return (f"{MOTIVO_LINEA_BASE_ALTERADA}: {LINEA_BASE_HISTORICA} ilegible",)
    if observado != BLOB_LINEA_BASE:
        return (f"{MOTIVO_LINEA_BASE_ALTERADA}: {observado} != {BLOB_LINEA_BASE}",)
    return ()


def fallos_de_ficha(fichas_congeladas: Sequence[cp.FichaConfirmada]) -> tuple[str, ...]:
    """T0 necesita ficha congelada: TOL-210 lo exige de todo lo que se ejecuta.

    Una ejecucion sin ficha previa **no es utilizable como evidencia**, y por
    tanto rederivar sin ella produciria cifras inservibles.
    """
    vigentes = [
        f for f in fichas_congeladas if f.candidato == CANDIDATO and f.estado == cp.ESTADO_CONGELADA
    ]
    if not vigentes:
        return (
            f"{MOTIVO_SIN_FICHA}: {CANDIDATO} no tiene ficha CONGELADA; una ejecucion sin "
            f"ficha previa no es utilizable como evidencia (TOL-210)",
        )
    return ()


@dataclass(frozen=True, slots=True)
class Precondiciones:
    """Resultado de todas las comprobaciones previas a rederivar."""

    fallos: tuple[str, ...]

    @property
    def permite_ejecutar(self) -> bool:
        return not self.fallos


def comprobar_precondiciones(
    entorno: EntornoCustodia, *, fichas_congeladas: Sequence[cp.FichaConfirmada]
) -> Precondiciones:
    """Todas las guardas, en orden, sin cortocircuito.

    No se corta en el primer fallo a proposito: quien prepare la ejecucion
    debe ver **todo** lo que le falta, no descubrirlo de uno en uno.
    """
    fallos: list[str] = []
    fallos.extend(fallos_de_autorizacion(entorno))
    fallos.extend(fallos_de_puertas(entorno))
    fallos.extend(fallos_de_corpus(entorno))
    fallos.extend(fallos_de_linea_base(entorno))
    fallos.extend(fallos_de_ficha(fichas_congeladas))
    return Precondiciones(fallos=tuple(dict.fromkeys(fallos)))


# --------------------------------------------------------------------------
# Magnitudes que la rederivacion producira
# --------------------------------------------------------------------------


def magnitudes_previstas() -> tuple[str, ...]:
    """Las seis magnitudes de la linea base, escenario por capa."""
    return tuple(f"{escenario}.{capa}" for escenario in ESCENARIOS for capa in CAPAS)


def evaluar_magnitud_rederivada(
    p50_por_sesion: Sequence[int], p95_por_sesion: Sequence[int], *, perfil: pp.Perfil
) -> pp.VeredictoMagnitud:
    """Evalua una magnitud rederivada contra el perfil aprobado.

    Se delega enteramente en ``profile_protocol``: la rederivacion **no
    inventa un criterio propio**. Con once sesiones, la magnitud deja de ser
    ``NO_COMPARABLE`` y por primera vez recibe veredicto.
    """
    return pp.evaluar_magnitud(p50_por_sesion, p95_por_sesion, perfil=perfil)


def deja_de_ser_no_comparable(sesiones: int) -> bool:
    """Lo que cambia con la rederivacion: el tamano de muestra, no el criterio."""
    return sesiones == SESIONES_EXIGIDAS


# --------------------------------------------------------------------------
# Controles internos preinscritos
# --------------------------------------------------------------------------

CONTROLES_BLOQUEANTES: Final[tuple[str, ...]] = (
    "autorizacion_expresa_presente",
    "actas_de_puerta_presentes",
    "corpus_congelado_intacto",
    "linea_base_historica_intacta",
    "ficha_de_t0_congelada_y_anterior",
    "once_sesiones_completas",
    "repeticiones_suficientes",
    "percentiles_por_rango_mas_cercano",
    "escenarios_y_capas_identicos_a_la_linea_base",
    "veredictos_delegados_al_perfil_aprobado",
    "sin_sustituir_la_linea_base_historica",
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
    return ResultadoControles(
        fallos=tuple(c for c in CONTROLES_BLOQUEANTES if estado.get(c) is not True)
    )
