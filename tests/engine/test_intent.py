"""IntentSignal: la frontera entre interpretación [M] y puerta determinista [D]."""

from __future__ import annotations

import pytest

from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.intent import DatosNuevoTrabajo, IntentSignal, TipoIntencion
from sirius_engine.domain.work_item import WorkItemClass


def _datos() -> DatosNuevoTrabajo:
    return DatosNuevoTrabajo(
        objetivo="objetivo",
        entregable="entregable",
        criterio_terminado="criterio",
        clase=WorkItemClass.PROGRAMACION,
        limites={"presupuesto": {"limite": 10.0}},
    )


def test_conversar_no_exige_ningun_dato_adicional() -> None:
    IntentSignal(tipo=TipoIntencion.CONVERSAR, mensaje_original="hola")


def test_orden_inequivoca_exige_datos_de_trabajo() -> None:
    with pytest.raises(ValueError, match="datos_trabajo"):
        IntentSignal(tipo=TipoIntencion.ORDEN_INEQUIVOCA, mensaje_original="implementa X")


def test_orden_inequivoca_con_datos_de_trabajo_es_valida() -> None:
    IntentSignal(
        tipo=TipoIntencion.ORDEN_INEQUIVOCA, mensaje_original="implementa X", datos_trabajo=_datos()
    )


def test_sensible_o_material_exige_causa() -> None:
    with pytest.raises(ValueError, match="causa_sensibilidad"):
        IntentSignal(
            tipo=TipoIntencion.SENSIBLE_O_MATERIAL,
            mensaje_original="borra todo",
            datos_trabajo=_datos(),
        )


def test_sensible_o_material_completa_es_valida() -> None:
    IntentSignal(
        tipo=TipoIntencion.SENSIBLE_O_MATERIAL,
        mensaje_original="borra todo",
        datos_trabajo=_datos(),
        causa_sensibilidad=CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE,
    )


def test_consultar_pasado_exige_consulta() -> None:
    with pytest.raises(ValueError, match="consulta"):
        IntentSignal(tipo=TipoIntencion.CONSULTAR_PASADO, mensaje_original="que paso con X")


def test_datos_nuevo_trabajo_congela_limites() -> None:
    limites_mutables = {"presupuesto": {"limite": 1.0}}
    datos = DatosNuevoTrabajo(
        objetivo="o",
        entregable="e",
        criterio_terminado="c",
        clase=WorkItemClass.INVESTIGACION,
        limites=limites_mutables,
    )
    limites_mutables["presupuesto"] = {"limite": 999.0}
    assert datos.limites == {"presupuesto": {"limite": 1.0}}
