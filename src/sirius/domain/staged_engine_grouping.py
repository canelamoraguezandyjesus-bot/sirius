"""Los dos mecanismos de agrupación del motor por etapas, que no son el
mismo y no se mezclan. Portado desde
``experiments/adr002/candidates/common/grouping.py`` (rama
``evidence/adr001-spikes``, PR #117), incidencia #457/ADR-109.

**A · Deduplicación exacta por identidad.** El mismo identificador canónico
aportado por varias etapas o procedencias. Una sola entrada lógica: fusiona
señales y procedencias, no pierde ninguna explicación y no elige
representante, porque no hay identidades distintas entre las que elegir.

**B · Agrupación de equivalentes.** Identificadores canónicos distintos,
agrupados solo cuando todos los ejes están determinados y coinciden.
Conserva a todos sus miembros. El representante encabeza; no sustituye.

**La duda no fusiona.** Cualquier eje indeterminado —sujeto ausente,
``property_key`` nula, clase de evidencia distinta, tiempos o condiciones
que no coinciden— excluye del grupo. Es fallo cerrado y deliberado: agrupar
por defecto perdería diferencias materiales en silencio. Sirius 0.1 no
persiste ``property_key`` hoy: en el camino real del producto
``propiedad_de`` devuelve siempre ``None`` y esta agrupación nunca fusiona
nada — el banco de 47 casos lo suministra desde
``experiments/adr002/benchmark/property_keys_v0_2.json`` (mismo origen,
``evidence/adr001-spikes``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Final

from sirius.domain.staged_engine_contracts import Candidata, GrupoDeEquivalentes
from sirius.domain.staged_engine_trace import estado_publicado

#: Los ejes que deben estar todos determinados y coincidir.
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

#: Cascada registrada de elección de representante. «Primero en llegar»
#: queda prohibido: dependería del orden de la base de datos.
CASCADA_DE_REPRESENTANTE: Final[tuple[str, ...]] = (
    "confirmacion",
    "autoridad",
    "vigencia",
    "procedencia",
    "identidad_estable",
)


@dataclass(frozen=True, slots=True)
class Agrupacion:
    """Lo que produce la agrupación: grupos, sueltos y el invariante."""

    grupos: tuple[GrupoDeEquivalentes, ...]
    sueltos: tuple[Candidata, ...]
    #: Todas las candidatas, agrupadas o no, indexadas por identidad.
    por_identidad: dict[str, Candidata]

    @property
    def miembros_totales(self) -> tuple[str, ...]:
        """Unión de los miembros de todos los grupos más los sueltos.

        Invariante comprobable: elegibles antes de agrupar = esta unión.
        """
        de_grupos = tuple(m for g in self.grupos for m in g.miembros)
        return tuple(sorted({*de_grupos, *(c.item.id for c in self.sueltos)}))


def deduplicar_por_identidad(
    candidatas: Sequence[Candidata],
) -> tuple[tuple[Candidata, ...], dict[str, tuple[str, ...]]]:
    """Mecanismo A. Una entrada lógica por identidad, sin perder señales.

    Conserva la primera etapa que aportó el elemento —la autoridad decrece
    de ``E1`` a ``E4``— y acumula las señales de todas las aportaciones.
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
    """La clave de los diez ejes, o ``None`` si alguno está indeterminado."""
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
    """Confirmado antes que no confirmado. Sin sujeto no llega hasta aquí."""
    return 0 if candidata.item.vigente else 1


def _orden_de_autoridad(candidata: Candidata) -> int:
    """Canónico antes que atribuido."""
    return 0 if candidata.item.clase_de_evidencia.value == "CANONICA" else 1


def _elegir_representante(miembros: Sequence[Candidata]) -> tuple[Candidata, str]:
    """Cascada registrada, y la razón sale con el grupo.

    Solo se aplica a grupos que ya pasaron los diez ejes, de modo que no hay
    diferencias materiales que elegir a ciegas.
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
    """Mecanismo B. Agrupa solo con los diez ejes determinados.

    ``propiedad_de`` viene del plano común y no se le entrega a ninguna
    fuente de candidatas: es la única vía por la que la equivalencia
    semántica entra, y entra en la capa común.
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
                    (c.item.id, estado_publicado(c.item))
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
    """Candidata con la señal compuesta de todas sus aportaciones."""
    return replace(candidata, senal=" + ".join(senales))


__all__ = [
    "CASCADA_DE_REPRESENTANTE",
    "EJES_DE_EQUIVALENCIA",
    "Agrupacion",
    "agrupar_equivalentes",
    "con_senales_fusionadas",
    "deduplicar_por_identidad",
]
