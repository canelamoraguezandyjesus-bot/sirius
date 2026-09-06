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

import importlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.domain.mirror import (
    EspejoIlegibleError,
    FormaDePermiso,
    MirroredWorkItem,
)
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.mirror_projection import (
    _LABEL_PRIORITY,
    _LABEL_STATE,
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


# --- El diagnóstico de un comentario FAILED_SAFELY (C1, incidencia #529) ---


def test_diagnostico_fallo_se_extrae_del_ultimo_comentario_de_confianza() -> None:
    """Mismo cuerpo exacto que ``sirius_apply_verdict.sh`` publica para
    ``FAILED_SAFELY``/``USAGE_LIMIT_REACHED``: marcador, cabecera fija en
    negrita, y el diagnóstico libre debajo.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:implementer:FAILED_SAFELY:run-1 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\n"
            "uv no estaba instalado en el runner y curl estaba denegado."
        ),
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
    assert (
        mirrored.diagnostico_fallo == "uv no estaba instalado en el runner y curl estaba denegado."
    )


def test_diagnostico_fallo_toma_el_ultimo_cuando_hay_varios() -> None:
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    viejo = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:implementer:FAILED_SAFELY:run-1 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\ndiagnóstico viejo"
        ),
        creado_en=_AHORA,
    )
    nuevo = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:corrector:FAILED_SAFELY:run-2 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\ndiagnóstico nuevo"
        ),
        creado_en=_AHORA,
    )
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=(viejo, nuevo))

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.diagnostico_fallo == "diagnóstico nuevo"


def test_diagnostico_fallo_de_un_comentario_no_confiable_no_cuenta() -> None:
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="un-tercero",
        autor_asociacion="NONE",
        cuerpo=(
            "<!-- sirius-verdict:implementer:FAILED_SAFELY:run-1 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\ndiagnóstico ajeno"
        ),
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
    assert mirrored.diagnostico_fallo is None


def test_diagnostico_fallo_se_extrae_de_una_parada_precheck(  # CODEX-001, PR #530
) -> None:
    """Cuerpo exacto que publica `stop_gate` en `review-sirius-work.yml`
    (y las paradas equivalentes de `repair-sirius-work.yml`/
    `sirius_apply_verdict.sh`): el marcador lleva `precheck:<motivo>` en vez
    de `FAILED_SAFELY`/`USAGE_LIMIT_REACHED`, pero aplica la misma etiqueta
    `sirius:failed-safely` con la misma cabecera fija. Antes de esta
    corrección esta lectura devolvía ``None`` (CODEX-001).
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="github-actions[bot]",
        autor_asociacion="NONE",
        cuerpo=(
            "<!-- sirius-verdict:reviewer:precheck:sin-pr:12345-1 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\n"
            "No encuentro ninguna PR asociada a esta incidencia; no hay nada que revisar."
        ),
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
    assert (
        mirrored.diagnostico_fallo
        == "No encuentro ninguna PR asociada a esta incidencia; no hay nada que revisar."
    )


def test_diagnostico_fallo_de_precheck_con_otra_etiqueta_no_cuenta() -> None:
    """Las paradas `precheck` que NO aplican `sirius:failed-safely` -por
    ejemplo `convergencia-<motivo>`, que aplica `sirius:blocked-decision`-
    publican una cabecera distinta (`🟡 Necesito una decisión`), así que no
    deben leerse como diagnóstico de fallo aunque compartan el prefijo
    `sirius-verdict:...:precheck:`.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="github-actions[bot]",
        autor_asociacion="NONE",
        cuerpo=(
            "<!-- sirius-verdict:corrector:precheck:convergencia-mismo-defecto:1-1 -->\n\n"
            "🟡 **Necesito una decisión**\n\n"
            "El ciclo de revisión-corrección ha dejado de converger."
        ),
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
    assert mirrored.diagnostico_fallo is None


def test_diagnostico_fallo_de_notificacion_no_cuenta() -> None:
    """Los comentarios de `notify-sirius-state.yml` usan el marcador
    `sirius-notification:`, no `sirius-verdict:`, aunque repitan la misma
    cabecera fija y el mismo texto genérico: no deben leerse como
    diagnóstico real.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="github-actions[bot]",
        autor_asociacion="NONE",
        cuerpo=(
            "<!-- sirius-notification:sirius:failed-safely:abc1234 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\n"
            "He encontrado un problema que no puedo resolver automáticamente sin riesgo.\n\n"
            "La incidencia contiene el diagnóstico y el siguiente paso recomendado."
        ),
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
    assert mirrored.diagnostico_fallo is None


def test_diagnostico_fallo_ausente_sin_comentario_de_fallo() -> None:
    metadatos = _metadatos_minimos()
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
    assert mirrored.diagnostico_fallo is None


# --- reanudacion_publicada: los tres marcadores de sirius_resume_on_command.sh
# (CODEX-001, ronda 4, PR #530) ----------------------------------------------
#
# Sin uno de estos tres marcadores publicado por una identidad de confianza,
# un cambio de etiqueta sobre un `WorkItem` parado no es una reanudación
# autoritativa: es indistinguible de una etiqueta sustituida a mano. Estas
# pruebas cubren los tres marcadores, la ausencia, y que un comentario no
# confiable no cuenta -mismo criterio que el resto de marcadores de este
# módulo (`es_autor_de_confianza`)-.


@pytest.mark.parametrize(
    "marcador",
    [
        "<!-- sirius-resume-stop:deadbee1 -->",
        "<!-- sirius-convergence-reset:deadbee2 -->",
        "<!-- sirius-restart-sin-pr:508:12345-1 -->",
    ],
)
def test_reanudacion_publicada_es_true_con_cada_uno_de_los_tres_marcadores(
    marcador: str,
) -> None:
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login=_OWNER_LOGIN,
        autor_asociacion="OWNER",
        cuerpo=f"{marcador}\n\n🟢 **Parada segura levantada por orden del propietario**\n",
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
    assert mirrored.reanudacion_publicada is True


def test_reanudacion_publicada_es_false_sin_ningun_marcador() -> None:
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login=_OWNER_LOGIN,
        autor_asociacion="OWNER",
        cuerpo="continua",
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
    assert mirrored.reanudacion_publicada is False


def test_reanudacion_publicada_de_un_comentario_no_confiable_no_cuenta() -> None:
    """Un marcador de reanudación citado -o publicado- por alguien que no es
    el propietario ni el bot no autoriza nada: mismo criterio de confianza
    que gobierna el resto de marcadores de este módulo.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    comentario = Comentario(
        autor_login="alguien-de-fuera",
        autor_asociacion="NONE",
        cuerpo="<!-- sirius-resume-stop:deadbee1 -->\n\ncontinua",
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
    assert mirrored.reanudacion_publicada is False


# --- reanudacion_publicada se ancla a la parada VIGENTE, no a "alguna vez"
# (CLAUDE-REVISOR-001/CODEX-002, ronda 5, PR #530) ---------------------------
#
# Las pruebas de arriba solo cubrían "el marcador está" / "el marcador no
# está" sobre un historial de un único comentario. Ninguna reproducía un
# marcador de una reanudación YA CONSUMIDA seguido de una parada NUEVA y sin
# relación: la versión de la ronda 4 devolvía `True` en ese caso con
# `any(...)` sin noción de orden, reabriendo exactamente el escenario que esa
# misma ronda decía cerrar.


def test_reanudacion_publicada_es_false_si_hay_parada_nueva_tras_marcador_consumido() -> None:
    """Un `sirius-resume-stop` antiguo no autoriza una parada `FAILED_SAFELY`
    posterior y distinta que nunca recibió su propio marcador de reanudación.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    viejo = Comentario(
        autor_login=_OWNER_LOGIN,
        autor_asociacion="OWNER",
        cuerpo="<!-- sirius-resume-stop:deadbee1 -->\n\ncontinua",
        creado_en=datetime(2026, 8, 1, tzinfo=UTC),
    )
    nuevo = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:corrector:FAILED_SAFELY:run-2 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\ndiagnóstico nuevo, sin relación"
        ),
        creado_en=datetime(2026, 8, 2, tzinfo=UTC),
    )
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=(viejo, nuevo))

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.reanudacion_publicada is False


def test_reanudacion_publicada_no_se_invalida_por_head_movido_tras_ci() -> None:
    """`precheck:head-movido-tras-ci` no es una parada: no debe invalidar una
    reanudación ya publicada (CODEX-001, ronda 6, PR #530).

    Esa rama de `repair-sirius-work.yml` (líneas 425-433) publica ese verdict
    y devuelve la incidencia a `sirius:ci-pending`, no a `failed-safely` ni a
    `blocked-decision`: es un evento consumible del camino normal, no una
    parada. Secuencia: parada real → reanudación → `head-movido-tras-ci`. Antes
    de esta corrección, `_STOP_MARKER_RE` clasificaba también ese último
    marcador como parada, así que `ultima_parada` quedaba DESPUÉS de
    `ultimo_resume` y `reanudacion_publicada` se leía como `False` pese a que
    nada nuevo había parado el ciclo.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    parada = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:corrector:FAILED_SAFELY:run-1 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\ndiagnóstico"
        ),
        creado_en=datetime(2026, 8, 1, tzinfo=UTC),
    )
    reanudacion = Comentario(
        autor_login=_OWNER_LOGIN,
        autor_asociacion="OWNER",
        cuerpo="<!-- sirius-resume-stop:deadbee1 -->\n\ncontinua",
        creado_en=datetime(2026, 8, 2, tzinfo=UTC),
    )
    head_movido = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:corrector:precheck:head-movido-tras-ci -->\n\n"
            "🟡 **El fallo de Quality registrado es de un head anterior**\n\n"
            "Devuelvo la incidencia a `sirius:ci-pending`."
        ),
        creado_en=datetime(2026, 8, 3, tzinfo=UTC),
    )
    comentarios = LecturaComentarios(
        estado=LecturaEstado.OK, comentarios=(parada, reanudacion, head_movido)
    )

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.reanudacion_publicada is True


def test_reanudacion_publicada_es_true_si_el_marcador_llega_tras_la_ultima_parada() -> None:
    """Orden normal de una reanudación real: la parada primero, el marcador de
    reanudación de `sirius_resume_on_command.sh` después. Sigue autorizando.
    """
    metadatos = _metadatos_minimos()
    cuerpo = _cuerpo_de_confianza("")
    parada = Comentario(
        autor_login="canelamoraguezandyjesus-bot",
        autor_asociacion="OWNER",
        cuerpo=(
            "<!-- sirius-verdict:corrector:FAILED_SAFELY:run-2 -->\n\n"
            "🔴 **Me he detenido de forma segura**\n\ndiagnóstico"
        ),
        creado_en=datetime(2026, 8, 1, tzinfo=UTC),
    )
    reanudacion = Comentario(
        autor_login=_OWNER_LOGIN,
        autor_asociacion="OWNER",
        cuerpo="<!-- sirius-resume-stop:deadbee1 -->\n\ncontinua",
        creado_en=datetime(2026, 8, 2, tzinfo=UTC),
    )
    comentarios = LecturaComentarios(estado=LecturaEstado.OK, comentarios=(parada, reanudacion))

    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=metadatos,
        cuerpo=cuerpo,
        comentarios=comentarios,
        ahora=_AHORA,
    )
    assert mirrored.reanudacion_publicada is True


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


# --- Las tres listas del vocabulario de etiquetas ----------------------------
#
# El estado del ciclo vive en tres sitios que tienen que decir lo mismo:
# quién CREA las etiquetas (el workflow de bootstrap), quién las INTERPRETA
# (`_LABEL_STATE`) y en qué ORDEN desempata (`_LABEL_PRIORITY`). Ninguna
# prueba las ataba, y el camino de fallo no es ruidoso: una etiqueta que esté
# en `_LABEL_STATE` y no en `_LABEL_PRIORITY` hace que `_estado_y_fase`
# recorra la prioridad sin encontrarla y devuelva `(None, None, False)` — es
# decir, «esta incidencia no tiene ninguna etiqueta `sirius:*`», con el tercer
# elemento diciendo además que no hay contradicción. La proyección quedaría
# ciega justo sobre la etiqueta nueva.

_BOOTSTRAP = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "bootstrap-sirius-automation-labels.yml"
)


def _etiquetas_que_crea_el_bootstrap() -> set[str]:
    return set(re.findall(r"sirius:[a-z-]+", _BOOTSTRAP.read_text(encoding="utf-8")))


def test_interpretar_y_desempatar_cubren_exactamente_las_mismas_etiquetas() -> None:
    """Una etiqueta sin fila en la prioridad deja la proyección ciega, sin ruido."""
    assert set(_LABEL_STATE) == set(_LABEL_PRIORITY), (
        "las etiquetas que se interpretan y las que se desempatan tienen que ser "
        "las mismas: una que esté solo en una de las dos se pierde en silencio"
    )


def test_el_vocabulario_interpretado_es_el_que_de_verdad_se_crea() -> None:
    """Lo que el bootstrap crea en GitHub y lo que la proyección entiende.

    Se lee el workflow, no se copia su lista: copiarla sería el mismo olvido
    que la prueba existe para hacer imposible.
    """
    creadas = _etiquetas_que_crea_el_bootstrap()
    assert creadas, "no se leyó ninguna etiqueta del bootstrap: la lectura falló"
    assert creadas == set(_LABEL_STATE), (
        f"solo se crean: {sorted(creadas - set(_LABEL_STATE))}; "
        f"solo se interpretan: {sorted(set(_LABEL_STATE) - creadas)}"
    )


# --- H-13 (incidencia #275): ejecutar la proyección ya no exige el árbol ---


def test_proyectar_funciona_sin_scripts_en_sys_path_ni_automation_importable() -> None:
    """LLAMAR a la proyección ya no exige el árbol de código, no solo importarla.

    Antes de este bloque, ``mirror_projection`` insertaba ``scripts/`` en
    ``sys.path`` e importaba ``automation.sirius_convergence`` en cuanto se
    LLAMABA a ``proyectar_work_item`` (incidencia #272): fuera de un checkout
    con ese árbol -por ejemplo, tras instalar el paquete desde un wheel- la
    llamada fallaba con ``ModuleNotFoundError``, aunque el módulo se pudiera
    IMPORTAR sin problema. Esta prueba quita ``scripts/`` de ``sys.path``,
    confirma que ``automation`` deja de ser importable en ese estado, y
    entonces LLAMA a ``proyectar_work_item`` sobre el ciclo completo de la
    fixture #186: si el arreglo no alcanzara para la llamada -y no solo para
    el import-, esta prueba fallaría con el mismo ``ModuleNotFoundError``.
    """
    scripts_dir = (Path(__file__).resolve().parents[2] / "scripts").resolve()
    ruta_original = list(sys.path)
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != scripts_dir]
    sys.modules.pop("automation", None)
    sys.modules.pop("automation.sirius_convergence", None)
    try:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("automation")

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

        assert [r.numero for r in mirrored.rondas] == list(range(1, 8))
        assert mirrored.fallos_quality_consecutivos == 0
        assert len(mirrored.eventos_quality) == 8
    finally:
        sys.path[:] = ruta_original


# --- `historial_estados` y `permisos_reanudacion` (ADR-147, incidencia #545) ---
#
# El camino y los permisos, no la foto. El material de partida de la PR #540
# ya exponía el historial de estados notificados; lo nuevo de ADR-147 es la
# CRONOLOGÍA de los permisos escritos del propietario y el `orden` compartido
# que hace comparables las dos cosas.


def _comentarios(*textos: tuple[str, str, str]) -> LecturaComentarios:
    """Comentarios de confianza en orden, cada uno `(login, asociación, cuerpo)`."""
    return LecturaComentarios(
        estado=LecturaEstado.OK,
        comentarios=tuple(
            Comentario(
                autor_login=login,
                autor_asociacion=asociacion,
                cuerpo=cuerpo,
                creado_en=datetime(2026, 9, 5, 3 + indice, tzinfo=UTC),
            )
            for indice, (login, asociacion, cuerpo) in enumerate(textos)
        ),
    )


def _bot(cuerpo: str) -> tuple[str, str, str]:
    return ("github-actions[bot]", "NONE", cuerpo)


def _propietario(cuerpo: str) -> tuple[str, str, str]:
    return (_OWNER_LOGIN, "OWNER", cuerpo)


def _proyectar(comentarios: LecturaComentarios) -> MirroredWorkItem:
    return proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=_metadatos_minimos(),
        cuerpo=_cuerpo_de_confianza(""),
        comentarios=comentarios,
        ahora=_AHORA,
    )


def test_historial_estados_recoge_las_notificaciones_de_etiqueta_en_orden() -> None:
    """Cada `sirius-notification` publicado es un estado por el que se PASÓ.

    Es lo que `notify-sirius-state.yml` escribe al aplicarse una de las seis
    etiquetas que vigila, y lo que permite al reflector recorrer una
    recuperación que ninguna pasada llegó a observar. La interpretación de
    etiqueta a (estado, fase) es la MISMA tabla que usa la foto.
    """
    mirrored = _proyectar(
        _comentarios(
            *(
                _bot(f"<!-- sirius-notification:{etiqueta}:{head} -->\n\ntexto")
                for etiqueta, head in (
                    ("sirius:implementing", "no-head"),
                    ("sirius:failed-safely", "1c934781"),
                    ("sirius:repair-requested", "786c82dc"),
                    ("sirius:completed", "92e5b9f4"),
                )
            )
        )
    )

    assert tuple(acreditado.etiqueta for acreditado in mirrored.historial_estados) == (
        "sirius:implementing",
        "sirius:failed-safely",
        "sirius:repair-requested",
        "sirius:completed",
    )
    assert tuple(
        (acreditado.estado, acreditado.fase) for acreditado in mirrored.historial_estados
    ) == tuple(
        _LABEL_STATE[etiqueta]
        for etiqueta in (
            "sirius:implementing",
            "sirius:failed-safely",
            "sirius:repair-requested",
            "sirius:completed",
        )
    )
    assert mirrored.historial_estados[0].head == "no-head"
    # El cuerpo de confianza ocupa la posición 0 del historial, así que el
    # primer comentario es la 1: es la escala que comparten los permisos.
    assert tuple(acreditado.orden for acreditado in mirrored.historial_estados) == (1, 2, 3, 4)


def test_historial_estados_ignora_las_notificaciones_de_autores_ajenos() -> None:
    """Mismo filtro de confianza que el resto de la proyección.

    Si un tercero pudiera publicar `sirius-notification`, podría fabricar el
    camino entero de una recuperación que nunca ocurrió y hacer que el motor
    la anotara en su diario.
    """
    mirrored = _proyectar(
        _comentarios(("alguien", "NONE", "<!-- sirius-notification:sirius:completed:deadbee1 -->"))
    )

    assert mirrored.historial_estados == ()


def test_historial_estados_ignora_una_etiqueta_que_la_tabla_no_reconoce() -> None:
    """Una notificación de algo que no está en el mapa no acredita ningún estado."""
    mirrored = _proyectar(
        _comentarios(_bot("<!-- sirius-notification:sirius:inventada:deadbee1 -->"))
    )

    assert mirrored.historial_estados == ()


def test_los_permisos_de_reanudacion_llevan_las_dos_formas_en_orden() -> None:
    """La cronología que ADR-147 exige: marcador y orden, con el mismo peso.

    El marcador es el RECIBO que publica `sirius_resume_on_command.sh`; la
    orden `continua` es el PERMISO mismo. Las dos formas hacen falta porque el
    recibo puede faltar estructuralmente -`sirius_comment_once` deduplica por
    el texto completo del marcador y el de `sirius-resume-stop` solo lleva el
    head, así que dos reanudaciones sobre un mismo head nunca dejan un segundo
    recibo (medición sobre el historial real de la #537)-.
    """
    mirrored = _proyectar(
        _comentarios(
            _propietario("continua\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_"),
            _bot("<!-- sirius-resume-stop:1c934781 -->\n\n🟢 **Parada segura levantada**"),
            _bot("<!-- sirius-notification:sirius:failed-safely:1c934781 -->"),
            _propietario("continua\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_"),
            _bot("<!-- sirius-convergence-reset:786c82dc -->"),
            _bot("<!-- sirius-restart-sin-pr:537:33991302556-1 -->"),
        )
    )

    assert tuple((permiso.forma, permiso.orden) for permiso in mirrored.permisos_reanudacion) == (
        (FormaDePermiso.ORDEN, 1),
        (FormaDePermiso.MARCADOR, 2),
        (FormaDePermiso.ORDEN, 4),
        (FormaDePermiso.MARCADOR, 5),
        (FormaDePermiso.MARCADOR, 6),
    )
    # El `orden` es comparable con el del historial de estados: la parada está
    # en la posición 3 y el segundo permiso, en la 4, es posterior a ella.
    assert mirrored.historial_estados[0].orden == 3


def _parada_publicada(diagnostico: str) -> tuple[str, str, str]:
    """El comentario literal que `sirius_apply_verdict.sh` escribe al parar en seguro."""
    return _propietario(
        "<!-- sirius-verdict:corrector:FAILED_SAFELY:33945456417-1 -->\n\n"
        f"🔴 **Me he detenido de forma segura**\n\n{diagnostico}"
    )


def test_cada_estado_acreditado_lleva_el_instante_de_su_comentario() -> None:
    """La posición ordena; el instante identifica (CODEX-002, ronda 2, PR #546).

    El mismo `(estado, fase)` aparece varias veces en un ciclo real, y la
    posición sola no dice cuál de esas ocurrencias guardó el almacén. El
    instante del comentario que la publicó sí lo acota: el almacén no pudo
    guardar una publicada después de su última escritura. Un marcador que viene
    del CUERPO no tiene instante propio -y es, por construcción, anterior a
    todo comentario-, así que se proyecta como `None` en vez de inventarle uno.
    """
    comentarios = _comentarios(
        _bot("<!-- sirius-notification:sirius:failed-safely:1c934781 -->"),
        _bot("<!-- sirius-notification:sirius:repair-requested:786c82dc -->"),
    )
    mirrored = proyectar_work_item(
        repo=_REPO,
        numero=1,
        metadatos=_metadatos_minimos(),
        cuerpo=_cuerpo_de_confianza("<!-- sirius-notification:sirius:implementing:1c934781 -->"),
        comentarios=comentarios,
        ahora=_AHORA,
    )

    assert comentarios.comentarios is not None
    assert tuple(
        (acreditado.etiqueta, acreditado.publicado_en)
        for acreditado in mirrored.historial_estados
    ) == (
        ("sirius:implementing", None),
        ("sirius:failed-safely", comentarios.comentarios[0].creado_en),
        ("sirius:repair-requested", comentarios.comentarios[1].creado_en),
    )


def test_cada_parada_acreditada_lleva_el_diagnostico_publicado_hasta_ella() -> None:
    """Cada parada conserva SU evidencia (CODEX-003, ronda 2, PR #546).

    `sirius_apply_verdict.sh` publica el diagnóstico ANTES de aplicar la
    etiqueta, y la etiqueta es lo que dispara el marcador de notificación: el
    diagnóstico que le toca a una parada es el último publicado hasta su
    posición. Sin esta atribución, el reflector recreaba todas las paradas
    históricas con el diagnóstico de la última de toda la incidencia.
    """
    mirrored = _proyectar(
        _comentarios(
            _parada_publicada("la ronda 1 se quedó sin turnos"),
            _bot("<!-- sirius-notification:sirius:failed-safely:1c934781 -->"),
            _propietario("continua"),
            _bot("<!-- sirius-notification:sirius:repair-requested:1c934781 -->"),
            _parada_publicada("la ronda 2 agotó el tiempo del job"),
            _bot("<!-- sirius-notification:sirius:failed-safely:786c82dc -->"),
        )
    )

    assert tuple(
        (acreditado.etiqueta, acreditado.diagnostico)
        for acreditado in mirrored.historial_estados
    ) == (
        ("sirius:failed-safely", "la ronda 1 se quedó sin turnos"),
        ("sirius:repair-requested", None),
        ("sirius:failed-safely", "la ronda 2 agotó el tiempo del job"),
    )
    assert mirrored.diagnostico_fallo == "la ronda 2 agotó el tiempo del job", (
        "el diagnóstico de la FOTO vigente sigue siendo el de la última parada"
    )


def test_una_parada_sin_diagnostico_publicado_hasta_ella_no_hereda_el_siguiente() -> None:
    """Abstenerse antes que atribuir lo que no es suyo.

    El diagnóstico se publica después del marcador de la primera parada: hasta
    ahí no hay ninguno atribuible, y la proyección lo dice con `None` en vez de
    prestarle el de la parada siguiente.
    """
    mirrored = _proyectar(
        _comentarios(
            _bot("<!-- sirius-notification:sirius:failed-safely:1c934781 -->"),
            _parada_publicada("la ronda 2 agotó el tiempo del job"),
            _bot("<!-- sirius-notification:sirius:failed-safely:786c82dc -->"),
        )
    )

    assert tuple(acreditado.diagnostico for acreditado in mirrored.historial_estados) == (
        None,
        "la ronda 2 agotó el tiempo del job",
    )


def test_la_orden_de_continuar_solo_cuenta_del_propietario() -> None:
    """`continua` es palabra del propietario, no del bot.

    El filtro de confianza general acepta a `github-actions[bot]` -y tiene que
    aceptarlo, porque es quien publica los marcadores-. Aceptar de él la orden
    sería dejar que la automatización se diera permiso a sí misma.
    """
    mirrored = _proyectar(_comentarios(_bot("continua"), ("alguien", "NONE", "continua")))

    assert mirrored.permisos_reanudacion == ()


def test_un_texto_que_no_es_la_orden_exacta_no_es_permiso() -> None:
    """La MISMA guarda que `sirius_resume_on_command.sh`: la palabra sola.

    Una mención casual de la palabra en una discusión no puede reanudar un
    ciclo que se detuvo por algo. Se tolera únicamente el bloque de
    atribución tras `---`, que es la excepción medida de ese guion.
    """
    mirrored = _proyectar(
        _comentarios(
            _propietario("continua ya, por favor"),
            _propietario("esto continua siendo raro"),
            _propietario("fusiona"),
            _propietario("Continua"),
        )
    )

    assert tuple(permiso.orden for permiso in mirrored.permisos_reanudacion) == (4,), (
        "solo `Continua` -la palabra sola, con el paso a minúsculas de `tr`- es la orden"
    )


def test_una_orden_en_mayusculas_con_tilde_no_cuenta_igual_que_en_el_guion() -> None:
    """Fidelidad byte a byte con `tr '[:upper:]' '[:lower:]'` en la localización C.

    `tr` no baja la `Ú`, así que `sirius_resume_on_command.sh` rechaza
    `CONTINÚA` y no repone ninguna etiqueta. Usar `str.lower()` aquí
    aceptaría un permiso que el propietario nunca llegó a dar: la fidelidad es
    lo conservador.
    """
    mirrored = _proyectar(_comentarios(_propietario("CONTINÚA"), _propietario("continúa")))

    assert tuple(permiso.orden for permiso in mirrored.permisos_reanudacion) == (2,)


def test_el_booleano_vigente_de_reanudacion_no_cambia_con_los_permisos() -> None:
    """La cronología se AÑADE al booleano; no lo sustituye ni lo redefine.

    `reanudacion_publicada` sigue siendo lo que era -el marcador más reciente
    es posterior a la última parada publicada- y sigue gobernando la regla 3
    del reflector, la del cálculo por foto. Una orden `continua` sin marcador
    no lo enciende: ampliar ese booleano habría cambiado el comportamiento de
    todos los caminos que no son el recorrido acreditado, y eso está fuera del
    alcance de la incidencia #545.
    """
    mirrored = _proyectar(
        _comentarios(
            _propietario("<!-- sirius-verdict:corrector:FAILED_SAFELY:33945456417-1 -->"),
            _propietario("continua"),
        )
    )

    assert mirrored.reanudacion_publicada is False
    assert tuple(permiso.forma for permiso in mirrored.permisos_reanudacion) == (
        FormaDePermiso.ORDEN,
    )
