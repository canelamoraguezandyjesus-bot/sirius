"""Traza minimizada del plan y explicación por resultado. Portado desde
``experiments/adr002/candidates/common/trace.py`` (rama
``evidence/adr001-spikes``, PR #117), incidencia #457/ADR-109.

La traza registra identificadores, clases y decisiones; nunca contenido
protegido. Por eso este módulo no acepta texto libre del canon: recibe
identificadores y clases, y el único texto que admite es el que la propia
capa común genera para describir una decisión.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from sirius.domain.staged_engine_contracts import (
    Candidata,
    ClaseDeEvidencia,
    Criticidad,
    CriticidadAplicada,
    Etapa,
    Explicacion,
    GrupoDeEquivalentes,
    ItemCanonico,
    Peticion,
    Resultado,
)

#: Los ejes de la clave de desempate, en su orden real.
EJES_DE_ORDEN_DECLARADOS: Final[tuple[str, ...]] = (
    "criticidad aplicada",
    "autoridad de la etapa de origen",
    "clave de sujeto",
    "identidad estable",
)

#: Marca base cuando el elemento es actual.
MARCA_VIGENTE: Final = "vigente"

#: Marca base cuando no lo es y el sustrato no declara por qué.
MARCA_NO_VIGENTE: Final = "no vigente"

#: Los tres estados históricos, con el eje que los distingue.
ESTADO_POR_EJE: Final[tuple[tuple[str, str, str], ...]] = (
    ("disponibilidad", "ARCHIVADA", "archivado"),
    ("validez", "SUSTITUIDA", "sustituido"),
    ("validez", "SIN_SOPORTE", "finalizado"),
)


def estado_publicado(item: ItemCanonico) -> str:
    """La marca de vigencia de un item, con cuál cuando el eje lo dice.

    Cuando el sustrato no declara ejes se devuelve la marca binaria y no se
    inventa un estado: un eje a ``None`` significa "el sustrato no lo
    declara", nunca "es permisivo". Solo cambia lo que se publica; la
    elegibilidad la deciden ``G2`` y ``G8`` leyendo los mismos ejes.
    """
    if item.vigente and item.disponible:
        return MARCA_VIGENTE
    ejes = item.ejes
    for campo, valor, nombre in ESTADO_POR_EJE:
        if getattr(ejes, campo, None) == valor:
            return f"{MARCA_NO_VIGENTE}: {nombre}"
    return MARCA_NO_VIGENTE


@dataclass(frozen=True, slots=True)
class PasoDeEtapa:
    """Una etapa ejecutada, con la causa que la autorizó."""

    etapa: Etapa
    causa_de_entrada: str
    aportadas: int
    admitidas_tras_puertas: int
    suficiente: bool


@dataclass(slots=True)
class Traza:
    """Plan reproducible: puertas, etapas, expansiones, agrupación y parada."""

    operation_id: str
    modo: str
    cardinalidad: str
    ambito: str
    candidato: str
    pasos: list[PasoDeEtapa] = field(default_factory=list)
    puertas: list[tuple[str, str, str]] = field(default_factory=list)
    agrupaciones: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]] = field(
        default_factory=list
    )
    deduplicaciones: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    conflictos: tuple[str, ...] = ()
    parada: tuple[str, str] | None = None
    suficiencia: str = ""
    desbordamiento: bool = False
    desbordamiento_critico: bool = False
    criticos_omitidos: tuple[str, ...] = ()
    miembros_omitidos: tuple[str, ...] = ()
    grupos_truncados: tuple[str, ...] = ()
    cardinalidad_semantica: int = 0
    cardinalidad_documental: int = 0

    def registrar_etapa(self, paso: PasoDeEtapa) -> None:
        self.pasos.append(paso)

    def registrar_descartes(self, descartes: Sequence[tuple[str, str, str]]) -> None:
        self.puertas.extend(descartes)

    def registrar_agrupacion(
        self,
        representante: str,
        miembros: Sequence[str],
        motivo: str,
        ejes: Sequence[str] = (),
    ) -> None:
        self.agrupaciones.append((representante, tuple(miembros), motivo, tuple(ejes)))

    def registrar_deduplicacion(self, identidad: str, senales: Sequence[str]) -> None:
        """La misma identidad aportada por varias señales. No es un grupo."""
        self.deduplicaciones.append((identidad, tuple(senales)))

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
                {
                    "representante": r,
                    "miembros": list(m),
                    "motivo": motivo,
                    "ejes": list(ejes),
                }
                for r, m, motivo, ejes in self.agrupaciones
            ],
            "deduplicaciones_por_identidad": [
                {"identidad": i, "senales_fusionadas": list(s)} for i, s in self.deduplicaciones
            ],
            "conflictos_conservados": list(self.conflictos),
            "parada": (
                {"identificador": self.parada[0], "fundamento": self.parada[1]}
                if self.parada
                else None
            ),
            "suficiencia": self.suficiencia,
            "desbordamiento_declarado": self.desbordamiento,
            "desbordamiento_critico": self.desbordamiento_critico,
            "criticos_omitidos": list(self.criticos_omitidos),
            "miembros_omitidos": list(self.miembros_omitidos),
            "grupos_truncados": list(self.grupos_truncados),
            "cardinalidad_semantica": self.cardinalidad_semantica,
            "cardinalidad_documental": self.cardinalidad_documental,
        }


def traza_nueva(peticion: Peticion, candidato: str) -> Traza:
    """Traza inicial. El ámbito se registra por forma, no por contenido."""
    ambito = "global" if peticion.ambito.global_ else f"proyectos:{len(peticion.ambito.proyectos)}"
    return Traza(
        operation_id=peticion.operation_id,
        modo=peticion.modo.value,
        cardinalidad=peticion.cardinalidad.value,
        ambito=ambito,
        candidato=candidato,
    )


def explicar(
    candidata: Candidata,
    peticion: Peticion,
    orden: int,
    criticidad: CriticidadAplicada | None = None,
    grupo: GrupoDeEquivalentes | None = None,
) -> Explicacion:
    """Los campos de la explicación mínima, todos poblados.

    Ninguno transcribe el texto del item: describen por qué ese resultado
    está ahí.
    """
    item = candidata.item
    atribuida = item.clase_de_evidencia is not ClaseDeEvidencia.CANONICA
    origen = "evidencia atribuida, no canonica" if atribuida else "del canon"
    procedencias = [f"{item.clase.value} {origen} via {candidata.lectura.medio}"]
    if grupo is not None:
        procedencias.extend(grupo.procedencias_adicionales)
    return Explicacion(
        item_id=item.id,
        coincidencia=f"{candidata.etapa.value} por {candidata.senal}",
        ambito=("global" if item.project_id is None else f"proyecto {item.project_id}"),
        tiempo=f"aplicable a {peticion.ventana.tiempo_objetivo}; registrado {item.created_at}",
        estado=estado_publicado(item),
        procedencias=tuple(procedencias),
        criticidad=(
            f"{criticidad.nivel.value} por {criticidad.regla_de_politica}: "
            f"{criticidad.razon_segura}"
            if criticidad is not None
            else Criticidad.ORDINARIA.value
        ),
        razon_de_orden=(
            f"posicion {orden} por clave de desempate ({', '.join(EJES_DE_ORDEN_DECLARADOS)}); "
            f"{candidata.razon}"
        ),
        grupo=("" if grupo is None else grupo.identificador),
    )


def fallos_de_minimizacion(traza: Mapping[str, Any], textos_protegidos: Sequence[str]) -> list[str]:
    """Comprueba que la traza no filtró contenido protegido."""
    serializada = repr(traza)
    return [
        f"la traza contiene texto protegido: {texto[:40]!r}"
        for texto in textos_protegidos
        if texto and texto in serializada
    ]


def fallos_de_explicacion(resultados: Sequence[Resultado]) -> list[str]:
    """Exige explicación completa en el 100 % de los resultados."""
    fallos: list[str] = []
    for resultado in resultados:
        explicacion = resultado.explicacion
        for campo in (
            "coincidencia",
            "ambito",
            "tiempo",
            "estado",
            "criticidad",
            "razon_de_orden",
        ):
            if not str(getattr(explicacion, campo)).strip():
                fallos.append(f"{resultado.item.id}: explicacion sin {campo}")
        if not [p for p in explicacion.procedencias if p.strip()]:
            fallos.append(f"{resultado.item.id}: explicacion sin procedencias")
    return fallos


__all__ = [
    "EJES_DE_ORDEN_DECLARADOS",
    "PasoDeEtapa",
    "Traza",
    "estado_publicado",
    "explicar",
    "fallos_de_explicacion",
    "fallos_de_minimizacion",
    "traza_nueva",
]
