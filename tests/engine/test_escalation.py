"""CausaEscalado: la lista cerrada de siete causas, y Escalada con contexto completo.

A5-P5 (incidencia #206): "una causa de las siete escala; ninguna otra lo
hace. Se prueban las dos direcciones." La dirección "ninguna otra escala" se
prueba aquí de forma ESTRUCTURAL: el conjunto de miembros de
``CausaEscalado`` se compara contra una lista literal de siete cadenas
escrita de forma independiente del propio enum -si alguien añadiera un
octavo miembro sin querer, esta prueba cae, sin depender de que nadie se
acuerde de revisar la lista a mano.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sirius_engine.domain.escalation import CausaEscalado, construir_escalada
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item

#: Lista literal, independiente de `CausaEscalado`: la comprobación de que
#: no hay una octava causa depende de que esta lista NO se derive del enum.
_SIETE_CAUSAS_CERRADAS = frozenset(
    {
        "decision_producto_o_arquitectura",
        "gasto_o_presupuesto",
        "permisos_o_credenciales_sensibles",
        "operacion_destructiva_o_irreversible",
        "privacidad_o_informacion_sensible",
        "alternativas_materialmente_distintas",
        "ausencia_de_convergencia",
    }
)


def test_la_lista_de_causas_tiene_exactamente_siete_miembros() -> None:
    assert len(CausaEscalado) == 7


def test_la_lista_de_causas_es_exactamente_la_cerrada_de_arquitectura_10() -> None:
    valores = frozenset(causa.value for causa in CausaEscalado)
    assert valores == _SIETE_CAUSAS_CERRADAS


def _work_item() -> WorkItem:
    return create_work_item(
        work_id="WI-ESC-0001",
        peticion_original="borra la base de producción",
        objetivo="atender la orden",
        contexto_origen=("sesion-cli",),
        entregable="lo pedido",
        criterio_terminado="criterio",
        limites={"presupuesto": {"limite": 10.0}},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
    )


def test_construir_escalada_copia_la_instantanea_completa_del_work_item() -> None:
    """Requisito: la escalada lleva contexto suficiente para decidir sin reconstruir nada."""
    work_item = _work_item()
    escalada = construir_escalada(
        work_item,
        causa=CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
        motivo="la orden pide borrar la base de producción",
        ocurrida_en=datetime(2026, 8, 19, 12, 5, tzinfo=UTC),
    )
    assert escalada.work_id == work_item.work_id
    assert escalada.causa is CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE
    assert escalada.peticion_original == work_item.peticion_original
    assert escalada.objetivo == work_item.objetivo
    assert escalada.entregable == work_item.entregable
    assert escalada.criterio_terminado == work_item.criterio_terminado
    assert escalada.limites == work_item.limites
    assert escalada.contexto_origen == work_item.contexto_origen


def test_construir_escalada_conserva_referencias_adicionales() -> None:
    work_item = _work_item()
    escalada = construir_escalada(
        work_item,
        causa=CausaEscalado.DECISION_PRODUCTO_O_ARQUITECTURA,
        motivo="motivo",
        ocurrida_en=datetime(2026, 8, 19, 12, 5, tzinfo=UTC),
        referencias=("incidencia:206:comentario:0",),
    )
    assert escalada.referencias == ("incidencia:206:comentario:0",)
