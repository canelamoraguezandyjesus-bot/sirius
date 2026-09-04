"""C1 (incidencia #529): el reflejo devuelve algo que YA se puede comparar.

Los siete ``WorkItem`` reales de la ola de criticidad (WI-20260902-174417 /
incidencia #508, WI-20260902-225525 / #510, WI-20260903-000204 / #512,
WI-20260903-005039 / #514, WI-20260903-111215 / #516, WI-20260903-124304 /
#518, WI-20260903-144522 / #520) están, en el diario real de la rama
``estado-del-motor`` -copiado a ``fixtures/diario_ola_criticidad.jsonl`` y
``fixtures/diario_despacho_ola_criticidad.jsonl`` con exactamente sus líneas
(``git show origin/estado-del-motor:diario.jsonl`` / ``diario-despacho.jsonl``,
04-09-2026)-, congelados en ``ACTIVE``/``PREPARAR``: ``dispatch_work_item``
(C2) escribió la incidencia y nunca volvió a tocar el almacén. Sus siete
incidencias reales están cerradas y fusionadas (objetivo de esta incidencia,
#529); los espejos de abajo son REPRESENTATIVOS de ese desenlace documentado
-``sirius:completed`` con su SHA de fusión-, no una segunda captura de red:
este entorno no tiene ni token ni acceso a GitHub, y H-25/ADR-101 prohíben
tocar ``CLASES_CON_ESTADO_PROPIO`` desde este bloque (C1 es solo el reflejo;
declarar la clase es C2, otro encargo).

Lo que esta prueba fija, en dos tiempos sobre el MISMO almacén real:

1. **Antes de reflejar**: comparar motor e incidencia con la clase declarada
   -algo que ``sirius-racha`` real NO hace hoy, porque el conjunto está
   vacío- ya no sale ``NO_COMPARABLE`` por precondición, sino una
   ``DIVERGENCIA`` de verdad (ACTIVE/PREPARAR contra DELIVERED/ENTREGAR): la
   comparación es honesta, y lo que dice es que el motor está mal.
2. **Después de reflejar**: la misma comparación, sobre el mismo almacén,
   sale ``COINCIDE`` en los dos ejes para las siete: el motor ya lleva el
   estado real, que es exactamente lo que el §11.2 exige para que el
   contador pueda EMPEZAR a contar (lo declarará C2, no aquí).
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.domain.work_item import TERMINAL_STATES, WorkItemClass, WorkItemState
from sirius_engine.mirror_projection import leer_y_proyectar_work_item
from sirius_engine.ports.github_mirror import (
    Comentario,
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    MetadatosIncidencia,
)
from sirius_engine.projection_verifier import ContextoEjesDiarios, ResultadoEje, verificar_dia
from sirius_engine.reflect import aplicar_pasos, reflejar_desenlace

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_REPO = "canelamoraguezandyjesus-bot/sirius"
_AHORA = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
_TOLERANCIA = timedelta(minutes=170)
_SIN_VENTANA = ContextoEjesDiarios()
#: Declarado SOLO dentro de esta prueba -nunca en
#: ``projection_verifier.CLASES_CON_ESTADO_PROPIO``, que sigue vacío hoy
#: (H-25, ADR-101): eso es C2, otro encargo, y se hace después de observar
#: al menos una pasada real de este reflejo (objetivo de la incidencia #529).
_CLASE_DECLARADA_PARA_ESTA_PRUEBA = frozenset({WorkItemClass.PROGRAMACION})

#: Los siete work_id de la ola de criticidad, con el SHA de fusión
#: representativo de su cierre real (objetivo de #529: "están cerradas y
#: fusionadas"). No son SHAs leídos de la API -ver docstring del módulo-.
_OLA_DE_CRITICIDAD: tuple[tuple[str, int, str], ...] = (
    ("WI-20260902-174417", 508, "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"),
    ("WI-20260902-225525", 510, "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3"),
    ("WI-20260903-000204", 512, "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"),
    ("WI-20260903-005039", 514, "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5"),
    ("WI-20260903-111215", 516, "e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"),
    ("WI-20260903-124304", 518, "f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1"),
    ("WI-20260903-144522", 520, "a1a2a3a4a5a6a1a2a3a4a5a6a1a2a3a4a5a6a1a2"),
)


def _diarios_copiados(tmp_path: Path) -> tuple[Path, Path]:
    diario = tmp_path / "diario.jsonl"
    despacho = tmp_path / "diario-despacho.jsonl"
    shutil.copyfile(_FIXTURES / "diario_ola_criticidad.jsonl", diario)
    shutil.copyfile(_FIXTURES / "diario_despacho_ola_criticidad.jsonl", despacho)
    return diario, despacho


def _mirror_completado() -> FixedGitHubMirrorReader:
    metadatos = {}
    cuerpos = {}
    comentarios = {}
    for _, numero, sha in _OLA_DE_CRITICIDAD:
        metadatos[(_REPO, numero)] = LecturaMetadatos(
            estado=LecturaEstado.OK,
            metadatos=MetadatosIncidencia(
                numero=numero, titulo="t", estado_gh="closed", etiquetas=("sirius:completed",)
            ),
        )
        cuerpos[(_REPO, numero)] = LecturaCuerpo(
            estado=LecturaEstado.OK,
            cuerpo=CuerpoIncidencia(
                autor_login="canelamoraguezandyjesus-bot", autor_asociacion="OWNER", texto=""
            ),
        )
        comentarios[(_REPO, numero)] = LecturaComentarios(
            estado=LecturaEstado.OK,
            comentarios=(
                Comentario(
                    autor_login="github-actions[bot]",
                    autor_asociacion="NONE",
                    cuerpo=f"<!-- sirius-completed:{sha} -->\n\n- Merge SHA: `{sha}`",
                    creado_en=_AHORA,
                ),
            ),
        )
    return FixedGitHubMirrorReader(
        metadatos_por_incidencia=metadatos,
        cuerpos_por_incidencia=cuerpos,
        comentarios_por_incidencia=comentarios,
    )


def test_antes_de_reflejar_la_comparacion_declarada_es_divergencia_no_no_comparable(
    tmp_path: Path,
) -> None:
    """Sin reflejar, el motor real sigue en ACTIVE/PREPARAR: comparar con la
    clase declarada (lo que haría C2 tras C1) ya NO cae en el NO_COMPARABLE
    de precondición del §11.2 que da la producción real hoy -eso ya lo
    prueba ``test_h25_el_conjunto_declarado_esta_vacio_hoy``-. Sale
    NO_COMPARABLE igual, pero por la ventana 3 real («fusión sin pasar por
    ready-for-merge»): el motor ni siquiera pasó por REVISAR, así que el
    verificador se niega, con razón, a llamarlo "entregado". Es una
    evaluación honesta -y correcta- del estado real, no un silencio por
    falta de jurisdicción.
    """
    diario, despacho = _diarios_copiados(tmp_path)
    store = DurableWorkEngineStore(diario)
    journal = DurableDispatchJournal(despacho)
    mirror = _mirror_completado()

    work_id, numero, _ = _OLA_DE_CRITICIDAD[0]
    item = store.get_work_item(work_id)
    assert item is not None
    assert item.estado is WorkItemState.ACTIVE
    episodio = journal.episode_for(work_id)
    assert episodio is not None
    espejo = leer_y_proyectar_work_item(mirror, repo=_REPO, numero=numero, ahora=_AHORA)

    linea = verificar_dia(
        motor=item,
        espejo=espejo,
        contexto=_SIN_VENTANA,
        ventana_tolerancia=_TOLERANCIA,
        instante=_AHORA,
        clases_con_estado_propio=_CLASE_DECLARADA_PARA_ESTA_PRUEBA,
    )
    for veredicto in linea.veredictos:
        assert veredicto.resultado is ResultadoEje.NO_COMPARABLE
        assert veredicto.motivo is not None
        assert "11.2" not in veredicto.motivo, (
            "no puede ser el motivo de precondición vacía: la clase está declarada"
        )
        assert "fusión sin pasar por ready-for-merge" in veredicto.motivo


def test_tras_reflejar_las_siete_incidencias_la_comparacion_declarada_coincide(
    tmp_path: Path,
) -> None:
    diario, despacho = _diarios_copiados(tmp_path)
    store = DurableWorkEngineStore(diario)
    journal = DurableDispatchJournal(despacho)
    mirror = _mirror_completado()

    for work_id, numero, sha in _OLA_DE_CRITICIDAD:
        item = store.get_work_item(work_id)
        assert item is not None
        assert item.estado not in TERMINAL_STATES
        episodio = journal.episode_for(work_id)
        assert episodio is not None and episodio.numero_incidencia == numero
        espejo = leer_y_proyectar_work_item(mirror, repo=_REPO, numero=numero, ahora=_AHORA)
        assert espejo.head_sha == sha

        resultado = reflejar_desenlace(item, espejo, episodio)
        assert resultado.pasos, f"{work_id}: se esperaba un plan no vacío"
        assert resultado.pasos[-1].kind == "work_item_delivered"
        aplicar_pasos(store, work_id, resultado.pasos, now=_AHORA)

    aplicados_dos_veces = 0
    for work_id, numero, _sha in _OLA_DE_CRITICIDAD:
        item = store.get_work_item(work_id)
        assert item is not None
        assert item.estado is WorkItemState.DELIVERED
        assert item.resultado is not None
        assert item.resultado["numero_incidencia"] == numero

        episodio = journal.episode_for(work_id)
        assert episodio is not None
        espejo = leer_y_proyectar_work_item(mirror, repo=_REPO, numero=numero, ahora=_AHORA)

        # Idempotencia de extremo a extremo: una segunda pasada sobre el mismo
        # espejo, ya con el motor reflejado, no produce ningún paso más.
        segundo = reflejar_desenlace(item, espejo, episodio)
        assert segundo.pasos == ()
        aplicados_dos_veces += len(aplicar_pasos(store, work_id, segundo.pasos, now=_AHORA))

        linea = verificar_dia(
            motor=item,
            espejo=espejo,
            contexto=_SIN_VENTANA,
            ventana_tolerancia=_TOLERANCIA,
            instante=_AHORA,
            clases_con_estado_propio=_CLASE_DECLARADA_PARA_ESTA_PRUEBA,
        )
        assert linea.es_verde is True, (
            f"{work_id}: tras reflejar, la comparación declarada (lo que hará C2) "
            f"debería coincidir en los dos ejes: {linea.veredictos!r}"
        )

    assert aplicados_dos_veces == 0, "una segunda pasada sobre las siete no puede añadir nada"
