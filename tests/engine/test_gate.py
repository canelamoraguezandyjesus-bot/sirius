"""puerta_determinista: arquitectura §8.5, tres desenlaces y ninguno más.

A5-P2 (incidencia #206): una orden inequívoca crea Y activa, sin segunda
confirmación -comprobado aquí de forma estructural: ``DecisionPuerta`` para
``ORDEN_INEQUIVOCA`` no tiene ningún campo de confirmación pendiente.
A5-P3: una petición ambigua no crea trabajo.
"""

from __future__ import annotations

import pytest

from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.intent import DatosNuevoTrabajo, IntentSignal, TipoIntencion
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.gate import ResultadoPuerta, decidir


def _datos() -> DatosNuevoTrabajo:
    return DatosNuevoTrabajo(
        objetivo="implementar X",
        entregable="X funcionando",
        criterio_terminado="las pruebas de X pasan",
        clase=WorkItemClass.PROGRAMACION,
        limites={"presupuesto": {"limite": 10.0}},
    )


def test_orden_inequivoca_crea_y_activa_sin_ningun_campo_de_confirmacion() -> None:
    signal = IntentSignal(
        tipo=TipoIntencion.ORDEN_INEQUIVOCA, mensaje_original="implementa X", datos_trabajo=_datos()
    )
    decision = decidir(signal)
    assert decision.resultado is ResultadoPuerta.CREAR_Y_ACTIVAR
    assert decision.datos_trabajo == _datos()
    # Estructural: DecisionPuerta no tiene ningún campo de "confirmación
    # pendiente" -no puede pedirla porque el tipo no lo permite.
    assert not hasattr(decision, "confirmacion_pendiente")
    assert not hasattr(decision, "requiere_confirmacion")


@pytest.mark.parametrize(
    "tipo",
    (TipoIntencion.CONVERSAR, TipoIntencion.EXPLORAR, TipoIntencion.AMBIGUA),
)
def test_tipos_sin_trabajo_nunca_crean_nada(tipo: TipoIntencion) -> None:
    signal = IntentSignal(tipo=tipo, mensaje_original="mensaje cualquiera")
    decision = decidir(signal)
    assert decision.resultado is ResultadoPuerta.NO_CREAR
    assert decision.datos_trabajo is None


def test_consultar_pasado_tampoco_crea_nada() -> None:
    signal = IntentSignal(
        tipo=TipoIntencion.CONSULTAR_PASADO, mensaje_original="que paso con X", consulta="X"
    )
    decision = decidir(signal)
    assert decision.resultado is ResultadoPuerta.NO_CREAR
    assert decision.consulta == "X"


def test_ambigua_conserva_la_pregunta_aclaratoria() -> None:
    signal = IntentSignal(
        tipo=TipoIntencion.AMBIGUA,
        mensaje_original="quizá deberíamos mejorar esto",
        pregunta_aclaratoria="¿qué debe existir al terminar?",
    )
    decision = decidir(signal)
    assert decision.resultado is ResultadoPuerta.NO_CREAR
    assert decision.pregunta_aclaratoria == "¿qué debe existir al terminar?"


def test_sensible_o_material_crea_pero_no_activa_directamente() -> None:
    signal = IntentSignal(
        tipo=TipoIntencion.SENSIBLE_O_MATERIAL,
        mensaje_original="borra la base de producción",
        datos_trabajo=_datos(),
        causa_sensibilidad=CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
    )
    decision = decidir(signal)
    assert decision.resultado is ResultadoPuerta.CREAR_Y_ESCALAR
    assert decision.causa_escalado is CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE
    assert decision.datos_trabajo == _datos()


def test_la_puerta_es_determinista_misma_entrada_misma_salida() -> None:
    signal = IntentSignal(
        tipo=TipoIntencion.ORDEN_INEQUIVOCA, mensaje_original="implementa X", datos_trabajo=_datos()
    )
    assert decidir(signal) == decidir(signal)
