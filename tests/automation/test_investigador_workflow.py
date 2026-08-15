"""El Investigador se lanza por etiqueta, lee la web, y sigue sin poder escribir.

ADR-017 monta el segundo agente sobre el molde de ADR-016 con tres diferencias
deliberadas: la web ENCENDIDA, la pregunta viaja en el cuerpo de la incidencia,
y el runbook es el del Investigador. Este fichero vigila esas diferencias y lo
que NO debe cambiar con ellas.

Qué NO se comprueba aquí porque ya lo vigila otro sitio: la frontera de
permisos con herencia (el barrido global de `test_auditor_workflow.py` recorre
TODOS los workflows, y el trabajo `investigar` entra en él solo por existir), y
que el Auditor siga sin web (su propia prueba lo fija).

Qué SÍ, con la forma de ADR-015 (buscar lo malo, derivar del YAML real,
verificar los supuestos en la misma prueba):

- La pregunta NUNCA se interpola en un guion: `github.event.issue.body` es
  texto de cualquiera con permiso de abrir incidencias, y dentro de un `run:`
  sería inyección de shell con el token del run a mano.
- `Task`, `--dangerously-skip-permissions` y `Bash` sin acotar siguen
  prohibidos; el token del modelo es el del run, nunca un secreto.
- La etiqueta queda fuera del ciclo por su prefijo, y nadie más reacciona a
  ella.
- El informe —escrito por un modelo que LEYÓ WEB NO CONFIABLE— se publica
  saneado. Aquí el saneador defiende contra un adversario más real que en el
  Auditor: una página web puede sembrar marcadores en el texto del informe.
- La huella del árbol la toma el arnés, con `--ignored=matching` en la línea
  de CAPTURA (FINDING-001 de RUN-002, #167), y un run sin informe o con el
  árbol tocado termina en rojo.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
INVESTIGADOR = WORKFLOWS / "investigate-sirius-question.yml"
RUNBOOK = REPO_ROOT / "docs" / "implementation" / "INVESTIGADOR_AGENT_V0.md"
LIBRERIA = REPO_ROOT / "scripts" / "automation" / "sirius_issue.sh"
RECONCILIADOR = REPO_ROOT / "scripts" / "automation" / "sirius_reconcile.sh"
BOOTSTRAP = WORKFLOWS / "bootstrap-sirius-automation-labels.yml"

ETIQUETA_DEL_INVESTIGADOR = "investigacion:solicitada"

# Registro cerrado de acciones (ADR-018), compartido con test_auditor_workflow.
REGISTRO: dict[str, Any] = yaml.safe_load(
    (Path(__file__).resolve().parent / "registro_de_acciones.yml").read_text(encoding="utf-8")
)
ACCIONES_CON_MODELO: dict[str, dict[str, str]] = REGISTRO["con_modelo"]


def _nombre_accion(uses: str) -> str:
    """El nombre de una acción sin @versión, en minúsculas (GitHub no
    distingue mayúsculas al resolverlas): la unidad del registro."""
    return uses.split("@")[0].strip().lower()


COMPARA_ETIQUETA = re.compile(r"github\.event\.label\.name\s*==\s*'([^']+)'")


def _cargar(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


def _todos_los_workflows() -> dict[str, dict[str, Any]]:
    ficheros = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
    return {ruta.name: _cargar(ruta) for ruta in ficheros}


def _pasos(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in (job.get("steps") or []) if isinstance(p, dict)]


def _ejecuta_modelo(job: dict[str, Any]) -> bool:
    return any(
        _nombre_accion(str(paso.get("uses") or "")) in ACCIONES_CON_MODELO for paso in _pasos(job)
    )


def _etiquetas_que_disparan(definicion: dict[str, Any]) -> set[str]:
    condiciones: list[str] = []
    for job in (definicion.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        condiciones.append(str(job.get("if") or ""))
        condiciones.extend(str(p.get("if") or "") for p in _pasos(job))
    return {e for c in condiciones for e in COMPARA_ETIQUETA.findall(c)}


def _job_del_modelo() -> dict[str, Any]:
    definicion = _cargar(INVESTIGADOR)
    job: dict[str, Any] = definicion["jobs"]["investigar"]
    return job


def _paso_del_modelo() -> dict[str, Any]:
    return next(
        p
        for p in _pasos(_job_del_modelo())
        if _nombre_accion(str(p.get("uses") or "")) in ACCIONES_CON_MODELO
    )


# ─────────────────────────── la pregunta, sin inyección ───────────────────────────


def test_la_pregunta_viaja_por_entorno_y_nunca_se_interpola_en_un_guion() -> None:
    """El cuerpo de la incidencia es texto de CUALQUIERA con permiso de abrir
    incidencias. Interpolado en un `run:` sería una inyección de shell dentro
    del runner, con el token del run al alcance. Por eso viaja como variable de
    entorno (el runner la pasa como valor, no como código) y el guion la usa
    solo con `printf '%s'`.
    """
    texto = INVESTIGADOR.read_text(encoding="utf-8")
    definicion = _cargar(INVESTIGADOR)

    for job in (definicion.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for paso in _pasos(job):
            assert "github.event.issue.body" not in str(paso.get("run") or ""), (
                f"El paso «{paso.get('name')}» interpola el cuerpo de la "
                "incidencia dentro de un guion: inyección de shell."
            )

    paso_prompt = next(p for p in _pasos(_job_del_modelo()) if p.get("id") == "build_prompt")
    entorno = paso_prompt.get("env") or {}
    assert entorno.get("PREGUNTA") == "${{ github.event.issue.body }}", (
        "La pregunta ya no llega por la variable de entorno PREGUNTA; si el "
        "canal cambió, re-examinar por dónde entra el texto no confiable. "
        f"env: {entorno}"
    )

    guion = str(paso_prompt.get("run") or "")
    assert 'if [ -z "${PREGUNTA:-}" ]' in guion, (
        "Sin la guarda de cuerpo vacío, una incidencia sin cuerpo lanzaría un "
        "run entero para investigar la nada."
    )
    assert 'printf \'%s\' "$PREGUNTA" | grep -q "SIRIUS_PROMPT_EOF"' in guion, (
        "Sin la guarda del delimitador, un cuerpo que contenga la marca del "
        "heredoc truncaría el prompt y colaría el resto como salida del paso."
    )
    # La comprobación de arriba mira el YAML parseado; esta mira el texto crudo
    # por si una futura edición mete la expresión en un sitio que el parseo no
    # recorre (un `if:` compuesto, un bloque de comentario ejecutable...).
    assert texto.count("github.event.issue.body") == 1, (
        "El cuerpo de la incidencia aparece más de una vez en el workflow; "
        "solo se admite la asignación a PREGUNTA en el env de build_prompt."
    )


# ─────────────────────────── herramientas y token ───────────────────────────


def test_el_modelo_recibe_el_token_recortado_y_la_web_encendida() -> None:
    """La mitad heredada de ADR-016 (token del run, nunca un secreto; nada de
    `Task` ni saltarse permisos; `Bash` acotado a git) más la diferencia propia
    de ADR-017: WebSearch y WebFetch PRESENTES — quitarle la web al Investigador
    lo convierte en un Auditor con otro nombre, y eso también es una regresión.
    """
    con = _paso_del_modelo().get("with") or {}

    token = str(con.get("github_token") or "")
    assert "github.token" in token, "El modelo no recibe el token del run."
    assert "secrets." not in token, (
        "El modelo recibe un secreto como github_token. Un PAT lleva sus "
        "propios permisos: anula el `contents: read` del job."
    )

    args = str(con.get("claude_args") or "")
    assert "--dangerously-skip-permissions" not in args, (
        "El Investigador lleva `--dangerously-skip-permissions`, prohibido "
        "para todos los agentes del laboratorio."
    )
    assert re.search(r'--disallowedTools\s+"[^"]*Task[^"]*"', args), (
        "`Task` no está denegada. La lección de RUN-001 del Auditor: sin la "
        "denegación explícita, el agente lanza subagentes y espera "
        "notificaciones que en un runner desatendido nunca llegan."
    )

    herramientas = re.search(r'--allowedTools\s+"([^"]+)"', args)
    assert herramientas, "El paso del modelo no acota sus herramientas."
    permitidas = herramientas.group(1)
    for web in ("WebSearch", "WebFetch"):
        assert web in permitidas, (
            f"`{web}` no está entre las herramientas del Investigador. La web "
            "encendida ES la diferencia con el Auditor (ADR-017): sin ella, "
            "investigar queda reducido a leer el propio repositorio."
        )
    assert not re.search(r"Bash(?!\()", permitidas), (
        "Hay un `Bash` sin acotar en las herramientas del Investigador; solo "
        "se admiten formas restringidas como `Bash(git log:*)`."
    )


def test_el_trabajo_que_publica_no_ejecuta_ningun_modelo_y_sus_permisos_son_fijos() -> None:
    definicion = _cargar(INVESTIGADOR)
    publicar = definicion["jobs"]["publicar"]

    assert not _ejecuta_modelo(publicar), (
        "«publicar» puede escribir y además ejecuta un modelo. Lo que protege "
        "el informe es que ese trabajo no invoque ninguno, para que todo lo "
        "que hace esté en el YAML y se lea entero."
    )
    assert publicar.get("permissions") == {"issues": "write", "contents": "read"}, (
        "Los permisos de «publicar» cambiaron. `issues: write` publica el "
        "comentario; `contents: read` existe solo para el checkout del "
        f"saneador. Hay: {publicar.get('permissions')}"
    )


# ─────────────────────────── fuera de la máquina de estados ───────────────────────────


def test_la_etiqueta_del_investigador_queda_fuera_del_ciclo_por_su_prefijo() -> None:
    """El ciclo reconoce lo suyo por PREFIJO. El supuesto se verifica aquí
    mismo, no se da por sabido: si el reconciliador o el completador cambian de
    mecanismo, esta prueba obliga a re-examinar la pertenencia.
    """
    reconciliador = RECONCILIADOR.read_text(encoding="utf-8")
    assert "grep '^sirius:'" in reconciliador, (
        "El reconciliador ya no filtra por el prefijo `^sirius:`. Re-examinar "
        "si la etiqueta del Investigador sigue quedando fuera de su alcance."
    )
    completador = (WORKFLOWS / "complete-sirius-after-merge.yml").read_text(encoding="utf-8")
    assert 'startswith("sirius:")' in completador, (
        'El completador ya no selecciona incidencias por `startswith("sirius:")`. '
        "Re-examinar la pertenencia de la etiqueta del Investigador."
    )

    assert not ETIQUETA_DEL_INVESTIGADOR.startswith("sirius:"), (
        "La etiqueta del Investigador lleva el prefijo `sirius:`: el "
        "reconciliador y el completador la contarían como estado del ciclo."
    )

    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    assert f'ensure_label "{ETIQUETA_DEL_INVESTIGADOR}"' in bootstrap, (
        "El bootstrap no aprovisiona la etiqueta del Investigador: aplicarla "
        "fallaría con «label not found» en un repositorio recién restaurado."
    )


def test_el_investigador_solo_reacciona_a_su_etiqueta() -> None:
    del_investigador = _etiquetas_que_disparan(_cargar(INVESTIGADOR))
    assert del_investigador == {ETIQUETA_DEL_INVESTIGADOR}, (
        f"El Investigador debe dispararse solo con `{ETIQUETA_DEL_INVESTIGADOR}`; "
        f"reacciona a {sorted(del_investigador)}."
    )


def test_ningun_otro_workflow_reacciona_a_la_etiqueta_del_investigador() -> None:
    culpables = [
        nombre
        for nombre, definicion in _todos_los_workflows().items()
        if nombre != INVESTIGADOR.name
        and ETIQUETA_DEL_INVESTIGADOR in _etiquetas_que_disparan(definicion)
    ]
    assert not culpables, (
        f"Estos workflows reaccionan a `{ETIQUETA_DEL_INVESTIGADOR}`: {culpables}. "
        "Un run del Investigador dejaría de ser un carril aparte."
    )


# ─────────────────── la frontera de confidencialidad (ADR-017/018) ───────────────────


def test_la_web_viene_con_la_regla_de_confidencialidad_y_su_registro_auditable() -> None:
    """El Investigador junta repositorio PRIVADO y salida a Internet: la web
    solo es aceptable con las dos piezas de ADR-017/018 — la regla de
    confidencialidad en el prompt y la extracción de consultas por el ARNÉS,
    publicada junto al informe. Lo malo que se busca: web sin regla, extractor
    que escribe texto de web no confiable al canal de outputs, degradación
    silenciosa, o un apéndice capaz de convertir un run mudo en válido.
    """
    pasos = _pasos(_job_del_modelo())
    ids = [str(p.get("id") or "") for p in pasos]

    guion_prompt = str(pasos[ids.index("build_prompt")].get("run") or "")
    assert "REGLA DE CONFIDENCIALIDAD" in guion_prompt, (
        "La web está encendida sin la regla de confidencialidad en el prompt: "
        "el canal de salida (texto de consultas, URLs) queda sin contrato."
    )

    assert "consultas" in ids, "El arnés ya no extrae las consultas web del run."
    assert ids.index("intacto") < ids.index("consultas") < ids.index("recoger"), (
        "La extracción debe correr tras la huella y antes de recoger, o el "
        "apéndice no llega al informe publicado."
    )

    guion_consultas = str(pasos[ids.index("consultas")].get("run") or "")
    assert "claude-execution-output.json" in guion_consultas, (
        "El extractor ya no lee el volcado de ejecución del runtime: las "
        "consultas dejarían de publicarse y el riesgo aceptado en ADR-017 "
        "quedaría sin vigilancia."
    )
    assert "$GITHUB_OUTPUT" not in guion_consultas, (
        "El extractor escribe en el canal de outputs texto que procede de web no confiable."
    )
    # Los DOS caminos de degradación, anclados por separado: una sola aserción
    # de «hay algún ::warning::» la satisface el aviso que quede — el vicio de
    # presencia-de-lo-bueno-en-el-sitio-equivocado que ADR-015 cataloga (y que
    # la mutación M12 de esta misma noche volvió a cazar).
    for aviso in (
        "::warning::Consultas web no auditables: falta claude-execution-output.json",
        "::warning::Consultas web no auditables: volcado con formato desconocido",
    ):
        assert aviso in guion_consultas, (
            f"Falta el aviso «{aviso}»: esa vía de degradación del extractor "
            "sería SILENCIOSA, y la auditabilidad —la mitad de la decisión de "
            "ADR-017— se apagaría sin que nadie lo viera."
        )

    guion_recoger = str(pasos[ids.index("recoger")].get("run") or "")
    assert guion_recoger.index('if [ ! -s "$informe" ]') < guion_recoger.index(
        "consultas_web.md"
    ), (
        "El apéndice de consultas entra ANTES de evaluar si el informe venía "
        "vacío: un run mudo pasaría por válido solo por el apéndice del arnés."
    )

    tope_paso = _paso_del_modelo().get("timeout-minutes")
    tope_job = _job_del_modelo().get("timeout-minutes")
    assert isinstance(tope_paso, int) and isinstance(tope_job, int) and tope_paso < tope_job, (
        "El paso del modelo necesita un tope propio menor que el del job para "
        "que la extracción de consultas y el artefacto corran SIEMPRE."
    )


# ─────────────────────────── el contenido del informe ───────────────────────────


def test_el_informe_se_publica_saneado() -> None:
    """Aquí el saneador defiende contra un adversario MÁS real que en el
    Auditor: el informe lo escribe un modelo que leyó web no confiable, y una
    página puede sembrar en él vallas ``` y marcadores `<!-- -->` que, sin
    sanear, gobernarían la numeración de rondas y las observaciones que consume
    el corrector (el comentario sale como `github-actions[bot]`, DENTRO del
    filtro de confianza `SIRIUS_TRUSTED_AUTHOR_JQ`).
    """
    libreria = LIBRERIA.read_text(encoding="utf-8")
    assert "sanitize_untrusted_text()" in libreria, (
        "El saneador ya no vive en la librería; «publicar» no tendría qué cargar."
    )
    assert "SIRIUS_TRUSTED_AUTHOR_JQ" in libreria and "github-actions[bot]" in libreria, (
        "El filtro de confianza cambió de forma: re-examinar si el informe del "
        "Investigador sigue cayendo dentro de él."
    )

    definicion = _cargar(INVESTIGADOR)
    guiones = [str(p.get("run") or "") for p in _pasos(definicion["jobs"]["publicar"])]
    publica = next(g for g in guiones if "gh issue comment" in g)
    assert "sanitize_untrusted_text" in publica, (
        "«publicar» pega el informe CRUDO en el comentario. Texto de un modelo "
        "que leyó web no confiable, publicado dentro del filtro de confianza, "
        "sin el saneado que el resto del repositorio aplica sin excepción."
    )


def test_el_runbook_no_esta_duplicado_dentro_del_workflow() -> None:
    """Dos copias del mismo runbook se desincronizan: el workflow lo LEE."""
    texto_workflow = INVESTIGADOR.read_text(encoding="utf-8")
    assert "INVESTIGADOR_AGENT_V0.md" in texto_workflow, (
        "El workflow no menciona el runbook: o no lo lee, o lo lleva copiado."
    )
    lineas_del_runbook = [
        linea.strip()
        for linea in RUNBOOK.read_text(encoding="utf-8").splitlines()
        if len(linea.strip()) > 60 and not linea.strip().startswith(("#", "-", "|", ">"))
    ]
    assert lineas_del_runbook, (
        "El filtro no extrajo ninguna línea del runbook: esta prueba estaría "
        "comprobando el vacío (guardián añadido en la revisión del 15-08)."
    )
    copiadas = [linea for linea in lineas_del_runbook if linea in texto_workflow]
    assert not copiadas, (
        "El workflow lleva copiado texto del runbook en vez de leerlo:\n"
        + "\n".join(f"  - {linea[:80]}…" for linea in copiadas[:5])
    )


# ─────────────────────────── la huella del árbol ───────────────────────────


def test_el_arnes_comprueba_la_huella_y_no_se_fia_del_agente() -> None:
    """La huella la toma el ARNÉS, no el agente. Con `--ignored=matching` en la
    línea de CAPTURA (no en cualquier aparición: la versión del Auditor de esta
    aserción la satisfacía el volcado de diagnóstico del else — ADR-015), y con
    consecuencia: informe inválido y trabajo en rojo.
    """
    pasos = _pasos(_job_del_modelo())
    ids = [str(p.get("id") or "") for p in pasos]

    assert "huella" in ids, "No hay huella inicial; «no modificó nada» sería una promesa."
    assert "intacto" in ids, "Nadie compara la huella al final."

    i_huella = ids.index("huella")
    con_modelo = [
        i
        for i, p in enumerate(pasos)
        if _nombre_accion(str(p.get("uses") or "")) in ACCIONES_CON_MODELO
    ]
    assert con_modelo, (
        "Ningún paso de «investigar» invoca la acción del modelo: o el workflow "
        "cambió, o `ACCIONES_CON_MODELO` dejó de reconocerla y esta prueba "
        "estaría comprobando el vacío."
    )
    i_intacto = ids.index("intacto")
    assert i_huella < con_modelo[0] < i_intacto, "El orden debe ser huella → modelo → comprobación."

    guion_intacto = str(pasos[i_intacto].get("run") or "")
    for señal in ("git rev-parse HEAD", "git branch"):
        assert señal in guion_intacto, f"La huella final no mira `{señal}`."
    assert 'arbol_despues="$(git status --porcelain --ignored=matching' in guion_intacto, (
        "La CAPTURA de la huella final no mira las rutas ignoradas "
        "(FINDING-001 de RUN-002, #167): una escritura en logs/ o .local/ "
        "daría «intacto» en falso."
    )
    guion_huella = str(pasos[i_huella].get("run") or "")
    assert "arbol=$(git status --porcelain --ignored=matching" in guion_huella, (
        "La CAPTURA de la huella inicial no mira las rutas ignoradas: las dos "
        "mitades deben medir lo mismo o la comparación no compara nada."
    )

    guion_recoger = next(str(p.get("run") or "") for p in pasos if p.get("id") == "recoger")
    assert "INTACTO" in guion_recoger, "El resultado de la huella no llega a quien recoge."
    assert "exit 1" in guion_recoger, (
        "Un run inválido o sin informe terminaría en verde: la señal "
        "`needs.investigar.result` que ve el comentario sería vacua."
    )


# ─────────────────────────── guardián de la guardiana ───────────────────────────


def test_estas_pruebas_miran_algo() -> None:
    """Todas las comprobaciones de arriba pasan trivialmente si el material
    desaparece. Una prueba que no puede fallar es peor que ninguna."""
    assert INVESTIGADOR.is_file(), f"No existe {INVESTIGADOR.name}."
    assert RUNBOOK.is_file(), "No existe el runbook del Investigador."

    definicion = _cargar(INVESTIGADOR)
    jobs = definicion.get("jobs") or {}
    assert set(jobs) == {"investigar", "publicar"}, (
        f"ADR-017 espera dos trabajos; hay {sorted(jobs)}."
    )

    con_modelo = [n for n, j in jobs.items() if _ejecuta_modelo(j)]
    assert con_modelo == ["investigar"], (
        f"Se esperaba que solo «investigar» ejecutara un modelo; ejecutan {con_modelo}. "
        "Vacío significa que `ACCIONES_CON_MODELO` dejó de reconocer la acción."
    )
