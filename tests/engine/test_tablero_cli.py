"""`sirius-tablero`: la cáscara que calcula el cuerpo del tablero (ADR-175).

No publica nada -eso es de `notify-sirius-state.yml`-, así que lo único que hay
que fijar aquí es lo que el workflow da por hecho: que el cuerpo sale por la
salida estándar, que empieza por su marcador, y que un fallo de lectura se
distingue de un tablero vacío en vez de confundirse con él.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path

from sirius_engine import tablero_cli
from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.ports.github_mirror import (
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    MetadatosIncidencia,
)
from sirius_engine.tablero import MARCADOR

_AHORA = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
_REPO = "canelamoraguezandyjesus-bot/sirius"
_NUMERO = 508

_CUERPO_REAL = """## Work ID

WI-20260912-120000

## Bloque

ENCARGO

## Objetivo

Implementa el tablero por incidencia.

## Alcance permitido

El cambio en el código que pide el objetivo, con sus pruebas, y nada más.

## Rama base

main
"""


def _mirror(
    *,
    etiquetas: tuple[str, ...] = ("sirius:implementing",),
    estado_cuerpo: LecturaEstado = LecturaEstado.OK,
    estado_meta: LecturaEstado = LecturaEstado.OK,
) -> FixedGitHubMirrorReader:
    return FixedGitHubMirrorReader(
        metadatos_por_incidencia={
            (_REPO, _NUMERO): LecturaMetadatos(
                estado=estado_meta,
                metadatos=(
                    MetadatosIncidencia(
                        numero=_NUMERO, titulo="t", estado_gh="open", etiquetas=etiquetas
                    )
                    if estado_meta is LecturaEstado.OK
                    else None
                ),
            )
        },
        cuerpos_por_incidencia={
            (_REPO, _NUMERO): LecturaCuerpo(
                estado=estado_cuerpo,
                cuerpo=(
                    CuerpoIncidencia(autor_login="x", autor_asociacion="OWNER", texto=_CUERPO_REAL)
                    if estado_cuerpo is LecturaEstado.OK
                    else None
                ),
            )
        },
        comentarios_por_incidencia={
            (_REPO, _NUMERO): LecturaComentarios(estado=LecturaEstado.OK, comentarios=())
        },
    )


def _correr(mirror: FixedGitHubMirrorReader) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = tablero_cli.main(
        ["--repo", _REPO, "--incidencia", str(_NUMERO)],
        salida=salida,
        ahora=_AHORA,
        mirror=mirror,
    )
    return codigo, salida.getvalue()


def test_escribe_el_tablero_por_la_salida_estandar() -> None:
    codigo, texto = _correr(_mirror())
    assert codigo == 0
    assert texto.startswith(MARCADOR)
    assert "WI-20260912-120000" in texto
    assert "Implementa el tablero por incidencia." in texto
    assert "trabajando" in texto


def test_un_cuerpo_ilegible_no_produce_un_tablero_a_medias() -> None:
    """Sin cuerpo no hay tablero, y es lo correcto.

    La proyección del espejo YA se niega a proyectar sin cuerpo -"no hay forma
    honesta de decir «no hay etiqueta»/«no hay PR» con datos parciales"-, así
    que aquí no hay nada que decidir: si no se pudo leer, se sale con 2 y el
    tablero anterior se queda donde está, que es mejor que pisarlo con uno
    incompleto.
    """
    codigo, texto = _correr(_mirror(estado_cuerpo=LecturaEstado.NO_DISPONIBLE))
    assert codigo == 2
    assert texto == ""


def test_un_espejo_ilegible_sale_con_2_y_no_escribe_nada() -> None:
    """El workflow trata el 2 como «hoy no hay tablero» y deja el anterior en pie.

    Distinguirlo de un tablero vacío importa: publicar un tablero en blanco
    borraría el último bueno, que es peor que no tocarlo.
    """
    codigo, texto = _correr(_mirror(estado_meta=LecturaEstado.NO_DISPONIBLE))
    assert codigo == 2
    assert texto == ""


def test_la_primera_linea_es_el_marcador_que_el_workflow_busca() -> None:
    """El workflow saca el marcador de aquí en vez de copiarlo: un dato, un dueño."""
    _, texto = _correr(_mirror())
    primera = texto.splitlines()[0]
    assert primera == MARCADOR
    assert primera.startswith("<!--") and primera.endswith("-->")


def test_el_workflow_llama_al_comando_tal_como_esta_declarado() -> None:
    """Que el paso del workflow y el punto de entrada no se separen en silencio."""
    raiz = Path(__file__).resolve().parents[2]
    workflow = (raiz / ".github" / "workflows" / "notify-sirius-state.yml").read_text(
        encoding="utf-8"
    )
    assert "uv run sirius-tablero --repo" in workflow
    assert "sirius_comment_upsert" in workflow
    pyproject = (raiz / "pyproject.toml").read_text(encoding="utf-8")
    assert 'sirius-tablero = "sirius_engine.tablero_cli:main"' in pyproject
