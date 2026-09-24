"""ADR-216: `scripts/cierre_del_ciclo.ps1` no puede seguir adelante sobre un
fallo, ni publicar nada que no sean los dos ficheros del motor.

Este guion existe porque el lote pegado a mano que lo precedió acumuló tres
defectos de la MISMA familia en dos rondas de revisión externa sobre la PR
#663: la rama local adelantada que `--ff-only` no rechaza, un
`git rev-list … 0 1` impreso que nadie lee porque imprimir no detiene nada, y
un `git add -A` que publicaría en `estado-del-motor` cualquier fichero suelto
de su carpeta. La raíz común: las salvaguardas estaban en la prosa de debajo
del bloque, no en el código. Dos rondas con la misma familia obligan a parar y
arreglar la raíz (ADR-001), y la raíz es que un lote no puede pararse a sí
mismo.

No hay `pwsh` en este entorno -igual que para `scripts/check.ps1` (ADR-153)-,
así que estos guardianes fijan la FORMA, que es lo decidible sin ejecutarlo.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUION = REPO_ROOT / "scripts" / "cierre_del_ciclo.ps1"

COMPROBACION = "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"
#: Una llamada a un programa nativo: `git …`, `uv …`, o una asignación que
#: captura su salida. `$ErrorActionPreference` no las alcanza, y por eso cada
#: una necesita su comprobación explícita.
LLAMADA_NATIVA = re.compile(r"^(\$\w+ = )?(git|uv) ")
TRABAJOS = (
    "WI-20260903-030529",
    "WI-20260903-095428",
    "WI-20260912-235558",
    "WI-20260913-142937",
)


def _lineas_de_codigo() -> list[str]:
    return [
        linea.strip()
        for linea in GUION.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]


def test_cada_llamada_nativa_comprueba_su_codigo_de_salida() -> None:
    """La regla de ADR-153, aplicada a todas: si una falla, el guion muere ahí
    y no sigue tocando el diario."""
    lineas = _lineas_de_codigo()
    nativas = [i for i, linea in enumerate(lineas) if LLAMADA_NATIVA.match(linea)]
    assert nativas, "el guardián no reconoce ninguna llamada nativa: revísalo antes que al guion"
    for posicion in nativas:
        siguiente = lineas[posicion + 1] if posicion + 1 < len(lineas) else ""
        assert siguiente == COMPROBACION, (
            f"tras `{lineas[posicion]}` no viene la comprobación de $LASTEXITCODE: "
            "un fallo ahí seguiría adelante y el guion escribiría igual en el diario"
        )


def test_solo_se_publican_los_dos_ficheros_del_motor() -> None:
    """`git add -A` en una carpeta con cualquier cosa suelta publicaría esa
    cosa en `estado-del-motor` (ronda 3 de Codex sobre la PR #663)."""
    lineas = _lineas_de_codigo()
    assert "git -C $Memoria add diario.jsonl DESENLACES.md" in lineas
    for linea in lineas:
        assert not re.search(r"\badd\b\s+(-A\b|-u\b|--all\b|\.$)", linea), (
            f"`{linea}` captura el árbol entero: en este guion se añaden los dos "
            "ficheros por su nombre"
        )


def test_no_toca_la_rama_del_repositorio_ni_fuerza_nada() -> None:
    """`estado-del-motor` es una rama huérfana de cuatro ficheros: un
    `git switch` en su repositorio dejaría el árbol sin `pyproject.toml` y el
    `uv run` siguiente no encontraría el proyecto. Y nada se fuerza nunca."""
    codigo = "\n".join(_lineas_de_codigo())
    for prohibido in ("git switch", "git checkout", "git reset", "--force", "-f "):
        assert prohibido not in codigo, (
            f"`{prohibido}` no tiene sitio en este guion: se clona aparte y se "
            "empuja con refspec explícita, que se rechaza sola si el remoto se movió"
        )


def test_los_cuatro_trabajos_son_los_de_adr_216_y_en_su_orden() -> None:
    lineas = _lineas_de_codigo()
    decididos = [linea.split()[3] for linea in lineas if linea.startswith("uv run sirius-decidir ")]
    assert tuple(decididos) == TRABAJOS


def test_la_vista_derivada_se_regenera_antes_de_confirmar() -> None:
    """ADR-171: `DESENLACES.md` se deriva del diario, y el workflow la
    regenera tras cada reflejo. Si se confirmara antes, la vista publicada
    contaría el estado anterior."""
    lineas = _lineas_de_codigo()
    desenlaces = lineas.index("uv run sirius-memoria desenlaces --diario $Diario")
    confirmacion = next(
        i for i, linea in enumerate(lineas) if linea.startswith("git -C $Memoria commit")
    )
    assert desenlaces < confirmacion
