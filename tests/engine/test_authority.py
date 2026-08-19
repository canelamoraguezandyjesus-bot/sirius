"""autoridad_de_clase: función total sobre WorkItemClass (contrato §11.1, ADR-041)."""

from __future__ import annotations

import pytest

from sirius_engine.domain.authority import Autoridad, autoridad_de_clase
from sirius_engine.domain.work_item import WorkItemClass


@pytest.mark.parametrize(
    "clase",
    (
        WorkItemClass.CONVERSACION_NO_APLICA,
        WorkItemClass.INVESTIGACION,
        WorkItemClass.DOCUMENTACION,
        WorkItemClass.CONSULTA_LARGA,
        WorkItemClass.MIXTA,
    ),
)
def test_clases_nativas_sin_proyeccion_github_son_autoridad_motor(clase: WorkItemClass) -> None:
    assert autoridad_de_clase(clase) is Autoridad.MOTOR


@pytest.mark.parametrize("clase", (WorkItemClass.PROGRAMACION, WorkItemClass.AUDITORIA))
def test_clases_con_proyeccion_github_son_autoridad_incidencia(clase: WorkItemClass) -> None:
    assert autoridad_de_clase(clase) is Autoridad.INCIDENCIA


def test_ninguna_clase_de_workitemclass_se_queda_sin_autoridad() -> None:
    """Función total: sin huecos (requisito 'un WorkItem nace siempre con autoridad')."""
    for clase in WorkItemClass:
        assert autoridad_de_clase(clase) in (Autoridad.MOTOR, Autoridad.INCIDENCIA)
