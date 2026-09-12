"""El tablero de una incidencia: la foto de AHORA, generada (ADR-175).

Nota de arranque en `docs/decisions/ADR-175-*.md`. Lo medido que la motiva: las
40 incidencias más recientes del ciclo acumulan 1.019 comentarios -mediana 21,
máximo 157- y ninguno dice el estado.

Esta batería fija tres cosas y ninguna más: que el marcador esté (sin él, el
publicador no sabría qué editar y publicaría un segundo tablero cada vez), que
lo que el espejo sabe se enseñe, y que lo que NO sabe no se invente.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius_engine.domain.mirror import (
    EventoQuality,
    MirroredWorkItem,
    OrigenLectura,
    RondaHallazgos,
)
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.issue_body_parsing import CuerpoDeclarado
from sirius_engine.tablero import MARCADOR, generar_tablero

_AHORA = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)


def _espejo(
    *,
    estado: WorkItemState | None = WorkItemState.ACTIVE,
    fase: WorkItemPhase | None = WorkItemPhase.EJECUTAR,
    etiquetas: tuple[str, ...] = ("sirius:implementing",),
    etiquetas_contradictorias: bool = False,
    cerrada: bool = False,
    pr_url: str | None = None,
    head_sha: str | None = None,
    rondas: tuple[RondaHallazgos, ...] = (),
    eventos_quality: tuple[EventoQuality, ...] = (),
    fallos_quality_consecutivos: int = 0,
    diagnostico_fallo: str | None = None,
) -> MirroredWorkItem:
    return MirroredWorkItem(
        work_id="repo#508",
        estado=estado,
        fase=fase,
        etiquetas=etiquetas,
        etiquetas_contradictorias=etiquetas_contradictorias,
        cerrada=cerrada,
        pr_url=pr_url,
        head_sha=head_sha,
        rondas=rondas,
        veredictos=(),
        eventos_quality=eventos_quality,
        fallos_quality_consecutivos=fallos_quality_consecutivos,
        origen=OrigenLectura(fuente="gh", leido_en=_AHORA),
        diagnostico_fallo=diagnostico_fallo,
    )


_CUERPO = CuerpoDeclarado(
    work_id="WI-20260912-120000",
    bloque="ENCARGO",
    objetivo="Implementa el tablero por incidencia.",
    entregable="El cambio en el código que pide el objetivo, con sus pruebas.",
    fuera_de_alcance="Cualquier cambio no descrito en el objetivo.",
    criterio_terminado="Las validaciones obligatorias en verde.",
    plan=("Escribir el generador", "Publicarlo desde el workflow"),
    rama_base="main",
)


# --- Lo que el publicador necesita para no duplicar -------------------------


def test_el_tablero_empieza_por_su_marcador() -> None:
    """Sin marcador no hay edición: cada pasada publicaría un tablero nuevo."""
    texto = generar_tablero(_CUERPO, _espejo(), numero=508)
    assert texto.startswith(MARCADOR)


def test_el_marcador_aparece_una_sola_vez() -> None:
    """Dos marcadores harían ambigua la búsqueda del publicador."""
    assert generar_tablero(_CUERPO, _espejo(), numero=508).count(MARCADOR) == 1


# --- Lo que el espejo sabe, enseñado ----------------------------------------


@pytest.mark.parametrize(
    ("estado", "esperado"),
    [
        (WorkItemState.ACTIVE, "trabajando"),
        (WorkItemState.NEEDS_DECISION, "necesita una decisión tuya"),
        (WorkItemState.FAILED_SAFELY, "detenido de forma segura"),
        (WorkItemState.DELIVERED, "entregado"),
        (WorkItemState.CANCELLED, "cancelado"),
    ],
)
def test_cada_estado_se_lee_en_castellano(estado: WorkItemState, esperado: str) -> None:
    texto = generar_tablero(_CUERPO, _espejo(estado=estado, fase=None), numero=508)
    assert esperado in texto


def test_listo_para_fusionar_dice_la_palabra_que_hay_que_escribir() -> None:
    """Es el único estado en que la pelota está en su tejado sin que el motor pare."""
    texto = generar_tablero(
        _CUERPO,
        _espejo(fase=WorkItemPhase.ENTREGAR, etiquetas=("sirius:ready-for-merge",)),
        numero=508,
    )
    assert "listo para fusionar" in texto
    assert "**fusiona**" in texto


def test_la_fase_actual_va_en_negrita_y_las_demas_no() -> None:
    texto = generar_tablero(_CUERPO, _espejo(fase=WorkItemPhase.COMPROBAR), numero=508)
    assert "**`comprobar`**" in texto
    assert "**`revisar`**" not in texto
    assert "`revisar`" in texto


def test_reparar_se_explica_aparte_porque_no_es_un_paso_adelante() -> None:
    texto = generar_tablero(_CUERPO, _espejo(fase=WorkItemPhase.REPARAR), numero=508)
    assert "vuelta de `revisar` a `comprobar`" in texto


def test_quality_y_las_rondas_salen_con_sus_numeros() -> None:
    texto = generar_tablero(
        _CUERPO,
        _espejo(
            eventos_quality=(
                EventoQuality(head="abc1234def", conclusion="failure"),
                EventoQuality(head="abc1234def", conclusion="success"),
            ),
            fallos_quality_consecutivos=0,
            rondas=(RondaHallazgos(numero=2, head="abc1234def", pendientes=1, gravedad_total=3),),
        ),
        numero=508,
    )
    assert "2 ejecución(es)" in texto
    assert "`success`" in texto
    assert "ronda **2**" in texto
    assert "**1** hallazgo(s) pendiente(s)" in texto


def test_una_parada_ensena_su_diagnostico() -> None:
    texto = generar_tablero(
        _CUERPO,
        _espejo(
            estado=WorkItemState.FAILED_SAFELY, fase=None, diagnostico_fallo="se acabó el tiempo"
        ),
        numero=508,
    )
    assert "Por qué se detuvo" in texto
    assert "se acabó el tiempo" in texto


def test_unas_etiquetas_contradictorias_no_se_esconden() -> None:
    texto = generar_tablero(
        _CUERPO,
        _espejo(
            estado=None,
            fase=None,
            etiquetas=("sirius:completed", "sirius:failed-safely"),
            etiquetas_contradictorias=True,
        ),
        numero=508,
    )
    assert "se contradicen" in texto


def test_una_incidencia_cerrada_lo_dice() -> None:
    texto = generar_tablero(_CUERPO, _espejo(cerrada=True), numero=508)
    assert "cerrada" in texto


# --- Lo que el espejo NO sabe, no se inventa --------------------------------


def test_sin_pr_no_se_inventa_ninguna() -> None:
    texto = generar_tablero(_CUERPO, _espejo(pr_url=None), numero=508)
    assert "todavía no hay ninguna enlazada" in texto


def test_un_cuerpo_sin_secciones_no_produce_una_tabla_inventada() -> None:
    """Un cuerpo ilegible da medio tablero, no un tablero falso."""
    texto = generar_tablero(CuerpoDeclarado(), _espejo(), numero=508)
    assert "no declara ninguna de las secciones" in texto
    assert "| Encargo |" not in texto
    # Y lo que sí se sabe por etiquetas sigue estando.
    assert "trabajando" in texto


def test_sin_quality_ni_rondas_se_dice_que_no_hay_todavia() -> None:
    texto = generar_tablero(_CUERPO, _espejo(), numero=508)
    assert "ninguna ejecución observada todavía" in texto
    assert "ninguna ronda registrada todavía" in texto


def test_el_tablero_dice_de_donde_lo_leyo() -> None:
    """Sin la fuente, el tablero es una afirmación sin comprobación detrás."""
    assert "Leído de: gh" in generar_tablero(_CUERPO, _espejo(), numero=508)


def test_un_objetivo_larguisimo_se_recorta_sin_romper_la_tabla() -> None:
    largo = CuerpoDeclarado(objetivo="palabra " * 300)
    texto = generar_tablero(largo, _espejo(), numero=508)
    fila = next(linea for linea in texto.splitlines() if linea.startswith("| Objetivo |"))
    assert len(fila) < 500
    assert fila.count("|") == 3


def test_el_generador_no_mira_el_reloj_ni_la_red_ni_git() -> None:
    """Puro: dos llamadas con lo mismo dan lo mismo, y el texto no trae fechas.

    La pureza es lo que permite publicarlo desde un workflow sin que dos
    pasadas seguidas produzcan cuerpos distintos y el tablero parpadee.
    """
    uno = generar_tablero(_CUERPO, _espejo(), numero=508)
    otro = generar_tablero(_CUERPO, _espejo(), numero=508)
    assert uno == otro
    fuente = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "src"
        / "sirius_engine"
        / "tablero.py"
    ).read_text(encoding="utf-8")
    for prohibido in ("datetime.now", "subprocess", "requests", "urllib", "import os"):
        assert prohibido not in fuente, f"el generador usa {prohibido}: ya no es puro"
