"""El Auditor se lanza por etiqueta, y lo que ejecuta un modelo no puede escribir.

ADR-016 parte el trabajo en dos y hace la frontera estructural en vez de
confiada: `auditar` declara `contents: read` y ejecuta el modelo; `publicar`
puede comentar y NO ejecuta ningún modelo.

La primera versión de estas pruebas cayó en el error que esta sesión lleva
repitiendo: comprobar la forma que se le ocurrió al autor en vez de la que usa
el código. Tres ejemplos que la ronda adversarial demostró:

- Derivaba «las etiquetas del ciclo» de los `if:` de los workflows, cuando el
  ciclo reconoce lo suyo por PREFIJO (`grep '^sirius:'` en el reconciliador,
  `startswith("sirius:")` en el completador). La etiqueta `sirius:audit-requested`
  entraba en la máquina de estados por donde la prueba juraba que no.
- Miraba solo los `permissions:` del job e ignoraba la herencia del nivel
  workflow, así que la lista de exenciones era decorativa: vaciarla no cambiaba
  nada.
- No fijaba el `github_token` del trabajo del modelo, que es la mitad del
  argumento de ADR-016: pasarle el PAT anularía el recorte de permisos.

Esta versión deriva de los mecanismos reales y, donde depende de un supuesto
sobre otro fichero, ese supuesto se verifica en la misma prueba en vez de
darse por sabido.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
AUDITOR = WORKFLOWS / "audit-sirius-repository.yml"
RUNBOOK = REPO_ROOT / "docs" / "implementation" / "AUDITOR_AGENT_V0.md"
LIBRERIA = REPO_ROOT / "scripts" / "automation" / "sirius_issue.sh"
RECONCILIADOR = REPO_ROOT / "scripts" / "automation" / "sirius_reconcile.sh"

ETIQUETA_DEL_AUDITOR = "auditoria:solicitada"

REGISTRO_DE_ACCIONES = Path(__file__).resolve().parent / "registro_de_acciones.yml"


def _registro() -> dict[str, Any]:
    return yaml.safe_load(REGISTRO_DE_ACCIONES.read_text(encoding="utf-8")) or {}


REGISTRO: dict[str, Any] = _registro()

# Lo que delata que un trabajo ejecuta un modelo. **Se DERIVA del registro**, no
# se escribe aquí (ADR-018, rescatado de la PR #171).
#
# Antes era la tupla `("anthropics/claude-code-action",)`, escrita a mano. Eso
# hacía que toda la defensa reconociera UN NOMBRE, no una categoría: un runtime
# nuevo —otra acción, otro proveedor, un contenedor— entraba sin que el barrido
# de permisos ni la regla de secretos lo miraran siquiera, porque su nombre no
# estaba en la tupla. Es la familia que ADR-033 nombró: una lista escrita a mano
# siempre tiene un hueco más.
#
# Derivándolo, la pregunta deja de ser «¿es esta acción?» y pasa a ser «¿está
# clasificada?». Meter un motor nuevo obliga a pasar por el registro, y entrar
# en `con_modelo` le aplica de golpe todas las defensas existentes.
ACCIONES_CON_MODELO = tuple(REGISTRO["con_modelo"])

# Comparación de etiqueta en una condición de Actions, en el `if:` del job o de
# cualquier paso. Es la forma en que TODOS los workflows de este repositorio
# deciden si reaccionan a un evento `labeled`.
COMPARA_ETIQUETA = re.compile(r"github\.event\.label\.name\s*==\s*'([^']+)'")


def _nombre_accion(uses: str) -> str:
    """El nombre de la acción sin su versión: `owner/repo@v4` -> `owner/repo`.

    Las formas `./ruta` (acción local) y `docker://imagen` se devuelven tal
    cual: no son nombres del registro y tienen que caer en «desconocida», que
    es justo lo que se quiere de ellas mientras nadie las clasifique.
    """
    return uses.split("@", 1)[0].strip()


def _cargar(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


def _todos_los_workflows() -> dict[str, dict[str, Any]]:
    # `*.yml` y `*.yaml`: GitHub acepta las dos extensiones, y barrer solo una
    # dejaría un workflow invisible a todas las comprobaciones.
    ficheros = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
    return {ruta.name: _cargar(ruta) for ruta in ficheros}


def _pasos(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in (job.get("steps") or []) if isinstance(p, dict)]


def _ejecuta_modelo(job: dict[str, Any]) -> bool:
    return any(
        accion in str(paso.get("uses") or "")
        for paso in _pasos(job)
        for accion in ACCIONES_CON_MODELO
    )


def _escrituras(permisos: object) -> dict[str, str]:
    """Los permisos de escritura que contiene una declaración `permissions:`."""
    if permisos == {}:
        return {}
    if isinstance(permisos, str):
        # Las formas cortas: `read-all` es lectura; `write-all`, escritura.
        return {} if permisos in ("read-all",) else {"(global)": permisos}
    if isinstance(permisos, dict):
        return {k: str(v) for k, v in permisos.items() if str(v) not in ("read", "none")}
    return {"(desconocido)": repr(permisos)}


def _escrituras_efectivas(job: dict[str, Any], definicion: dict[str, Any]) -> dict[str, str]:
    """Permisos de escritura EFECTIVOS de un job, con la herencia de GitHub.

    Un job sin bloque `permissions:` hereda el del workflow; sin ninguno de los
    dos, aplica el valor por defecto del repositorio, que puede ser permisivo.
    Ese caso se trata como escritura: la primera versión de esta prueba lo
    trataba como «sin permisos» y con eso la lista de exenciones era decorativa.
    """
    if "permissions" in job:
        return _escrituras(job["permissions"])
    if "permissions" in definicion:
        return _escrituras(definicion["permissions"])
    return {"(sin declarar)": "hereda el valor por defecto del repositorio"}


def _etiquetas_que_disparan(definicion: dict[str, Any]) -> set[str]:
    """Toda etiqueta comparada en un `if:`, de job o de paso."""
    condiciones: list[str] = []
    for job in (definicion.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        condiciones.append(str(job.get("if") or ""))
        condiciones.extend(str(p.get("if") or "") for p in _pasos(job))
    return {e for c in condiciones for e in COMPARA_ETIQUETA.findall(c)}


def _job_del_modelo() -> dict[str, Any]:
    definicion = _cargar(AUDITOR)
    job: dict[str, Any] = definicion["jobs"]["auditar"]
    return job


def _paso_del_modelo() -> dict[str, Any]:
    return next(
        p
        for p in _pasos(_job_del_modelo())
        if any(a in str(p.get("uses") or "") for a in ACCIONES_CON_MODELO)
    )


# ─────────────────────────── la frontera de permisos ───────────────────────────


def test_ningun_trabajo_que_ejecute_un_modelo_puede_escribir() -> None:
    """La propiedad central de ADR-016, con la herencia de permisos incluida.

    Los tres roles del ciclo están exentos y declarados: escribir código y abrir
    PR es su cometido. La lista es cerrada a propósito — añadir un nombre aquí
    es una decisión, y este es el sitio donde se ve.
    """
    ROLES_DEL_CICLO = {
        "implement-sirius-work.yml",
        "review-sirius-work.yml",
        "repair-sirius-work.yml",
    }

    infracciones: list[str] = []
    for nombre, definicion in _todos_los_workflows().items():
        if nombre in ROLES_DEL_CICLO:
            continue
        for nombre_job, job in (definicion.get("jobs") or {}).items():
            if not isinstance(job, dict) or not _ejecuta_modelo(job):
                continue
            escrituras = _escrituras_efectivas(job, definicion)
            if escrituras:
                infracciones.append(f"{nombre} · trabajo «{nombre_job}» · permisos {escrituras}")

    assert not infracciones, (
        "Estos trabajos ejecutan un modelo Y pueden escribir (contando la "
        "herencia del nivel workflow):\n\n" + "\n".join(f"  - {i}" for i in infracciones)
    )


def test_el_modelo_recibe_el_token_recortado_y_sin_herramientas_prohibidas() -> None:
    """La otra mitad del argumento de ADR-016, que la primera versión no fijaba.

    `contents: read` solo acota el `github.token` DEL RUN. Si al modelo se le
    pasara el PAT —que existe en este repositorio y el ciclo ya usa así—, el
    recorte no acotaría nada: un PAT lleva sus propios permisos, no los del job.

    Y las herramientas: sin web (prohibición expresa del propietario en #154),
    sin `--dangerously-skip-permissions` (el Auditor es la única llamada a la
    acción que no debe llevarlo), y sin `Bash` sin acotar.
    """
    con = _paso_del_modelo().get("with") or {}

    token = str(con.get("github_token") or "")
    assert "github.token" in token, "El modelo no recibe el token del run."
    assert "secrets." not in token, (
        "El modelo recibe un secreto como github_token. Un PAT lleva sus "
        "propios permisos: anula el `contents: read` del job."
    )

    args = str(con.get("claude_args") or "")
    for prohibido in ("WebSearch", "WebFetch", "--dangerously-skip-permissions"):
        assert prohibido not in args, f"El Auditor lleva `{prohibido}`, que está prohibido."

    herramientas = re.search(r'--allowedTools\s+"([^"]+)"', args)
    assert herramientas, "El paso del modelo no acota sus herramientas."
    assert not re.search(r"Bash(?!\()", herramientas.group(1)), (
        "Hay un `Bash` sin acotar en las herramientas del Auditor; solo se "
        "admiten formas restringidas como `Bash(git log:*)`."
    )


def test_el_trabajo_que_publica_no_ejecuta_ningun_modelo_y_sus_permisos_son_fijos() -> None:
    definicion = _cargar(AUDITOR)
    publicar = definicion["jobs"]["publicar"]

    assert not _ejecuta_modelo(publicar), (
        "«publicar» puede escribir y además ejecuta un modelo. Lo que protege "
        "el informe es que ese trabajo no invoque ninguno, para que todo lo que "
        "hace esté en el YAML y se lea entero."
    )
    assert publicar.get("permissions") == {"issues": "write", "contents": "read"}, (
        "Los permisos de «publicar» cambiaron. `issues: write` publica el "
        "comentario; `contents: read` existe solo para el checkout del "
        f"saneador. Hay: {publicar.get('permissions')}"
    )


# ─────────────────────────── fuera de la máquina de estados ───────────────────────────


def test_la_etiqueta_del_auditor_queda_fuera_del_ciclo_por_su_prefijo() -> None:
    """El ciclo reconoce lo suyo por PREFIJO, no por lista de estados.

    El supuesto se verifica aquí mismo en vez de darse por sabido: si esos
    mecanismos cambian de forma, esta prueba falla y obliga a re-examinar la
    pertenencia, en vez de seguir afirmándola sobre un mecanismo que ya no
    existe. La primera etiqueta (`sirius:audit-requested`) entró en la máquina
    de estados exactamente por esto.
    """
    reconciliador = RECONCILIADOR.read_text(encoding="utf-8")
    assert "grep '^sirius:'" in reconciliador, (
        "El reconciliador ya no filtra por el prefijo `^sirius:`. Esta prueba "
        "asume ese mecanismo: re-examinar si la etiqueta del Auditor sigue "
        "quedando fuera de su alcance."
    )
    completador = (WORKFLOWS / "complete-sirius-after-merge.yml").read_text(encoding="utf-8")
    assert 'startswith("sirius:")' in completador, (
        'El completador ya no selecciona incidencias por `startswith("sirius:")`. '
        "Re-examinar la pertenencia de la etiqueta del Auditor."
    )

    assert not ETIQUETA_DEL_AUDITOR.startswith("sirius:"), (
        "La etiqueta del Auditor lleva el prefijo `sirius:`: el reconciliador y "
        "el completador la contarían como estado del ciclo."
    )


def test_el_auditor_solo_reacciona_a_su_etiqueta() -> None:
    del_auditor = _etiquetas_que_disparan(_cargar(AUDITOR))
    assert del_auditor == {ETIQUETA_DEL_AUDITOR}, (
        f"El Auditor debe dispararse solo con `{ETIQUETA_DEL_AUDITOR}`; "
        f"reacciona a {sorted(del_auditor)}."
    )


def test_ningun_otro_workflow_reacciona_a_la_etiqueta_del_auditor() -> None:
    culpables = [
        nombre
        for nombre, definicion in _todos_los_workflows().items()
        if nombre != AUDITOR.name and ETIQUETA_DEL_AUDITOR in _etiquetas_que_disparan(definicion)
    ]
    assert not culpables, (
        f"Estos workflows reaccionan a `{ETIQUETA_DEL_AUDITOR}`: {culpables}. "
        "Un run del Auditor dejaría de ser un carril aparte."
    )


# ─────────────────────────── el contenido del informe ───────────────────────────


def test_el_informe_se_publica_saneado() -> None:
    """El informe lo escribe un modelo y se publica como `github-actions[bot]`,
    que está DENTRO del filtro de confianza del ciclo (`SIRIUS_TRUSTED_AUTHOR_JQ`).

    Sin sanear, sus vallas ``` y sus marcadores `<!-- -->` gobernarían la
    numeración de rondas y las observaciones que consume el corrector — el
    ataque que el propio `sirius_issue.sh` documenta y del que ya se defiende
    en todos los demás caminos con `sanitize_untrusted_text`.
    """
    libreria = LIBRERIA.read_text(encoding="utf-8")
    assert "sanitize_untrusted_text()" in libreria, (
        "El saneador ya no vive en la librería; «publicar» no tendría qué cargar."
    )
    assert "SIRIUS_TRUSTED_AUTHOR_JQ" in libreria and "github-actions[bot]" in libreria, (
        "El filtro de confianza cambió de forma: re-examinar si el informe del "
        "Auditor sigue cayendo dentro de él."
    )

    definicion = _cargar(AUDITOR)
    guiones = [str(p.get("run") or "") for p in _pasos(definicion["jobs"]["publicar"])]
    publica = next(g for g in guiones if "gh issue comment" in g)
    assert "sanitize_untrusted_text" in publica, (
        "«publicar» pega el informe CRUDO en el comentario. Texto de un modelo, "
        "publicado dentro del filtro de confianza, sin el saneado que el resto "
        "del repositorio aplica sin excepción."
    )


def test_el_runbook_no_esta_duplicado_dentro_del_workflow() -> None:
    """Dos copias del mismo runbook se desincronizan: el workflow lo LEE."""
    texto_workflow = AUDITOR.read_text(encoding="utf-8")
    assert "AUDITOR_AGENT_V0.md" in texto_workflow, (
        "El workflow no menciona el runbook: o no lo lee, o lo lleva copiado."
    )
    lineas_del_runbook = [
        linea.strip()
        for linea in RUNBOOK.read_text(encoding="utf-8").splitlines()
        if len(linea.strip()) > 60 and not linea.strip().startswith(("#", "-", "|", ">"))
    ]
    copiadas = [linea for linea in lineas_del_runbook if linea in texto_workflow]
    assert not copiadas, (
        "El workflow lleva copiado texto del runbook en vez de leerlo:\n"
        + "\n".join(f"  - {linea[:80]}…" for linea in copiadas[:5])
    )


# ─────────────────────────── la huella del árbol ───────────────────────────


def test_el_arnes_comprueba_la_huella_y_no_se_fia_del_agente() -> None:
    """La frontera mecánica que `AUDITOR_AGENT_V0.md` §2 vuelve obligatoria
    cuando los runs pasan a desatendidos — que es lo que hace este workflow.

    La huella la toma el ARNÉS, no el agente: un agente que certifica su propia
    inocencia es «el observador dentro de lo observado». Y tiene consecuencia:
    el informe sale marcado inválido y el trabajo termina en rojo.
    """
    pasos = _pasos(_job_del_modelo())
    ids = [str(p.get("id") or "") for p in pasos]

    assert "huella" in ids, "No hay huella inicial; «no modificó nada» sería una promesa."
    assert "intacto" in ids, "Nadie compara la huella al final."

    i_huella = ids.index("huella")
    con_modelo = [
        i
        for i, p in enumerate(pasos)
        if any(a in str(p.get("uses") or "") for a in ACCIONES_CON_MODELO)
    ]
    assert con_modelo, (
        "Ningún paso de «auditar» invoca la acción del modelo: o el workflow "
        "cambió, o `ACCIONES_CON_MODELO` dejó de reconocerla y esta prueba "
        "estaría comprobando el vacío."
    )
    i_intacto = ids.index("intacto")
    assert i_huella < con_modelo[0] < i_intacto, "El orden debe ser huella → modelo → comprobación."

    guion_intacto = str(pasos[i_intacto].get("run") or "")
    # `--ignored=matching` obligatorio: sin él, una escritura en una ruta que
    # coincide con .gitignore no aparece en `git status --porcelain` y la
    # huella daría «intacto» en falso. Lo encontró el PROPIO Auditor en su
    # primera ejecución real (FINDING-001 de RUN-002, #167): el mecanismo que
    # lo vigila tenía un punto ciego del tamaño del .gitignore.
    for señal in ("git rev-parse HEAD", "git branch"):
        assert señal in guion_intacto, f"La huella final no mira `{señal}`."
    # Anclado a la línea de CAPTURA (la asignación), no a cualquier aparición:
    # la primera versión de esta aserción buscaba la orden en todo el paso y la
    # satisfacía el volcado de diagnóstico del else — presencia de lo bueno en
    # el sitio equivocado, el vicio exacto que ADR-015 registró.
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
        "`needs.auditar.result` que ve el comentario sería vacua."
    )


# ─────────────────────────── guardián de la guardiana ───────────────────────────


def test_estas_pruebas_miran_algo() -> None:
    """Todas las comprobaciones de arriba pasan trivialmente si el barrido deja
    de encontrar material. Una prueba que no puede fallar es peor que ninguna."""
    assert AUDITOR.is_file(), f"No existe {AUDITOR.name}."
    assert RUNBOOK.is_file(), "No existe el runbook."

    definicion = _cargar(AUDITOR)
    jobs = definicion.get("jobs") or {}
    assert set(jobs) == {"auditar", "publicar"}, f"ADR-016 espera dos trabajos; hay {sorted(jobs)}."

    con_modelo = [n for n, j in jobs.items() if _ejecuta_modelo(j)]
    assert con_modelo == ["auditar"], (
        f"Se esperaba que solo «auditar» ejecutara un modelo; ejecutan {con_modelo}. "
        "Vacío significa que `ACCIONES_CON_MODELO` dejó de reconocer la acción."
    )

    todos = _todos_los_workflows()
    assert len(todos) >= 10, (
        f"Solo {len(todos)} workflows: el barrido no está leyendo el directorio."
    )
    con_disparo = [n for n, d in todos.items() if _etiquetas_que_disparan(d)]
    assert len(con_disparo) >= 4, (
        f"Solo {con_disparo} reaccionan a etiquetas: el extractor de condiciones "
        "dejó de entender los `if:` y las comprobaciones de solapamiento pasan por vacío."
    )


# ─────────────── El registro cerrado de acciones (ADR-018, PR #171) ───────────────


def _acciones_sin_clasificar(
    workflows: dict[str, dict[str, Any]], conocidas: set[str]
) -> list[str]:
    """Las `uses:` de esos workflows que no están en `conocidas`.

    Se recorren las de PASO **y las de NIVEL JOB** (workflows reutilizables):
    un barrido solo de pasos dejaría entrar un workflow reutilizable entero sin
    clasificar, que es una puerta más ancha que la que se está cerrando.
    """
    desconocidas: list[str] = []
    for nombre, definicion in workflows.items():
        for nombre_job, job in (definicion.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            usos = [str(job["uses"])] if "uses" in job else []
            usos += [str(p["uses"]) for p in _pasos(job) if "uses" in p]
            desconocidas += [
                f"{nombre} · «{nombre_job}» · {uso}"
                for uso in usos
                if _nombre_accion(uso) not in conocidas
            ]
    return desconocidas


def _conocidas() -> set[str]:
    return set(REGISTRO["con_modelo"]) | set(REGISTRO["sin_modelo"])


def test_toda_accion_de_workflow_esta_clasificada_en_el_registro() -> None:
    """Neutralidad al runtime por construcción.

    La defensa deja de reconocer un nombre de acción concreto y pasa a
    reconocer «acción clasificada». Un motor nuevo —Inspect, un contenedor,
    una acción de otro proveedor— no puede entrar sin pasar por
    `registro_de_acciones.yml`, y entrar en `con_modelo` le aplica de golpe el
    barrido de permisos y la regla de secretos que ya existen.
    """
    desconocidas = _acciones_sin_clasificar(_todos_los_workflows(), _conocidas())
    assert not desconocidas, (
        "Acciones sin clasificar en registro_de_acciones.yml (¿un runtime nuevo "
        "entrando sin pasar por el registro?):\n" + "\n".join(f"  - {d}" for d in desconocidas)
    )


def test_una_accion_desconocida_en_un_paso_se_detecta() -> None:
    """Defecto sembrado: sin esto, la prueba de arriba pasaría estando rota.

    Se siembra sobre definiciones sintéticas y no sobre `.github/`, porque
    escribir un workflow falso en el árbol real para probar una guarda es
    exactamente la clase de prueba que deja basura detrás.
    """
    sintetico = {
        "falso.yml": {"jobs": {"trabajo": {"steps": [{"uses": "proveedor/motor-nuevo@v1"}]}}}
    }
    assert _acciones_sin_clasificar(sintetico, _conocidas()) == [
        "falso.yml · «trabajo» · proveedor/motor-nuevo@v1"
    ]


def test_un_workflow_reutilizable_sin_clasificar_tambien_se_detecta() -> None:
    """El `uses:` de nivel job, que un barrido de pasos no vería."""
    sintetico = {"falso.yml": {"jobs": {"trabajo": {"uses": "otro/workflow-entero@v2"}}}}
    assert _acciones_sin_clasificar(sintetico, _conocidas()) == [
        "falso.yml · «trabajo» · otro/workflow-entero@v2"
    ]


def test_las_formas_locales_y_docker_no_pasan_por_conocidas() -> None:
    """`./ruta` y `docker://` no son nombres del registro: caen en desconocida."""
    sintetico = {
        "falso.yml": {
            "jobs": {
                "t": {"steps": [{"uses": "./.github/acciones/propia"}, {"uses": "docker://alpine"}]}
            }
        }
    }
    assert len(_acciones_sin_clasificar(sintetico, _conocidas())) == 2


def test_la_version_no_cuenta_para_clasificar() -> None:
    """`actions/checkout@v4` y `@v6` son la misma acción para el registro."""
    for version in ("v4", "v6", "abc123"):
        sintetico = {"f.yml": {"jobs": {"t": {"steps": [{"uses": f"actions/checkout@{version}"}]}}}}
        assert _acciones_sin_clasificar(sintetico, _conocidas()) == []


def test_el_registro_no_tiene_entradas_muertas() -> None:
    """Una acción clasificada que ya nadie usa es una excepción que sobra.

    Mismo criterio que las excepciones declaradas del resto del repositorio: se
    quitan cuando dejan de hacer falta, para que la lista no crezca sola.
    """
    usadas = {
        _nombre_accion(str(p["uses"]))
        for definicion in _todos_los_workflows().values()
        for job in (definicion.get("jobs") or {}).values()
        if isinstance(job, dict)
        for p in _pasos(job)
        if "uses" in p
    } | {
        _nombre_accion(str(job["uses"]))
        for definicion in _todos_los_workflows().values()
        for job in (definicion.get("jobs") or {}).values()
        if isinstance(job, dict) and "uses" in job
    }
    muertas = sorted(_conocidas() - usadas)
    assert muertas == [], f"clasificadas en el registro pero ya sin uso: {muertas}"
