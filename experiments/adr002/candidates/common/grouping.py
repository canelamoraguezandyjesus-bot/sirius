"""Los **dos** mecanismos de ``B04 §7.2``, que no son el mismo y no se mezclan.

**A · Deduplicacion exacta por identidad.** El mismo identificador canonico
aportado por varias etapas o procedencias. Una sola entrada logica. Fusiona
senales y procedencias, no pierde ninguna explicacion y **no elige
representante**, porque no hay identidades distintas entre las que elegir.

**B · Agrupacion de equivalentes.** Identificadores canonicos **distintos**,
agrupados solo cuando **todos** los ejes estan determinados y coinciden.
Conserva a todos sus miembros. El representante encabeza; no sustituye.

Que los dos vivan en un modulo aparte no es orden cosmetico: mientras
compartieron funcion, la deduplicacion por sujeto borraba miembros y la
agrupacion se comportaba como una deduplicacion, de modo que ni el limite ni
``G12`` podian ver lo absorbido.

**La duda no fusiona.** Cualquier eje indeterminado —sujeto ausente,
``property_key`` nula, clase de evidencia distinta, tiempos o condiciones que
no coinciden— excluye del grupo. Es fallo cerrado y es deliberado: agrupar por
defecto perderia diferencias materiales en silencio.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Final

from experiments.adr002.candidates.common.contracts import (
    Candidata,
    GrupoDeEquivalentes,
)

#: Los ejes que deben estar **todos** determinados y coincidir. Que sean
#: constantes con nombre y no una tupla anonima dentro de una funcion es lo que
#: permite que la traza diga por que eje se agrupo.
EJES_DE_EQUIVALENCIA: Final[tuple[str, ...]] = (
    "sujeto",
    "propiedad",
    "clase",
    "clase_de_evidencia",
    "ambito",
    "polaridad",
    "condicion",
    "tiempo",
    "vigencia",
    "disponibilidad",
)

#: Cascada **registrada** de eleccion de representante (``§7.4``). «Primero en
#: llegar» queda prohibido: dependia del orden de la base de datos y no era
#: reproducible.
CASCADA_DE_REPRESENTANTE: Final[tuple[str, ...]] = (
    "confirmacion",
    "autoridad",
    "vigencia",
    "procedencia",
    "identidad_estable",
)


@dataclass(frozen=True, slots=True)
class Agrupacion:
    """Lo que produce la agrupacion: grupos, sueltos y el invariante."""

    grupos: tuple[GrupoDeEquivalentes, ...]
    sueltos: tuple[Candidata, ...]
    #: Todas las candidatas, agrupadas o no, indexadas por identidad.
    por_identidad: dict[str, Candidata]

    @property
    def miembros_totales(self) -> tuple[str, ...]:
        """Union de los miembros de todos los grupos mas los sueltos.

        **Invariante comprobable de ``§7.9``:** elegibles antes de agrupar =
        esta union. Si alguna vez dejara de cumplirse, un elegible habria
        desaparecido dentro de un grupo.
        """
        de_grupos = tuple(m for g in self.grupos for m in g.miembros)
        return tuple(sorted({*de_grupos, *(c.item.id for c in self.sueltos)}))


def deduplicar_por_identidad(
    candidatas: Sequence[Candidata],
) -> tuple[tuple[Candidata, ...], dict[str, tuple[str, ...]]]:
    """Mecanismo **A**. Una entrada logica por identidad, sin perder senales.

    Conserva la **primera etapa** que aporto el elemento —la autoridad decrece
    de ``E1`` a ``E4``, de modo que reemplazarla por una posterior degradaria el
    orden— y acumula las senales de todas las aportaciones. Devuelve tambien
    que senales se fusionaron en cada identidad, para que la traza lo diga.
    """
    unicas: dict[str, Candidata] = {}
    senales: dict[str, list[str]] = {}
    for candidata in candidatas:
        identidad = candidata.item.id
        senales.setdefault(identidad, []).append(candidata.senal)
        if identidad not in unicas:
            unicas[identidad] = candidata
    fusionadas = {
        identidad: tuple(sorted(set(vistas)))
        for identidad, vistas in senales.items()
        if len(set(vistas)) > 1
    }
    return tuple(unicas.values()), fusionadas


def _clave_de_equivalencia(
    candidata: Candidata, propiedad: str | None
) -> tuple[object, ...] | None:
    """La clave de los diez ejes, o ``None`` si alguno esta indeterminado."""
    item = candidata.item
    lectura = candidata.lectura
    if not item.sujeto_determinado:
        return None
    if not propiedad:
        return None
    if not lectura.sujeto.strip():
        return None
    return (
        item.subject_key,
        propiedad,
        item.clase.value,
        item.clase_de_evidencia.value,
        item.project_id,
        lectura.polaridad.value,
        lectura.condicion,
        lectura.tiempo,
        item.vigente,
        item.disponible,
    )


def _orden_de_confirmacion(candidata: Candidata) -> int:
    """Confirmado antes que no confirmado. Sin sujeto no llega hasta aqui."""
    return 0 if candidata.item.vigente else 1


def _orden_de_autoridad(candidata: Candidata) -> int:
    """Canonico antes que atribuido (``B04-RF-13``)."""
    return 0 if candidata.item.clase_de_evidencia.value == "CANONICA" else 1


def _elegir_representante(miembros: Sequence[Candidata]) -> tuple[Candidata, str]:
    """``§7.4``: cascada registrada, y la razon sale con el grupo.

    Solo se aplica a grupos que ya pasaron los diez ejes, de modo que no hay
    diferencias materiales que elegir a ciegas: ``B04:196`` prohibe elegir
    representante cuando las hay, y aqui ya no las hay.
    """
    ordenados = sorted(
        miembros,
        key=lambda c: (
            _orden_de_confirmacion(c),
            _orden_de_autoridad(c),
            0 if c.item.vigente else 1,
            0 if c.razon.strip() else 1,
            c.item.id,
        ),
    )
    elegido = ordenados[0]
    razon = (
        f"cascada {'/'.join(CASCADA_DE_REPRESENTANTE)}: "
        f"{elegido.item.id} encabeza {len(miembros)} miembros equivalentes"
    )
    return elegido, razon


def agrupar_equivalentes(
    candidatas: Sequence[Candidata],
    propiedad_de: Callable[[str], str | None],
    relaciones_de: Callable[[str], tuple[str, ...]] | None = None,
) -> Agrupacion:
    """Mecanismo **B**. Agrupa solo con los diez ejes determinados.

    ``propiedad_de`` viene del plano comun y **no se le entrega a ningun
    candidato**: es la unica via por la que la equivalencia semantica entra, y
    entra en la capa comun.
    """
    clases: dict[tuple[object, ...], list[Candidata]] = {}
    sueltos: list[Candidata] = []
    for candidata in candidatas:
        clave = _clave_de_equivalencia(candidata, propiedad_de(candidata.item.id))
        if clave is None:
            sueltos.append(candidata)
            continue
        clases.setdefault(clave, []).append(candidata)

    grupos: list[GrupoDeEquivalentes] = []
    for _clave, miembros in sorted(clases.items(), key=lambda p: str(p[0])):
        if len(miembros) == 1:
            sueltos.append(miembros[0])
            continue
        representante, razon = _elegir_representante(miembros)
        identidades = tuple(sorted(c.item.id for c in miembros))
        grupos.append(
            GrupoDeEquivalentes(
                identificador=f"GRP-{identidades[0]}",
                representante=representante.item.id,
                miembros=identidades,
                procedencias_adicionales=tuple(
                    sorted({c.senal for c in miembros if c.item.id != representante.item.id})
                ),
                # Ya no hay diferencias materiales: los diez ejes coinciden. Lo
                # que si difiere —etapa de origen y senal— se conserva aqui en
                # vez de desaparecer con el miembro absorbido.
                diferencias_materiales=tuple(
                    sorted({f"{c.item.id}: {c.etapa.value} por {c.senal}" for c in miembros})
                ),
                relaciones_entre_miembros=(
                    tuple(sorted({r for c in miembros for r in relaciones_de(c.item.id)}))
                    if relaciones_de is not None
                    else ()
                ),
                razon_del_representante=razon,
                estado_historico_por_miembro=tuple(
                    (c.item.id, "vigente" if c.item.vigente else "no vigente")
                    for c in sorted(miembros, key=lambda c: c.item.id)
                ),
                ejes=EJES_DE_EQUIVALENCIA,
            )
        )

    return Agrupacion(
        grupos=tuple(grupos),
        sueltos=tuple(sorted(sueltos, key=lambda c: c.item.id)),
        por_identidad={c.item.id: c for c in candidatas},
    )


def con_senales_fusionadas(candidata: Candidata, senales: tuple[str, ...]) -> Candidata:
    """Candidata con la senal compuesta de todas sus aportaciones."""
    return replace(candidata, senal=" + ".join(senales))


__all__ = [
    "CASCADA_DE_REPRESENTANTE",
    "EJES_DE_EQUIVALENCIA",
    "Agrupacion",
    "agrupar_equivalentes",
    "con_senales_fusionadas",
    "deduplicar_por_identidad",
]
