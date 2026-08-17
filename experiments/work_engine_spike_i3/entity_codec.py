"""(De)serialización JSON de ``WorkItem`` para el diario durable del spike (ADR-026).

Traduce instancias del dominio de A1 (:mod:`sirius_engine.domain.work_item`)
a diccionarios JSON-seguros y de vuelta. No reimplementa ninguna transición
del dominio: solo empaqueta y desempaqueta sus campos.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemPhase, WorkItemState


def work_item_to_dict(work_item: WorkItem) -> dict[str, Any]:
    return {
        "work_id": work_item.work_id,
        "peticion_original": work_item.peticion_original,
        "objetivo": work_item.objetivo,
        "contexto_origen": list(work_item.contexto_origen),
        "entregable": work_item.entregable,
        "criterio_terminado": work_item.criterio_terminado,
        "limites": dict(work_item.limites),
        "prioridad": work_item.prioridad,
        "clase": work_item.clase.value,
        "estado": work_item.estado.value,
        "fase": work_item.fase.value,
        "plan": list(work_item.plan),
        "version": work_item.version,
        "created_at": work_item.created_at.isoformat(),
        "updated_at": work_item.updated_at.isoformat(),
        "evidencia": list(work_item.evidencia),
        "resultado": (dict(work_item.resultado) if work_item.resultado is not None else None),
        "diagnostico": work_item.diagnostico,
        "paused_from": (work_item.paused_from.value if work_item.paused_from is not None else None),
    }


def work_item_from_dict(data: Mapping[str, Any]) -> WorkItem:
    resultado = data["resultado"]
    paused_from = data["paused_from"]
    return WorkItem(
        work_id=data["work_id"],
        peticion_original=data["peticion_original"],
        objetivo=data["objetivo"],
        contexto_origen=tuple(data["contexto_origen"]),
        entregable=data["entregable"],
        criterio_terminado=data["criterio_terminado"],
        limites=MappingProxyType(dict(data["limites"])),
        prioridad=data["prioridad"],
        clase=WorkItemClass(data["clase"]),
        estado=WorkItemState(data["estado"]),
        fase=WorkItemPhase(data["fase"]),
        plan=tuple(data["plan"]),
        version=data["version"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        evidencia=tuple(data["evidencia"]),
        resultado=None if resultado is None else dict(resultado),
        diagnostico=data["diagnostico"],
        paused_from=None if paused_from is None else WorkItemState(paused_from),
    )
