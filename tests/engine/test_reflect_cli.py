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
from typing import Any

import pytest

from sirius_engine import reflect_cli
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.divergencias import (
    DivergenciaApartada,
    Instantanea,
    escribir_instantanea,
    leer_instantanea,
)
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


def _completa(*divergencias: DivergenciaApartada) -> Instantanea:
    return Instantanea(
        tuple(divergencias), interrumpida=False, sin_evaluar=(), perdida_posible=False
    )


def _apartadas(ruta: Path) -> tuple[DivergenciaApartada, ...]:
    instantanea = leer_instantanea(ruta)
    return () if instantanea is None else instantanea.divergencias


def _instantanea(ruta: Path) -> Instantanea:
    instantanea = leer_instantanea(ruta)
    assert instantanea is not None, f"{ruta.name} no existe"
    return instantanea


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
    clase: WorkItemClass = WorkItemClass.PROGRAMACION,
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


def test_espejo_sin_etiqueta_de_estado_no_mueve_nada_pero_lo_cuenta(tmp_path: Path) -> None:
    """Contar no es mover: no se aplica ningún paso, pero la pasada dice dónde está.

    Esta prueba fijaba lo contrario -que la pasada no dijera NADA- y ADR-173
    revierte esa decisión a propósito, con lo medido: ese silencio dejó 21
    encargos varados durante hasta doce días sin que ninguna pasada los
    nombrara. La propiedad que importa sigue intacta -el almacén no se toca-,
    y la que cambia es la que escondía el fallo.
    """
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
    assert f"{_WORK_ID}: sin cambios" in texto
    assert "ninguna etiqueta de estado reconocida" in texto
    assert f"#{_NUMERO} (abierta)" in texto
    assert "Pasos aplicados en total: 0." in texto
    sin_tocar = store.get_work_item(_WORK_ID)
    assert sin_tocar is not None
    assert sin_tocar.estado is WorkItemState.ACTIVE
    assert sin_tocar.fase is WorkItemPhase.PREPARAR


def _datos_contradictorios(numero: int = _NUMERO) -> dict[str, Any]:
    """La incidencia #392 de H-216: cerrada con dos etiquetas de estado que se contradicen."""
    return dict(
        metadatos_por_incidencia={
            (_REPO, numero): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=numero,
                    titulo="t",
                    estado_gh="closed",
                    etiquetas=("sirius:failed-safely", "sirius:completed"),
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


def _mirror_contradictorio(numero: int = _NUMERO) -> FixedGitHubMirrorReader:
    return FixedGitHubMirrorReader(**_datos_contradictorios(numero))


def _mirror_completado(numero: int = _NUMERO) -> FixedGitHubMirrorReader:
    """Una incidencia cerrada como completada con su sha de fusión: el reflector la entrega."""
    return FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, numero): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=numero, titulo="t", estado_gh="closed", etiquetas=("sirius:completed",)
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
            (_REPO, numero): LecturaComentarios(
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


class _EspejoQueSeCae(FixedGitHubMirrorReader):
    """Un espejo que REVIENTA al leer una incidencia concreta: la API que se cae
    a mitad de la pasada, no una lectura que el reflector sabe tratar como
    ilegible (`EspejoIlegibleError`)."""

    def __init__(self, *, numero_que_se_cae: int, **datos: Any) -> None:
        super().__init__(**datos)
        self._numero_que_se_cae = numero_que_se_cae

    def leer_metadatos(self, *, repo: str, numero: int) -> LecturaMetadatos:
        if numero == self._numero_que_se_cae:
            raise RuntimeError("la API se cayó a mitad de la pasada")
        return super().leer_metadatos(repo=repo, numero=numero)


_ENTRADA_VIEJA = DivergenciaApartada(
    work_id=_WORK_ID,
    incidencia=_NUMERO,
    motivo="motivo de una pasada anterior",
    primera_vez="2026-09-01T03:24:00+00:00",
    ultima_vez="2026-09-03T03:24:00+00:00",
    pasadas=3,
)


def test_una_pasada_que_muere_a_medias_conserva_lo_observado_y_lo_no_alcanzado(
    tmp_path: Path,
) -> None:
    """Ronda 1 de Codex en la PR #674: si la pasada revienta tras ver una
    divergencia, el workflow confirma igual el diario (`if: always()`) y la
    vista se regeneraría de un fichero viejo. Lo observado se escribe y lo que
    la pasada no llegó a mirar se conserva tal cual."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal, work_id="WI-1", numero=_NUMERO)
    _preparar(store, journal, work_id="WI-2", numero=999)
    _preparar(store, journal, work_id="WI-3", numero=1000)
    ruta = tmp_path / "divergencias.json"
    vieja = DivergenciaApartada(
        "WI-2", 999, "motivo viejo", "2026-09-01T03:24:00+00:00", "2026-09-03T03:24:00+00:00", 3
    )
    escribir_instantanea(ruta, _completa(vieja))
    espejo = _EspejoQueSeCae(numero_que_se_cae=999, **_datos_contradictorios(_NUMERO))

    with pytest.raises(RuntimeError, match="se cayó"):
        _correr(
            ["--diario", str(tmp_path / "diario.jsonl")],
            store=store,
            journal=journal,
            mirror=espejo,
        )

    instantanea = _instantanea(ruta)
    por_encargo = {d.work_id: d for d in instantanea.divergencias}
    assert set(por_encargo) == {"WI-1", "WI-2"}
    assert "se contradicen" in por_encargo["WI-1"].motivo and por_encargo["WI-1"].pasadas == 1
    assert por_encargo["WI-2"] == vieja, "lo que la pasada no llegó a mirar se conserva tal cual"
    assert instantanea.interrumpida and not instantanea.completa, (
        "ronda 2 de Codex: el fichero dice que la pasada no fue entera"
    )
    assert "WI-2" in instantanea.sin_evaluar and not instantanea.perdida_posible
    assert "WI-3" in instantanea.sin_evaluar, (
        "ronda 3 de Codex: lo no alcanzado se deriva de todos los encargos conocidos, no solo "
        "de los que ya tenían entrada; sin esto la vista no podía decir qué no se miró"
    )
    assert "WI-1" not in instantanea.sin_evaluar


def test_un_fichero_de_divergencias_roto_no_para_el_reflejo_y_se_reescribe(tmp_path: Path) -> None:
    """Revisión independiente de la PR #674: un `divergencias.json` corrupto
    mataba la pasada DESPUÉS de aplicar los pasos, y en cada pasada siguiente,
    hasta que alguien lo arreglara a mano. El reflejo es lo primero: el fichero
    se lee antes de tocar el almacén, se avisa nombrándolo y se reescribe."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    ruta = tmp_path / "divergencias.json"
    ruta.write_text('{"divergencias": [', encoding="utf-8")

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
    )

    assert codigo == 0
    assert "AVISO: " in texto and "divergencias.json: no es JSON" in texto
    assert f"{_WORK_ID}: aplicados 1 paso(s)" in texto
    instantanea = _instantanea(ruta)
    assert instantanea == _completa(), "reescrito, legible y entero: la pasada evaluó todo"


def test_en_ensayo_el_aviso_del_fichero_roto_no_promete_reescribirlo(tmp_path: Path) -> None:
    """Ronda 5 de Codex en la PR #674: con `--ensayo` el aviso decía que esta pasada
    reescribiría el fichero, pero el ensayo no escribe nada. Dice lo que haría una
    pasada real, y el fichero roto queda tal cual."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    ruta = tmp_path / "divergencias.json"
    ruta.write_text('{"divergencias": [', encoding="utf-8")

    codigo, texto = _correr(
        ["--ensayo", "--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
    )

    assert codigo == 0
    assert "divergencias.json: no es JSON" in texto
    assert "en --ensayo no se toca" in texto and "Una pasada real lo volvería a escribir" in texto
    assert "esta pasada lo vuelve a escribir" not in texto
    assert ruta.read_text(encoding="utf-8") == '{"divergencias": [', "el ensayo no toca el fichero"
    assert not (tmp_path / "divergencias.json.tmp").exists()


def test_fichero_roto_mas_pasada_incompleta_deja_dicho_que_lo_anterior_pudo_perderse(
    tmp_path: Path,
) -> None:
    """Ronda 2 de Codex en la PR #674: con el fichero roto, el conjunto anterior
    ya era `()`, y una pasada que no podía leer una incidencia (o moría a
    medias) lo sustituía por un fichero válido y vacío que la vista leía como
    «ninguna». El fichero lleva ahora la duda escrita hasta que una pasada
    completa rehaga el conjunto."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    diario = tmp_path / "diario.jsonl"
    ruta = tmp_path / "divergencias.json"
    ruta.write_text('{"divergencias": [', encoding="utf-8")

    codigo, texto = _correr(
        ["--diario", str(diario)], store=store, journal=journal, mirror=FixedGitHubMirrorReader()
    )
    assert codigo == 0
    assert "Pasada incompleta: 1 encargo(s) sin evaluar; lo anterior pudo perderse." in texto
    incompleta = _instantanea(ruta)
    assert not incompleta.completa and incompleta.perdida_posible
    assert incompleta.sin_evaluar == (_WORK_ID,) and incompleta.divergencias == ()

    codigo, texto = _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
        ahora=_AHORA.replace(day=5),
    )
    assert codigo == 0 and "Pasada incompleta" not in texto
    assert _instantanea(ruta) == _completa(), "una pasada completa apaga la duda"


def test_la_primera_pasada_completa_sin_divergencias_deja_el_fichero_escrito(
    tmp_path: Path,
) -> None:
    """Ronda 2 de Codex en la PR #674: un fichero ausente no es «ninguna», es
    «nadie ha escrito todavía», y la vista lo dice así. Para que «ninguna» se
    pueda afirmar, la primera pasada completa escribe el conjunto vacío; una
    pasada igual después no reescribe nada."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    diario = tmp_path / "diario.jsonl"
    ruta = tmp_path / "divergencias.json"

    codigo, texto = _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
    )
    assert codigo == 0
    assert "Divergencias apartadas para una persona: 0, escritas en divergencias.json." in texto
    assert _instantanea(ruta) == _completa()
    escrito = ruta.read_text(encoding="utf-8")

    codigo, texto = _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
        ahora=_AHORA.replace(day=5),
    )
    assert codigo == 0
    assert "Divergencias apartadas para una persona: 0 (sin cambios en divergencias.json)." in texto
    assert ruta.read_text(encoding="utf-8") == escrito


def test_una_entrada_de_un_encargo_resuelto_o_terminal_se_retira(tmp_path: Path) -> None:
    """Las dos mutaciones que sobrevivían (revisión independiente de la PR #674):
    conservar la entrada de un encargo que la pasada resolvió con pasos, y la
    de uno ya terminal. Es el camino real de #392 el 01-10: la etiqueta falsa
    se retiró, el reflector entregó el encargo, y su entrada tiene que irse."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    diario = tmp_path / "diario.jsonl"
    ruta = tmp_path / "divergencias.json"

    escribir_instantanea(ruta, _completa(_ENTRADA_VIEJA))
    codigo, _ = _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=_mirror(etiqueta="sirius:implementing"),
    )
    assert codigo == 0
    assert _apartadas(ruta) == (), "resuelta con pasos: la entrada se retira"

    codigo, texto = _correr(
        ["--diario", str(diario)], store=store, journal=journal, mirror=_mirror_completado()
    )
    assert codigo == 0 and "work_item_delivered" in texto
    escribir_instantanea(ruta, _completa(_ENTRADA_VIEJA))
    codigo, _ = _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=_mirror_completado(),
        ahora=_AHORA.replace(day=5),
    )
    assert codigo == 0
    assert _apartadas(ruta) == (), "terminal: la entrada se retira"


def test_una_divergencia_apartada_queda_escrita_junto_al_diario(tmp_path: Path) -> None:
    """ADR-227 (H-216): la divergencia que el reflector aparta para una persona
    no se queda en el log del run. `WI-20260828-122242` estuvo 27 días así sin
    que nadie la viera. Vista fallar contra el comando anterior: ningún fichero."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    diario = tmp_path / "diario.jsonl"

    codigo, texto = _correr(
        ["--diario", str(diario)], store=store, journal=journal, mirror=_mirror_contradictorio()
    )

    assert codigo == 0
    assert "etiquetas de estado que se contradicen" in texto
    assert "Divergencias apartadas para una persona: 1, escritas en divergencias.json." in texto
    apartadas = _apartadas(tmp_path / "divergencias.json")
    assert len(apartadas) == 1
    (apartada,) = apartadas
    assert apartada.work_id == _WORK_ID and apartada.incidencia == _NUMERO
    assert "se contradicen" in apartada.motivo
    assert apartada.primera_vez == apartada.ultima_vez == _AHORA.isoformat()
    assert apartada.pasadas == 1
    sin_tocar = store.get_work_item(_WORK_ID)
    assert sin_tocar is not None and sin_tocar.estado is WorkItemState.ACTIVE

    despues = _AHORA.replace(day=5)
    _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=_mirror_contradictorio(),
        ahora=despues,
    )
    (otra_vez,) = _apartadas(tmp_path / "divergencias.json")
    assert otra_vez.primera_vez == _AHORA.isoformat(), "la primera vez no se mueve"
    assert otra_vez.ultima_vez == despues.isoformat() and otra_vez.pasadas == 2


def test_el_ensayo_no_escribe_las_divergencias(tmp_path: Path) -> None:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)

    codigo, texto = _correr(
        ["--ensayo", "--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror_contradictorio(),
    )

    assert codigo == 0
    assert (
        "Divergencias apartadas para una persona: 1 (en ensayo no se escribe divergencias.json)."
        in texto
    )
    assert not (tmp_path / "divergencias.json").exists()


def test_una_divergencia_ilegible_se_conserva_y_una_resuelta_se_retira(tmp_path: Path) -> None:
    """Tres pasadas: se aparta; la incidencia no se puede leer (se conserva con
    su fecha); la incidencia deja de contradecirse (se retira)."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal)
    diario = tmp_path / "diario.jsonl"
    _correr(
        ["--diario", str(diario)], store=store, journal=journal, mirror=_mirror_contradictorio()
    )

    ilegible = FixedGitHubMirrorReader()  # nada configurado: LecturaEstado.NO_DISPONIBLE
    codigo, texto = _correr(
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=ilegible,
        ahora=_AHORA.replace(day=5),
    )
    assert codigo == 0
    assert f"{_WORK_ID}: no pude leer la incidencia" in texto
    (conservada,) = _apartadas(tmp_path / "divergencias.json")
    assert conservada.ultima_vez == _AHORA.isoformat() and conservada.pasadas == 1

    # La incidencia deja de contradecirse: sin etiqueta de estado, el reflector
    # no tiene nada que decir (idempotencia) y la pasada la evalúa sin divergencia.
    sin_etiquetas = FixedGitHubMirrorReader(
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
        ["--diario", str(diario)],
        store=store,
        journal=journal,
        mirror=sin_etiquetas,
        ahora=_AHORA.replace(day=6),
    )
    assert codigo == 0
    assert f"{_WORK_ID}: sin cambios" in texto
    assert "Divergencias apartadas para una persona: 0, escritas en divergencias.json." in texto
    assert _apartadas(tmp_path / "divergencias.json") == ()


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
    cerrada: bool = True,
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
                    estado_gh="closed" if cerrada else "open",
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


def test_sin_la_orden_del_propietario_con_la_incidencia_abierta_no_se_toca_nada(
    tmp_path: Path,
) -> None:
    """Contraejemplo 1 de la incidencia #545, sobre la misma pasada real.

    Mismo motor, mismo historial de estados notificados: la recuperación
    ocurrió igual. Lo único que se quita es el `continua` de las 05:29. Sin esa
    palabra escrita no hay permiso, y el reflector declara la divergencia y no
    toca nada.

    La incidencia va **abierta** aquí, y eso no es un detalle: mientras lo
    esté, la parada se puede reanudar de verdad -basta con que el propietario
    escriba la orden-, así que conservarla es lo correcto. El caso de la
    incidencia CERRADA es el de abajo, y ADR-176 lo separa a propósito.
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
        mirror=_mirror_537(entradas=sin_orden, cerrada=False),
    )

    assert codigo == 0
    assert "no hay camino hacia delante, no se toca nada" in texto
    assert "Pasos aplicados en total: 0." in texto
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_sin_la_orden_y_con_la_incidencia_cerrada_la_parada_se_termina(
    tmp_path: Path,
) -> None:
    """Lo que ADR-176 cambia, dicho entero: la parada se TERMINA, no se reanuda.

    Misma pasada que la de arriba y sin el `continua`, pero con la incidencia
    cerrada. Una parada cuya incidencia está cerrada no se puede reanudar
    -reanudar se hace sobre la incidencia-, así que dejarla declarando
    divergencia en cada pasada no la protege: la deja muerta y ruidosa.

    Y la mitad que SÍ protegía se comprueba aquí explícitamente: el encargo no
    pasa por `ACTIVE` en ningún momento. Sin permiso escrito no se reanuda
    nada, que es lo que costó cuatro rondas en la PR #530; cancelar no es
    reanudar.
    """
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _motor_parado_en_reparar(store, journal)
    sin_orden = tuple(entrada for entrada in _COMENTARIOS_537 if entrada[:2] != (5, 29))

    codigo, _ = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=_mirror_537(entradas=sin_orden),
    )

    assert codigo == 0
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.CANCELLED
    kinds = tuple(evento.kind for evento in store.list_events() if evento.aggregate_id == _WORK_ID)
    assert "work_item_reactivated" not in kinds, (
        "el encargo se reactivó sin permiso escrito del propietario"
    )
    # Desde FAILED_SAFELY el dominio admite `cancel` directo: un solo paso.
    assert kinds[-1] == "work_item_cancelled"


# --- La puerta de clase se deriva de lo que el despachador despacha (ADR-173) ---


@pytest.mark.parametrize(
    "clase",
    [
        WorkItemClass.DOCUMENTACION,
        WorkItemClass.INVESTIGACION,
        WorkItemClass.AUDITORIA,
        WorkItemClass.PROGRAMACION,
    ],
)
def test_el_reflector_mira_toda_clase_que_el_despachador_despacha(
    tmp_path: Path, clase: WorkItemClass
) -> None:
    """Las cuatro filas de `TABLA_ACTIVACION`, no las dos de la tabla de autoridad.

    Medido el 12-09-2026 sobre el diario real: de los 74 encargos despachados
    a GitHub, 15 eran de `documentacion` (10) o `investigacion` (5) —clases
    que ADR-088 y ADR-099 metieron en el ciclo con las mismas etiquetas que
    `programacion`— y los 15 seguían en `active`, ninguno había alcanzado
    jamás un estado terminal, porque la puerta leía la tabla de autoridad de
    ADR-041, que es anterior a esas dos decisiones.
    """
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal, clase=clase)
    mirror = FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, _NUMERO): LecturaMetadatos(
                estado=LecturaEstado.OK,
                metadatos=MetadatosIncidencia(
                    numero=_NUMERO,
                    titulo="t",
                    estado_gh="closed",
                    etiquetas=("sirius:completed",),
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
    assert f"{_WORK_ID}: aplicados" in texto
    final = store.get_work_item(_WORK_ID)
    assert final is not None
    assert final.estado is WorkItemState.DELIVERED


def test_una_clase_que_el_despachador_no_despacha_se_salta_diciendolo(tmp_path: Path) -> None:
    """`mixta` no está en `TABLA_ACTIVACION`: no se refleja, y se dice por qué."""
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar(store, journal, clase=WorkItemClass.MIXTA)
    mirror = FixedGitHubMirrorReader(
        metadatos_por_incidencia={}, cuerpos_por_incidencia={}, comentarios_por_incidencia={}
    )

    codigo, texto = _correr(
        ["--diario", str(tmp_path / "diario.jsonl")],
        store=store,
        journal=journal,
        mirror=mirror,
    )

    assert codigo == 0
    assert f"{_WORK_ID}: la clase mixta no se despacha a GitHub" in texto
    final = store.get_work_item(_WORK_ID)
    assert final is not None
    assert final.estado is WorkItemState.ACTIVE
