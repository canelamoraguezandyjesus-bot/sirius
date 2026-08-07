"""Pruebas estructurales de ``.github/workflows/repair-sirius-work.yml``.

La puerta del corrector dejó de contar ciclos y ahora consulta la política de
convergencia (contrato §5.1). Estas pruebas fijan, sin ejecutar Actions, que el
tope fijo desapareció de verdad del workflow y que el bloqueo por falta de
convergencia sigue siendo determinista: motivo exacto, sin invocar a Claude y
sin degradar a una corrección a ciegas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "repair-sirius-work.yml"


def _load() -> dict[Any, Any]:
    with WORKFLOW.open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    assert isinstance(doc, dict)
    return doc


def _steps(doc: dict[Any, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = doc["jobs"]["repair"]["steps"]
    return steps


def _step(doc: dict[Any, Any], fragment: str) -> dict[str, Any]:
    for step in _steps(doc):
        if fragment in str(step.get("name") or ""):
            return step
    raise AssertionError(f"paso no encontrado: {fragment!r}")


def _source() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_yaml_is_valid_and_triggered_by_repair_requested() -> None:
    doc = _load()
    trigger = doc.get("on") or doc.get(True)
    assert trigger == {"issues": {"types": ["labeled"]}}
    assert doc["jobs"]["repair"]["if"] == "github.event.label.name == 'sirius:repair-requested'"


def test_the_fixed_two_cycle_limit_is_gone() -> None:
    source = _source()
    assert "máximo de dos" not in source
    assert "de 2 como máximo" not in source
    assert "limite-ciclos" not in source
    # Y no queda ninguna comparación numérica que actúe como tope.
    assert "-ge 2" not in source


def test_gate_consults_the_convergence_policy() -> None:
    doc = _load()
    gate = _step(doc, "Evaluar la convergencia")
    run = gate["run"]
    assert "sirius_convergence.py decide" in run
    assert "sirius_dump_comments" in run
    assert "sirius_next_round_number" in run


def test_gate_blocks_for_human_decision_when_convergence_stops() -> None:
    doc = _load()
    run = _step(doc, "Evaluar la convergencia")["run"]
    assert 'if [ "$decision" != "CONTINUE" ]' in run
    assert "sirius:blocked-decision" in run
    # El motivo exacto de la política viaja al comentario de la incidencia.
    assert "convergencia-${reason}" in run
    assert "${detail}" in run


def test_unreadable_history_stops_safely_instead_of_repairing_blind() -> None:
    doc = _load()
    run = _step(doc, "Evaluar la convergencia")["run"]
    assert "historial-ilegible" in run
    assert "sirius:failed-safely" in run


def test_a_failed_decision_defaults_to_block() -> None:
    # Si la decisión no se puede leer, el valor por defecto es BLOCK: nunca se
    # continúa corrigiendo sin haber demostrado convergencia.
    run = _step(_load(), "Evaluar la convergencia")["run"]
    assert 'decision="${decision:-BLOCK}"' in run
    assert '[ "$decision" != "CONTINUE" ]' in run


def test_the_defaults_survive_an_empty_decision_file() -> None:
    # El respaldo de jq (`// "BLOCK"`) no cubre el archivo VACÍO: sobre una
    # entrada vacía jq no emite nada y sale con 0, así que ni el operador de
    # jq ni el `||` actúan y la variable queda vacía. El bloqueo seguiría
    # siendo seguro, pero se publicaría sin motivo ni detalle. El respaldo se
    # aplica sobre la variable ya expandida, que sí cubre los tres casos.
    run = _step(_load(), "Evaluar la convergencia")["run"]
    for name, fallback in (
        ("decision", "BLOCK"),
        ("reason", "indeterminado"),
        ("rounds", "0"),
    ):
        assert f'{name}="${{{name}:-{fallback}}}"' in run
    assert 'detail="${detail:-' in run


def test_the_round_number_comes_from_the_history_already_read() -> None:
    # Releer el historial para numerar la ronda abre una ventana en la que la
    # segunda lectura falla y la ronda se numeraría a ciegas.
    run = _step(_load(), "Evaluar la convergencia")["run"]
    assert 'sirius_next_round_number "$GH_REPO" "$ISSUE_NUMBER" "$comments_file"' in run
    # Y la numeración ocurre DESPUÉS de comprobar que el volcado se pudo leer.
    assert run.index("sirius_dump_comments") < run.index("sirius_next_round_number")


def test_an_unnumberable_round_stops_safely() -> None:
    run = _step(_load(), "Evaluar la convergencia")["run"]
    assert 'if [ -z "${next_cycle:-}" ]; then' in run
    assert "ronda-innumerable" in run
    assert "sirius:failed-safely" in run


def test_blocking_never_invokes_claude() -> None:
    doc = _load()
    claude = _step(doc, "Ejecutar Claude Code")
    assert claude["if"] == "steps.gate.outputs.valid == 'true'"


def test_corrector_keeps_write_permissions_and_the_bot_token() -> None:
    # El corrector sigue siendo el único rol que empuja commits, con el PAT que
    # hace que `synchronize` vuelva a disparar Quality.
    doc = _load()
    assert doc["permissions"]["contents"] == "write"
    checkout = _step(doc, "Checkout")
    assert checkout["with"]["token"] == "${{ secrets.SIRIUS_BOT_TOKEN }}"
    assert checkout["with"]["persist-credentials"] is True


def test_prompt_states_there_is_no_fixed_round_cap() -> None:
    run = _step(_load(), "Preparar instrucciones")["run"]
    assert "Ronda de corrección" in run
    assert "No hay un tope fijo de rondas" in run


def test_apply_step_always_runs() -> None:
    apply_step = _step(_load(), "Aplicar el veredicto")
    assert apply_step["if"] == "always() && steps.gate.outputs.valid == 'true'"
    assert "sirius_apply_verdict.sh" in apply_step["run"]


def test_the_corrector_prompt_states_the_rule_the_gate_implements() -> None:
    # El prompt describía el progreso como una disyunción que incluía "la
    # resolución de hallazgos concretos", regla que la puerta ya no implementa:
    # el corrector podía creer que sustituir un defecto por otro contaba como
    # avance y encontrarse la ronda bloqueada sin entender por qué. El prompt y
    # la política deben decir lo mismo.
    prompt = (REPO_ROOT / "scripts" / "automation" / "prompts" / "corrector.md").read_text(
        encoding="utf-8"
    )
    assert "mejor marca histórica" in prompt
    assert "menor gravedad agregada o la resolución de hallazgos concretos" not in prompt
    # Y el encabezado del workflow tampoco puede describir la regla antigua.
    assert "menor gravedad agregada o resolución de hallazgos concretos" not in _source()


def test_the_gate_reports_the_ci_failure_streak() -> None:
    # El bloqueo por fallos de Quality debe llegar a la incidencia con su motivo
    # y su cuenta, no diluido en el genérico de convergencia.
    run = _step(_load(), "Evaluar la convergencia")["run"]
    assert 'ci_failures="$(jq -r' in run
    assert "convergencia-${reason}" in run


# --------------------------------------------------------------------------- #
# El paso de diagnóstico se retiró (incidencia #135)
# --------------------------------------------------------------------------- #


def test_there_is_no_measured_diagnosis_step() -> None:
    """El paso que medía el trabajo del corrector se retiró, no se arregló.

    Cinco rondas de revisión encontraron siete defectos en él y TODOS eran de la
    misma familia: una afirmación que el dato no sostenía —contar commits sobre
    un rango inexistente, tomar el head de `main` por el de la PR, publicar un 0
    fabricado cuando el comando fallaba, atribuir el push al corrector, y afirmar
    que el head no cambió cuando dos muestras solo prueban que coinciden—.
    Además podía volver rojo el job que venía a diagnosticar, porque `always()`
    garantiza que un paso se ejecute pero no que su fallo no cuente.

    Lo que sobrevive es un HECHO sin medida: el enlace a la ejecución en la
    parada segura. Si alguien vuelve a añadir aquí un paso que mida, que sea con
    la decisión tomada de nuevo y no por inercia.

    Cómo se comprueba, y por qué así. Han hecho falta dos intentos:

    1. Buscar «diagnóstico» en `name` era vacuo: reintroducir el paso entero
       bajo otro nombre —«Medir estado del corrector»— restauraba el
       comportamiento con la prueba en verde.
    2. Añadir un veto de comandos (`git log`, `git status`…) tampoco bastaba:
       una lista negra prohíbe grafías, no comportamientos, y la misma medida
       cabía con `gh api` o `git show` dentro de un paso ya permitido.

    Ninguna prueba puede decidir «este guion no mide nada»: es una propiedad
    semántica de shell arbitrario. Lo que sí es decidible, y basta, es cerrar
    el CANAL. Medir el trabajo del corrector exige correr DESPUÉS de él, y
    después de él solo corre un paso: el que aplica el veredicto. Ese paso
    recibía la medida por una variable de entorno (`SIRIUS_STOP_CONTEXT`) y la
    pasaba al comentario de la parada. Fijando su entorno completo y su guion
    completo, no queda por dónde entrar: cualquier medida nueva —con el comando
    que sea— tiene que tocar algo que esta prueba fija, y entonces falla.

    Lo que esta prueba NO afirma: que ningún paso calcule nada. Afirma que nada
    calculado puede llegar al comentario de la parada. Es lo que se quería.
    """
    doc = _load()
    nombres = [str(step.get("name") or "") for step in _steps(doc)]
    assert nombres == [
        "Checkout",
        "Evaluar la convergencia y localizar la PR",
        "Consumir el evento y marcar en curso",
        "Preparar instrucciones para Claude Code",
        "Ejecutar Claude Code (corrector)",
        "Aplicar el veredicto",
    ]
    # Después del corrector solo corre el paso que aplica el veredicto. Si
    # apareciera otro detrás, mediría sin que nada de lo de abajo lo notase.
    assert nombres.index("Ejecutar Claude Code (corrector)") == len(nombres) - 2

    aplicar = _step(doc, "Aplicar el veredicto")
    # El entorno COMPLETO: era el canal por el que la medida llegaba al
    # comentario. Cualquier variable nueva obliga a pasar por aquí.
    assert sorted(aplicar["env"]) == ["CYCLE", "GH_REPO", "GH_TOKEN", "ISSUE_NUMBER"]
    # Y el guion COMPLETO: es la invocación y nada más, así que tampoco cabe
    # medir aquí mismo antes de llamar al script.
    assert [linea.strip() for linea in str(aplicar["run"]).strip().splitlines()] == [
        "set -uo pipefail",
        "bash scripts/automation/sirius_apply_verdict.sh \\",
        '"$GH_REPO" "$ISSUE_NUMBER" "corrector" "${RUNNER_TEMP}/sirius_verdict.json" "$CYCLE"',
    ]
