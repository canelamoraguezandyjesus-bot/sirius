"""Módulo compartido de análisis de historial (H-13, incidencia #275).

``src/sirius_engine/round_history.py`` es la única definición de
``parse_round_records``, ``history_after_last_resume`` y ``ci_failure_streak``.
``scripts/automation/round_history.py`` es un ENLACE SIMBÓLICO a ese mismo
fichero, no una segunda copia: así lo necesita ``sirius_convergence.py`` para
seguir funcionando sin el paquete instalado, sin duplicar el analizador que
gobierna la convergencia real (criterio de parada (b) de la incidencia #275:
duplicar estas funciones habría sido peor que el `sys.path` que sustituyen).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL = REPO_ROOT / "src" / "sirius_engine" / "round_history.py"
SYMLINK = REPO_ROOT / "scripts" / "automation" / "round_history.py"

_FUNCIONES_COMPARTIDAS = ("parse_round_records", "history_after_last_resume", "ci_failure_streak")


def test_el_enlace_de_scripts_apunta_al_mismo_fichero_que_el_paquete() -> None:
    """Sin esto, nada impide que las dos rutas diverjan en un commit futuro."""
    assert SYMLINK.is_symlink()
    assert CANONICAL.samefile(SYMLINK)


def test_las_tres_funciones_compartidas_tienen_una_unica_definicion() -> None:
    """Comprobación estructural del requisito 4: ninguna función queda duplicada.

    ``def <nombre>(`` aparece exactamente una vez en el fichero canónico, y
    CERO veces en cualquier otro ``.py`` de ``src/`` o ``scripts/automation/``:
    así, una copia manual futura -en vez de reutilizar el enlace simbólico- se
    detecta aquí, no en producción.
    """
    texto_canonico = CANONICAL.read_text(encoding="utf-8")
    for nombre in _FUNCIONES_COMPARTIDAS:
        assert texto_canonico.count(f"def {nombre}(") == 1

    otros_ficheros = [
        path for path in (REPO_ROOT / "src").rglob("*.py") if path.resolve() != CANONICAL.resolve()
    ] + [
        path
        for path in (REPO_ROOT / "scripts" / "automation").glob("*.py")
        if path.resolve() != CANONICAL.resolve()
    ]
    for path in otros_ficheros:
        texto = path.read_text(encoding="utf-8")
        for nombre in _FUNCIONES_COMPARTIDAS:
            assert f"def {nombre}(" not in texto, (
                f"{path} redefine {nombre}(): debería importarla de round_history, no duplicarla."
            )
