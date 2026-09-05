"""``sirius-reflejar``: la cáscara de C1 (incidencia #529).

Igual que ``tests/engine/test_seven_day_streak_cli.py``: fija el CABLEADO
-que la pasada lea el trabajo correcto, calcule el plan con
:func:`sirius_engine.reflect.reflejar_desenlace` y lo aplique (o no, en
``--ensayo``)- sin tocar red ni disco real; las propiedades del cálculo del
plan ya las prueba ``tests/engine/test_reflect.py``.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine import reflect_cli
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.work_item import WorkItemClass, WorkItemPhase, WorkItemState
from sirius_engine.ports.github_mirror import (
    Comentario,
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    MetadatosIncidencia,
)

_AHORA = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
_REPO = "canelamoraguezandyjesus-bot/sirius"
_NUMERO = 508
_WORK_ID = "WI-1"


def _correr(
    argv: list[str],
    *,
    store: InMemoryWorkEngineStore,
    journal: InMemoryDispatchJournal,
    mirror: FixedGitHubMirrorReader,
    ahora: datetime = _AHORA,
) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = reflect_cli.main(
        argv,
        entorno={},
        salida=salida,
        ahora=ahora,
        store=store,
        dispatch_journal=journal,
        mirror=mirror,
    )
    return codigo, salida.getvalue()


def _mirror(*, etiqueta: str, numero: int = _NUMERO) -> FixedGitHubMirrorReader:
    return FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, numero): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=numero, titulo="t", estado_gh="open", etiquetas=(etiqueta,)
                ),
            )
        },
        cuerpos_por_incidencia={
            (_REPO, numero): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(autor_login="x", autor_asociacion="OWNER", texto=""),
            )
        },
        comentarios_por_incidencia={
            (_REPO, numero): LecturaComentarios(estado=LecturaEstado.OK, comentarios=())
        },
    )


def _preparar(
    store: InMemoryWorkEngineStore,
    journal: InMemoryDispatchJournal,
    *,
    work_id: str = _WORK_ID,
    numero: int = _NUMERO,
) -> None:
    store.create_work_item(
        work_id=work_id,
        peticion_original="texto",
        objetivo="objetivo",
        contexto_origen=("incidencia:1",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_AHORA,
    )
    store.activate_work_item(work_id, now=_AHORA)
    journal.record(
        DispatchEpisode(
            work_id=work_id,
            orden_enlazada="orden-propietario:issue#1",
            repo=_REPO,
            numero_incidencia=numero,
            etiqueta="sirius:implement-requested",
            recorded_at=_AHORA,
        )
    )


def test_sin_ensayo_aplica_el_plan_y_lo_deja_en_el_diario(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:ci-pending"),
    )

    assert codigo == 0
    assert f"{_WORK_ID}: aplicados 2 paso(s)" in texto
    assert "Pasos aplicados en total: 2." in texto
    final = store.get_work_item(_WORK_ID)
    assert final is not None
    assert final.fase is WorkItemPhase.COMPROBAR


def test_ensayo_no_aplica_nada(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)

    codigo, texto = _correr(
        ["--ensayo", "--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
    )

    assert codigo == 0
    assert "ENSAYO" in texto
    assert f"{_WORK_ID}: aplicaría 1 paso(s)" in texto
    final = store.get_work_item(_WORK_ID)
    assert final is not None
    assert final.fase is WorkItemPhase.PREPARAR, "el ensayo no puede tocar el almacén"


def test_un_workitem_ya_terminal_se_salta(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    store.begin_work_item_check(_WORK_ID, now=_AHORA)
    store.begin_work_item_review(_WORK_ID, now=_AHORA)
    store.approve_work_item_review(_WORK_ID, now=_AHORA)
    store.deliver_work_item(_WORK_ID, resultado={"numero_incidencia": _NUMERO}, now=_AHORA)

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:completed"),
    )

    assert codigo == 0
    assert _WORK_ID not in texto, "un WorkItem terminal no necesita leer su incidencia otra vez"


def test_una_incidencia_illegible_no_impide_seguir_con_las_demas(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal, work_id="WI-1", numero=508)
    _preparar(store, journal, work_id="WI-2", numero=999)
    mirror = _mirror(etiqueta="sirius:implementing", numero=508)
    # WI-2 (incidencia #999) se queda sin configurar en el espejo: LecturaEstado.NO_DISPONIBLE.

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=mirror,
    )

    assert codigo == 0
    assert "no pude leer la incidencia #999" in texto
    assert "WI-1: aplicados 1 paso(s)" in texto
    final_1 = store.get_work_item("WI-1")
    assert final_1 is not None and final_1.fase is WorkItemPhase.EJECUTAR
    final_2 = store.get_work_item("WI-2")
    assert final_2 is not None and final_2.fase is WorkItemPhase.PREPARAR


def test_espejo_sin_etiqueta_de_estado_no_dice_nada(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    mirror = FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, _NUMERO): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=_NUMERO, titulo="t", estado_gh="open", etiquetas=()
                ),
            )
        },
        cuerpos_por_incidencia={
            (_REPO, _NUMERO): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(autor_login="x", autor_asociacion="OWNER", texto=""),
            )
        },
        comentarios_por_incidencia={
            (_REPO, _NUMERO): LecturaComentarios(estado=LecturaEstado.OK, comentarios=())
        },
    )

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=mirror,
    )

    assert codigo == 0
    assert _WORK_ID not in texto
    assert "Pasos aplicados en total: 0." in texto


def test_completed_con_sha_de_fusion_entrega_el_workitem(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    mirror = FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, _NUMERO): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=_NUMERO, titulo="t", estado_gh="closed", etiquetas=("sirius:completed",)
                ),
            )
        },
        cuerpos_por_incidencia={
            (_REPO, _NUMERO): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(autor_login="x", autor_asociacion="OWNER", texto=""),
            )
        },
        comentarios_por_incidencia={
            (_REPO, _NUMERO): LecturaComentarios(
                estado=LecturaEstado.OK,
                comentarios=(
                    Comentario(
                        autor_login="github-actions[bot]",
                        autor_asociacion="NONE",
                        cuerpo=(
                            "<!-- sirius-completed:deadbeef1234 -->\n\n- Merge SHA: `deadbeef1234`"
                        ),
                        creado_en=_AHORA,
                    ),
                ),
            )
        },
    )

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=mirror,
    )

    assert codigo == 0
    assert "work_item_delivered" in texto
    final = store.get_work_item(_WORK_ID)
    assert final is not None
    assert final.estado is WorkItemState.DELIVERED
    assert final.resultado == {"numero_incidencia": _NUMERO, "merge_sha": "deadbeef1234"}


# --- El caso vivo de la #537, de punta a punta (ADR-147, incidencia #545) ---

#: Los comentarios reales de la incidencia #537, recortados a sus marcadores y
#: al orden en que se publicaron (`gh api repos/.../issues/537/comments
#: --paginate`, 05-09-2026). Están TODOS los del ciclo, no solo los que el
#: recorrido usa: la prueba tiene que pasar por la misma proyección que la
#: pasada real, incluido el marcador de reanudación de las 04:46 que NO se
#: repitió tras la segunda orden `continua` -`sirius_comment_once` deduplica
#: por el texto del marcador y el head no había cambiado-, que es justo lo que
#: dejó `reanudacion_publicada` en False y lo que hizo falsa la premisa
#: original del encargo.
_COMENTARIOS_537: tuple[tuple[int, int, str, str], ...] = (
    (3, 49, "github-actions[bot]", "<!-- sirius-notification:sirius:implementing:no-head -->"),
    (4, 9, "canelamoraguezandyjesus-bot", "PR abierta: https://github.com/x/y/pull/538"),
    (
        4,
        10,
        "canelamoraguezandyjesus-bot",
        "<!-- sirius-verdict:implementer:READY_FOR_REVIEW:1c93 -->",
    ),
    (4, 17, "canelamoraguezandyjesus-bot", "<!-- sirius-quality:1c934781:success -->"),
    (4, 24, "canelamoraguezandyjesus-bot", "<!-- sirius-verdict:reviewer:changes:1c934781:339 -->"),
    (
        4,
        24,
        "github-actions[bot]",
        "<!-- sirius-notification:sirius:repair-requested:1c934781 -->",
    ),
    (
        4,
        36,
        "canelamoraguezandyjesus-bot",
        "<!-- sirius-verdict:corrector:blocked:33944464077-1 -->",
    ),
    (
        4,
        37,
        "github-actions[bot]",
        "<!-- sirius-notification:sirius:blocked-decision:1c934781 -->",
    ),
    (4, 45, "canelamoraguezandyjesus-bot", "## Decisión del propietario registrada\n\ntexto"),
    (
        4,
        45,
        "canelamoraguezandyjesus-bot",
        "continua\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_",
    ),
    (
        4,
        46,
        "github-actions[bot]",
        "<!-- sirius-resume-stop:1c934781 -->\n\n🟢 **Parada levantada**",
    ),
    (
        5,
        17,
        "canelamoraguezandyjesus-bot",
        "<!-- sirius-verdict:corrector:FAILED_SAFELY:33945456417-1 -->\n\n"
        "🔴 **Me he detenido de forma segura**\n\nsin tiempo para la ronda",
    ),
    (5, 17, "github-actions[bot]", "<!-- sirius-notification:sirius:failed-safely:1c934781 -->"),
    (
        5,
        29,
        "canelamoraguezandyjesus-bot",
        "continua\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_",
    ),
    (5, 52, "canelamoraguezandyjesus-bot", "<!-- sirius-verdict:corrector:FIXED:786c82dc:339 -->"),
    (6, 0, "canelamoraguezandyjesus-bot", "<!-- sirius-quality:786c82dc:success -->"),
    (6, 6, "canelamoraguezandyjesus-bot", "<!-- sirius-verdict:reviewer:changes:786c82dc:339 -->"),
    (6, 6, "github-actions[bot]", "<!-- sirius-notification:sirius:repair-requested:786c82dc -->"),
    (6, 34, "canelamoraguezandyjesus-bot", "<!-- sirius-verdict:corrector:FIXED:92e5b9f4:339 -->"),
    (6, 42, "canelamoraguezandyjesus-bot", "<!-- sirius-quality:92e5b9f4:success -->"),
    (6, 49, "canelamoraguezandyjesus-bot", "<!-- sirius-verdict:reviewer:approved:92e5b9f4 -->"),
    (6, 49, "github-actions[bot]", "<!-- sirius-notification:sirius:ready-for-merge:92e5b9f4 -->"),
    (7, 0, "canelamoraguezandyjesus-bot", "fusiona"),
    (7, 0, "github-actions[bot]", "<!-- sirius-notification:sirius:completed:92e5b9f4 -->"),
    (
        7,
        0,
        "canelamoraguezandyjesus-bot",
        "<!-- sirius-completed:78e81fc7 -->\n\n- Merge SHA: `78e81fc7`",
    ),
)


def _mirror_537(
    *,
    numero: int = _NUMERO,
    entradas: tuple[tuple[int, int, str, str], ...] = _COMENTARIOS_537,
) -> FixedGitHubMirrorReader:
    comentarios = tuple(
        Comentario(
            autor_login=autor,
            autor_asociacion="NONE" if autor == "github-actions[bot]" else "OWNER",
            cuerpo=cuerpo,
            creado_en=datetime(2026, 9, 5, hora, minuto, tzinfo=UTC),
        )
        for hora, minuto, autor, cuerpo in entradas
    )
    return FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, numero): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=numero,
                    titulo="t",
                    estado_gh="closed",
                    etiquetas=("sirius:completed",),
                ),
            )
        },
        cuerpos_por_incidencia={
            (_REPO, numero): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(
                    autor_login="canelamoraguezandyjesus-bot",
                    autor_asociacion="OWNER",
                    texto="cuerpo del encargo",
                ),
            )
        },
        comentarios_por_incidencia={
            (_REPO, numero): LecturaComentarios(estado=LecturaEstado.OK, comentarios=comentarios)
        },
    )


def _motor_parado_en_reparar(
    store: InMemoryWorkEngineStore, journal: InMemoryDispatchJournal
) -> None:
    """Donde se quedó WI-20260905-034826: failed_safely/reparar, parada de las 05:17."""
    _preparar(store, journal)
    store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    store.begin_work_item_check(_WORK_ID, now=_AHORA)
    store.begin_work_item_review(_WORK_ID, now=_AHORA)
    store.request_work_item_repair(_WORK_ID, now=_AHORA)
    store.fail_work_item_safely(_WORK_ID, diagnostico="sin tiempo para la ronda", now=_AHORA)


def test_una_pasada_real_recorre_la_recuperacion_de_la_537(tmp_path: Path) -> None:
    """La pasada entera, desde los comentarios crudos: proyección, plan y almacén.

    Antes de ADR-147 esta misma pasada imprimía «no hay camino hacia delante,
    no se toca nada» y «Pasos aplicados en total: 0» -es literalmente lo que
    hizo el run 33951766681 del 05-09-2026 a las 07:09-. Lo único que la
    cambia es la orden `continua` del propietario de las 05:29, leída del
    historial por la proyección real.
    """
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _motor_parado_en_reparar(store, journal)

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror_537(),
    )

    assert codigo == 0
    assert "aplicados 5 paso(s)" in texto
    assert "Pasos aplicados en total: 5." in texto
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.DELIVERED
    assert item.fase is WorkItemPhase.ENTREGAR
    assert tuple(evento.kind for evento in store.list_events() if evento.aggregate_id == _WORK_ID)[
        -5:
    ] == (
        "work_item_reactivated",
        "work_item_repair_resumed",
        "work_item_review_started",
        "work_item_review_approved",
        "work_item_delivered",
    )

    # C1, invariante 3: la pasada siguiente no añade nada. Aquí ni siquiera
    # entra al cálculo -DELIVERED es terminal y el bucle lo salta-, que es la
    # forma más fuerte de idempotencia que este comando puede dar.
    sucesos_antes = len(store.list_events())
    _, segundo_texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror_537(),
    )
    assert "Pasos aplicados en total: 0." in segundo_texto
    assert len(store.list_events()) == sucesos_antes


def test_sin_la_orden_del_propietario_la_misma_pasada_declara_y_no_toca_nada(
    tmp_path: Path,
) -> None:
    """Contraejemplo 1 de la incidencia #545, sobre la misma pasada real.

    Mismo motor, misma foto (`sirius:completed`) y EL MISMO historial de
    estados notificados: la recuperación ocurrió igual. Lo único que se quita
    es el `continua` de las 05:29. Sin esa palabra escrita no hay permiso, y
    el reflector conserva exactamente el comportamiento de hoy -declarar la
    divergencia, no tocar nada, exit 0-.
    """
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _motor_parado_en_reparar(store, journal)
    sin_orden = tuple(entrada for entrada in _COMENTARIOS_537 if entrada[:2] != (5, 29))
    assert len(sin_orden) == len(_COMENTARIOS_537) - 1

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror_537(entradas=sin_orden),
    )

    assert codigo == 0
    assert "no hay camino hacia delante, no se toca nada" in texto
    assert "Pasos aplicados en total: 0." in texto
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY
