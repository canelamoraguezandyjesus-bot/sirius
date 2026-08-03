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
from typing import Any, Final

from experiments.adr002.candidates.common.contracts import (
    Candidata,
    ClaseDeEvidencia,
    Criticidad,
    CriticidadAplicada,
    Etapa,
    Explicacion,
    GrupoDeEquivalentes,
    Peticion,
    Resultado,
)

#: Los ejes de la clave de desempate, en su orden real. La explicacion los cita
#: en vez de inventar una frase distinta de la comparacion aplicada.
EJES_DE_ORDEN_DECLARADOS: Final[tuple[str, ...]] = (
    "criticidad aplicada",
    "autoridad de la etapa de origen",
    "clave de sujeto",
    "identidad estable",
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
    #: Agrupaciones **con su motivo y sus ejes**. Sin ellos, la traza decia que
    #: se agrupo pero no por que, y una agrupacion sin motivo no es auditable.
    agrupaciones: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]] = field(
        default_factory=list
    )
    #: Deduplicaciones por identidad, separadas de las agrupaciones: son
    #: mecanismos distintos y mezclarlos impedia distinguirlos en la auditoria.
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
        """La misma identidad aportada por varias senales. **No** es un grupo."""
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
    """Traza inicial. El ambito se registra por forma, no por contenido."""
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
    """``B04-RF-28``: los campos de la explicacion minima, todos poblados.

    Ninguno transcribe el texto del item: describen **por que** ese resultado
    esta ahi, que es lo que la regla pide y lo unico que se puede publicar sin
    filtrar contenido.

    Tres cosas que antes decia mal:

    * la procedencia afirmaba «del canon» tambien para lo ``ATRIBUIDA``, contra
      ``B04-RF-13``, que exige que lo externo se presente como evidencia
      atribuida y no como verdad canonica;
    * la razon de orden citaba la razon de la candidata en vez de la clave de
      desempate realmente aplicada, de modo que auditar el orden con la
      explicacion era imposible;
    * las procedencias eran una sola, y las de los demas miembros de un grupo
      se perdian al elegir representante.
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
        estado=("vigente" if item.vigente else "no vigente"),
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
            "criticidad",
            "razon_de_orden",
        ):
            if not str(getattr(explicacion, campo)).strip():
                fallos.append(f"{resultado.item.id}: explicacion sin {campo}")
        # Las procedencias son plurales y al menos una es obligatoria: un
        # resultado sin procedencia no cumple G10 ni RF-28.
        if not [p for p in explicacion.procedencias if p.strip()]:
            fallos.append(f"{resultado.item.id}: explicacion sin procedencias")
    return fallos


__all__ = [
    "EJES_DE_ORDEN_DECLARADOS",
    "PasoDeEtapa",
    "Traza",
    "explicar",
    "fallos_de_explicacion",
    "fallos_de_minimizacion",
    "traza_nueva",
]
