"""Invariantes comunes a TODOS los prompts de rol de la automatización.

Los tres roles (implementador, revisor, corrector) se ejecutan sin interlocutor
dentro de un runner de GitHub Actions, con el mismo perímetro de permisos y la
misma consecuencia si terminan sin veredicto: la incidencia se detiene esperando
a una persona. Las reglas que evitan eso son idénticas para los tres, pero viven
copiadas en tres ficheros, así que olvidar una es posible — y ya pasó tres veces,
en tres roles distintos y por el mismo motivo:

    corrector    run 31953500564  «Espero a que termine el pytest en segundo plano»
    revisor      run 31963233730  «Standing by for the three background review agents»
    implementador run 31985897583 «I'm waiting for the background pytest run to finish»

Los tres con ``terminal_reason: completed``: ninguno se quedó sin turnos ni sin
tiempo; los tres creyeron que la conversación seguía.

Extraer un fragmento común obligaría a tocar los tres workflows que construyen el
prompt, y ADR-002 lo prohíbe. Estas pruebas son la mitigación que sí cabe: en vez
de una lista escrita a mano, **recorren el directorio de prompts**, así que un
cuarto rol que se añada mañana no puede nacer sin las reglas. La omisión deja de
depender de que alguien se acuerde.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "scripts" / "automation" / "prompts"

# El directorio ES la lista. No se enumeran los ficheros a mano a propósito: una
# lista escrita a mano habría que acordarse de ampliarla, que es exactamente el
# olvido que estas pruebas existen para hacer imposible.
PROMPTS = sorted(PROMPTS_DIR.glob("*.md"))

# Valores de `verdict` que afirman que el trabajo salió bien, en cualquiera de los
# tres roles. Ninguno puede aparecer en el veredicto provisional.
SUCCESS_VERDICTS = ("READY_FOR_REVIEW", "REVIEW_APPROVED", "CHANGES_REQUESTED", "FIXED")


def _flat(texto: str) -> str:
    """Texto con los espacios en blanco colapsados a uno solo.

    Los prompts son markdown ajustado a 80 columnas, así que una frase cae
    partida por un salto de línea según dónde toque. Comparar contra el texto
    crudo haría que una regla presente fallara solo por haberse reajustado el
    párrafo — y eso enseñaría a desactivar la prueba en vez de a leerla.
    """
    return " ".join(texto.split())


def test_hay_prompts_que_comprobar() -> None:
    """Si el glob no encuentra nada, las demás pruebas pasarían en vacío.

    Un `parametrize` sobre una lista vacía no falla: simplemente no ejecuta nada.
    Sin esta comprobación, mover o renombrar el directorio dejaría toda la
    familia sin vigilancia y en verde.
    """
    assert PROMPTS, f"no se encontró ningún prompt de rol en {PROMPTS_DIR}"
    assert len(PROMPTS) >= 3, (
        "faltan prompts: hay al menos tres roles (implementador, revisor, corrector)"
    )


@pytest.mark.parametrize("prompt_path", PROMPTS, ids=lambda p: p.name)
def test_todo_rol_escribe_un_veredicto_provisional_al_empezar(prompt_path: Path) -> None:
    """El tope de turnos hace inalcanzable una regla de «última acción» sola.

    Si el rol agota turnos o tiempo trabajando, no hay última acción: lo cortan a
    mitad, el archivo de veredicto no existe y la ronda muere en `sin-veredicto`
    —silencio, no diagnóstico—. Por eso el veredicto se escribe DOS veces, y el
    provisional tiene que ser una PARADA: si el corte llega antes de sustituirlo,
    la incidencia se detiene en vez de declarar hecho lo que no lo está.
    """
    prompt = _flat(prompt_path.read_text(encoding="utf-8"))
    assert "PRIMERA acción" in prompt
    assert "ÚLTIMA acción" in prompt

    provisional = prompt[prompt.index("PRIMERA acción") : prompt.index("ÚLTIMA acción")]
    assert '"verdict": "FAILED_SAFELY"' in provisional, "el provisional debe ser una parada"
    for exito in SUCCESS_VERDICTS:
        assert exito not in provisional, f"el provisional no puede declarar éxito: {exito}"


@pytest.mark.parametrize("prompt_path", PROMPTS, ids=lambda p: p.name)
def test_todo_rol_tiene_prohibido_terminar_el_turno_esperando_algo(prompt_path: Path) -> None:
    """La causa real de las tres rondas perdidas, en los tres roles.

    Cubre expresamente los subagentes: en el revisor el vehículo del fallo no fue
    un comando sino tres agentes en segundo plano, así que una regla que solo
    hablara de comandos no habría cubierto el caso observado.
    """
    prompt = _flat(prompt_path.read_text(encoding="utf-8"))
    assert "Nadie te va a contestar" in prompt, "falta la sección anti-espera"
    seccion = prompt[prompt.index("Nadie te va a contestar") :]

    assert "segundo plano" in seccion
    assert "No lances subagentes en segundo plano" in seccion
    assert "dentro de este mismo turno" in seccion
    # El desenlace correcto de «no me cabe en el turno» es una parada con
    # diagnóstico, nunca una espera.
    assert "FAILED_SAFELY" in seccion


@pytest.mark.parametrize("prompt_path", PROMPTS, ids=lambda p: p.name)
def test_todo_rol_sabe_que_el_entorno_es_acotado(prompt_path: Path) -> None:
    """Una instrucción de entorno que falte se paga en denegaciones.

    Dos de los tres roles intentaron instalarse `uv` con `curl` y perdieron las
    órdenes: el revisor en el run 31963233730 y el implementador en el 31985897583.
    """
    prompt = _flat(prompt_path.read_text(encoding="utf-8"))
    assert "El entorno es acotado" in prompt, "falta la sección de entorno acotado"
    seccion = prompt[prompt.index("El entorno es acotado") :]

    assert "no instales herramientas ni dependencias" in seccion
    assert "`curl`" in seccion
    assert "`wget`" in seccion
    # La única salida cuando falta algo es adaptarse o parar, nunca improvisar.
    assert "FAILED_SAFELY" in seccion


@pytest.mark.parametrize("prompt_path", PROMPTS, ids=lambda p: p.name)
def test_lo_que_los_prompts_prohiben_esta_denegado_de_verdad(prompt_path: Path) -> None:
    """El texto no puede mentir sobre el perímetro real.

    Si el prompt prohibiera algo que en realidad está permitido, estaría
    estrechando el trabajo sin motivo; si permitiera algo denegado, el rol
    gastaría el turno en denegaciones. Se ata a la lista real.
    """
    import json

    permissions = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))[
        "permissions"
    ]
    prompt = _flat(prompt_path.read_text(encoding="utf-8"))

    if "`curl`" in prompt:
        assert "Bash(curl*)" in permissions["deny"]
    if "`wget`" in prompt:
        assert "Bash(wget*)" in permissions["deny"]


# Workflow que ejecuta cada rol. Si el prompt promete que el entorno viene
# preparado, es ESE workflow el que tiene que prepararlo.
WORKFLOW_DE_CADA_ROL = {
    "implementer.md": "implement-sirius-work.yml",
    "corrector.md": "repair-sirius-work.yml",
    "reviewer.md": "review-sirius-work.yml",
}

PROMESA_DE_ENTORNO = "El workflow ya te ha preparado el entorno antes de arrancarte"


@pytest.mark.parametrize("prompt_path", PROMPTS, ids=lambda p: p.name)
def test_el_prompt_que_promete_entorno_corre_donde_de_verdad_se_prepara(
    prompt_path: Path,
) -> None:
    """Una promesa sobre el entorno tiene que ser verificable, no un supuesto.

    Este test nace de un defecto real. El texto del prompt afirmaba que las
    herramientas «ya están disponibles» cuando el workflow del implementador no
    instalaba ninguna: solo `quality.yml` traía `uv`. El rol, obedeciendo la
    prohibición de instalar, se detuvo en `FAILED_SAFELY` — correctamente, pero
    la ronda se perdió por una frase que nadie había contrastado
    (incidencia #182, run 31990550597).

    Así que la promesa queda atada a los pasos reales del workflow que ejecuta
    ese rol: si alguien la escribe donde no se cumple, o quita el `setup-uv` de
    un workflow cuyo prompt la promete, esto falla.
    """
    import yaml

    if PROMESA_DE_ENTORNO not in _flat(prompt_path.read_text(encoding="utf-8")):
        pytest.skip(f"{prompt_path.name} no promete un entorno preparado")

    nombre = WORKFLOW_DE_CADA_ROL.get(prompt_path.name)
    assert nombre, (
        f"{prompt_path.name} promete un entorno preparado pero no se sabe qué "
        "workflow lo ejecuta; añádelo a WORKFLOW_DE_CADA_ROL"
    )
    workflow = REPO_ROOT / ".github" / "workflows" / nombre
    with workflow.open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    pasos = next(iter(doc["jobs"].values()))["steps"]

    usos = " ".join(str(p.get("uses") or "") for p in pasos)
    comandos = " ".join(str(p.get("run") or "") for p in pasos)
    assert "astral-sh/setup-uv" in usos, f"{nombre} no instala uv, pero su prompt lo promete"
    assert "uv sync" in comandos, f"{nombre} no sincroniza dependencias, pero su prompt lo promete"

    # Y la preparación debe ocurrir ANTES de arrancar al modelo: instalarla
    # después no le serviría de nada.
    i_uv = next(i for i, p in enumerate(pasos) if "setup-uv" in str(p.get("uses") or ""))
    i_claude = next(
        i for i, p in enumerate(pasos) if "claude-code-action" in str(p.get("uses") or "")
    )
    assert i_uv < i_claude, f"{nombre} instala uv después de arrancar al modelo"


def test_ningun_prompt_promete_una_reanudacion_automatica() -> None:
    """La frase que mató las tres rondas, en sus variantes.

    Ningún prompt debe sugerir que el turno continúa solo, ni en español ni en
    inglés: es justo la creencia que produjo `sin-veredicto` tres veces.
    """
    prohibidas = re.compile(
        r"reanud[ao] autom|will resume automatically|contin[úu]o en el siguiente mensaje",
        re.IGNORECASE,
    )
    for prompt_path in PROMPTS:
        texto = _flat(prompt_path.read_text(encoding="utf-8"))
        for match in prohibidas.finditer(texto):
            # Aparecer como EJEMPLO de lo que no se debe hacer es legítimo: lo que
            # se prohíbe es prometerlo. El discriminante es que la cita vaya
            # dentro de la sección anti-espera, que es donde se cita para vetarla.
            anti_espera = texto.find("Nadie te va a contestar")
            assert anti_espera != -1 and match.start() > anti_espera, (
                f"{prompt_path.name} sugiere una reanudación automática fuera de la "
                f"sección que la prohíbe: {match.group(0)!r}"
            )
