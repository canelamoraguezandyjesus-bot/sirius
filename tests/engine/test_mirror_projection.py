"""Espejo de solo lectura de la vía GitHub (A3, incidencia #193).

Requisitos ejercitados aquí:

1. Reconstrucción fiel del ciclo completo de una incidencia histórica desde
   fixtures capturadas del repositorio (``fixtures/github_issue_186.json``).
2. Una lectura caída NUNCA es una ausencia: se comprueba simulando el fallo
   de cada proveedor por separado.
3. Instante de lectura y origen presentes en toda proyección.
5. Idempotencia y determinismo: proyectar dos veces produce el mismo espejo.
6. Prueba por mutación: ver :mod:`tests.engine.test_mirror_projection`
   docstrings de cada caso para qué mutación demuestra cada uno.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine import mirror_projection
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.domain.mirror import EspejoIlegibleError, MirroredWorkItem
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.mirror_projection import (
    leer_y_proyectar_run,
    leer_y_proyectar_work_item,
    proyectar_run,
    proyectar_work_item,
)
from sirius_engine.ports.github_mirror import (
    Comentario,
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    LecturaRunActions,
    MetadatosIncidencia,
    RunActions,
)

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_REPO = "canelamoraguezandyjesus-bot/sirius"
_AHORA = datetime(2026, 8, 18, 15, 0, tzinfo=UTC)
_OWNER_LOGIN = "canelamoraguezandyjesus-bot"


def _cuerpo_de_confianza(texto: str) -> LecturaCuerpo:
    """Cuerpo escrito por el propietario: el caso normal de una incidencia de Sirius.

    Desde ADR-051 el cuerpo viaja con su autor, así que una lectura de cuerpo
    ya no se puede construir sin decir quién lo escribió. Este ayudante fija
    el caso de confianza para las pruebas que no van sobre el filtro.
    """
    return LecturaCuerpo(
        estado=LecturaEstado.OK,
        cuerpo=CuerpoIncidencia(autor_login=_OWNER_LOGIN, autor_asociacion="OWNER", texto=texto),
    )


def _cargar_fixture(nombre: str) -> dict[str, Any]:
    with open(_FIXTURES_DIR / nombre, encoding="utf-8") as handle:
        contenido: dict[str, Any] = json.load(handle)
    return contenido


def _lecturas_desde_fixture(
    fixture: dict[str, Any],
) -> tuple[LecturaMetadatos, LecturaCuerpo, LecturaComentarios]:
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(
            numero=fixture["numero"],
            titulo=fixture["titulo"],
            estado_gh=fixture["estado_gh"],
            etiquetas=tuple(fixture["etiquetas"]),
        ),
    )
    cuerpo = LecturaCuerpo(
        estado=LecturaEstado.OK,
        cuerpo=CuerpoIncidencia(
            autor_login=fixture["cuerpo_autor_login"],
            autor_asociacion=fixture["cuerpo_autor_asociacion"],
            texto=fixture["cuerpo"],
        ),
    )
    comentarios = LecturaComentarios(
        estado=LecturaEstado.OK,
        comentarios=tuple(
            Comentario(
                autor_login=c["autor_login"],
                autor_asociacion=c["autor_asociacion"],
                cuerpo=c["cuerpo"],
                creado_en=datetime.fromisoformat(c["creado_en"].replace("Z", "+00:00")),
            )
            for c in fixture["comentarios"]
        ),
    )
    return metadatos, cuerpo, comentarios


# --- Requisito 1: reconstrucción fiel del ciclo completo (incidencia #186) -


def test_reconstruye_ciclo_completo_de_incidencia_186_desde_fixture() -> None:
    """El espejo reconstruye el ciclo COMPLETO de la #186 desde su fixture real.

    #186 (A2, elegida por esta incidencia como candidata a #148: 7 rondas de
    revisión, 7 de corrección, dos paradas y una reanudación manual) pasó de
    verdad por: implementación (3 precheck + IMPLEMENTACION_LISTA) -> Quality
    en verde -> revisión dual (CHANGES_REQUESTED x7) -> 7 rondas de
    corrección (FIXED x7) -> un fallo de Quality intermedio seguido de un
    verde -> bloqueo por convergencia-sin-progreso -> completado. Los valores
    esperados aquí están verificados contra la API real de GitHub (ver
    ADR-034), no inventados.
    """
    fixture = _cargar_fixture("github_issue_186.json")
    metadatos, cuerpo, comentarios = _lecturas_desde_fixture(fixture)

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=186,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )

    assert mirrored.work_id == f"{_REPO}#186"
    assert mirrored.estado is WorkItemState.DELIVERED
    assert mirrored.fase is WorkItemPhase.ENTREGAR
    assert mirrored.cerrada is True
    assert mirrored.pr_url == "https://github.com/canelamoraguezandyjesus-bot/sirius/pull/189"
    assert mirrored.head_sha == "88cd7cfdf561c534f736718f5212057584a45c5c"

    # Siete rondas de revisión-corrección, numeradas 1..7, con avance
    # estrictamente decreciente de pendientes -exactamente lo que exige la
    # política de convergencia para dejar CONTINUE en todas ellas.
    assert [r.numero for r in mirrored.rondas] == list(range(1, 8))
    assert mirrored.rondas[0].pendientes == 3
    assert mirrored.rondas[-1].pendientes == 1
    assert mirrored.rondas[0].head == "297fac15228f2dac62c69b245ca1405dba46f7ff"

    # La racha de fallos de Quality se reinicia: hubo un `failure`
    # (a2959b57c) pero un `success` posterior sobre el MISMO head lo cierra.
    assert mirrored.fallos_quality_consecutivos == 0

    # Pero la secuencia COMPLETA de eventos no se pierde: el `failure` sigue
    # siendo un hecho ocurrido en el ciclo, aunque ya no cuente para la racha.
    assert len(mirrored.eventos_quality) == 8
    assert [e.conclusion for e in mirrored.eventos_quality] == [
        "success",
        "success",
        "success",
        "success",
        "success",
        "failure",
        "success",
        "success",
    ]
    assert mirrored.eventos_quality[5].head.startswith("a2959b57")
    assert mirrored.eventos_quality[6].head == mirrored.eventos_quality[5].head

    veredictos_por_rol = [v.rol for v in mirrored.veredictos]
    assert veredictos_por_rol.count("corrector") == 7
    assert veredictos_por_rol.count("reviewer") == 7
    assert mirrored.veredictos[0].rol == "implementer"
    assert mirrored.veredictos[0].veredicto == "precheck"

    # Requisito 3: instante de lectura y origen, siempre.
    assert mirrored.origen.leido_en == _AHORA
    assert mirrored.origen.fuente == f"github:{_REPO}#186"

    # Nota de arranque, pregunta 4: estructuralmente imposible marcarlo
    # autoritativo.
    assert mirrored.autoritativo is False


def test_reconstruccion_es_determinista_e_idempotente() -> None:
    """Requisito 5: proyectar dos veces el mismo hilo produce el mismo espejo."""
    fixture = _cargar_fixture("github_issue_186.json")
    metadatos, cuerpo, comentarios = _lecturas_desde_fixture(fixture)

    primero = proyectar_work_item(
        repo=_REPO,
        numero=186,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    segundo = proyectar_work_item(
        repo=_REPO,
        numero=186,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert primero == segundo


# --- Requisito 2: una lectura caída no es una ausencia ---------------------


def test_fallo_de_metadatos_lanza_espejo_ilegible_no_ausencia() -> None:
    """Mutación (b): si esto devolviera un WorkItem vacío en vez de lanzar,
    esta prueba fallaría -confirma que la ausencia y el fallo no se
    confunden para el proveedor de metadatos.
    """
    metadatos = LecturaMetadatos(estado=LecturaEstado.NO_DISPONIBLE, error="503")
    cuerpo = _cuerpo_de_confianza("")
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=())

    with pytest.raises(EspejoIlegibleError) as excinfo:
        proyectar_work_item(
            repo=_REPO,
            numero=1,
            metadatos=metadatos,
            cuerpo=cuerpo,
            comentarios=comentarios,
            ahora=_AHORA,
        )
    assert excinfo.value.proveedor == "metadatos"


def test_fallo_de_cuerpo_lanza_espejo_ilegible_no_ausencia() -> None:
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(numero=1, titulo="t", estado_gh="open", etiquetas=()),
    )
    cuerpo = LecturaCuerpo(estado=LecturaEstado.NO_DISPONIBLE, error="cuerpo truncado")
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=())

    with pytest.raises(EspejoIlegibleError) as excinfo:
        proyectar_work_item(
            repo=_REPO,
            numero=1,
            metadatos=metadatos,
            cuerpo=cuerpo,
            comentarios=comentarios,
            ahora=_AHORA,
        )
    assert excinfo.value.proveedor == "cuerpo"


def test_fallo_de_comentarios_lanza_espejo_ilegible_no_ausencia() -> None:
    """Este es el caso real de `sirius_reconcile.sh`: un 503 en comentarios
    NO puede leerse como "sin observaciones"/"sin PR" (requisito 2, los
    cinco hallazgos citados en la incidencia #193).
    """
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(numero=1, titulo="t", estado_gh="open", etiquetas=()),
    )
    cuerpo = _cuerpo_de_confianza("")
    comentarios = LecturaComentarios(estado=LecturaEstado.NO_DISPONIBLE, error="503")

    with pytest.raises(EspejoIlegibleError) as excinfo:
        proyectar_work_item(
            repo=_REPO,
            numero=1,
            metadatos=metadatos,
            cuerpo=cuerpo,
            comentarios=comentarios,
            ahora=_AHORA,
        )
    assert excinfo.value.proveedor == "comentarios"


def test_leer_y_proyectar_orquesta_las_tres_lecturas_del_puerto() -> None:
    fixture = _cargar_fixture("github_issue_186.json")
    metadatos, cuerpo, comentarios = _lecturas_desde_fixture(fixture)
    puerto = FixedGitHubMirrorReader(
        metadatos_por_incidencia={(_REPO, 186): metadatos},
        cuerpos_por_incidencia={(_REPO, 186): cuerpo},
        comentarios_por_incidencia={(_REPO, 186): comentarios},
    )
    mirrored = leer_y_proyectar_work_item(puerto, repo=_REPO, numero=186, ahora=_AHORA)
    assert mirrored.estado is WorkItemState.DELIVERED


def test_leer_y_proyectar_sobre_puerto_sin_configurar_lanza_espejo_ilegible() -> None:
    """El doble de fixtures devuelve NO_DISPONIBLE por defecto, no un valor vacío."""
    puerto = FixedGitHubMirrorReader()
    with pytest.raises(EspejoIlegibleError):
        leer_y_proyectar_work_item(puerto, repo=_REPO, numero=999, ahora=_AHORA)


# --- Etiquetas y filtro de confianza ----------------------------------------


def test_etiqueta_sirius_desconocida_produce_estado_none_no_un_valor_por_defecto() -> None:
    """Ninguna etiqueta reconocible es un hecho observado, no una ausencia de
    lectura: se representa como ``None`` explícito, nunca como PLANNED por
    defecto (que sería fingir que sabemos algo que no sabemos).
    """
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(
            numero=1, titulo="t", estado_gh="open", etiquetas=("etiqueta-no-reconocida",)
        ),
    )
    cuerpo = _cuerpo_de_confianza("")
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=())

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.estado is None
    assert mirrored.fase is None


def test_etiquetas_de_estado_contradictorias_no_eligen_una_ganadora() -> None:
    """`sirius:repairing` + `sirius:completed` a la vez no es un estado real:
    es una contradicción que el espejo debe exponer, no resolver en silencio
    quedándose con la de mayor prioridad.
    """
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(
            numero=1,
            titulo="t",
            estado_gh="open",
            etiquetas=("sirius:repairing", "sirius:completed"),
        ),
    )
    cuerpo = _cuerpo_de_confianza("")
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=())

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.estado is None
    assert mirrored.fase is None
    assert mirrored.etiquetas_contradictorias is True


def test_par_de_activacion_planned_e_implement_requested_no_es_contradiccion() -> None:
    """La única excepción real: `sirius_validate_activation.sh` exige
    `sirius:planned` y `implement-sirius-work.yml` retira las dos juntas al
    consumir el evento, así que esta combinación es una activación normal.
    """
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(
            numero=1,
            titulo="t",
            estado_gh="open",
            etiquetas=("sirius:planned", "sirius:implement-requested"),
        ),
    )
    cuerpo = _cuerpo_de_confianza("")
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=())

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.etiquetas_contradictorias is False
    assert mirrored.estado is WorkItemState.PLANNED
    assert mirrored.fase is WorkItemPhase.PREPARAR


def test_comentario_no_confiable_no_se_interpreta_como_marcador() -> None:
    """Mutación (c): si el filtro de confianza se rompiera (p. ej. aceptando
    cualquier autor), esta prueba fallaría -un tercero sin autoridad NO
    puede fabricar una ronda, un veredicto ni una PR en el espejo.
    """
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(numero=1, titulo="t", estado_gh="open", etiquetas=()),
    )
    cuerpo = _cuerpo_de_confianza("")
    comentario_falso = Comentario(
        autor_login="un-tercero-cualquiera",
        autor_asociacion="NONE",
        cuerpo=(
            "<!-- sirius-round:99 -->\n\n## RONDA_HALLAZGOS\n```json\n"
            '{"round": 99, "head": "deadbeef", "findings": [], "pending": 0, '
            '"severity_total": 0}\n```\n'
            "<!-- sirius-verdict:reviewer:approved:deadbeef -->\n"
            "PR abierta: https://github.com/example/otro/pull/1\n"
        ),
        creado_en=_AHORA,
    )
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=(comentario_falso,))

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.rondas == ()
    assert mirrored.veredictos == ()
    assert mirrored.pr_url is None


def test_marcador_pr_abierta_citado_en_texto_no_se_confunde_con_uno_real() -> None:
    """Contraejemplo real de la #186 (comentario de precheck): citar el
    marcador como texto («Comentario 'PR abierta: <URL>' publicado…») no
    debe interpretarse como una PR real -solo cuenta un esquema http(s)
    real tras "PR abierta:".
    """
    metadatos = LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(numero=1, titulo="t", estado_gh="open", etiquetas=()),
    )
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo="Comentario 'PR abierta: <URL>' publicado en la incidencia #186.",
        creado_en=_AHORA,
    )
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=(comentario,))

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.pr_url is None


# --- El cuerpo pasa por el MISMO filtro que los comentarios (H-1, #215) ----
#
# El defecto: `_texto_cronologico_de_confianza` filtraba los comentarios por
# autor y concatenaba el cuerpo sin filtrar, porque `LecturaCuerpo` no
# transportaba autor y la función no tenía con qué filtrarlo. Ese texto
# alimenta `parse_round_records` y `ci_failure_streak`: gobierna la
# numeración de rondas y el corte por CI. Ver ADR-051.

_REGISTRO_DE_RONDA_99 = (
    "<!-- sirius-round:99 -->\n\n## RONDA_HALLAZGOS\n```json\n"
    '{"round": 99, "head": "deadbeef", "findings": [], "pending": 0, '
    '"severity_total": 0}\n```\n'
)


def _metadatos_minimos() -> LecturaMetadatos:
    return LecturaMetadatos(
        estado=LecturaEstado.OK,
        metadatos=MetadatosIncidencia(numero=1, titulo="t", estado_gh="open", etiquetas=()),
    )


def test_el_mismo_texto_de_ronda_se_filtra_igual_venga_del_cuerpo_o_de_un_comentario() -> None:
    """La prueba A/B del defecto H-1: MISMO texto, MISMO autor, distinto sitio.

    Un tercero sin autoridad publica el registro de la ronda 99. Puesto en un
    comentario, el filtro lo descarta -eso ya funcionaba-. Puesto en el
    cuerpo de la incidencia, escapaba del filtro y fabricaba una ronda 99 en
    el espejo.

    Que las dos mitades vivan en la MISMA prueba es deliberado: lo que se fija
    aquí no es «el cuerpo se filtra», sino que **el sitio del texto no cambia
    la respuesta**. Una prueba que solo mirase el cuerpo pasaría también si
    alguien rompiera el filtro de los comentarios.

    Mutación que la tumba: volver a
    ``"\\n".join((*de_confianza, cuerpo))`` en
    ``_texto_cronologico_de_confianza``.
    """
    tercero = "un-tercero-cualquiera"

    desde_comentario = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=_metadatos_minimos(),
        cuerpo=_cuerpo_de_confianza(""),
        comentarios=LecturaComentarios(
            estado=LecturaEstado.OK,
            comentarios=(
                Comentario(
                    autor_login=tercero,
                    autor_asociacion="NONE",
                    cuerpo=_REGISTRO_DE_RONDA_99,
                    creado_en=_AHORA,
                ),
            ),
        ),
        ahora=_AHORA,
    )

    desde_cuerpo = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=_metadatos_minimos(),
        cuerpo=LecturaCuerpo(
            estado=LecturaEstado.OK,
            cuerpo=CuerpoIncidencia(
                autor_login=tercero,
                autor_asociacion="NONE",
                texto=_REGISTRO_DE_RONDA_99,
            ),
        ),
        comentarios=LecturaComentarios(estado=LecturaEstado.OK, comentarios=()),
        ahora=_AHORA,
    )

    assert desde_comentario.rondas == ()
    assert desde_cuerpo.rondas == (), "el cuerpo de un tercero fabricó una ronda en el espejo"
    assert desde_cuerpo.rondas == desde_comentario.rondas


def test_el_cuerpo_de_un_tercero_tampoco_gobierna_la_racha_de_fallos_de_quality() -> None:
    """El otro motor del ciclo que ese texto alimenta: ``ci_failure_streak``.

    Dos marcadores de fallo sobre heads distintos en el cuerpo sumaban una
    racha de 2 de las 3 que agotan el margen y mandan la incidencia a
    decisión humana (``MAX_CI_FAILURE_STREAK``). Se comprueba aparte de las
    rondas porque son dos consumidores distintos del mismo texto: arreglar
    uno sin el otro dejaría la mitad del defecto en pie.

    Mutación que la tumba: la misma que la prueba anterior.
    """
    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=_metadatos_minimos(),
        cuerpo=LecturaCuerpo(
            estado=LecturaEstado.OK,
            cuerpo=CuerpoIncidencia(
                autor_login="un-tercero-cualquiera",
                autor_asociacion="NONE",
                texto=(
                    "<!-- sirius-quality:cafecafe:failure -->\n"
                    "<!-- sirius-quality:beefbeef:failure -->\n"
                ),
            ),
        ),
        comentarios=LecturaComentarios(estado=LecturaEstado.OK, comentarios=()),
        ahora=_AHORA,
    )

    assert mirrored.fallos_quality_consecutivos == 0
    assert mirrored.eventos_quality == ()


def test_el_cuerpo_del_propietario_si_cuenta_como_de_confianza() -> None:
    """El complemento imprescindible: el arreglo no puede ser «tirar el cuerpo».

    Sin esta prueba, la anterior pasaría igual con una implementación que
    ignorase el cuerpo siempre -y el espejo perdería en silencio las rondas
    que el propietario o el bot publiquen ahí-. Cubre las dos identidades de
    confianza, que son las dos que ``es_autor_de_confianza`` reconoce.

    Mutación que la tumba: hacer que ``_texto_cronologico_de_confianza``
    descarte el cuerpo incondicionalmente.
    """
    for login, asociacion in (
        ("canelamoraguezandyjesus-bot", "OWNER"),
        ("github-actions[bot]", "NONE"),
    ):
        mirrored = proyectar_work_item(
            repo=_REPO,
            numero=1,
            metadatos=_metadatos_minimos(),
            cuerpo=LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(
                    autor_login=login,
                    autor_asociacion=asociacion,
                    texto=_REGISTRO_DE_RONDA_99,
                ),
            ),
            comentarios=LecturaComentarios(estado=LecturaEstado.OK, comentarios=()),
            ahora=_AHORA,
        )
        assert [r.numero for r in mirrored.rondas] == [99], f"{login}/{asociacion}"


def test_el_cuerpo_se_concatena_primero_por_ser_lo_mas_antiguo() -> None:
    """Segundo hallazgo de la misma función: el orden contradecía su docstring.

    ``_texto_cronologico_de_confianza`` promete «del más antiguo al más
    reciente» y ponía el cuerpo -lo primero que existe en una incidencia- al
    FINAL. No se notaba en la numeración de rondas porque
    ``parse_round_records`` ordena internamente por número de marcador; sí se
    nota en ``history_after_last_resume``, que **corta** el texto por la
    última orden de continuar: con el cuerpo al final, un
    ``sirius-convergence-reset`` en el cuerpo se leía como posterior a todos
    los comentarios y los borraba a todos.

    Mutación que la tumba: volver a poner ``cuerpo`` al final de la
    concatenación.
    """
    comentario = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=_REGISTRO_DE_RONDA_99,
        creado_en=_AHORA,
    )

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=_metadatos_minimos(),
        cuerpo=_cuerpo_de_confianza("<!-- sirius-convergence-reset:deadbee -->"),
        comentarios=LecturaComentarios(estado=LecturaEstado.OK, comentarios=(comentario,)),
        ahora=_AHORA,
    )

    assert [r.numero for r in mirrored.rondas] == [99], (
        "una reanudación escrita en el cuerpo borró rondas publicadas DESPUÉS"
    )


# --- Estructura de las proyecciones (nota de arranque, pregunta 4) ---------


def test_mirrored_work_item_no_admite_autoritativo_por_constructor() -> None:
    """Mutación (a) del lado del campo: si ``autoritativo`` tuviera ``init=True``
    con un valor por defecto ``False``, esta prueba seguiría en verde pero
    ya no demostraría nada -por eso se comprueba que el propio constructor
    RECHAZA el argumento, no solo que el valor por defecto sea correcto.
    """
    with pytest.raises(TypeError):
        MirroredWorkItem(  # type: ignore[call-arg]
            work_id="x#1",
            estado=None,
            fase=None,
            etiquetas=(),
            etiquetas_contradictorias=False,
            cerrada=False,
            pr_url=None,
            head_sha=None,
            rondas=(),
            veredictos=(),
            eventos_quality=(),
            fallos_quality_consecutivos=0,
            origen=None,  # type: ignore[arg-type]
            autoritativo=True,
        )


# --- Run de Actions ----------------------------------------------------------


def test_proyectar_run_ok_lleva_origen_y_no_es_autoritativo() -> None:
    lectura = LecturaRunActions(
        estado=LecturaEstado.OK,
        run=RunActions(
            run_id="123",
            estado_run="completed",
            conclusion="success",
            head_sha="deadbeef",
            url="https://github.com/x/y/actions/runs/123",
        ),
    )
    mirrored = proyectar_run(run_id="123", lectura=lectura, ahora=_AHORA)
    assert mirrored is not None
    assert mirrored.origen.leido_en == _AHORA
    assert mirrored.autoritativo is False


def test_proyectar_run_leido_pero_inexistente_es_ausencia_real() -> None:
    lectura = LecturaRunActions(estado=LecturaEstado.OK, run=None)
    assert proyectar_run(run_id="123", lectura=lectura, ahora=_AHORA) is None


def test_proyectar_run_no_disponible_lanza_espejo_ilegible() -> None:
    lectura = LecturaRunActions(estado=LecturaEstado.NO_DISPONIBLE, error="timeout")
    with pytest.raises(EspejoIlegibleError) as excinfo:
        proyectar_run(run_id="123", lectura=lectura, ahora=_AHORA)
    assert excinfo.value.proveedor == "run_actions"


def test_leer_y_proyectar_run_orquesta_el_puerto() -> None:
    puerto = FixedGitHubMirrorReader(
        runs_por_id={
            (_REPO, "123"): LecturaRunActions(
                estado=LecturaEstado.OK,
                run=RunActions(
                    run_id="123",
                    estado_run="completed",
                    conclusion="success",
                    head_sha="abc",
                    url="https://x",
                ),
            )
        }
    )
    mirrored = leer_y_proyectar_run(puerto, repo=_REPO, run_id="123", ahora=_AHORA)
    assert mirrored is not None
    assert mirrored.conclusion == "success"


# --- `scripts/automation` no es parte del artefacto instalado (CODEX-001, ronda 3) ---
#
# ``pyproject.toml`` empaqueta únicamente ``sirius`` y ``sirius_engine``:
# ``scripts/`` es automatización de este repositorio, no algo que un wheel
# instalado lleve consigo. Un `import automation...` a nivel de módulo aquí
# bastaba para que CARGAR este módulo -y por tanto `sirius_engine.cli` y
# `sirius_engine.seven_day_streak_cli`, que lo importan- reventara con
# `ModuleNotFoundError` fuera de un checkout, incluso para quien no necesita
# leer GitHub en absoluto (`sirius-racha --hora-recomendada`, resolver
# `--raiz`). Comprobado construyendo el wheel real e instalándolo en un
# entorno limpio: https://github.com/canelamoraguezandyjesus-bot/sirius/pull/269#discussion_r3837235813


def test_cargar_este_modulo_no_importa_automation_a_nivel_de_modulo() -> None:
    """El import de ``automation`` debe vivir DENTRO de una función, nunca en el cuerpo del módulo.

    ``ast.walk`` recorrería también las funciones y no distinguiría los dos
    casos; aquí se recorre solo ``tree.body`` -las sentencias de nivel de
    módulo- a propósito, porque la propiedad exigida es justamente que
    ``automation`` no aparezca ahí.
    """
    ruta = Path(mirror_projection.__file__)
    cuerpo_del_modulo = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta)).body

    nombres_importados_a_nivel_de_modulo: set[str] = set()
    for sentencia in cuerpo_del_modulo:
        if isinstance(sentencia, ast.Import):
            nombres_importados_a_nivel_de_modulo.update(alias.name for alias in sentencia.names)
        elif isinstance(sentencia, ast.ImportFrom) and sentencia.module is not None:
            nombres_importados_a_nivel_de_modulo.add(sentencia.module)

    ofensores = {
        nombre
        for nombre in nombres_importados_a_nivel_de_modulo
        if nombre == "automation" or nombre.startswith("automation.")
    }
    assert ofensores == set(), (
        f"{ruta.name} importa {ofensores} al cargarse: eso rompe con ModuleNotFoundError "
        "fuera de un checkout, porque el wheel instalado no empaqueta scripts/automation"
    )


def test_sirius_convergence_se_resuelve_bajo_demanda_a_las_mismas_funciones() -> None:
    """El diferimiento no cambia QUÉ se reutiliza (incidencia #193): sigue siendo el script real.

    Sin esto, la prueba anterior por sí sola aceptaría también una
    corrección que rompiera la reutilización -por ejemplo, duplicar la
    lógica en vez de diferir el import-, que es justo lo que el diseño
    original quería evitar (una segunda copia que podría divergir).
    """
    convergencia = mirror_projection._sirius_convergence()
    assert convergencia.__name__ == "automation.sirius_convergence"
    assert callable(convergencia.parse_round_records)
    assert callable(convergencia.history_after_last_resume)
    assert callable(convergencia.ci_failure_streak)
