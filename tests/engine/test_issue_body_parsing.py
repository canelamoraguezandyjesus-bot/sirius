"""La inversa de la proyección: leer de vuelta lo que el cuerpo declara.

La propiedad que importa no es «el parser funciona con este ejemplo», sino
**ida y vuelta**: proyectar un WorkItem y volver a leerlo devuelve lo que el
cuerpo declaraba. Escrita como propiedad sobre WorkItems generados, no sobre
un cuerpo pegado a mano — un cuerpo pegado a mano envejece en cuanto la
proyección cambia una palabra, y entonces la prueba mide el pegado.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemPhase, WorkItemState
from sirius_engine.issue_body_parsing import CuerpoDeclarado, leer_cuerpo_declarado
from sirius_engine.issue_body_projection import generar_cuerpo_incidencia
from sirius_engine.profile_field import ProfileRef

_AHORA = datetime(2026, 8, 22, tzinfo=UTC)
_PERFIL = ProfileRef(ref="implementer", version=1)


def _work_item(
    *,
    objetivo: str = "Corrige la cita rota del contrato",
    contexto_origen: tuple[str, ...] = ("sesion-cli",),
    entregable: str = "El cambio en el código que pide el objetivo, y nada más.",
    criterio_terminado: str = "Las validaciones obligatorias en verde.",
    plan: tuple[str, ...] = (),
    limites: dict[str, object] | None = None,
) -> WorkItem:
    return WorkItem(
        work_id="WI-20260822-120000",
        peticion_original="da igual: el cuerpo no la lleva",
        objetivo=objetivo,
        contexto_origen=contexto_origen,
        entregable=entregable,
        criterio_terminado=criterio_terminado,
        limites=MappingProxyType(dict(limites or {})),
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.PREPARAR,
        plan=plan,
        version=1,
        created_at=_AHORA,
        updated_at=_AHORA,
    )


def _ida_y_vuelta(
    work_item: WorkItem, *, bloque: str = "C9", base: str = "main"
) -> CuerpoDeclarado:
    cuerpo = generar_cuerpo_incidencia(
        work_item, profile_ref=_PERFIL, bloque=bloque, base_branch=base
    )
    return leer_cuerpo_declarado(cuerpo)


def test_ida_y_vuelta_devuelve_lo_que_el_cuerpo_declara() -> None:
    w = _work_item()
    leido = _ida_y_vuelta(w)
    assert leido.work_id == w.work_id
    assert leido.objetivo == w.objetivo
    assert leido.entregable == w.entregable
    assert leido.criterio_terminado == w.criterio_terminado
    assert leido.contexto_origen == w.contexto_origen
    assert leido.bloque == "C9"
    assert leido.rama_base == "main"


@pytest.mark.parametrize(
    "objetivo",
    [
        "Una línea sola",
        "Con dos puntos: y una coma, y un punto.",
        "Con acentos, eñes y símbolos — guion largo incluido",
        "Con `código en línea` y **negrita**",
        "Con una línea\ny otra debajo",
    ],
)
def test_el_objetivo_sobrevive_a_la_ida_y_vuelta(objetivo: str) -> None:
    """El objetivo es texto libre del propietario: no puede romper el parser."""
    assert _ida_y_vuelta(_work_item(objetivo=objetivo)).objetivo == objetivo


def test_el_plan_se_separa_del_criterio_de_terminado() -> None:
    """La proyección los CONCATENA en una sección; la inversa tiene que partirlos."""
    w = _work_item(criterio_terminado="Todo en verde.", plan=("Primero esto", "Después lo otro"))
    leido = _ida_y_vuelta(w)
    assert leido.criterio_terminado == "Todo en verde."
    assert leido.plan == ("Primero esto", "Después lo otro")


def test_sin_plan_el_criterio_llega_entero_y_el_plan_es_none() -> None:
    leido = _ida_y_vuelta(_work_item(criterio_terminado="Todo en verde.", plan=()))
    assert leido.criterio_terminado == "Todo en verde."
    assert leido.plan is None


def test_sin_referencias_se_lee_lista_vacia_y_no_none() -> None:
    """«No hay referencias» y «no se pudo leer» no son lo mismo.

    La proyección escribe una frase fija cuando no hay contexto de origen.
    Leerla como `()` permite comparar ese caso; leerla como `None` lo excluiría
    de la verificación, que es como se fabrica un verde vacío.
    """
    leido = _ida_y_vuelta(_work_item(contexto_origen=()))
    assert leido.contexto_origen == ()


def test_varias_referencias_se_leen_todas() -> None:
    w = _work_item(contexto_origen=("sesion-cli", "ADR-001", "incidencia #250"))
    assert _ida_y_vuelta(w).contexto_origen == ("sesion-cli", "ADR-001", "incidencia #250")


def test_el_fuera_de_alcance_declarado_en_limites_se_lee() -> None:
    w = _work_item(limites={"fuera_de_alcance": "No tocar .github/**"})
    assert _ida_y_vuelta(w).fuera_de_alcance == "No tocar .github/**"


def test_un_cuerpo_sin_una_seccion_devuelve_none_en_ese_campo() -> None:
    """Ausente es `None`, no cadena vacía: el verificador tiene que poder decir
    «esto no lo pude leer» en vez de «esto está vacío»."""
    leido = leer_cuerpo_declarado("## Work ID\n\nWI-1\n\n## Objetivo\n\nAlgo\n")
    assert leido.work_id == "WI-1"
    assert leido.objetivo == "Algo"
    assert leido.entregable is None
    assert leido.rama_base is None
    assert leido.contexto_origen is None


def test_un_cuerpo_vacio_no_revienta_y_no_declara_nada() -> None:
    leido = leer_cuerpo_declarado("")
    assert leido.work_id is None and leido.objetivo is None and leido.plan is None


def test_una_seccion_presente_pero_vacia_es_none() -> None:
    assert leer_cuerpo_declarado("## Objetivo\n\n\n\n## Bloque\n\nX\n").objetivo is None
