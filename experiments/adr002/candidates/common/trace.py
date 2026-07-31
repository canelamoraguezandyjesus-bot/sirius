"""Traza minimizada del plan (``B04-RF-29``) y explicacion por resultado (``RF-28``).

La traza registra **identificadores, clases y decisiones**; nunca contenido
protegido. No es una precaucion cosmetica: ``B04-Q18`` exige la traza «siempre
con no revelacion», y una traza que copiase el texto de los items convertiria
el instrumento de auditoria en un canal lateral —justo lo que ``RF-26`` y la
puerta de indistinguibilidad persiguen—.

Por eso este modulo **no acepta texto libre del canon**: recibe identificadores
y clases, y el unico texto que admite es el que la propia capa comun genera
para describir una decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from experiments.adr002.candidates.common.contracts import (
    Candidata,
    Etapa,
    Explicacion,
    Peticion,
    Resultado,
)


@dataclass(frozen=True, slots=True)
class PasoDeEtapa:
    """Una etapa ejecutada, con la causa que la autorizo."""

    etapa: Etapa
    causa_de_entrada: str
    aportadas: int
    admitidas_tras_puertas: int
    suficiente: bool


@dataclass(slots=True)
class Traza:
    """Plan reproducible: puertas, etapas, expansiones, agrupacion y parada."""

    operation_id: str
    modo: str
    cardinalidad: str
    ambito: str
    candidato: str
    pasos: list[PasoDeEtapa] = field(default_factory=list)
    puertas: list[tuple[str, str, str]] = field(default_factory=list)
    agrupaciones: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    conflictos: tuple[str, ...] = ()
    parada: tuple[str, str] | None = None
    suficiencia: str = ""
    desbordamiento: bool = False
    criticos_omitidos: tuple[str, ...] = ()

    def registrar_etapa(self, paso: PasoDeEtapa) -> None:
        self.pasos.append(paso)

    def registrar_descartes(self, descartes: Sequence[tuple[str, str, str]]) -> None:
        self.puertas.extend(descartes)

    def registrar_agrupacion(self, representante: str, agrupados: Sequence[str]) -> None:
        self.agrupaciones.append((representante, tuple(agrupados)))

    def como_dict(self) -> dict[str, Any]:
        """Forma serializable. Solo identificadores, clases y decisiones."""
        return {
            "operation_id": self.operation_id,
            "modo": self.modo,
            "cardinalidad": self.cardinalidad,
            "ambito": self.ambito,
            "candidato": self.candidato,
            "etapas": [
                {
                    "etapa": p.etapa.value,
                    "causa_de_entrada": p.causa_de_entrada,
                    "aportadas": p.aportadas,
                    "admitidas_tras_puertas": p.admitidas_tras_puertas,
                    "suficiente": p.suficiente,
                }
                for p in self.pasos
            ],
            "descartes_por_puerta": [
                {"item": item, "puerta": puerta, "motivo": motivo}
                for item, puerta, motivo in self.puertas
            ],
            "agrupaciones": [
                {"representante": r, "agrupados": list(a)} for r, a in self.agrupaciones
            ],
            "conflictos_conservados": list(self.conflictos),
            "parada": (
                {"identificador": self.parada[0], "fundamento": self.parada[1]}
                if self.parada
                else None
            ),
            "suficiencia": self.suficiencia,
            "desbordamiento_declarado": self.desbordamiento,
            "criticos_omitidos": list(self.criticos_omitidos),
        }


def traza_nueva(peticion: Peticion, candidato: str) -> Traza:
    """Traza inicial. El ambito se registra por forma, no por contenido."""
    ambito = "global" if peticion.ambito.global_ else f"proyectos:{len(peticion.ambito.proyectos)}"
    return Traza(
        operation_id=peticion.operation_id,
        modo=peticion.modo.value,
        cardinalidad=peticion.cardinalidad.value,
        ambito=ambito,
        candidato=candidato,
    )


def explicar(candidata: Candidata, peticion: Peticion, orden: int) -> Explicacion:
    """``B04-RF-28``: los siete campos de la explicacion minima.

    Ninguno transcribe el texto del item: describen **por que** ese resultado
    esta ahi, que es lo que la regla pide y lo unico que se puede publicar sin
    filtrar contenido.
    """
    item = candidata.item
    return Explicacion(
        item_id=item.id,
        coincidencia=f"{candidata.etapa.value} por {candidata.senal}",
        ambito=("global" if item.project_id is None else f"proyecto {item.project_id}"),
        tiempo=f"aplicable a {peticion.ventana.tiempo_objetivo}; registrado {item.created_at}",
        estado=("vigente" if item.vigente else "no vigente"),
        procedencia=f"{item.clase.value} del canon via {candidata.lectura.medio}",
        criticidad=item.criticidad.value,
        razon_de_orden=f"posicion {orden} por {candidata.razon}",
    )


def fallos_de_minimizacion(traza: Mapping[str, Any], textos_protegidos: Sequence[str]) -> list[str]:
    """Comprueba que la traza no filtro contenido protegido.

    Se usa en pruebas y como control: si el texto de un item aparece en la
    traza, la minimizacion fallo, por mucho que el resto del plan sea correcto.
    """
    serializada = repr(traza)
    return [
        f"la traza contiene texto protegido: {texto[:40]!r}"
        for texto in textos_protegidos
        if texto and texto in serializada
    ]


def fallos_de_explicacion(resultados: Sequence[Resultado]) -> list[str]:
    """``RF-28`` exige explicacion **completa** en el 100 % de los resultados."""
    fallos: list[str] = []
    for resultado in resultados:
        explicacion = resultado.explicacion
        for campo in (
            "coincidencia",
            "ambito",
            "tiempo",
            "estado",
            "procedencia",
            "criticidad",
            "razon_de_orden",
        ):
            if not str(getattr(explicacion, campo)).strip():
                fallos.append(f"{resultado.item.id}: explicacion sin {campo}")
    return fallos


__all__ = [
    "PasoDeEtapa",
    "Traza",
    "explicar",
    "fallos_de_explicacion",
    "fallos_de_minimizacion",
    "traza_nueva",
]
