"""Pruebas estructurales de ``.github/workflows/review-sirius-work.yml``.

El workflow de revisión es el orquestador de la revisión dual (contrato
operativo §4, v1.4). Estas pruebas validan, sin ejecutar Actions, las
propiedades que el contrato exige: sintaxis YAML, condiciones de la bandera
``SIRIUS_CODEX_REVIEW_ENABLED``, tokens correctos por paso,
``continue-on-error`` solo donde hay tratamiento posterior seguro, ``always()``
en el paso que convierte fallos en veredictos estructurados, y la ausencia de
un camino que aplique el veredicto de Claude sin esperar a Codex cuando el
modo dual está activo.

Cubren además el prompt del revisor (``scripts/automation/prompts/reviewer.md``),
que el workflow inserta literalmente: las reglas que evitan que una ronda muera
sin veredicto —provisional al empezar, prohibición de esperar nada, y entorno
acotado— son parte de la misma garantía y se comprueban contra el workflow y
contra la lista real de permisos, no por sí solas.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "review-sirius-work.yml"
COLLECTOR = REPO_ROOT / "scripts" / "automation" / "sirius_codex_review.py"
REVIEWER_PROMPT = REPO_ROOT / "scripts" / "automation" / "prompts" / "reviewer.md"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def _reviewer_prompt() -> str:
    return REVIEWER_PROMPT.read_text(encoding="utf-8")


def _permissions() -> dict[str, list[str]]:
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    permissions: dict[str, list[str]] = settings["permissions"]
    return permissions


def _collector_module() -> Any:
    """Importa el recolector para contrastar sus topes con los del workflow."""
    name = "sirius_codex_review_for_workflow_tests"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, COLLECTOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def test_job_declares_every_scope_its_gate_actually_uses() -> None:
    # Declarar un bloque `permissions` explícito deja en `none` todo alcance no
    # listado. El gate lee `commits/<sha>/check-runs`, que exige `checks: read`:
    # sin esa línea la lectura da 403 y TODA ronda —en ambos modos— muere en la
    # parada segura `quality-sin-marca`.
    doc = _load()
    permissions = doc["permissions"]
    gate_run = _step(doc, "Localizar la PR")["run"]
    if "check-runs" in gate_run:
        assert permissions.get("checks") == "read"


def test_concurrency_group_prevents_parallel_rounds() -> None:
    doc = _load()
    concurrency = doc["concurrency"]
    assert "sirius-review-" in concurrency["group"]
    assert concurrency["cancel-in-progress"] is False


def test_job_timeout_covers_every_bounded_step_plus_margin() -> None:
    # El presupuesto del job debe cubrir la SUMA de todos los pasos acotados —
    # revisor Claude, recolección de Codex, agregación y aplicación — más
    # margen para los pasos deterministas cortos. Si el job muriera durante la
    # espera, el recolector no llegaría a emitir su FAILED_SAFELY; si muriera
    # después, el veredicto agregado no llegaría a aplicarse.
    # Desde ADR-152 hay un quinto paso acotado: la congelación de
    # `scripts/automation` de `main` (1 min), que no puede quedar sin plazo
    # porque sin la copia no hay veredicto, y un paso colgado ahí se comería el
    # presupuesto de los cuatro que sí pueden tardar.
    doc = _load()
    bounded = [step["timeout-minutes"] for step in _steps(doc) if "timeout-minutes" in step]
    assert len(bounded) == 5, (
        "los cuatro pasos que pueden tardar y la congelación deben declarar su timeout"
    )
    assert _job(doc)["timeout-minutes"] >= sum(bounded) + 5


def test_aggregation_and_application_have_a_guaranteed_budget() -> None:
    # Margen garantizado, no meramente probable: ambos pasos declaran su propio
    # timeout y quedan dentro del presupuesto del job.
    doc = _load()
    assert _step(doc, "Agregar los veredictos")["timeout-minutes"] >= 5
    assert _step(doc, "Aplicar el veredicto")["timeout-minutes"] >= 5


def test_collect_step_timeout_exceeds_the_collector_hard_cap() -> None:
    # El tope interno de espera del recolector (25 min por defecto) debe caber
    # holgadamente dentro del timeout del paso, para que el resultado
    # estructurado se escriba siempre antes de que el paso expire.
    doc = _load()
    module = _collector_module()
    cap_minutes = module.DEFAULT_MAX_TIMEOUT_SECONDS / 60
    assert _step(doc, "Recoger el resultado")["timeout-minutes"] > cap_minutes


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
        # La ronda forma parte de la identidad del disparador en ambos pasos.
        assert '--round-id "$ROUND_ID"' in step["run"]
        assert step["env"]["ROUND_ID"] == "${{ github.run_id }}"
    assert "sirius_aggregate_reviews.py" in aggregate["run"]
    assert "--mode dual" in aggregate["run"]
    assert '--expected-head "$HEAD_SHA"' in aggregate["run"]


def test_gate_reads_the_authoritative_quality_completion_mark() -> None:
    # El instante en que Quality terminó se lee de la API de check-runs, no de
    # un texto de la incidencia (editable): es lo que ancla la ronda.
    doc = _load()
    gate = _step(doc, "Localizar la PR")
    assert "check-runs" in gate["run"]
    assert "quality_completed_at=" in gate["run"]
    assert "quality-sin-marca" in gate["run"]


def test_trigger_step_receives_the_quality_completion_mark() -> None:
    doc = _load()
    trigger = _step(doc, "Solicitar la revisión de Codex")
    assert trigger["env"]["QUALITY_COMPLETED_AT"] == (
        "${{ steps.gate.outputs.quality_completed_at }}"
    )
    assert '--quality-completed-at "$QUALITY_COMPLETED_AT"' in trigger["run"]


def test_the_quality_mark_is_only_required_in_dual_mode() -> None:
    # La marca de Quality solo la consume el disparador de Codex. Exigirla
    # también con la bandera apagada dejaba que un 403 sobre `check-runs` —o un
    # cambio de nombre del check— matara una ronda de revisión solo-Claude que
    # antes de esta funcionalidad habría funcionado: la bandera dejaría de ser
    # reversible de verdad, que es la garantía por la que existe.
    run = _step(_load(), "Localizar la PR")["run"]
    quality_block = run[run.index("quality_completed_at=") :]
    guard = run.rindex('if [ "$dual" = "true" ]; then', 0, run.index("quality-sin-marca"))
    assert guard > 0
    assert "quality-sin-marca" in quality_block
    # La verificación de head, que sí es del contrato §4.1, queda FUERA del
    # condicional: aplica a los dos modos.
    assert run.index("head-obsoleto") < guard


def test_the_checks_scope_is_declared_for_the_check_runs_read() -> None:
    # Un bloque `permissions` explícito deja en `none` todo alcance no listado.
    doc = _load()
    assert doc["permissions"]["checks"] == "read"


# --- El prompt del revisor -------------------------------------------------
#
# Las tres reglas siguientes existen porque tres rondas de la incidencia #177
# murieron sin veredicto. No son estilo: cada una cierra un camino por el que la
# revisión terminó en silencio, y el silencio del revisor detiene la incidencia
# entera esperando a una persona.


def test_the_workflow_actually_feeds_the_reviewer_prompt() -> None:
    """El prompt que validan las pruebas de abajo tiene que ser alcanzable.

    Sin esta comprobación, las tres que siguen podrían validar un archivo que el
    workflow ya no inserta: pasarían en verde sobre un prompt muerto.

    Desde C3 (incidencia #333) el prompt ya no está clavado a fuego: se elige por
    el campo ``Perfil:`` del cuerpo, para que una orden de documentación no
    ejecute la vara del código. Así que se comprueban las tres cosas que sostienen
    esa elección, no una cadena literal.
    """
    run = _step(_load(), "Preparar instrucciones")["run"]

    # Desde H-28 (auditoría #396) la elección vive en el manifiesto: el workflow
    # invoca al resolver con el carril de revisión, y que reviewer.md y
    # revisor-documental.md sigan alcanzables (y con el texto registrado) lo
    # garantizan las pruebas del manifiesto en test_resolver_prompt.py.
    assert "python3 scripts/automation/resolver_prompt.py --carril revision" in run, (
        "el prompt del revisor tiene que salir del manifiesto versionado, no de rutas a fuego"
    )
    assert 'cat "$PROMPT_ROL"' in run, (
        "el prompt elegido tiene que insertarse de verdad, no solo nombrarse"
    )


def test_un_perfil_no_reconocido_no_cae_en_un_prompt_por_defecto() -> None:
    """Elegir mal el prompt produce trabajo que PARECE hecho y no lo está.

    Un repliegue silencioso a `reviewer.md` revisaría un documento con la vara
    del código y publicaría su veredicto como bueno. Cuesta más que un workflow
    en rojo, que se arregla en un minuto y se ve.
    """
    run = _step(_load(), "Preparar instrucciones")["run"]

    # El mensaje ::error:: vive ahora en el resolver (visto en rojo en
    # test_resolver_prompt.py con rol@N desconocido); al workflow le toca no
    # tragarse ese fallo: si el resolver no entrega ruta, el paso muere.
    assert "if ! PROMPT_ROL=$(python3 scripts/automation/resolver_prompt.py" in run, (
        "la ruta del prompt tiene que venir del resolver, comprobando su salida"
    )
    assert "exit 1" in run, (
        "un perfil que el manifiesto no reconoce tiene que salir en rojo, no elegir "
        "un prompt por su cuenta"
    )


def test_el_cuerpo_de_la_incidencia_no_se_interpola_en_el_script() -> None:
    """El cuerpo lo escribe quien abre la incidencia: es dato, nunca código.

    Un ``${{ github.event.issue.body }}`` dentro del ``run:`` se sustituye antes
    de que bash lea nada, así que un cuerpo con acentos graves o ``$(...)``
    ejecutaría lo que llevara dentro con los permisos del trabajo. Por ``env:``
    no puede.
    """
    paso = _step(_load(), "Preparar instrucciones")

    assert "${{ github.event.issue.body }}" not in paso["run"], (
        "el cuerpo de la incidencia no puede interpolarse dentro del script"
    )
    assert "ISSUE_BODY" in paso.get("env", {}), (
        "el cuerpo tiene que viajar por `env:`, que es lo que lo convierte en dato"
    )


def test_the_reviewer_writes_a_provisional_verdict_before_reviewing() -> None:
    """El tope duro de turnos hace inalcanzable una regla de «última acción».

    El prompt solo exigía el veredicto al final. Pero el paso acota al revisor
    con `--max-turns` y con `timeout-minutes`, y agotar cualquiera de los dos lo
    corta a mitad: no hay última acción, el archivo no existe y la ronda muere en
    la parada `sin-veredicto` —exactamente lo que ocurrió en el run 31963233730—.

    Por eso el veredicto se escribe DOS veces: un `FAILED_SAFELY` provisional al
    empezar y el definitivo al terminar. Lo escribe el revisor, no el workflow:
    un veredicto sembrado por el envoltorio se publicaría como suyo sin que lo
    hubiera emitido.
    """
    prompt = _reviewer_prompt()
    assert "PRIMERA acción" in prompt
    assert "ÚLTIMA acción" in prompt
    assert "--max-turns" in prompt
    # El provisional es una parada, nunca un resultado de revisión: si el corte
    # llega antes de sustituirlo, la incidencia se detiene en vez de pronunciarse
    # sobre una PR que nadie llegó a auditar.
    provisional = prompt[prompt.index("PRIMERA acción") : prompt.index("ÚLTIMA acción")]
    assert '"verdict": "FAILED_SAFELY"' in provisional, "el provisional debe ser una parada"
    for resultado in ("REVIEW_APPROVED", "CHANGES_REQUESTED"):
        assert resultado not in provisional, f"el provisional no puede pronunciarse: {resultado}"
    # Y ambos topes existen de verdad en el workflow: si desaparecieran, esta
    # regla quedaría explicando una restricción imaginaria.
    claude = _step(_load(), "Ejecutar Claude Code")
    assert "--max-turns" in str(claude["with"]["claude_args"])
    assert claude["timeout-minutes"] > 0


def test_the_reviewer_is_told_that_nobody_will_answer_and_must_not_wait() -> None:
    """La causa real del corte de #177: el modelo creyó que la conversación seguía.

    Terminó el turno con «Standing by for the three background review agents to
    report back before writing the final verdict» y `terminal_reason: completed`.
    No fue el tope de turnos ni el de tiempo: 106 s de 30 min. El runner mató los
    agentes al cerrar el turno y no quedó ningún veredicto.
    """
    prompt = _reviewer_prompt()
    seccion = prompt[prompt.index("Nadie te va a contestar") :]
    assert "segundo plano" in seccion
    # La prohibición cubre expresamente los subagentes, que es por donde se
    # perdió esta ronda: si se usan, su resultado se recoge en el mismo turno.
    assert "No lances subagentes en segundo plano" in seccion
    assert "dentro de este mismo turno" in seccion
    # Quedarse esperando no es una espera: es el final de la ronda, y su
    # desenlace correcto es un fallo seguro con diagnóstico.
    assert "FAILED_SAFELY" in seccion
    # La evidencia literal viaja con la regla: sin ella es una opinión.
    assert "Standing by for the three background review agents" in seccion
    assert "31963233730" in seccion


def test_the_bounded_environment_section_matches_the_real_permission_list() -> None:
    """Una instrucción de entorno que mienta gasta el turno en denegaciones.

    En el run 31963233730 el revisor perdió tres órdenes: dos bloques enteros por
    incluir `git merge-base` —capturado por el patrón `git merge*` de la lista de
    denegación— y un intento de instalar `uv` con `curl`. Esta prueba ata el
    texto a la lista real: lo que el prompt prohíbe está denegado de verdad, y lo
    que recomienda está permitido de verdad.
    """
    prompt = _reviewer_prompt()
    seccion = prompt[prompt.index("El entorno es acotado") : prompt.index("## Veredicto final")]
    permissions = _permissions()
    deny, allow = permissions["deny"], permissions["allow"]

    assert "no instales herramientas ni dependencias" in seccion
    for prohibida, regla in (("`curl`", "Bash(curl*)"), ("`wget`", "Bash(wget*)")):
        assert prohibida in seccion
        assert regla in deny, f"el prompt prohíbe {prohibida} pero la lista no lo deniega"

    for herramienta, regla in (
        ("`gh pr diff`", "Bash(gh pr diff*)"),
        ("`gh pr view`", "Bash(gh pr view*)"),
        ("`gh api`", "Bash(gh api*)"),
        ("`git diff`", "Bash(git diff *)"),
        ("`git log`", "Bash(git log *)"),
        ("`git show`", "Bash(git show *)"),
    ):
        assert herramienta in seccion
        assert regla in allow, f"el prompt recomienda {herramienta} pero no está permitida"
        assert regla not in deny

    # `git merge-base` se nombra porque su denegación no es evidente: la lista no
    # menciona esa orden, la captura por prefijo.
    assert "git merge-base" in seccion
    assert "Bash(git merge*)" in deny
    # Quality en verde es la precondición de esta fase; reconstruir el entorno de
    # CI es trabajo ya hecho por otro paso.
    assert "reconstruir el entorno de CI" in seccion
    # Y la única salida cuando algo falta es adaptarse o parar, nunca improvisar.
    assert "FAILED_SAFELY" in seccion
