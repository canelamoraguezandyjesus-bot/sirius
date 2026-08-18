"""(De)serialización JSON de ``WorkItem`` y ``Run`` para el diario durable (ADR-026, ADR-029).

Promovido desde el spike desechable de S1
(:mod:`experiments.work_engine_spike_i3.entity_codec`, incidencia #182) a
código de producción para A2. No reimplementa ninguna transición del
dominio: solo empaqueta y desempaqueta sus campos.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sirius_engine.domain.events import AggregateType
from sirius_engine.domain.run import CancellationStatus, Run, RunOutcome, RunState
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
        resultado=None if resultado is None else MappingProxyType(dict(resultado)),
        diagnostico=data["diagnostico"],
        paused_from=None if paused_from is None else WorkItemState(paused_from),
    )


def run_to_dict(run: Run) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "work_id": run.work_id,
        "paso": run.paso,
        "worker": run.worker,
        "work_package": dict(run.work_package),
        "intento": run.intento,
        "estado": run.estado.value,
        "deadline": run.deadline.isoformat(),
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "desenlace": (run.desenlace.value if run.desenlace is not None else None),
        "cancellation_status": run.cancellation_status.value,
        "ultima_observacion": run.ultima_observacion,
        "observado_en": (run.observado_en.isoformat() if run.observado_en is not None else None),
        "resultado": (dict(run.resultado) if run.resultado is not None else None),
        "diagnostico": run.diagnostico,
        "recurso_mutable": run.recurso_mutable,
        "sustituye_a": run.sustituye_a,
        "motivo_sustitucion": run.motivo_sustitucion,
        "invalidado_por_alcance": run.invalidado_por_alcance,
    }


def run_from_dict(data: Mapping[str, Any]) -> Run:
    desenlace = data["desenlace"]
    observado_en = data["observado_en"]
    resultado = data["resultado"]
    return Run(
        run_id=data["run_id"],
        work_id=data["work_id"],
        paso=data["paso"],
        worker=data["worker"],
        work_package=MappingProxyType(dict(data["work_package"])),
        intento=data["intento"],
        estado=RunState(data["estado"]),
        deadline=datetime.fromisoformat(data["deadline"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        desenlace=None if desenlace is None else RunOutcome(desenlace),
        cancellation_status=CancellationStatus(data["cancellation_status"]),
        ultima_observacion=data["ultima_observacion"],
        observado_en=None if observado_en is None else datetime.fromisoformat(observado_en),
        resultado=None if resultado is None else MappingProxyType(dict(resultado)),
        diagnostico=data["diagnostico"],
        recurso_mutable=data["recurso_mutable"],
        sustituye_a=data["sustituye_a"],
        motivo_sustitucion=data["motivo_sustitucion"],
        invalidado_por_alcance=data["invalidado_por_alcance"],
    )


def entity_to_dict(aggregate_type: AggregateType, entity: WorkItem | Run) -> dict[str, Any]:
    """Empaquetar cualquiera de los dos tipos de agregado que lleva un ``Event``."""
    if aggregate_type is AggregateType.WORK_ITEM:
        assert isinstance(entity, WorkItem)
        return work_item_to_dict(entity)
    assert isinstance(entity, Run)
    return run_to_dict(entity)


def entity_from_dict(aggregate_type: AggregateType, data: Mapping[str, Any]) -> WorkItem | Run:
    """Contraparte de :func:`entity_to_dict`, indexada por ``aggregate_type``."""
    if aggregate_type is AggregateType.WORK_ITEM:
        return work_item_from_dict(data)
    return run_from_dict(data)
