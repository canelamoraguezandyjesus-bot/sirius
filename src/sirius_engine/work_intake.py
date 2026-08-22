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

``CREAR_Y_ESCALAR`` crea el WorkItem directamente en ``NEEDS_DECISION`` con
``WorkEngineStore.create_and_escalate_work_item`` -una única operación de
almacén, no la secuencia crear+activar+escalar-, así que ningún observador
externo ni una caída a mitad de camino puede dejar visible un trabajo
sensible como ``ACTIVE``, despachable.
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
    evidencia: tuple[str, ...] = (),
) -> ResultadoIntake:
    """Aplicar la decisión de la puerta contra el almacén real.

    ``CREAR_Y_ACTIVAR`` crea y activa sin ningún paso intermedio de
    confirmación (requisito: "una orden inequívoca no pide confirmación").
    ``CREAR_Y_ESCALAR`` crea el WorkItem directamente en ``NEEDS_DECISION``
    en una sola operación de almacén: nunca queda ``ACTIVE`` de forma
    visible para un despachador, ni siquiera momentáneamente entre dos
    llamadas.

    ``evidencia`` viaja hasta el ``WorkItem`` creado porque es el único
    momento en que se sabe de dónde vino la orden. El despachador C2 exige
    que ahí conste la referencia a la orden del propietario
    (:func:`~sirius_engine.domain.dispatch.orden_enlazada`) y se niega a
    activar sin ella; antes de este parámetro ningún camino de producción
    escribía ``evidencia``, así que esa guarda no podía satisfacerse desde
    fuera de las pruebas (H-12).
    """
    if decision.resultado is ResultadoPuerta.NO_CREAR:
        return ResultadoIntake(work_item=None, autoridad=None, escalada=None)

    assert decision.datos_trabajo is not None
    datos = decision.datos_trabajo
    autoridad = autoridad_de_clase(datos.clase)

    if decision.resultado is ResultadoPuerta.CREAR_Y_ACTIVAR:
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
            evidencia=evidencia,
        )
        work_item = store.activate_work_item(work_id, now=now)
        return ResultadoIntake(work_item=work_item, autoridad=autoridad, escalada=None)

    assert decision.resultado is ResultadoPuerta.CREAR_Y_ESCALAR
    assert decision.causa_escalado is not None
    work_item = store.create_and_escalate_work_item(
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
        evidencia=evidencia,
    )
    escalada = construir_escalada(
        work_item, causa=decision.causa_escalado, motivo=decision.motivo, ocurrida_en=now
    )
    if notificar is not None:
        notificar.notificar(escalada)
    return ResultadoIntake(work_item=work_item, autoridad=autoridad, escalada=escalada)
