"""``sirius-racha``: la costura entre el almacén, el diario del despachador y D1a (#268).

Estas pruebas fijan el CABLEADO -que la pasada lea el trabajo correcto, lo
compare, añada su línea al registro y evalúe la racha por clase- sin tocar
red ni el sistema de ficheros real; las propiedades del verificador y del
contador ya tienen sus propias pruebas.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

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
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
    formatear_linea,
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
    # LAS DOS MITADES DEL §11, y por eso ya no se busca la frase entera: desde
    # que la pasada cablea la reversion de emergencia (D1c), el texto dice DOS
    # cosas distintas y confundirlas seria grave.
    #
    #   §11.3 — hacia el motor NO conmuta: eso sigue siendo un acto del propietario.
    #   §11.4 — hacia GitHub SI revierte, y una sola divergencia real basta.
    #
    # Comprobar la frase literal ataba la prueba a la redaccion; comprobar las dos
    # propiedades la ata a lo que importa.
    assert "no conmuta" in texto.lower() and "hacia el motor" in texto.lower(), (
        "la pasada tiene que declarar que NO conmuta hacia el motor (§11.3)"
    )
    assert "11.4" in texto, (
        "la pasada tiene que dejar dicho qué hizo con la salida de emergencia del "
        "§11.4: callarlo sería tener una salvaguarda que nadie sabe si actuó"
    )
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


def test_lecturas_caidas_hoy_se_declaran_en_la_misma_linea_del_veredicto_cumple(
    tmp_path: Path,
) -> None:
    """Reproduce la incidencia #313: CUMPLE en la misma pasada que dice que no pudo leer.

    Dos ``WorkItem`` de clase ``programacion``: WI-A con siete días verdes ya
    registrados hasta hoy (sembrados directamente, como dejaría una racha
    real), WI-B sin ninguna línea nunca. La pasada corre con un mirror que
    falla para los dos -misma disciplina que
    ``test_una_lectura_caida_del_espejo_se_informa_y_se_salta_sin_inventar_linea``-,
    así que no añade ninguna línea nueva. El registro histórico ya sostiene
    el CUMPLE (ADR-084: una avería operativa no interrumpe el contador), pero
    la línea del veredicto tiene que decir que esta pasada tuvo lecturas
    caídas -no solo las tres líneas de arriba.
    """
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-A", clase=WorkItemClass.PROGRAMACION)
    _preparar_trabajo_activo(store, journal, work_id="WI-B", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / "registro.jsonl"
    dias = [_AHORA - timedelta(days=delta) for delta in range(6, -1, -1)]
    with registro.open("w", encoding="utf-8") as fichero:
        for instante in dias:
            linea = LineaRegistro(
                instante=instante,
                clase=WorkItemClass.PROGRAMACION,
                work_id="WI-A",
                veredictos=(
                    VeredictoEje(eje=EJE_FASE, resultado=ResultadoEje.COINCIDE),
                    VeredictoEje(eje=EJE_ESTADO, resultado=ResultadoEje.COINCIDE),
                ),
            )
            fichero.write(formatear_linea(linea))
            fichero.write("\n")
    mirror_caido = FixedGitHubMirrorReader()  # sin configurar: NO_DISPONIBLE en las tres lecturas

    codigo, texto = _correr(
        registro=registro,
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=mirror_caido,
    )

    assert codigo == 0
    assert "0 línea(s) nueva(s)" in texto
    lineas_de_veredicto = [
        linea_texto
        for linea_texto in texto.splitlines()
        if linea_texto.startswith(f"{WorkItemClass.PROGRAMACION.value} (")
    ]
    assert len(lineas_de_veredicto) == 1
    linea_veredicto = lineas_de_veredicto[0]
    assert "CUMPLE" in linea_veredicto, (
        "el contrato §11.2 no deja que una avería operativa rompa una racha ya registrada"
    )
    assert "WI-A" in linea_veredicto and "WI-B" in linea_veredicto, (
        "la MISMA línea del veredicto tiene que declarar las lecturas caídas de esta pasada, "
        "no solo las líneas de arriba"
    )


# --- CODEX-002: --raiz/SIRIUS_RACHA_RAIZ, no __file__, resuelven los recursos ---


def test_resolver_raiz_argumento_manda_sobre_entorno_y_defecto(tmp_path: Path) -> None:
    del_entorno = seven_day_streak_cli.resolver_raiz(
        argumento=None, entorno={seven_day_streak_cli.VARIABLE_RAIZ: str(tmp_path)}
    )
    manda_el_argumento = seven_day_streak_cli.resolver_raiz(
        argumento=str(tmp_path / "otra"),
        entorno={seven_day_streak_cli.VARIABLE_RAIZ: str(tmp_path)},
    )

    assert seven_day_streak_cli.resolver_raiz(argumento=None, entorno={}) == Path.cwd()
    assert del_entorno == tmp_path
    assert manda_el_argumento == tmp_path / "otra"


def test_el_registro_por_defecto_se_resuelve_bajo_la_raiz_no_bajo_file(tmp_path: Path) -> None:
    """Sin ``--registro``, la ruta por defecto debe venir de ``--raiz``, no de ``__file__``.

    En un wheel instalado ``__file__`` cae bajo ``site-packages`` -sin
    ``docs/operations``-, así que una pasada real necesita que el registro se
    resuelva desde una raíz que sí exista (CODEX-002).
    """
    raiz = tmp_path / "checkout"
    workflows = raiz / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        yaml.safe_dump({"on": {"push": None}, "jobs": {"j": {"timeout-minutes": 30}}}),
        encoding="utf-8",
    )
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    # Un trabajo real, para que la pasada escriba de verdad una línea: con el
    # almacén vacío, `anadir_lineas` no tiene nada que anexar y nunca llega a
    # crear el fichero, así que la ruta por defecto no quedaría fijada.
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)

    salida = io.StringIO()
    codigo = seven_day_streak_cli.main(
        ["--diario", str(tmp_path / "diario.jsonl"), "--raiz", str(raiz)],
        entorno={},
        salida=salida,
        ahora=_AHORA,
        store=store,
        dispatch_journal=journal,
        mirror=_mirror_verde(),
    )

    registro_esperado = raiz / "docs" / "operations" / "racha_siete_dias.jsonl"
    assert codigo == 0
    assert f"en {registro_esperado}" in salida.getvalue()
    assert registro_esperado.exists()


# --- CODEX-003: --hora-recomendada expone la hora derivada desde el comando ---


def test_hora_recomendada_se_expone_sin_ejecutar_la_pasada(tmp_path: Path) -> None:
    raiz = tmp_path / "checkout"
    workflows = raiz / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "reconciliar.yml").write_text(
        yaml.safe_dump(
            {
                "on": {"schedule": [{"cron": "17 */6 * * *"}]},
                "jobs": {"j": {"timeout-minutes": 30}},
            }
        ),
        encoding="utf-8",
    )

    salida = io.StringIO()
    codigo = seven_day_streak_cli.main(
        ["--raiz", str(raiz), "--hora-recomendada"], entorno={}, salida=salida
    )

    assert codigo == 0
    assert "03:17 UTC" in salida.getvalue()
    registro_por_defecto = raiz / "docs" / "operations" / "racha_siete_dias.jsonl"
    assert not registro_por_defecto.exists(), (
        "--hora-recomendada solo informa: no ejecuta la pasada ni escribe nada (CODEX-003)"
    )
