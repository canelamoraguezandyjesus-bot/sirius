"""Crear y activar (o crear y escalar) el WorkItem que decide la puerta.

Aplica una :class:`~sirius_engine.gate.DecisionPuerta` contra el
``WorkEngineStore`` real, adjuntando la autoridad de la clase (contrato §11,
ADR-041) al resultado en el mismo movimiento que crea el WorkItem: aquí es
donde "todo WorkItem nace con autoridad asignada" deja de ser una tabla de
consulta y pasa a ser algo que ocurre siempre, en el único sitio por el que
un WorkItem de este flujo puede nacer.

``ResultadoPuerta.NO_CREAR`` nunca llega hasta aquí como creación: no hay
ninguna rama de este módulo que produzca un ``WorkItem`` para ese
desenlace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.authority import Autoridad, autoridad_de_clase
from sirius_engine.domain.escalation import Escalada, construir_escalada
from sirius_engine.domain.work_item import WorkItem
from sirius_engine.gate import DecisionPuerta, ResultadoPuerta
from sirius_engine.ports.notification import NotificationPort
from sirius_engine.ports.store import WorkEngineStore


@dataclass(frozen=True, slots=True)
class ResultadoIntake:
    """Lo que produjo aplicar una ``DecisionPuerta``: puede no haber creado nada."""

    work_item: WorkItem | None
    autoridad: Autoridad | None
    escalada: Escalada | None


def aplicar_decision(
    decision: DecisionPuerta,
    *,
    store: WorkEngineStore,
    work_id: str,
    peticion_original: str,
    now: datetime,
    notificar: NotificationPort | None = None,
) -> ResultadoIntake:
    """Aplicar la decisión de la puerta contra el almacén real.

    ``CREAR_Y_ACTIVAR`` crea y activa sin ningún paso intermedio de
    confirmación (requisito: "una orden inequívoca no pide confirmación").
    ``CREAR_Y_ESCALAR`` crea, activa y escala en la misma llamada: el
    WorkItem nunca queda ``ACTIVE`` de forma visible para un despachador
    antes de escalar.
    """
    if decision.resultado is ResultadoPuerta.NO_CREAR:
        return ResultadoIntake(work_item=None, autoridad=None, escalada=None)

    assert decision.datos_trabajo is not None
    datos = decision.datos_trabajo
    autoridad = autoridad_de_clase(datos.clase)
    store.create_work_item(
        work_id=work_id,
        peticion_original=peticion_original,
        objetivo=datos.objetivo,
        contexto_origen=datos.contexto_origen,
        entregable=datos.entregable,
        criterio_terminado=datos.criterio_terminado,
        limites=datos.limites,
        prioridad=datos.prioridad,
        clase=datos.clase,
        now=now,
        plan=datos.plan,
    )
    work_item = store.activate_work_item(work_id, now=now)

    if decision.resultado is ResultadoPuerta.CREAR_Y_ACTIVAR:
        return ResultadoIntake(work_item=work_item, autoridad=autoridad, escalada=None)

    assert decision.resultado is ResultadoPuerta.CREAR_Y_ESCALAR
    assert decision.causa_escalado is not None
    work_item = store.escalate_work_item(work_id, now=now)
    escalada = construir_escalada(
        work_item, causa=decision.causa_escalado, motivo=decision.motivo, ocurrida_en=now
    )
    if notificar is not None:
        notificar.notificar(escalada)
    return ResultadoIntake(work_item=work_item, autoridad=autoridad, escalada=escalada)
