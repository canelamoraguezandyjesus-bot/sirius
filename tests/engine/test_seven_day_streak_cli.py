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

import pytest
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
    LecturaRunsEnVentana,
    MetadatosIncidencia,
    RunEnVentana,
)
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
    formatear_linea,
)
from sirius_engine.seven_day_streak import (
    NOMBRE_DEL_WORKFLOW_DEL_CONTADOR,
    hora_recomendada_pasada,
    leer_registro,
)

_AHORA = datetime(2026, 8, 22, 3, 17, tzinfo=UTC)
_REPO = "canelamoraguezandyjesus-bot/sirius"
_NUMERO = 268
_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]


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
    # H-25 (#376): mientras ninguna clase tenga estado propio declarado
    # (`CLASES_CON_ESTADO_PROPIO` vacío, que hoy es la verdad), la línea sale
    # NO_COMPARABLE citando el §11.2 y el día NO es verde: la etapa que el
    # contador mide no ha empezado, y un verde aquí sería el falso verde que
    # D1a existe para impedir. Antes esta prueba afirmaba `es_verde is True`
    # con un espejo idéntico al motor; esa verdad era del instrumento sin
    # precondición.
    assert lineas[0].es_verde is False
    for veredicto in lineas[0].veredictos:
        assert veredicto.resultado is ResultadoEje.NO_COMPARABLE
        assert veredicto.motivo is not None and "11.2" in veredicto.motivo


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


def test_h25_declarar_una_clase_devuelve_la_comparacion_real_por_el_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simula EXACTAMENTE lo que hará el bloque (C) de #376: declarar la clase.

    Con la clase en `CLASES_CON_ESTADO_PROPIO`, la misma pasada que hoy sale
    NO_COMPARABLE (§11.2) vuelve a comparar de verdad — espejo idéntico al
    motor → día verde. Prueba dos cosas a la vez: que el CLI lee la constante
    real (cableado por comportamiento, no por grep) y que la corrección de
    H-25 no capa el instrumento, solo lo hace honesto sobre su precondición.
    """
    monkeypatch.setattr(
        seven_day_streak_cli,
        "CLASES_CON_ESTADO_PROPIO",
        frozenset({WorkItemClass.PROGRAMACION}),
    )
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / "registro.jsonl"

    codigo, _texto = _correr(
        registro=registro,
        diario=tmp_path / "diario.jsonl",
        store=store,
        journal=journal,
        mirror=_mirror_verde(),
    )

    assert codigo == 0
    lineas = leer_registro(registro)
    assert len(lineas) == 1
    assert lineas[0].es_verde is True


# --- #416: el docstring de este módulo cita la cadencia real de motor-sirius.yml ---


def test_docstring_no_afirma_que_el_motor_arranca_solo_a_mano() -> None:
    """El docstring dijo, hasta el #416, que ``motor-sirius.yml`` «arranca solo a
    mano, sin horario» -falso desde #343 (25-08-2026): el motor tiene cadencia
    real (D2, ADR-090). Esa frase obsoleta llegó a generar un parte erróneo al
    propietario el 28-08 (ver docs/audits/evidencia-el-motor-esta-preparado.md).

    Esta prueba no fija un texto suelto: lee el cron REAL de
    ``motor-sirius.yml`` y comprueba que el docstring lo cita. Si alguien
    cambia el minuto del motor sin tocar este docstring -o revierte la
    afirmación a «solo a mano» mientras el workflow sigue con horario-, esto
    rompe en vez de quedarse obsoleto en silencio.
    """
    workflow = dict(
        yaml.safe_load(
            (_RAIZ_REPOSITORIO / ".github" / "workflows" / "motor-sirius.yml").read_text(
                encoding="utf-8"
            )
        )
    )
    disparadores = workflow.get("on") or workflow.get(True)
    assert isinstance(disparadores, dict), f"motor-sirius.yml no declara disparadores: {workflow}"
    crones = [str(entrada["cron"]) for entrada in disparadores.get("schedule") or []]
    assert crones, (
        "motor-sirius.yml ya no tiene cadencia programada: el docstring de "
        "seven_day_streak_cli tendría que volver a decir que arranca solo a mano"
    )

    docstring = seven_day_streak_cli.__doc__ or ""
    cron_real = crones[0]
    assert cron_real in docstring, (
        f"el docstring no cita el cron real de motor-sirius.yml ({cron_real!r}); "
        "si el horario cambió sin actualizar el docstring, vuelve a quedar obsoleto"
    )
    assert "workflow_dispatch" in disparadores, (
        "motor-sirius.yml perdió el arranque manual: el docstring afirma que la "
        "cadencia programada convive con él"
    )
    assert "ya no arranca solo a mano" in docstring, (
        "el docstring dejó de afirmar la cadencia real: no cita la frase que "
        "corrige la afirmación falsa (#416)"
    )
    # CODEX-001 (ronda 2, #416): la cadencia (D2, ADR-090) y el contador (D1,
    # ADR-101) son dos precondiciones distintas. Cerrar la primera no cierra
    # la segunda, y el docstring tiene que decir las dos cosas por separado en
    # vez de dejar que «lo que faltaba está cerrado» se lea como las dos.
    assert "CLASES_CON_ESTADO_PROPIO" in docstring, (
        "el docstring tiene que nombrar la precondición que sigue bloqueando "
        "el contador (H-25, ADR-101, #376), no solo la cadencia ya cerrada"
    )
    assert "NO_COMPARABLE" in docstring, (
        "el docstring tiene que decir con qué resultado sigue midiendo la "
        "pasada mientras el contador siga bloqueado, no dejarlo implícito"
    )


# --- ADR-151: la pasada mide y declara CÓMO llegó, sin cambiar ningún veredicto ---


#: La hora programada NO se copia a mano: se deriva del mismo sitio que la
#: deriva el comando (y que el guardián de ADR-144 mantiene igual al `cron`
#: cableado). Copiarla aquí ataría la prueba a un número que ya se sabe
#: derivar, que es justo lo que ADR-144 existe para no hacer.
_HORA_PROGRAMADA, _ = hora_recomendada_pasada(_RAIZ_REPOSITORIO / ".github" / "workflows")
_A_SU_HORA = datetime.combine(_AHORA.date(), _HORA_PROGRAMADA, tzinfo=UTC)
_TARDE = _A_SU_HORA + timedelta(minutes=280)


def _con_runs(mirror: FixedGitHubMirrorReader, *runs: RunEnVentana) -> FixedGitHubMirrorReader:
    mirror.runs_en_ventana_por_repo[_REPO] = LecturaRunsEnVentana(
        estado=LecturaEstado.OK, runs=runs
    )
    return mirror


def _run(workflow: str, run_id: str) -> RunEnVentana:
    return RunEnVentana(run_id=run_id, workflow=workflow, inicio=_A_SU_HORA, fin=_A_SU_HORA)


def _pasada(
    tmp_path: Path,
    *,
    mirror: FixedGitHubMirrorReader,
    ahora: datetime,
    sufijo: str,
) -> tuple[str, tuple[LineaRegistro, ...]]:
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / f"registro-{sufijo}.jsonl"
    _codigo, texto = _correr(
        registro=registro,
        diario=tmp_path / f"diario-{sufijo}.jsonl",
        store=store,
        journal=journal,
        mirror=mirror,
        ahora=ahora,
    )
    return texto, leer_registro(registro)


def test_una_pasada_puntual_con_ventana_tranquila_lo_declara_y_lo_registra(
    tmp_path: Path,
) -> None:
    texto, lineas = _pasada(
        tmp_path,
        mirror=_con_runs(_mirror_verde()),
        ahora=_A_SU_HORA,
        sufijo="puntual",
    )

    assert "ventana previa tranquila: 0 runs" in texto
    assert "retraso" not in texto
    assert lineas[0].entrega is not None
    assert lineas[0].entrega.retraso_min == 0
    assert lineas[0].entrega.lectura_de_runs is LecturaEstado.OK


def test_una_pasada_tardia_con_ventana_sucia_lo_declara_sin_cambiar_ningun_eje(
    tmp_path: Path,
) -> None:
    """El caso que motivó ADR-151, y su límite: se declara, y NADA MÁS cambia.

    Las dos pasadas son idénticas salvo en cómo llegaron -una a su hora con la
    ventana vacía, otra 280 min tarde y con dos runs dentro-. Si medir la
    entrega tocara algún eje, los veredictos de las dos no coincidirían.
    """
    texto_tarde, lineas_tarde = _pasada(
        tmp_path,
        mirror=_con_runs(
            _mirror_verde(),
            _run("implement-sirius-work.yml", "11"),
            _run("implement-sirius-work.yml", "12"),
        ),
        ahora=_TARDE,
        sufijo="tarde",
    )
    _texto_puntual, lineas_puntual = _pasada(
        tmp_path,
        mirror=_con_runs(_mirror_verde()),
        ahora=_A_SU_HORA,
        sufijo="control",
    )

    assert "280 min de retraso" in texto_tarde
    assert _HORA_PROGRAMADA.isoformat(timespec="minutes") in texto_tarde
    assert "NO tranquila: 2 runs" in texto_tarde
    assert "implement-sirius-work.yml#11" in texto_tarde
    assert "implement-sirius-work.yml#12" in texto_tarde

    assert lineas_tarde[0].entrega is not None
    assert lineas_tarde[0].entrega.retraso_min == 280
    assert lineas_tarde[0].veredictos == lineas_puntual[0].veredictos, (
        "medir la entrega no puede cambiar ningún veredicto de ningún eje (ADR-151)"
    )
    assert lineas_tarde[0].es_verde == lineas_puntual[0].es_verde


def test_una_lectura_de_runs_caida_no_rompe_la_pasada_ni_se_llama_tranquila(
    tmp_path: Path,
) -> None:
    """El doble sin configurar devuelve NO_DISPONIBLE: la pasada sigue y lo dice."""
    texto, lineas = _pasada(
        tmp_path,
        mirror=_mirror_verde(),  # sin `runs_en_ventana_por_repo`: lectura caída
        ahora=_A_SU_HORA,
        sufijo="caida",
    )

    assert "no se pudieron leer los runs de la ventana previa" in texto
    assert "tranquila" not in texto
    assert len(lineas) == 1, "la pasada siguió y registró su línea"
    assert lineas[0].entrega is not None
    assert lineas[0].entrega.lectura_de_runs is LecturaEstado.NO_DISPONIBLE


def test_los_runs_del_propio_contador_no_ensucian_la_ventana_de_su_pasada(
    tmp_path: Path,
) -> None:
    texto, lineas = _pasada(
        tmp_path,
        mirror=_con_runs(_mirror_verde(), _run(NOMBRE_DEL_WORKFLOW_DEL_CONTADOR, "9")),
        ahora=_A_SU_HORA,
        sufijo="propio",
    )

    assert "ventana previa tranquila: 0 runs" in texto, (
        "una pasada no se estorba a sí misma: mismo criterio nombrado que ADR-144"
    )
    assert lineas[0].entrega is not None
    assert lineas[0].entrega.runs_en_ventana == ()


def test_si_la_hora_programada_no_se_puede_derivar_la_pasada_sigue_y_lo_declara(
    tmp_path: Path,
) -> None:
    """El escenario del margen de dos minutos: sale en ROJO en su guardián, no aquí.

    ``hora_recomendada_pasada`` lanza a propósito cuando ninguna hora del día
    dejaría tranquila la ventana de tolerancia. Perder la medición del día
    entero por no poder medir el retraso sería cambiar un aviso por una avería,
    así que la pasada sigue, lo declara y escribe la línea sin ``entrega``.
    """
    raiz = tmp_path / "raiz"
    workflows = raiz / ".github" / "workflows"
    workflows.mkdir(parents=True)
    # Un único workflow con `cron`, y un tope tan alto que la tolerancia
    # (el doble) no cabe en ningún hueco del día.
    (workflows / "solo-uno.yml").write_text(
        "on:\n  schedule:\n    - cron: '0 1 * * *'\njobs:\n"
        "  uno:\n    timeout-minutes: 900\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    store = InMemoryWorkEngineStore()
    journal = InMemoryDispatchJournal()
    _preparar_trabajo_activo(store, journal, work_id="WI-1", clase=WorkItemClass.PROGRAMACION)
    registro = tmp_path / "registro-sin-hora.jsonl"
    salida = io.StringIO()

    codigo = seven_day_streak_cli.main(
        [
            "--diario",
            str(tmp_path / "diario-sin-hora.jsonl"),
            "--registro",
            str(registro),
            "--raiz",
            str(raiz),
        ],
        entorno={},
        salida=salida,
        ahora=_A_SU_HORA,
        store=store,
        dispatch_journal=journal,
        mirror=_con_runs(_mirror_verde()),
    )

    assert codigo == 0
    assert "no se pudo derivar la hora programada" in salida.getvalue()
    lineas = leer_registro(registro)
    assert len(lineas) == 1
    assert lineas[0].entrega is None, "sin medida no se inventa una: ausente = no medido"
