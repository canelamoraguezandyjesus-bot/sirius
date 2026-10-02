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
SIRIUS_CONVERGENCE = REPO_ROOT / "scripts" / "automation" / "sirius_convergence.py"

_FUNCIONES_COMPARTIDAS = ("parse_round_records", "history_after_last_resume", "ci_failure_streak")


def test_el_script_carga_el_mismo_fichero_que_importa_el_paquete() -> None:
    """La propiedad es que haya UN fichero, no el mecanismo para alcanzarlo.

    La primera versión de esta prueba exigía `is_symlink()`. No sobrevivió: el
    árbol versionado no admite enlaces simbólicos —lo prohíbe
    `test_el_arbol_versionado_no_contiene_enlaces_simbolicos`, porque
    `_contenida_en_raiz` colapsa los `..` sin resolverlos y una cita que
    atravesara uno validaría un fichero distinto del citado— y además un
    checkout de Windows sin `core.symlinks` materializa el enlace como texto,
    con lo que la afirmación habría fallado en la máquina del propietario.

    Lo que de verdad hay que garantizar es que el script y el paquete lean el
    mismo contenido, y eso se comprueba resolviendo la ruta que el script usa.
    """
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("sirius_convergence_bajo_prueba", SIRIUS_CONVERGENCE)
    assert spec is not None and spec.loader is not None
    modulo = module_from_spec(spec)
    spec.loader.exec_module(modulo)

    assert modulo._RUTA_COMPARTIDA.resolve() == CANONICAL.resolve(), (
        "el script carga un fichero distinto del que importa el paquete"
    )
    assert not (REPO_ROOT / "scripts" / "automation" / "round_history.py").exists(), (
        "volvió a aparecer el fichero hermano: el árbol no admite enlaces simbólicos"
    )


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


def test_los_revisores_declarados_se_leen_y_sin_ellos_la_ronda_es_entera() -> None:
    """ADR-230: el registro dice qué revisores tuvo la ronda; sin el campo (todo el
    historial anterior) la ronda es entera, y una lista vacía o sin forma también."""
    from sirius_engine.round_history import (
        parse_round_records,
        revisores_declarados,
        rondas_parciales,
    )

    assert revisores_declarados(None) is None and revisores_declarados([]) is None
    assert revisores_declarados(["codex", " Claude "]) == ("CLAUDE", "CODEX")
    assert revisores_declarados("CLAUDE") is None and revisores_declarados([1, ""]) is None

    def ronda(n: int, extra: str = "") -> str:
        return (
            f"<!-- sirius-round:{n} -->\n\n## RONDA_HALLAZGOS\n```json\n"
            f'{{"round": {n}, "head": "h{n}", "findings": []{extra}}}\n```\n'
        )

    registros = parse_round_records(
        ronda(1)
        + ronda(2, ', "reviewers": ["CLAUDE"]')
        + ronda(3, ', "reviewers": ["CLAUDE", "CODEX"]')
    )
    assert [r["reviewers"] for r in registros] == [None, ("CLAUDE",), ("CLAUDE", "CODEX")]
    assert rondas_parciales(registros) == {2}
    assert rondas_parciales(registros[:2]) == set(), "sin una ronda mayor conocida nadie es parcial"
    assert rondas_parciales([registros[0]]) == set()

    # `expected_reviewers` (ronda 1 de Codex en la PR #678): la primera ronda
    # parcial tras un historial antiguo declara a quién esperaba y ya es parcial.
    con_esperados = parse_round_records(
        ronda(1) + ronda(2, ', "reviewers": ["CLAUDE"], "expected_reviewers": ["CLAUDE", "CODEX"]')
    )
    assert con_esperados[1]["expected_reviewers"] == ("CLAUDE", "CODEX")
    assert rondas_parciales(con_esperados) == {2}

    # Ronda 2 de Codex en la PR #678: manda lo que cada ronda declara. Una ronda
    # solo de Claude de cuando la revisión dual estaba apagada (esperaba solo a
    # Claude) es entera aunque después el historial conozca a Codex.
    solo_y_luego_dual = parse_round_records(
        ronda(1, ', "reviewers": ["CLAUDE"], "expected_reviewers": ["CLAUDE"]')
        + ronda(2, ', "reviewers": ["CLAUDE", "CODEX"], "expected_reviewers": ["CLAUDE", "CODEX"]')
        + ronda(3, ', "reviewers": ["CLAUDE"], "expected_reviewers": ["CLAUDE", "CODEX"]')
    )
    assert rondas_parciales(solo_y_luego_dual) == {3}, "la 1 esperaba solo a Claude: entera"
