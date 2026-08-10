"""Pruebas estructurales de ``.github/workflows/repair-sirius-work.yml``.

La puerta del corrector dejó de contar ciclos y ahora consulta la política de
convergencia (contrato §5.1). Estas pruebas fijan, sin ejecutar Actions, que el
tope fijo desapareció de verdad del workflow y que el bloqueo por falta de
convergencia sigue siendo determinista: motivo exacto, sin invocar a Claude y
sin degradar a una corrección a ciegas.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
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


def test_the_corrector_writes_a_provisional_verdict_before_working() -> None:
    """El tope duro de turnos hace inalcanzable una regla de «última acción».

    El prompt exigía escribir el veredicto como última acción. Pero el workflow
    acota al corrector con `--max-turns`, y agotarlo trabajando lo corta a mitad:
    no hay última acción, el archivo no existe y sale la parada `sin-veredicto`
    que la regla venía a evitar —la incidencia #135 otra vez—.

    Por eso el veredicto se escribe DOS veces: un `FAILED_SAFELY` provisional al
    empezar y el definitivo al terminar. Lo escribe el corrector, no el
    workflow: un veredicto sembrado por el envoltorio se publicaría como suyo
    sin que lo hubiera emitido, que es el defecto que esta automatización lleva
    trece hallazgos corrigiendo.
    """
    prompt = (REPO_ROOT / "scripts" / "automation" / "prompts" / "corrector.md").read_text(
        encoding="utf-8"
    )
    assert "PRIMERA acción" in prompt
    assert "ÚLTIMA acción" in prompt
    assert "--max-turns" in prompt
    # El provisional es una parada, nunca un éxito: si el corte llega antes de
    # sustituirlo, la incidencia se detiene en vez de declarar trabajo hecho.
    provisional = prompt[prompt.index("PRIMERA acción") : prompt.index("ÚLTIMA acción")]
    assert '"verdict": "FAILED_SAFELY"' in provisional, "el provisional debe ser una parada"
    for exito in ('"verdict": "FIXED"', "READY_FOR_REVIEW"):
        assert exito not in provisional, f"el provisional no puede declarar éxito: {exito}"
    # Y el tope de turnos existe de verdad en el workflow: si desapareciera, esta
    # regla quedaría explicando una restricción imaginaria.
    claude = _step(_load(), "Ejecutar Claude Code")
    assert "--max-turns" in str(claude["with"]["claude_args"])


def test_the_gate_stops_itself_before_its_step_timeout_kills_it() -> None:
    """Un tope de paso mata desde fuera; no produce un desenlace.

    `timeout-minutes: 8` corta la shell sin que llegue a escribir `valid=false`
    ni a publicar una parada segura. Y como aplicar el veredicto exige
    `valid == 'true'`, ese paso tampoco corre: la incidencia se queda sin
    diagnóstico —la #135 otra vez—. El plazo interno convierte el corte en un
    desenlace: las lecturas fallan solas y caen en las paradas que ya existen.

    Y hay una trampa que el plazo por sí solo empeoraría.
    `sirius_find_pr_for_issue` y `sirius_extract_observations` se tragan los
    fallos de `gh` y devuelven vacío. Con el plazo agotado, ese vacío se
    interpretaría como «no hay ninguna PR» o «no hay observaciones» y la
    incidencia publicaría una afirmación falsa. Por eso el plazo se comprueba
    ANTES de interpretar, y por eso publicar no puede heredarlo: exigirle a la
    parada segura que ocurra en el tiempo que ya se acabó la dejaría muda.
    """
    doc = _load()
    gate = _step(doc, "Evaluar la convergencia")
    run = str(gate["run"])

    # El plazo interno existe y deja margen bajo el tope del paso.
    assert 'export SIRIUS_GH_DEADLINE="$gate_deadline"' in run
    margen = gate["timeout-minutes"] * 60 - 300
    assert margen >= 120, f"solo {margen}s para publicar la parada tras agotar el plazo"

    # Publicar lleva su PROPIO plazo, no el de lectura ya agotado ni ninguno:
    # todas las transiciones de la puerta pasan por `parada`, y ninguna llama ya
    # a `sirius_transition` directamente. Esta aserción fijaba antes el `unset`
    # que causó la incidencia #140, así que fijaba el defecto en vez de la
    # propiedad; ver los casos GATE-001..004 al final del módulo.
    assert "export SIRIUS_GH_DEADLINE=$(( $(_sirius_now) + PLAZO_PUBLICACION ))" in run
    assert "unset SIRIUS_GH_DEADLINE" not in run
    assert 'sirius_transition "$GH_REPO"' not in run
    assert run.count('parada "$GH_REPO"') >= 5

    # Y el plazo se comprueba antes de interpretar un vacío como un hecho. La
    # guardia tiene que ir en la línea INMEDIATAMENTE posterior a cada lectura:
    # buscarla "en algún sitio después" dejaría pasar una guardia colocada tras
    # la interpretación, que es justo lo que no sirve.
    guardia = '[ "$(_sirius_now)" -lt "$gate_deadline" ] || sin_tiempo'
    for llamada in (
        "mapfile -t pr_numbers < <(sirius_find_pr_for_issue",
        'observations="$(sirius_extract_observations',
    ):
        siguiente = run.index("\n", run.index(llamada)) + 1
        assert run[siguiente:].startswith(guardia), (
            f"un vacío de `{llamada}` se interpretaría como un hecho sin comprobar el plazo"
        )
    assert "puerta-sin-tiempo" in run


def test_job_timeout_covers_every_bounded_step_plus_margin() -> None:
    """El corrector no puede consumir el presupuesto entero del job.

    El veredicto provisional del prompt cubre el corte por `--max-turns`, pero
    no el otro camino: si el corrector agota los minutos del JOB, GitHub lo
    cancela y el paso que aplica el veredicto no llega a leer nada. La
    incidencia se quedaba en `sirius:repairing` sin parada ni diagnóstico —la
    #135 otra vez, y una regla que no se puede cumplir porque alguien tiene que
    llegar a leerla—.

    Misma regla que `review-sirius-work.yml`: cada paso que puede tardar declara
    su tope, y el del job cubre la suma más margen para los pasos deterministas
    cortos. Así, agotar el tiempo del corrector se traduce SIEMPRE en un
    veredicto aplicado, nunca en una cancelación.

    Y el presupuesto solo es real si TODOS los pasos están acotados. Con solo
    dos topes la cuenta salía —30 + 5 sobre 45— pero no reservaba nada: la
    puerta lee comentarios, localiza la PR y extrae las observaciones con
    varios `gh` y sus reintentos, sin `SIRIUS_GH_DEADLINE` ni tope de paso, así
    que podía comerse el margen y dejar que el job caducara durante el
    corrector exactamente igual que antes.
    """
    doc = _load()
    pasos = _steps(doc)
    sin_tope = [str(s.get("name")) for s in pasos if "timeout-minutes" not in s]
    assert not sin_tope, f"un paso sin tope puede comerse el margen de los demás: {sin_tope}"

    job = doc["jobs"]["repair"]["timeout-minutes"]
    acotados = [s["timeout-minutes"] for s in pasos]
    assert job >= sum(acotados) + 5, f"suma {sum(acotados)} sin margen bajo el job {job}"

    # El del corrector tiene que ser ESTRICTAMENTE menor que el del job: si
    # coincidieran, el job podría caducar durante ese mismo paso.
    assert _step(doc, "Ejecutar Claude Code")["timeout-minutes"] < job
    # Y aplicar el veredicto necesita margen propio: es el paso que convierte
    # cualquier desenlace en un estado visible de la incidencia.
    assert _step(doc, "Aplicar el veredicto")["timeout-minutes"] >= 5


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

    Lo que esta prueba NO afirma: que ningún paso calcule nada, ni que el
    publicador se comporte. Afirma exactamente una cosa: que EL WORKFLOW no
    puede inyectar texto en el comentario de la parada. La otra mitad —que el
    publicador tampoco lo añada por su cuenta— la fija
    `test_the_stop_publishes_the_link_and_nothing_else`, que compara el cuerpo
    entero de una parada bajo Actions. Hicieron falta las dos: fijar solo este
    lado dejaba reintroducir la medida dentro de `sirius_apply_verdict.sh`,
    que es quien construye el comentario.
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


# --------------------------------------------------------------------------- #
# La parada segura publica ACOTADA (incidencia #140)
# --------------------------------------------------------------------------- #

# `parada()` hacía `unset SIRIUS_GH_DEADLINE` antes de publicar. El razonamiento
# original era correcto a medias —publicar no puede heredar un plazo agotado—
# pero la conclusión no: heredar un plazo agotado deja la parada MUDA, mientras
# que soltarlo la deja COLGADA hasta que el tope externo del paso mata la shell
# sin escribir `valid=false` ni publicar transición alguna. Es peor: al menos la
# muda falla rápido y visible. Tocaba fijar un plazo NUEVO, no quitar la cota.

_SIMULADOR_GH = """#!/usr/bin/env bash
printf '%s\\n' "${SIRIUS_GH_DEADLINE:-VACIO}" >>"$SIRIUS_TEST_PLAZOS"
exit 0
"""

_LIBRETO = """set -uo pipefail
_sirius_now() {{ date +%s; }}
sirius_transition() {{ gh api /simulado >/dev/null; }}
{bloque}
export SIRIUS_GH_DEADLINE={plazo_previo}
parada repo 1 marcador cuerpo etiqueta color desc noclose previa
"""


def _guion_de_la_puerta() -> str:
    return str(_step(_load(), "Evaluar la convergencia")["run"])


def _bloque_de_parada() -> str:
    """Extrae del YAML la `parada()` REAL, en vez de copiarla aquí.

    Una copia se queda vieja en silencio y la prueba pasaría a medir un texto
    que ya no se ejecuta: es la forma más común de prueba vacua en este
    repositorio.
    """
    guion = _guion_de_la_puerta()
    inicio = guion.index("PLAZO_PUBLICACION=")
    fin = guion.index("\n\n", guion.index("parada() {"))
    return guion[inicio:fin]


def _ejecuta_parada(tmp_path: Path, plazo_previo: str) -> list[str]:
    """Ejecuta la parada real con un `gh` simulado; devuelve los plazos vistos."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_SIMULADOR_GH, encoding="utf-8")
    gh.chmod(0o755)

    plazos = tmp_path / "plazos.txt"
    libreto = tmp_path / "correr.sh"
    libreto.write_text(
        _LIBRETO.format(bloque=_bloque_de_parada(), plazo_previo=plazo_previo),
        encoding="utf-8",
    )

    entorno = dict(os.environ)
    entorno["PATH"] = f"{bin_dir}{os.pathsep}{entorno['PATH']}"
    entorno["SIRIUS_TEST_PLAZOS"] = str(plazos)
    resultado = subprocess.run(
        ["bash", str(libreto)],
        capture_output=True,
        text=True,
        env=entorno,
        check=False,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr
    return plazos.read_text(encoding="utf-8").split() if plazos.exists() else []


def test_gate_001_la_parada_publica_con_el_plazo_de_lectura_agotado(tmp_path: Path) -> None:
    # El caso que motiva la incidencia: el plazo de lectura ya expiró y aun así
    # la parada tiene que llegar a publicar.
    assert _ejecuta_parada(tmp_path, plazo_previo="1"), (
        "la parada no llegó a invocar gh: no se publicó nada"
    )


def test_gate_002_la_publicacion_nunca_corre_sin_cota(tmp_path: Path) -> None:
    ahora = int(time.time())
    for plazo in _ejecuta_parada(tmp_path, plazo_previo="1"):
        assert plazo != "VACIO", "la parada publicó sin ninguna cota de tiempo"
        assert int(plazo) > ahora, "la parada publicó con un plazo ya expirado"


def test_gate_003_el_plazo_de_publicacion_cabe_bajo_el_tope_del_paso() -> None:
    puerta = _step(_load(), "Evaluar la convergencia")
    guion = str(puerta["run"])
    lectura_m = re.search(r"gate_deadline=\$\(\( \$\(_sirius_now\) \+ (\d+) \)\)", guion)
    publicacion_m = re.search(r"PLAZO_PUBLICACION=(\d+)", guion)
    # Sin los dos plazos la comparación no mide nada: se falla diciéndolo, en
    # vez de reventar con un AttributeError que oculta la causa.
    assert lectura_m and publicacion_m, "no encuentro los dos plazos en el guion de la puerta"
    lectura = int(lectura_m.group(1))
    publicacion = int(publicacion_m.group(1))
    tope = puerta["timeout-minutes"] * 60
    assert lectura + publicacion <= tope - 30, (
        f"lectura {lectura}s + publicación {publicacion}s no cabe con margen en {tope}s"
    )


def test_gate_004_la_parada_no_suelta_el_plazo() -> None:
    # El patrón exacto que causó el defecto no puede volver por inercia.
    guion = _guion_de_la_puerta()
    assert "unset SIRIUS_GH_DEADLINE" not in guion, (
        "soltar el plazo deja la publicación sin cota (incidencia #140)"
    )
    assert "export SIRIUS_GH_DEADLINE=$(( $(_sirius_now) + PLAZO_PUBLICACION ))" in guion
