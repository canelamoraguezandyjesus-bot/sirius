"""SesionCLI: interfaz v0, sin estado propio (objetivo 5, incidencia #206).

A5-P1: una conversación de varios turnos, con consultas al pasado incluidas,
no crea ningún WorkItem.
A5-P2: una orden inequívoca crea y activa, sin segunda confirmación.
A5-P3: una petición ambigua no crea trabajo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.escalation import Escalada
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.session import ContextoRecuperarConfig, SesionCLI

_NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


class _Notificador:
    def __init__(self) -> None:
        self.entregadas: list[Escalada] = []

    def notificar(self, escalada: Escalada) -> None:
        self.entregadas.append(escalada)


def _sesion(*, tmp_path: Path) -> tuple[SesionCLI, InMemoryWorkEngineStore, _Notificador]:
    store = InMemoryWorkEngineStore()
    notificador = _Notificador()
    contexto_cfg = ContextoRecuperarConfig(
        raiz_repo=tmp_path,
        port=FixedGitHubMirrorReader(),
        repo="canelamoraguezandyjesus-bot/sirius",
        numeros_incidencias=(),
        entradas_git_log=(),
    )
    sesion = SesionCLI(store=store, notificar=notificador, contexto_recuperar=contexto_cfg)
    return sesion, store, notificador


def test_conversacion_de_varios_turnos_no_crea_ningun_workitem(tmp_path: Path) -> None:
    """A5-P1."""
    sesion, store, _ = _sesion(tmp_path=tmp_path)
    turnos = (
        "hola",
        "¿qué pasó con el bloque B12?",
        "¿cómo va la migración de la base de datos?",
        "quizá deberíamos revisar el enfoque del despachador",
        "gracias",
    )
    for indice, mensaje in enumerate(turnos):
        respuesta = sesion.procesar_turno(
            mensaje, work_id=f"WI-SESION-{indice}", now=_NOW + timedelta(minutes=indice)
        )
        assert respuesta.intake is None

    assert store.list_events() == ()


def test_orden_inequivoca_crea_y_activa_sin_segunda_confirmacion(tmp_path: Path) -> None:
    """A5-P2."""
    sesion, store, _ = _sesion(tmp_path=tmp_path)
    respuesta = sesion.procesar_turno(
        "implementa el despachador de programación", work_id="WI-SESION-ORDEN", now=_NOW
    )
    assert respuesta.intake is not None
    assert respuesta.intake.work_item is not None
    assert respuesta.intake.work_item.estado is WorkItemState.ACTIVE

    work_item = store.get_work_item("WI-SESION-ORDEN")
    assert work_item is not None
    assert work_item.estado is WorkItemState.ACTIVE


def test_peticion_ambigua_no_crea_trabajo(tmp_path: Path) -> None:
    """A5-P3."""
    sesion, store, _ = _sesion(tmp_path=tmp_path)
    respuesta = sesion.procesar_turno("el despachador", work_id="WI-SESION-AMBIGUA", now=_NOW)
    assert respuesta.intake is None
    assert store.get_work_item("WI-SESION-AMBIGUA") is None
    assert respuesta.mensaje


def test_orden_sensible_escala_y_notifica_en_vez_de_activar(tmp_path: Path) -> None:
    sesion, _store, notificador = _sesion(tmp_path=tmp_path)
    respuesta = sesion.procesar_turno(
        "borra la base de producción", work_id="WI-SESION-SENSIBLE", now=_NOW
    )
    assert respuesta.intake is not None
    assert respuesta.intake.work_item is not None
    assert respuesta.intake.work_item.estado is WorkItemState.NEEDS_DECISION
    assert len(notificador.entregadas) == 1


def test_una_conversacion_larga_intercalada_con_una_orden_solo_crea_ese_workitem(
    tmp_path: Path,
) -> None:
    """A5-P1 + A5-P2 combinadas: la conversación no deja rastro, la orden sí."""
    sesion, store, _ = _sesion(tmp_path=tmp_path)
    guion = (
        ("hola", False),
        ("¿qué pasó con la incidencia 177?", False),
        ("quizá convendría revisar esto primero", False),
        ("implementa el despachador de programación", True),
        ("gracias", False),
    )
    for indice, (mensaje, crea_trabajo) in enumerate(guion):
        respuesta = sesion.procesar_turno(
            mensaje, work_id=f"WI-GUION-{indice}", now=_NOW + timedelta(minutes=indice)
        )
        assert (respuesta.intake is not None) is crea_trabajo

    work_items_creados = [
        event for event in store.list_events() if event.kind == "work_item_created"
    ]
    assert len(work_items_creados) == 1
    assert work_items_creados[0].aggregate_id == "WI-GUION-3"
