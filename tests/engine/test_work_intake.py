"""aplicar_decision: crear/activar/escalar el WorkItem que decide la puerta, contra el almacén real.

Corre contra ambas implementaciones de ``WorkEngineStore`` vía la fixture
``store`` de ``conftest.py`` (A2, requisito 1: la misma batería vale para el
almacén en memoria y el durable).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius_engine.domain.authority import Autoridad
from sirius_engine.domain.escalation import CausaEscalado, Escalada
from sirius_engine.domain.intent import DatosNuevoTrabajo
from sirius_engine.domain.work_item import WorkItemClass as Clase
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.gate import DecisionPuerta, ResultadoPuerta
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.work_intake import aplicar_decision

_NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _datos(clase: Clase = Clase.PROGRAMACION) -> DatosNuevoTrabajo:
    return DatosNuevoTrabajo(
        objetivo="implementar X",
        entregable="X funcionando",
        criterio_terminado="las pruebas de X pasan",
        clase=clase,
        limites={"presupuesto": {"limite": 10.0}},
        contexto_origen=("sesion-cli",),
    )


def test_no_crear_no_toca_el_almacen(store: WorkEngineStore) -> None:
    decision = DecisionPuerta(resultado=ResultadoPuerta.NO_CREAR, motivo="ambigua")
    resultado = aplicar_decision(
        decision, store=store, work_id="WI-INTAKE-0001", peticion_original="mensaje", now=_NOW
    )
    assert resultado.work_item is None
    assert resultado.autoridad is None
    assert resultado.escalada is None
    assert store.get_work_item("WI-INTAKE-0001") is None


def test_crear_y_activar_deja_el_workitem_active_con_su_autoridad(store: WorkEngineStore) -> None:
    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ACTIVAR, motivo="orden inequívoca", datos_trabajo=_datos()
    )
    resultado = aplicar_decision(
        decision,
        store=store,
        work_id="WI-INTAKE-0002",
        peticion_original="implementa X",
        now=_NOW,
    )
    assert resultado.work_item is not None
    assert resultado.work_item.estado is WorkItemState.ACTIVE
    assert resultado.autoridad is Autoridad.INCIDENCIA  # PROGRAMACION
    assert resultado.escalada is None


def test_crear_y_activar_no_pide_ninguna_confirmacion_intermedia(store: WorkEngineStore) -> None:
    """A5-P2: sin ningún paso adicional entre decidir y activar."""
    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ACTIVAR, motivo="orden inequívoca", datos_trabajo=_datos()
    )
    aplicar_decision(
        decision, store=store, work_id="WI-INTAKE-0003", peticion_original="implementa X", now=_NOW
    )
    # Una única versión: crear + activar, sin ningún estado intermedio de espera.
    versiones = store.list_work_item_versions("WI-INTAKE-0003")
    assert len(versiones) == 1
    assert versiones[0].estado is WorkItemState.ACTIVE


def test_crear_y_escalar_deja_el_workitem_en_needs_decision(store: WorkEngineStore) -> None:
    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ESCALAR,
        motivo="operación destructiva",
        datos_trabajo=_datos(),
        causa_escalado=CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
    )
    resultado = aplicar_decision(
        decision,
        store=store,
        work_id="WI-INTAKE-0004",
        peticion_original="borra la base de producción",
        now=_NOW,
    )
    assert resultado.work_item is not None
    assert resultado.work_item.estado is WorkItemState.NEEDS_DECISION
    assert resultado.escalada is not None
    assert resultado.escalada.causa is CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE
    assert resultado.escalada.peticion_original == "borra la base de producción"


def test_crear_y_escalar_nunca_deja_visible_un_estado_active_intermedio(
    store: WorkEngineStore,
) -> None:
    """CODEX-003: una sola operación de almacén, sin ``work_item_activated`` observable."""
    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ESCALAR,
        motivo="operación destructiva",
        datos_trabajo=_datos(),
        causa_escalado=CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
    )
    aplicar_decision(
        decision,
        store=store,
        work_id="WI-INTAKE-0007",
        peticion_original="borra la base de producción",
        now=_NOW,
    )
    eventos = [e for e in store.list_events() if e.aggregate_id == "WI-INTAKE-0007"]
    assert len(eventos) == 1
    assert eventos[0].kind == "work_item_created_needing_decision"
    assert eventos[0].entity.estado is WorkItemState.NEEDS_DECISION


def test_crear_y_escalar_notifica(store: WorkEngineStore) -> None:
    entregadas: list[Escalada] = []

    class _Notificador:
        def notificar(self, escalada: Escalada) -> None:
            entregadas.append(escalada)

    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ESCALAR,
        motivo="gasto no autorizado",
        datos_trabajo=_datos(),
        causa_escalado=CausaEscalado.GASTO_O_PRESUPUESTO,
    )
    aplicar_decision(
        decision,
        store=store,
        work_id="WI-INTAKE-0005",
        peticion_original="gasta lo que haga falta",
        now=_NOW,
        notificar=_Notificador(),
    )
    assert len(entregadas) == 1


def test_autoridad_motor_para_clase_nativa(store: WorkEngineStore) -> None:
    """Una clase nativa del motor nace con autoridad MOTOR.

    Hasta ADR-177 el ejemplo era `INVESTIGACION`, y fijaba la copia vieja de la
    tabla de autoridad: investigación existe en la vía GitHub desde ADR-099.
    `CONSULTA_LARGA` sí es nativa del motor.
    """
    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ACTIVAR,
        motivo="orden inequívoca",
        datos_trabajo=_datos(clase=Clase.CONSULTA_LARGA),
    )
    resultado = aplicar_decision(
        decision, store=store, work_id="WI-INTAKE-0006", peticion_original="consulta X", now=_NOW
    )
    assert resultado.autoridad is Autoridad.MOTOR


@pytest.mark.parametrize("clase", [Clase.DOCUMENTACION, Clase.INVESTIGACION])
def test_documentacion_e_investigacion_nacen_con_autoridad_incidencia(
    store: WorkEngineStore, clase: Clase
) -> None:
    """El defecto de ADR-177 en el punto exacto donde nace la autoridad.

    Quince encargos reales de estas dos clases nacieron aquí con MOTOR y
    corrieron enteros en la vía GitHub.
    """
    decision = DecisionPuerta(
        resultado=ResultadoPuerta.CREAR_Y_ACTIVAR,
        motivo="orden inequívoca",
        datos_trabajo=_datos(clase=clase),
    )
    resultado = aplicar_decision(
        decision, store=store, work_id="WI-INTAKE-0007", peticion_original="haz X", now=_NOW
    )
    assert resultado.autoridad is Autoridad.INCIDENCIA
