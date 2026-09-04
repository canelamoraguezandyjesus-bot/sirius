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
