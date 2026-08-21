"""SesionCLI: interfaz v0, sin estado propio (objetivo 5, incidencia #206).

A5-P1: una conversación de varios turnos, con consultas al pasado incluidas,
no crea ningún WorkItem.
A5-P2: una orden inequívoca crea y activa, sin segunda confirmación.
A5-P3: una petición ambigua no crea trabajo.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.context_recall import LecturaHistorialGit
from sirius_engine.domain.escalation import Escalada
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.ports.github_mirror import LecturaEstado
from sirius_engine.session import ContextoRecuperarConfig, SesionCLI

_NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


class _Notificador:
    def __init__(self) -> None:
        self.entregadas: list[Escalada] = []

    def notificar(self, escalada: Escalada) -> None:
        self.entregadas.append(escalada)


_HISTORIAL_LEIDO_Y_VACIO = LecturaHistorialGit(estado=LecturaEstado.OK, entradas=())
_HISTORIAL_ILEGIBLE = LecturaHistorialGit(
    estado=LecturaEstado.NO_DISPONIBLE, error="git log no se pudo ejecutar"
)


def _sesion(
    *,
    tmp_path: Path,
    numeros_incidencias: Sequence[int] = (),
    lectura_historial_git: LecturaHistorialGit = _HISTORIAL_LEIDO_Y_VACIO,
) -> tuple[SesionCLI, InMemoryWorkEngineStore, _Notificador]:
    """Sesión de pruebas.

    Por defecto, las tres fuentes de ``contexto.recuperar`` se leen bien y no
    tienen nada: es el caso "miré y no había nada". Los dos parámetros
    permiten tirar fuentes por separado -``FixedGitHubMirrorReader`` devuelve
    ``NO_DISPONIBLE`` para cualquier número que no tenga configurado- sin
    tocar las demás.
    """
    store = InMemoryWorkEngineStore()
    notificador = _Notificador()
    contexto_cfg = ContextoRecuperarConfig(
        raiz_repo=tmp_path,
        port=FixedGitHubMirrorReader(),
        repo="canelamoraguezandyjesus-bot/sirius",
        numeros_incidencias=numeros_incidencias,
        lectura_historial_git=lectura_historial_git,
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


# --- H-9 (incidencia #224, ADR-059): la sesión no miente cuando no pudo mirar ---
#
# El texto que devuelve un turno es lo ÚNICO que ve una persona. Si las fuentes
# de `contexto.recuperar` no se pudieron leer, decir "no encontré referencias"
# es afirmar una ausencia que nadie ha comprobado (familia ADR-036, un nivel por
# encima de H-5). Estas cuatro pruebas fijan las tres frases posibles y, sobre
# todo, que no se confundan entre sí.

_CONSULTA = "¿qué pasó con el bloque B12e?"


def _preguntar(sesion: SesionCLI) -> str:
    return sesion.procesar_turno(_CONSULTA, work_id="WI-H9", now=_NOW).mensaje


def test_la_sesion_dice_que_no_pudo_mirar_en_vez_de_que_no_hay_nada(tmp_path: Path) -> None:
    """H-9: con las tres fuentes caídas, «no encontré» sería una mentira."""
    sesion, _store, _ = _sesion(
        tmp_path=tmp_path,
        numeros_incidencias=(404,),
        lectura_historial_git=_HISTORIAL_ILEGIBLE,
    )
    mensaje = _preguntar(sesion)

    # Lo que NO puede decir: la frase que suena a respuesta comprobada.
    assert "No encontré referencias" not in mensaje
    # Lo que SÍ tiene que decir: que hay sitios sin leer, y cuáles.
    assert "no se dejaron leer" in mensaje
    assert "historial_git" in mensaje
    assert "incidencia:404:cuerpo" in mensaje
    assert "incidencia:404:comentarios" in mensaje


def test_la_sesion_sigue_diciendo_igual_que_hoy_que_miro_y_no_habia_nada(tmp_path: Path) -> None:
    """H-9 requisito 2: sin huecos, la frase de siempre, sin avisos añadidos."""
    sesion, _store, _ = _sesion(tmp_path=tmp_path)
    mensaje = _preguntar(sesion)

    assert mensaje == f"No encontré referencias para {_CONSULTA!r}."
    assert "no se dejaron leer" not in mensaje


def test_la_sesion_ensena_lo_encontrado_y_ademas_el_hueco(tmp_path: Path) -> None:
    """H-9 requisito 3: el caso mixto enseña las dos cosas, no solo una."""
    (tmp_path / "NOTAS.md").write_text(f"- {_CONSULTA} quedó a medias\n", encoding="utf-8")
    sesion, _store, _ = _sesion(tmp_path=tmp_path, lectura_historial_git=_HISTORIAL_ILEGIBLE)
    mensaje = _preguntar(sesion)

    # Lo encontrado sigue estando, con su cita.
    assert "fichero:NOTAS.md:1" in mensaje
    # Y el hueco también: una respuesta parcial que se lee como completa es la
    # misma mentira, con hallazgos delante.
    assert "no se dejaron leer" in mensaje
    assert "historial_git" in mensaje


def test_la_sesion_no_avisa_de_huecos_cuando_pudo_leerlo_todo(tmp_path: Path) -> None:
    """H-9: el arreglo tramposo «avisar siempre» no vale como arreglo."""
    (tmp_path / "NOTAS.md").write_text(f"- {_CONSULTA} quedó a medias\n", encoding="utf-8")
    sesion, _store, _ = _sesion(tmp_path=tmp_path)
    mensaje = _preguntar(sesion)

    assert mensaje == f"Encontré 1 referencia(s) para {_CONSULTA!r}: fichero:NOTAS.md:1"
    assert "no se dejaron leer" not in mensaje


def test_la_sesion_no_le_vuelca_a_una_persona_una_lista_interminable_de_sitios(
    tmp_path: Path,
) -> None:
    """H-9: «cuáles» no puede convertirse en un muro de texto ilegible.

    Catorce lecturas caídas (siete incidencias x cuerpo + comentarios) se citan
    como las referencias encontradas: las cinco primeras y el recuento del
    resto. El número que se anuncia es siempre el total, nunca el de la lista
    recortada.
    """
    sesion, _store, _ = _sesion(tmp_path=tmp_path, numeros_incidencias=(1, 2, 3, 4, 5, 6, 7))
    mensaje = _preguntar(sesion)

    assert "14 sitio(s) no se dejaron leer" in mensaje
    assert "y 9 más" in mensaje
    assert "incidencia:7:comentarios" not in mensaje
