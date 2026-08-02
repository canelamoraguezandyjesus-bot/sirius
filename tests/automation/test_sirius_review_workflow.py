"""Pruebas estructurales de ``.github/workflows/review-sirius-work.yml``.

El workflow de revisión es el orquestador de la revisión dual (contrato
operativo §4, v1.4). Estas pruebas validan, sin ejecutar Actions, las
propiedades que el contrato exige: sintaxis YAML, condiciones de la bandera
``SIRIUS_CODEX_REVIEW_ENABLED``, tokens correctos por paso,
``continue-on-error`` solo donde hay tratamiento posterior seguro, ``always()``
en el paso que convierte fallos en veredictos estructurados, y la ausencia de
un camino que aplique el veredicto de Claude sin esperar a Codex cuando el
modo dual está activo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "review-sirius-work.yml"


def _load() -> dict[Any, Any]:
    # La clave YAML `on` se decodifica como el booleano True (YAML 1.1), así
    # que el documento se tipa con claves Any a propósito.
    with WORKFLOW.open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    assert isinstance(doc, dict)
    return doc


def _job(doc: dict[str, Any]) -> dict[str, Any]:
    jobs = doc["jobs"]
    assert list(jobs) == ["review"], "debe seguir existiendo un único job de revisión"
    job: dict[str, Any] = jobs["review"]
    return job


def _steps(doc: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = _job(doc)["steps"]
    return steps


def _step(doc: dict[str, Any], fragment: str) -> dict[str, Any]:
    for step in _steps(doc):
        if fragment in str(step.get("name") or ""):
            return step
    raise AssertionError(f"paso no encontrado: {fragment!r}")


def _step_index(doc: dict[str, Any], fragment: str) -> int:
    for index, step in enumerate(_steps(doc)):
        if fragment in str(step.get("name") or ""):
            return index
    raise AssertionError(f"paso no encontrado: {fragment!r}")


def test_yaml_is_valid_and_triggered_by_review_requested() -> None:
    doc = _load()
    trigger = doc.get("on") or doc.get(True)
    assert trigger == {"issues": {"types": ["labeled"]}}
    assert _job(doc)["if"] == "github.event.label.name == 'sirius:review-requested'"


def test_reviewer_job_keeps_read_only_contents_permission() -> None:
    doc = _load()
    assert doc["permissions"]["contents"] == "read"
    assert doc["permissions"]["pull-requests"] == "read"


def test_concurrency_group_prevents_parallel_rounds() -> None:
    doc = _load()
    concurrency = doc["concurrency"]
    assert "sirius-review-" in concurrency["group"]
    assert concurrency["cancel-in-progress"] is False


def test_job_timeout_covers_claude_plus_codex_wait() -> None:
    doc = _load()
    assert _job(doc)["timeout-minutes"] >= 45


def test_gate_reads_flag_from_repository_variable() -> None:
    doc = _load()
    gate = _step(doc, "Localizar la PR")
    assert gate["env"]["SIRIUS_CODEX_REVIEW_ENABLED"] == ("${{ vars.SIRIUS_CODEX_REVIEW_ENABLED }}")
    # Solo el valor exacto `true` activa el modo dual; ausente o cualquier otro
    # valor conserva el flujo vigente de revisión solo Claude.
    assert '= "true"' in gate["run"]
    assert "dual=false" in gate["run"].replace('"', "")


def test_gate_verifies_head_against_last_quality_head() -> None:
    doc = _load()
    gate = _step(doc, "Localizar la PR")
    assert "sirius_extract_sha" in gate["run"]
    assert "head-obsoleto" in gate["run"]
    assert "head_sha=" in gate["run"]


def test_codex_steps_run_only_in_dual_mode_and_after_gate() -> None:
    doc = _load()
    for fragment in [
        "Solicitar la revisión de Codex",
        "Recoger el resultado",
        "Agregar los veredictos",
    ]:
        step = _step(doc, fragment)
        condition = step["if"]
        assert "steps.gate.outputs.valid == 'true'" in condition
        assert "steps.gate.outputs.dual == 'true'" in condition


def test_claude_step_runs_in_both_modes() -> None:
    doc = _load()
    claude = _step(doc, "Ejecutar Claude Code")
    assert claude["if"] == "steps.gate.outputs.valid == 'true'"
    assert "dual" not in claude["if"]


def test_codex_trigger_uses_bot_pat_and_runs_before_claude() -> None:
    doc = _load()
    trigger = _step(doc, "Solicitar la revisión de Codex")
    assert trigger["env"]["GH_TOKEN"] == "${{ secrets.SIRIUS_BOT_TOKEN }}"
    # Concurrencia real: el disparador se publica antes de ejecutar a Claude,
    # y el resultado se recoge después.
    assert _step_index(doc, "Solicitar la revisión de Codex") < _step_index(
        doc, "Ejecutar Claude Code"
    )
    assert _step_index(doc, "Ejecutar Claude Code") < _step_index(doc, "Recoger el resultado")
    assert _step_index(doc, "Recoger el resultado") < _step_index(doc, "Agregar los veredictos")
    assert _step_index(doc, "Agregar los veredictos") < _step_index(doc, "Aplicar el veredicto")


def test_codex_collect_uses_read_only_token_and_configurable_timeout() -> None:
    doc = _load()
    collect = _step(doc, "Recoger el resultado")
    assert collect["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert collect["env"]["SIRIUS_CODEX_REVIEW_TIMEOUT_SECONDS"] == (
        "${{ vars.SIRIUS_CODEX_REVIEW_TIMEOUT_SECONDS }}"
    )


def test_continue_on_error_only_where_failure_is_handled_later() -> None:
    doc = _load()
    tolerated = {
        "Solicitar la revisión de Codex (modo dual)",
        "Ejecutar Claude Code (revisor)",
        "Recoger el resultado de Codex (modo dual)",
        "Agregar los veredictos (modo dual)",
    }
    for step in _steps(doc):
        name = str(step.get("name") or "")
        if name in tolerated:
            # Sus fallos terminan en un veredicto estructurado (archivo ausente
            # → parada segura en el paso determinista), nunca en éxito tácito.
            assert step.get("continue-on-error") is True, name
        else:
            assert step.get("continue-on-error") is None, name


def test_apply_step_always_runs_and_uses_aggregated_verdict_in_dual_mode() -> None:
    doc = _load()
    apply_step = _step(doc, "Aplicar el veredicto")
    assert apply_step["if"] == "always() && steps.gate.outputs.valid == 'true'"
    assert apply_step["env"]["GH_TOKEN"] == "${{ secrets.SIRIUS_BOT_TOKEN }}"
    assert apply_step["env"]["DUAL_MODE"] == "${{ steps.gate.outputs.dual }}"
    run = apply_step["run"]
    # En modo dual solo se aplica el veredicto agregado: no existe un camino
    # que aplique el veredicto de Claude sin haber esperado a Codex.
    assert "sirius_aggregated_verdict.json" in run
    assert 'if [ "${DUAL_MODE}" = "true" ]' in run
    assert run.index("sirius_aggregated_verdict.json") < run.index("sirius_verdict.json")
    assert "sirius_apply_verdict.sh" in run


def test_claude_reviewer_keeps_read_only_tools() -> None:
    doc = _load()
    claude = _step(doc, "Ejecutar Claude Code")
    claude_args = claude["with"]["claude_args"]
    assert '--allowedTools "Bash,Read,Grep,Glob"' in claude_args
    assert "Write" not in claude_args
    assert "Edit" not in claude_args


def test_prompt_context_pins_the_expected_head() -> None:
    doc = _load()
    prompt = _step(doc, "Preparar instrucciones")
    assert "HEAD_SHA" in prompt["run"]
    assert prompt["env"]["HEAD_SHA"] == "${{ steps.gate.outputs.head_sha }}"


def test_codex_scripts_receive_expected_head_and_state_file() -> None:
    doc = _load()
    trigger = _step(doc, "Solicitar la revisión de Codex")
    collect = _step(doc, "Recoger el resultado")
    aggregate = _step(doc, "Agregar los veredictos")
    for step in (trigger, collect):
        assert "sirius_codex_review.py" in step["run"]
        assert "sirius_codex_state.json" in step["run"]
        assert '--head "$HEAD_SHA"' in step["run"]
    assert "sirius_aggregate_reviews.py" in aggregate["run"]
    assert "--mode dual" in aggregate["run"]
    assert '--expected-head "$HEAD_SHA"' in aggregate["run"]
