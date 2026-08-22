"""``sirius-racha``: la costura entre el almacén, el diario del despachador y D1a (#268).

Estas pruebas fijan el CABLEADO -que la pasada lea el trabajo correcto, lo
compare, añada su línea al registro y evalúe la racha por clase- sin tocar
red ni el sistema de ficheros real; las propiedades del verificador y del
contador ya tienen sus propias pruebas.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine import seven_day_streak_cli
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.authority import Autoridad, autoridad_de_clase
from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.ports.github_mirror import (
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    MetadatosIncidencia,
)
from sirius_engine.seven_day_streak import leer_registro

_AHORA = datetime(2026, 8, 22, 3, 17, tzinfo=UTC)
_REPO = "canelamoraguezandyjesus-bot/sirius"
_NUMERO = 268


def _correr(
    *,
    registro: Path,
    diario: Path,
    store: InMemoryWorkEngineStore,
    journal: InMemoryDispatchJournal,
    mirror: FixedGitHubMirrorReader,
    ahora: datetime = _AHORA,
) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = seven_day_streak_cli.main(
        ["--diario", str(diario), "--registro", str(registro)],
        entorno={},
        salida=salida,
        ahora=ahora,
        store=store,
        dispatch_journal=journal,
        mirror=mirror,
    )
    return codigo, salida.getvalue()


def _mirror_verde(*, numero: int = _NUMERO) -> FixedGitHubMirrorReader:
    """Un espejo que refleja lo que ``begin_work_item_execution`` deja: ACTIVE/EJECUTAR."""
    return FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, numero): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=numero,
                    titulo="D1b",
                    estado_gh="open",
                    etiquetas=("sirius:implementing",),
                ),
            )
        },
        cuerpos_por_incidencia={
            (_REPO, numero): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(
                    autor_login="github-actions[bot]", autor_asociacion="NONE", texto=""
                ),
            )
        },
        comentarios_por_incidencia={
            (_REPO, numero): LecturaComentarios(estado=LecturaEstado.OK, comentarios=())
        },
    )


def _preparar_trabajo_activo(
    store: InMemoryWorkEngineStore,
    journal: InMemoryDispatchJournal,
    *,
    work_id: str,
    clase: WorkItemClass,
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
        clase=clase,
        now=_AHORA,
    )
    store.activate_work_item(work_id, now=_AHORA)
    store.begin_work_item_execution(work_id, now=_AHORA)
    journal.record(
        DispatchEpisode(
            work_id=work_id,
            orden_enlazada="orden-propietario:issue#1",
            repo=_REPO,
            numero_incidencia=_NUMERO,
            etiqueta="sirius:implementing",
            recorded_at=_AHORA,
        )
    )


def test_una_pasada_anade_una_linea_y_evalua_las_dos_clases_con_autoridad(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / "registro.jsonl"

    codigo, texto = _correr(
        registro=registro,
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=_mirror_verde(),
    )

    assert codigo == 0
    assert "1 línea(s) nueva(s)" in texto
    assert WorkItemClass.PROGRAMACION.value in texto
    assert WorkItemClass.AUDITORIA.value in texto
    assert "no conmuta nada" in texto
    lineas = leer_registro(registro)
    assert len(lineas) == 1
    assert lineas[0].work_id == "WI-1"
    assert lineas[0].es_verde is True


def test_dos_pasadas_con_el_mismo_instante_no_duplican_la_linea(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / "registro.jsonl"
    diario = tmp_path / "diario.jsonl"
    mirror = _mirror_verde()

    _correr(registro=registro, diario=diario, store=store, journal=journal, mirror=mirror)
    _codigo, texto_segunda = _correr(
        registro=registro, diario=diario, store=store, journal=journal, mirror=mirror
    )

    assert "0 línea(s) nueva(s)" in texto_segunda
    assert len(leer_registro(registro)) == 1


def test_un_trabajo_sin_despachar_todavia_no_produce_linea_ni_falla(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()  # sin episodio: nunca se despachó
    store.create_work_item(
        work_id="WI-SIN-DESPACHAR",
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
    store.activate_work_item("WI-SIN-DESPACHAR", now=_AHORA)
    registro = tmp_path / "registro.jsonl"

    codigo, texto = _correr(
        registro=registro,
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=FixedGitHubMirrorReader(),
    )

    assert codigo == 0
    assert "aún sin despachar" in texto
    assert leer_registro(registro) == ()


def test_una_clase_sin_autoridad_de_incidencia_se_ignora(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-DOC", clase=WorkItemClass.DOCUMENTACION)
    registro = tmp_path / "registro.jsonl"

    _correr(
        registro=registro,
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=_mirror_verde(),
    )

    assert leer_registro(registro) == (), (
        "documentación tiene autoridad MOTOR (ADR-041): nada que comparar contra una "
        "incidencia que no gobierna su estado"
    )


def test_la_pasada_no_cambia_la_autoridad_de_ninguna_clase(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    autoridad_antes = {clase: autoridad_de_clase(clase) for clase in WorkItemClass}

    _correr(
        registro=tmp_path / "registro.jsonl",
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=_mirror_verde(),
    )

    autoridad_despues = {clase: autoridad_de_clase(clase) for clase in WorkItemClass}
    assert autoridad_antes == autoridad_despues
    assert autoridad_de_clase(WorkItemClass.PROGRAMACION) is Autoridad.INCIDENCIA


def test_una_lectura_caida_del_espejo_se_informa_y_se_salta_sin_inventar_linea(
    tmp_path: Path,
) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / "registro.jsonl"
    # FixedGitHubMirrorReader sin configurar para (repo, numero) devuelve
    # NO_DISPONIBLE en las tres lecturas: exactamente una caída del espejo.
    mirror_caido = FixedGitHubMirrorReader()

    codigo, texto = _correr(
        registro=registro,
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=mirror_caido,
    )

    assert codigo == 0
    assert "no pude leer la incidencia" in texto
    assert "no es que no hubiera nada" in texto
    assert leer_registro(registro) == ()
