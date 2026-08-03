"""Los siete criterios de parada ``S1-S7`` de ``B04 §15.3``.

Toda ejecucion termina con **exactamente una** parada adjudicada y registrada.
Una recuperacion que se detuviera sin decir por que seria irreproducible, y
``B04-RF-29`` exige el criterio de parada dentro del plan.

La regla que mas se olvida esta hecha estructura aqui: **``S1`` no existe en
``EXHAUSTIVA``**. Una busqueda exhaustiva no puede declararse suficiente por
cuota; debe agotar los espacios autorizados o terminar por ``S2-S7``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from experiments.adr002.candidates.common.contracts import (
    Candidata,
    Cardinalidad,
    Criticidad,
    Etapa,
    Peticion,
)

PARADAS: Final[tuple[tuple[str, str], ...]] = (
    ("S1", "suficiencia por cardinalidad; nunca en EXHAUSTIVA"),
    ("S2", "el modo o proposito no autoriza el siguiente espacio"),
    ("S3", "ambiguedad material: expandir cambiaria entidad, ambito, tiempo o significado"),
    ("S4", "limite duro fijado que no puede ampliarse"),
    ("S5", "agotamiento autorizado de todas las etapas permitidas"),
    ("S6", "riesgo semantico: las senales discrepan y no se fusionan"),
    ("S7", "fuente necesaria inaccesible"),
)

IDENTIFICADORES: Final[tuple[str, ...]] = tuple(s for s, _ in PARADAS)


@dataclass(frozen=True, slots=True)
class Parada:
    """La parada adjudicada, con su fundamento."""

    identificador: str
    fundamento: str

    def __post_init__(self) -> None:
        if self.identificador not in IDENTIFICADORES:
            msg = f"parada desconocida: {self.identificador}"
            raise ValueError(msg)


def s1_disponible(cardinalidad: Cardinalidad) -> bool:
    """``S1`` esta **deshabilitada** en ``EXHAUSTIVA``. Sin excepcion."""
    return cardinalidad is not Cardinalidad.EXHAUSTIVA


def hay_criticos_pendientes(
    pendientes: Sequence[Candidata],
    criticidad_de: Callable[[str], Criticidad] | None = None,
) -> bool:
    """Control interno de criticos: ``S1`` exige que sea cero.

    La criticidad **no vive en el item**: la trae el plano comun. Mientras
    vivio en el item, el puerto la codificaba siempre a ``ORDINARIA`` y esta
    funcion era codigo muerto en cualquier ejecucion real.
    """
    nivel = criticidad_de if criticidad_de is not None else (lambda _id: Criticidad.ORDINARIA)
    return any(nivel(c.item.id) is Criticidad.CRITICA for c in pendientes)


def evaluar_suficiencia(
    admitidas: Sequence[Candidata],
    peticion: Peticion,
    *,
    pendientes: Sequence[Candidata] = (),
    criticidad_de: Callable[[str], Criticidad] | None = None,
    cardinalidad_semantica: int | None = None,
    grupo_truncado: bool = False,
) -> Parada | None:
    """Adjudica ``S1`` si —y solo si— la cardinalidad lo permite y se cumple.

    Tres condiciones, y la tercera es la que ``§7.7`` regla 9 anade: ``S1``
    **no puede** adjudicarse si el limite impide entregar integro un grupo que
    compute en la cuota. Prevalece ``S4`` con estado ``PARCIAL``, porque
    declarar suficiencia mientras se recorta un grupo diria que la necesidad
    quedo cubierta cuando parte de su evidencia no se entrego.

    El conteo es **semantico**: un grupo de equivalentes cuenta una vez, porque
    sus miembros sirven a una unica necesidad. Contarlos por separado permitiria
    satisfacer la cuota repitiendo equivalentes.
    """
    if not s1_disponible(peticion.cardinalidad):
        return None
    if hay_criticos_pendientes(pendientes, criticidad_de):
        return None
    if grupo_truncado:
        return None
    contadas = len(admitidas) if cardinalidad_semantica is None else cardinalidad_semantica
    if peticion.cardinalidad is Cardinalidad.EXACTA:
        if contadas >= peticion.objetivos:
            return Parada("S1", f"objetivos resueltos: {contadas}/{peticion.objetivos}")
        return None
    if contadas >= peticion.limite_objetivo:
        return Parada("S1", f"cuota cumplida: {contadas}/{peticion.limite_objetivo}")
    return None


def parada_por_grupo_truncado(grupo: str, omitidos: int) -> Parada:
    """``S4`` con causa: el limite parte un grupo y el estado sera ``PARCIAL``.

    El grupo **no es atomico** frente al limite duro —``CA-44`` ordena entregar
    lo que quepa—, pero los omitidos se cuentan y se declaran. Nunca se amplia
    el limite duro y nunca se omite en silencio.
    """
    return Parada("S4", f"limite duro parte el grupo {grupo}: {omitidos} miembros no entregados")


def parada_por_modo(siguiente: Etapa, peticion: Peticion) -> Parada | None:
    """``S2``: el modo no autoriza consultar el siguiente espacio."""
    if siguiente in peticion.espacios_autorizados:
        return None
    return Parada("S2", f"el modo {peticion.modo} no autoriza {siguiente}")


def parada_por_limite_duro(admitidas: Sequence[Candidata], peticion: Peticion) -> Parada | None:
    """``S4``: se alcanzo un maximo que no puede ampliarse."""
    if len(admitidas) >= peticion.limite_duro:
        return Parada("S4", f"limite duro alcanzado: {peticion.limite_duro}")
    return None


def parada_por_riesgo_semantico(conflictos: Sequence[str]) -> Parada | None:
    """``S6``: las senales discrepan y se conserva el conflicto."""
    if not conflictos:
        return None
    return Parada("S6", f"conflicto de polaridad en: {', '.join(conflictos)}")


def parada_por_agotamiento(peticion: Peticion) -> Parada:
    """``S5``: todas las etapas permitidas se ejecutaron."""
    return Parada("S5", f"agotadas las etapas autorizadas para {peticion.modo}")


def parada_por_fuente_inaccesible(fuente: str) -> Parada:
    """``S7``: una fuente autorizada necesaria no pudo consultarse.

    La salida es parcial e identifica la **clase** de limitacion **sin
    inventar ausencia**: no saber si algo existe no es saber que no existe.
    """
    return Parada("S7", f"fuente autorizada inaccesible: {fuente}")


def parada_por_ambiguedad(motivo: str) -> Parada:
    """``S3``: expandir cambiaria entidad, ambito, tiempo o significado."""
    return Parada("S3", motivo)


__all__ = [
    "IDENTIFICADORES",
    "PARADAS",
    "Parada",
    "evaluar_suficiencia",
    "hay_criticos_pendientes",
    "parada_por_agotamiento",
    "parada_por_ambiguedad",
    "parada_por_fuente_inaccesible",
    "parada_por_grupo_truncado",
    "parada_por_limite_duro",
    "parada_por_modo",
    "parada_por_riesgo_semantico",
    "s1_disponible",
]
