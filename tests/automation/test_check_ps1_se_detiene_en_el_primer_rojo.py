"""ADR-153: `scripts/check.ps1` se detiene en el primer paso rojo y propaga su
código de salida.

El guion encadenaba los cuatro comandos sin comprobar el código de salida de
ninguno. `$ErrorActionPreference = "Stop"` no alcanza a los ejecutables
nativos, y `pwsh -File` devuelve el código del ÚLTIMO comando: el «exit 0» que
la validación obligatoria de ADR-145 pide transcribir era el de pytest y solo
el de pytest. En #545 el corrector declaró, con verdad, «código de salida 0»
sobre un árbol que Quality tumbó en `ruff format` (ronda 2) y en `mypy`
(tras el parche del operador); la ronda 3 encontró la causa.

No hay `pwsh` en el entorno del operador, así que este guardián fija la FORMA
del guion, que es lo decidible sin ejecutarlo: los cuatro comandos en su
orden, cada uno de los tres primeros seguido inmediatamente de la comprobación
de `$LASTEXITCODE`, y el último seguido de `exit $LASTEXITCODE`.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUION = REPO_ROOT / "scripts" / "check.ps1"

COMANDOS = [
    "uv run ruff format --check .",
    "uv run ruff check .",
    "uv run mypy src tests",
    "uv run pytest",
]
COMPROBACION = "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"
SALIDA_FINAL = "exit $LASTEXITCODE"


def _lineas_de_codigo() -> list[str]:
    return [
        linea.strip()
        for linea in GUION.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]


def test_los_cuatro_comandos_siguen_en_su_orden() -> None:
    """La validación obligatoria sigue siendo la misma: ADR-145 la nombra por
    estos cuatro comandos, en este orden."""
    comandos = [linea for linea in _lineas_de_codigo() if linea.startswith("uv run ")]
    assert comandos == COMANDOS


def test_cada_comando_comprueba_su_codigo_de_salida_antes_del_siguiente() -> None:
    lineas = _lineas_de_codigo()
    for comando in COMANDOS[:-1]:
        posicion = lineas.index(comando)
        assert lineas[posicion + 1] == COMPROBACION, (
            f"tras `{comando}` no viene la comprobación de $LASTEXITCODE: un rojo "
            "ahí seguiría adelante y el guion devolvería el código de pytest, no el suyo "
            "(ADR-153, #545)"
        )


def test_el_guion_devuelve_el_codigo_del_ultimo_comando_de_forma_explicita() -> None:
    lineas = _lineas_de_codigo()
    assert lineas[-2:] == [COMANDOS[-1], SALIDA_FINAL], (
        "el guion debe terminar en `uv run pytest` seguido de `exit $LASTEXITCODE`: "
        "sin el `exit` explícito, lo que devuelve depende de la versión de pwsh"
    )


def test_no_hay_nada_ejecutable_fuera_de_los_comandos_y_sus_comprobaciones() -> None:
    """Un guion de comprobación que hiciera algo más ya no sería «una sola
    invocación» de los cuatro comandos (ADR-145)."""
    lineas = _lineas_de_codigo()
    permitidas = set(COMANDOS) | {COMPROBACION, SALIDA_FINAL, '$ErrorActionPreference = "Stop"'}
    sobrantes = [linea for linea in lineas if linea not in permitidas]
    assert sobrantes == [], sobrantes
