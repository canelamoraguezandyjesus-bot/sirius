"""autoridad_de_clase: función total sobre WorkItemClass (contrato §11.1, ADR-041).

D1c (incidencia #276, contrato §11.3) añade el segundo término: la tabla
estática más lo que diga un registro fechado de conmutaciones
(:class:`EntradaConmutacion`). Las pruebas de esta segunda mitad viven en la
sección propia más abajo; las de la tabla estática, arriba, no cambian -es
exactamente la garantía que este bloque no puede romper.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius_engine.domain import authority
from sirius_engine.domain.authority import (
    Autoridad,
    EntradaConmutacion,
    autoridad_de_clase,
    formatear_entrada_conmutacion,
    parsear_entrada_conmutacion,
)
from sirius_engine.domain.work_item import WorkItemClass

_CLASES_MOTOR = (
    WorkItemClass.CONVERSACION_NO_APLICA,
    WorkItemClass.INVESTIGACION,
    WorkItemClass.DOCUMENTACION,
    WorkItemClass.CONSULTA_LARGA,
    WorkItemClass.MIXTA,
)
_CLASES_INCIDENCIA = (WorkItemClass.PROGRAMACION, WorkItemClass.AUDITORIA)


def _instante(dia: int = 1) -> datetime:
    return datetime(2026, 8, dia, tzinfo=UTC)


@pytest.mark.parametrize("clase", _CLASES_MOTOR)
def test_clases_nativas_sin_proyeccion_github_son_autoridad_motor(clase: WorkItemClass) -> None:
    assert autoridad_de_clase(clase) is Autoridad.MOTOR


@pytest.mark.parametrize("clase", _CLASES_INCIDENCIA)
def test_clases_con_proyeccion_github_son_autoridad_incidencia(clase: WorkItemClass) -> None:
    assert autoridad_de_clase(clase) is Autoridad.INCIDENCIA


def test_ninguna_clase_de_workitemclass_se_queda_sin_autoridad() -> None:
    """Función total: sin huecos (requisito 'un WorkItem nace siempre con autoridad')."""
    for clase in WorkItemClass:
        assert autoridad_de_clase(clase) in (Autoridad.MOTOR, Autoridad.INCIDENCIA)


# --- D1c: el registro de conmutaciones, segundo término de la función -----


def test_ninguna_clase_se_queda_sin_autoridad_con_registro_no_vacio() -> None:
    """La misma totalidad, ahora con un registro no vacío -para TODO WorkItemClass.

    Requisito 3 de la incidencia #276: una prueba recorre `WorkItemClass`
    entero y exige respuesta con y sin registro.
    """
    registro = (
        EntradaConmutacion(
            instante=_instante(),
            clase=WorkItemClass.PROGRAMACION,
            autoridad=Autoridad.MOTOR,
            motivo="conmutación de prueba",
        ),
    )
    for clase in WorkItemClass:
        assert autoridad_de_clase(clase, registro=registro) in (
            Autoridad.MOTOR,
            Autoridad.INCIDENCIA,
        )


def test_clase_sin_fila_en_la_tabla_revienta_explicito_con_y_sin_registro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simula un `WorkItemClass` nuevo sin fila: sigue reventando, nunca asume nada.

    Requisito 3: la propiedad de ADR-041 -función total, sin valor por
    defecto, `KeyError` explícito- sobrevive al segundo término añadido por
    D1c, tanto si se pasa `registro` como si no.
    """
    tabla_incompleta = {
        clase: valor
        for clase, valor in authority._TABLA_AUTORIDAD.items()
        if clase is not WorkItemClass.PROGRAMACION
    }
    monkeypatch.setattr(authority, "_TABLA_AUTORIDAD", tabla_incompleta)

    with pytest.raises(KeyError):
        autoridad_de_clase(WorkItemClass.PROGRAMACION)

    registro_de_otra_clase = (
        EntradaConmutacion(
            instante=_instante(),
            clase=WorkItemClass.AUDITORIA,
            autoridad=Autoridad.MOTOR,
            motivo="otra clase, no protege a la que perdió su fila",
        ),
    )
    with pytest.raises(KeyError):
        autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=registro_de_otra_clase)


@pytest.mark.parametrize("clase", _CLASES_MOTOR)
def test_una_clase_motor_no_puede_entrar_en_el_registro(clase: WorkItemClass) -> None:
    """Requisito 4: nacieron canónicas y no conmutan; intentarlo falla ruidosamente."""
    with pytest.raises(ValueError, match="no conmuta"):
        EntradaConmutacion(
            instante=_instante(),
            clase=clase,
            autoridad=Autoridad.INCIDENCIA,
            motivo="intento inválido",
        )


@pytest.mark.parametrize("clase", _CLASES_INCIDENCIA)
def test_una_clase_con_proyeccion_github_si_puede_entrar_en_el_registro(
    clase: WorkItemClass,
) -> None:
    entrada = EntradaConmutacion(
        instante=_instante(), clase=clase, autoridad=Autoridad.MOTOR, motivo="conmutación válida"
    )
    assert entrada.clase is clase


def test_sin_entradas_para_la_clase_el_registro_no_cambia_nada() -> None:
    """Un registro no vacío pero de OTRA clase no afecta a la consultada."""
    registro = (
        EntradaConmutacion(
            instante=_instante(),
            clase=WorkItemClass.AUDITORIA,
            autoridad=Autoridad.MOTOR,
            motivo="conmutación de AUDITORIA",
        ),
    )
    assert autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=registro) is Autoridad.INCIDENCIA


def test_la_entrada_mas_reciente_manda() -> None:
    """Dos entradas de la misma clase: manda la de mayor `instante`, no el orden de la lista."""
    conmuta = EntradaConmutacion(
        instante=_instante(1),
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.MOTOR,
        motivo="conmuta",
    )
    revierte = EntradaConmutacion(
        instante=_instante(10),
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.INCIDENCIA,
        motivo="revierte",
    )
    assert (
        autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=(revierte, conmuta))
        is Autoridad.INCIDENCIA
    )
    assert autoridad_de_clase(WorkItemClass.PROGRAMACION, registro=(conmuta,)) is Autoridad.MOTOR


def test_formatear_y_parsear_una_entrada_es_la_identidad() -> None:
    entrada = EntradaConmutacion(
        instante=_instante(3),
        clase=WorkItemClass.AUDITORIA,
        autoridad=Autoridad.INCIDENCIA,
        motivo="divergencia en el eje fase",
    )
    assert parsear_entrada_conmutacion(formatear_entrada_conmutacion(entrada)) == entrada


def test_formatear_es_deterministico() -> None:
    """Misma entrada, mismo texto exacto -condición del registro append-only (requisito 8)."""
    entrada = EntradaConmutacion(
        instante=_instante(3),
        clase=WorkItemClass.PROGRAMACION,
        autoridad=Autoridad.MOTOR,
        motivo="x",
    )
    assert formatear_entrada_conmutacion(entrada) == formatear_entrada_conmutacion(entrada)
