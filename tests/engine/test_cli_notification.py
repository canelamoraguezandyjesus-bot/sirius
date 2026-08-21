"""NotificadorCLI: adapter v0 del NotificationPort, sin estado durable propio."""

from __future__ import annotations

from datetime import UTC, datetime

from sirius_engine.adapters.cli_notification import NotificadorCLI
from sirius_engine.domain.escalation import CausaEscalado, Escalada, construir_escalada
from sirius_engine.domain.work_item import WorkItemClass, create_work_item


def _escalada() -> Escalada:
    work_item = create_work_item(
        work_id="WI-CLI-0001",
        peticion_original="borra la base",
        objetivo="atender la orden",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={"presupuesto": {"limite": 1.0}},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=datetime(2026, 8, 19, tzinfo=UTC),
    )
    return construir_escalada(
        work_item,
        causa=CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
        motivo="motivo de prueba",
        ocurrida_en=datetime(2026, 8, 19, tzinfo=UTC),
    )


def test_notificar_escribe_por_el_escritor_inyectado_y_conserva_la_escalada() -> None:
    escritos: list[str] = []
    notificador = NotificadorCLI(escritor=escritos.append)
    escalada = _escalada()

    notificador.notificar(escalada)

    assert len(escritos) == 1
    assert "WI-CLI-0001" in escritos[0]
    assert "operacion_destructiva_o_irreversible" in escritos[0]
    assert notificador.entregadas == [escalada]


def test_no_tiene_ningun_estado_durable_mas_alla_del_turno_de_la_sesion() -> None:
    notificador = NotificadorCLI(escritor=lambda _texto: None)
    assert notificador.entregadas == []
    notificador.notificar(_escalada())
    assert len(notificador.entregadas) == 1
    # Sin ningún mecanismo de persistencia: es una lista en memoria del propio
    # objeto, que desaparece con la sesión (interfaz v0, "sin estado propio").
    otro_notificador = NotificadorCLI(escritor=lambda _texto: None)
    assert otro_notificador.entregadas == []
