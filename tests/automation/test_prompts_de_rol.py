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
APPLY_VERDICT = REPO_ROOT / "scripts" / "automation" / "sirius_apply_verdict.sh"

# El directorio ES la lista. No se enumeran los ficheros a mano a propósito: una
# lista escrita a mano habría que acordarse de ampliarla, que es exactamente el
# olvido que estas pruebas existen para hacer imposible.
PROMPTS = sorted(PROMPTS_DIR.glob("*.md"))

# Veredictos que NO afirman éxito: son paradas. Todo lo demás que un rol puede
# emitir sí lo afirma, y por eso esta es la lista que se escribe a mano — es
# cerrada por naturaleza (parar, bloquear, agotarse) y no crece cuando alguien
# inventa una forma nueva de decir que algo salió bien.
VEREDICTOS_DE_PARADA = frozenset({"BLOCKED_BY_DECISION", "FAILED_SAFELY", "USAGE_LIMIT_REACHED"})

#: Los roles que `sirius_apply_verdict.sh` reconoce, con su vocabulario. La
#: lista vive en el script y se lee de ahí, no se copia: cuando se añadió
#: `CHECKS_UNRELATED` al corrector, una copia escrita a mano en este fichero se
#: quedó sin él y la guarda del veredicto provisional dejó de cubrirlo en
#: silencio. Es el mismo olvido que el comentario de `PROMPTS`, tres líneas más
#: arriba, dice que estas pruebas existen para hacer imposible.
_ALLOWED_RE = re.compile(r'^\s*(\w+)\)\s*allowed="([^"]+)"', re.MULTILINE)


def _vocabulario_por_rol() -> dict[str, frozenset[str]]:
    fuente = APPLY_VERDICT.read_text(encoding="utf-8")
    return {rol: frozenset(v.split()) for rol, v in _ALLOWED_RE.findall(fuente)}


VOCABULARIO_POR_ROL = _vocabulario_por_rol()

# Valores de `verdict` que afirman que el trabajo salió bien, en cualquiera de los
# tres roles. Ninguno puede aparecer en el veredicto provisional.
SUCCESS_VERDICTS = tuple(
    sorted(frozenset().union(*VOCABULARIO_POR_ROL.values()) - VEREDICTOS_DE_PARADA)
)


def _flat(texto: str) -> str:
    """Texto con los espacios en blanco colapsados a uno solo.

    Los prompts son markdown ajustado a 80 columnas, así que una frase cae
    partida por un salto de línea según dónde toque. Comparar contra el texto
    crudo haría que una regla presente fallara solo por haberse reajustado el
    párrafo — y eso enseñaría a desactivar la prueba en vez de a leerla.
    """
    return " ".join(texto.split())


def test_el_vocabulario_de_veredictos_se_leyo_de_verdad() -> None:
    """Una derivación que no encuentra nada deja la guarda vacía y siempre verde.

    `SUCCESS_VERDICTS` se deriva leyendo `sirius_apply_verdict.sh`. Si ese
    formato cambia y la expresión deja de casar, la lista queda vacía y
    `test_el_veredicto_provisional_nunca_declara_exito` pasaría sin comprobar
    nada — el mismo falso verde que la derivación venía a impedir, con otra
    cara. Esta prueba es la que lo hace imposible.
    """
    assert set(VOCABULARIO_POR_ROL) == {"implementer", "reviewer", "corrector"}, (
        "los tres roles del contrato tienen que salir del script, no de aquí"
    )
    assert SUCCESS_VERDICTS, "la derivación no encontró ningún veredicto"
    for parada in VEREDICTOS_DE_PARADA:
        assert any(parada in v for v in VOCABULARIO_POR_ROL.values()), (
            f"{parada} ya no existe en el script: la lista de paradas se quedó vieja"
        )
        assert parada not in SUCCESS_VERDICTS


def test_el_corrector_puede_declarar_que_el_fallo_no_es_suyo() -> None:
    """`CHECKS_UNRELATED` afirma éxito, y la lista escrita a mano no lo tenía.

    Se añadió al corrector después de que esta guarda se escribiera -el propio
    script lo cuenta: «hasta ahora el corrector solo tenía FIXED»- y la copia
    de este fichero no se amplió. Sin él en la lista, un prompt podía declarar
    por adelantado que el fallo de Quality no era suyo, que es exactamente lo
    que el veredicto provisional no puede hacer.
    """
    assert "CHECKS_UNRELATED" in SUCCESS_VERDICTS
    assert "CHECKS_UNRELATED" in VOCABULARIO_POR_ROL["corrector"]


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
    """La regla debe enunciar una PROPIEDAD, no enumerar vehículos.

    Cuatro rondas se han perdido por esto, en los tres roles y las cuatro con
    `terminal_reason: completed`. La cuarta (#193, run 32166867844) es la que
    obliga a esta forma: la regla YA existía, pero decía «nada de `pytest` en
    segundo plano» y «no lances subagentes», y el modelo esperó una notificación
    de la herramienta Monitor — un tercer mecanismo que la lista no nombraba.
    Hizo justo lo prohibido sin incumplir ninguna frase.

    Por eso esta prueba NO se limita a comprobar que aparecen las palabras de la
    lista. Si lo hiciera, seguiría dando por buena una regla esquivable con el
    siguiente mecanismo que se invente, que es exactamente cómo llegamos aquí.
    Lo que exige es que la prohibición esté enunciada como propiedad general y
    que los ejemplos se declaren no exhaustivos.
    """
    prompt = _flat(prompt_path.read_text(encoding="utf-8"))
    assert "Nadie te va a contestar" in prompt, "falta la sección anti-espera"
    seccion = prompt[prompt.index("Nadie te va a contestar") :]

    # 1) La propiedad: la prohibición no depende del mecanismo.
    assert "Da igual el mecanismo" in seccion, (
        "la regla debe prohibir esperar SEA CUAL SEA el vehículo, no enumerar vehículos"
    )
    assert "no va a llegar" in seccion

    # 2) Los ejemplos, declarados explícitamente no exhaustivos. Sin esto, un
    # lector razonable puede leer la lista como la definición de lo prohibido.
    assert "No son la lista completa" in seccion, (
        "los ejemplos deben declararse no exhaustivos, o la lista vuelve a ser la regla"
    )

    # 3) La propiedad va ANTES que los ejemplos. El orden no es estilo: lo que se
    # lee primero es lo que se toma por la regla.
    posicion_propiedad = seccion.index("Da igual el mecanismo")
    posicion_ejemplos = seccion.index("- **Ejecuta las validaciones")
    assert posicion_propiedad < posicion_ejemplos, (
        "la propiedad debe preceder a los ejemplos, no ir de nota al pie"
    )

    # 4) Los vehículos ya observados siguen nombrados, incluido el de la #193.
    assert "No lances subagentes en segundo plano" in seccion
    assert "notificaciones" in seccion, "falta el mecanismo que costó la ronda de #193"
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
    "documentalista.md": "implement-sirius-work.yml",
    "revisor-documental.md": "review-sirius-work.yml",
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


@pytest.mark.parametrize("prompt_path", PROMPTS, ids=lambda p: p.name)
def test_el_prompt_cuyo_workflow_no_prepara_el_entorno_lo_advierte(
    prompt_path: Path,
) -> None:
    """La otra mitad de la promesa: callarse también engaña.

    `test_el_prompt_que_promete_entorno_corre_donde_de_verdad_se_prepara` cubre
    una dirección —prometer un entorno que el workflow no monta—. Faltaba la
    contraria, y costó dos rondas enteras de la #193.

    El workflow del revisor no instala `uv` ni sincroniza el proyecto, y su
    prompt no lo decía: ni lo prometía ni lo desmentía. El rol hizo lo natural
    con ese silencio — usar el `python3` que encontró en el `PATH` —, y ese no
    es el del proyecto (`requires-python >=3.14`). Obtuvo un `SyntaxError` en
    código perfectamente válido (`except A, B:`, PEP 758) y lo publicó como
    hallazgo bloqueante en la ronda 2. En la ronda 4 volvió a publicarlo, esta
    vez «verificado por dos vías independientes» que eran el mismo intérprete
    equivocado. Quality estaba en verde las dos veces, que es la refutación.

    Así que no basta con no mentir: si el entorno NO está preparado, el prompt
    tiene que decirlo, y decirlo como PROPIEDAD. Enumerar herramientas vetadas
    dejaría siempre una fuera (ADR-033): lo que se afirma aquí es que ejecutar
    código en ese runner no dice nada del proyecto, sea cual sea el vehículo.
    """
    import yaml

    nombre = WORKFLOW_DE_CADA_ROL.get(prompt_path.name)
    if not nombre:
        pytest.skip(f"{prompt_path.name} no tiene un workflow conocido que lo ejecute")

    workflow = REPO_ROOT / ".github" / "workflows" / nombre
    with workflow.open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)
    pasos = next(iter(doc["jobs"].values()))["steps"]
    usos = " ".join(str(p.get("uses") or "") for p in pasos)
    if "astral-sh/setup-uv" in usos:
        pytest.skip(f"{nombre} sí prepara el entorno del proyecto")

    texto = _flat(prompt_path.read_text(encoding="utf-8"))

    assert PROMESA_DE_ENTORNO not in texto, (
        f"{nombre} no prepara el entorno y {prompt_path.name} lo promete igualmente"
    )
    assert "no es el del proyecto" in texto, (
        f"{prompt_path.name} corre sin el entorno del proyecto y no advierte de "
        f"que el intérprete del runner no es el suyo"
    )
    assert "sobre este runner" in texto, (
        f"{prompt_path.name} no enuncia la propiedad: lo que se averigua "
        f"ejecutando código aquí es una afirmación sobre el runner, no sobre el proyecto"
    )
    assert "Da igual con qué lo ejecutes" in texto, (
        f"{prompt_path.name} deja la regla atada a herramientas concretas; "
        f"una regla que enumera vehículos siempre tiene un hueco más (ADR-033)"
    )

    # Y la propiedad va ANTES que los ejemplos: leída al revés, la tabla de
    # casos pasados parece la lista completa de lo prohibido.
    posicion_propiedad = texto.find("sobre este runner")
    posicion_ejemplos = texto.find("Esto ya costó dos rondas")
    assert posicion_ejemplos != -1, f"{prompt_path.name} no cita la evidencia que motivó la regla"
    assert posicion_propiedad < posicion_ejemplos, (
        f"{prompt_path.name} pone los ejemplos antes que la propiedad que los explica"
    )


# --------------------------------------------------------------------------- #
# Dirección del propietario (31-08-2026): la revisión es UNA pasada exhaustiva.
# El goteo — un hallazgo por ronda sobre texto que llevaba idéntico desde la
# primera — convierte cada gota en un ciclo entero de máquina.
# --------------------------------------------------------------------------- #

_REVISORES = ("reviewer.md", "revisor-documental.md")


@pytest.mark.parametrize("nombre", _REVISORES)
def test_todo_revisor_manda_una_pasada_exhaustiva(nombre: str) -> None:
    texto = (PROMPTS_DIR / nombre).read_text(encoding="utf-8")
    assert "EXHAUSTIVA" in texto, (
        f"{nombre} ya no manda la pasada exhaustiva: el goteo de un hallazgo "
        "por ronda volvería, y cada gota cuesta un ciclo entero"
    )
    assert "goteo" in texto, (
        f"{nombre} ya no exige que un hallazgo tardío declare su origen "
        "(código nuevo de la corrección, regresión, o goteo del revisor)"
    )


def test_agents_declara_la_politica_de_revision() -> None:
    """Codex lee AGENTS.md: la política tiene que vivir también ahí."""
    texto = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Política de revisión" in texto
    assert "EXHAUSTIVA" in texto
