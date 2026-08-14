"""El Auditor se lanza por etiqueta, y lo que ejecuta un modelo no puede escribir.

ADR-016 parte el trabajo en dos y hace la frontera estructural en vez de
confiada:

- `auditar` declara `contents: read` y ejecuta el modelo. El token que recibe el
  agente está acotado por esos permisos: es incapaz de escribir aunque se le
  pida.
- `publicar` puede comentar, y por eso NO ejecuta ningún modelo: todo lo que
  hace está en el YAML y se lee entero.

Estas pruebas están escritas en la forma que impuso ADR-015: **buscan lo malo,
no lo bueno**, y derivan del YAML real en vez de copiar listas. Preguntar «¿está
el permiso correcto en algún sitio?» se satisface con una aparición y no dice
nada de las demás; preguntar «¿hay algún trabajo con modelo que pueda escribir?»
no tiene ese agujero.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
AUDITOR = WORKFLOWS / "audit-sirius-repository.yml"
RUNBOOK = REPO_ROOT / "docs" / "implementation" / "AUDITOR_AGENT_V0.md"

ETIQUETA_DEL_AUDITOR = "sirius:audit-requested"

# Lo que delata que un trabajo ejecuta un modelo. Ancho a propósito: cualquier
# acción de Anthropic cuenta, se llame como se llame la versión.
ACCIONES_CON_MODELO = ("anthropics/claude-code-action",)

# Todo permiso de GitHub Actions que no sea `read` o `none` es escritura.
LECTURAS = frozenset({"read", "none"})


def _cargar(ruta: Path) -> dict[str, Any]:
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}


def _pasos(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in (job.get("steps") or []) if isinstance(p, dict)]


def _ejecuta_modelo(job: dict[str, Any]) -> bool:
    return any(
        accion in str(paso.get("uses") or "")
        for paso in _pasos(job)
        for accion in ACCIONES_CON_MODELO
    )


def _permisos_de_escritura(job: dict[str, Any]) -> dict[str, str]:
    permisos = job.get("permissions")
    if permisos in (None, {}):
        return {}
    if isinstance(permisos, str):
        # `permissions: write-all` — la forma más peligrosa y la más corta.
        return {} if permisos in LECTURAS else {"(global)": permisos}
    return {k: v for k, v in permisos.items() if str(v) not in LECTURAS}


def _etiquetas_que_disparan(definicion: dict[str, Any]) -> set[str]:
    """Las etiquetas que aparecen en los `if:` de los trabajos de un workflow.

    Se leen del YAML real. Copiar la lista del ciclo aquí la dejaría vieja en
    silencio, que es la forma más común de prueba vacua en este repositorio.
    """
    etiquetas: set[str] = set()
    for job in (definicion.get("jobs") or {}).values():
        condicion = str(job.get("if") or "")
        for trozo in condicion.replace("'", '"').split('"'):
            if trozo.startswith("sirius:"):
                etiquetas.add(trozo)
    return etiquetas


def _workflows_del_ciclo() -> dict[str, dict[str, Any]]:
    """Los workflows que reaccionan a etiquetas, salvo el del Auditor."""
    ciclo: dict[str, dict[str, Any]] = {}
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        if ruta.name == AUDITOR.name:
            continue
        definicion = _cargar(ruta)
        if _etiquetas_que_disparan(definicion):
            ciclo[ruta.name] = definicion
    return ciclo


def test_ningun_trabajo_que_ejecute_un_modelo_puede_escribir() -> None:
    """La propiedad central de ADR-016, y la única que de verdad protege algo.

    Se comprueba sobre TODOS los workflows, no solo el del Auditor: si mañana
    alguien añade un modelo a un trabajo con permisos de escritura, esto lo ve.

    El ciclo de programación está exento y declarado: sus roles SÍ escriben
    código y abren PR, que es su cometido. Lo que aquí se defiende es que
    ningún trabajo nuevo se cuele con esa capacidad sin que nadie lo note.
    """
    # Exención explícita y cerrada. Añadir un nombre aquí es una decisión, y
    # esta lista es el sitio donde se ve.
    ROLES_DEL_CICLO = {
        "implement-sirius-work.yml",
        "review-sirius-work.yml",
        "repair-sirius-work.yml",
    }

    infracciones: list[str] = []
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        if ruta.name in ROLES_DEL_CICLO:
            continue
        definicion = _cargar(ruta)
        for nombre_job, job in (definicion.get("jobs") or {}).items():
            if not isinstance(job, dict) or not _ejecuta_modelo(job):
                continue
            escrituras = _permisos_de_escritura(job)
            if escrituras:
                infracciones.append(f"{ruta.name} · trabajo «{nombre_job}» · permisos {escrituras}")

    assert not infracciones, (
        "Estos trabajos ejecutan un modelo Y pueden escribir. ADR-016 exige que "
        "el trabajo que ejecuta el modelo no escriba, y que el que escribe no "
        "ejecute modelos:\n\n" + "\n".join(f"  - {i}" for i in infracciones)
    )


def test_el_trabajo_que_publica_no_ejecuta_ningun_modelo() -> None:
    """La otra mitad de la frontera, mirada desde el lado que sí puede escribir."""
    definicion = _cargar(AUDITOR)
    for nombre_job, job in (definicion.get("jobs") or {}).items():
        if _permisos_de_escritura(job):
            assert not _ejecuta_modelo(job), (
                f"El trabajo «{nombre_job}» del Auditor puede escribir y además "
                "ejecuta un modelo. Lo que protege el informe no es el permiso: "
                "es que ese trabajo no invoque ningún modelo, para que todo lo "
                "que hace esté escrito en el YAML y se lea entero."
            )


def test_el_auditor_no_reacciona_a_ninguna_etiqueta_del_ciclo() -> None:
    """Un run del Auditor no es un bloque de la tubería.

    Si reaccionara a una etiqueta del ciclo, cada bloque de trabajo lanzaría
    además una auditoría, y la incidencia acabaría en un estado que la máquina
    no espera.
    """
    del_auditor = _etiquetas_que_disparan(_cargar(AUDITOR))
    assert del_auditor == {ETIQUETA_DEL_AUDITOR}, (
        f"El Auditor debe dispararse solo con `{ETIQUETA_DEL_AUDITOR}`; "
        f"reacciona a {sorted(del_auditor)}."
    )

    del_ciclo: set[str] = set()
    for definicion in _workflows_del_ciclo().values():
        del_ciclo |= _etiquetas_que_disparan(definicion)

    solapamiento = del_auditor & del_ciclo
    assert not solapamiento, f"El Auditor comparte disparador con el ciclo: {sorted(solapamiento)}."


def test_ningun_workflow_del_ciclo_reacciona_a_la_etiqueta_del_auditor() -> None:
    """La comprobación simétrica, que es la que se olvida.

    Comprobar solo que el Auditor no toca el ciclo deja pasar el caso contrario:
    que un workflow del ciclo empiece a reaccionar a `sirius:audit-requested`.
    """
    culpables = [
        nombre
        for nombre, definicion in _workflows_del_ciclo().items()
        if ETIQUETA_DEL_AUDITOR in _etiquetas_que_disparan(definicion)
    ]
    assert not culpables, (
        f"Estos workflows del ciclo reaccionan a `{ETIQUETA_DEL_AUDITOR}`: {culpables}. "
        "Un run del Auditor entraría en la máquina de estados."
    )


def test_el_runbook_no_esta_duplicado_dentro_del_workflow() -> None:
    """Dos copias del mismo runbook se desincronizan.

    El workflow debe LEER `AUDITOR_AGENT_V0.md` del árbol, no llevar su texto
    dentro. La deriva documental es uno de los defectos que la auditoría lleva
    corrigiendo desde el principio.
    """
    texto_workflow = AUDITOR.read_text(encoding="utf-8")
    assert "AUDITOR_AGENT_V0.md" in texto_workflow, (
        "El workflow no menciona el runbook: o no lo lee, o lo lleva copiado."
    )

    # Frases largas y propias del runbook. Si aparecen en el workflow, es que se
    # copió el texto en vez de leerlo.
    lineas_del_runbook = [
        linea.strip()
        for linea in RUNBOOK.read_text(encoding="utf-8").splitlines()
        if len(linea.strip()) > 60 and not linea.strip().startswith(("#", "-", "|", ">"))
    ]
    copiadas = [linea for linea in lineas_del_runbook if linea in texto_workflow]
    assert not copiadas, (
        "El workflow lleva copiado el texto del runbook en vez de leerlo:\n"
        + "\n".join(f"  - {linea[:80]}…" for linea in copiadas[:5])
    )


def test_el_arnes_comprueba_la_huella_y_no_se_fia_del_agente() -> None:
    """La frontera mecánica que `AUDITOR_AGENT_V0.md` §2 vuelve obligatoria.

    §2 dice que la restricción de escritura del Auditor es **procedimental**, y
    que la frontera mecánica «se vuelve obligatoria» si ocurre cualquiera de tres
    cosas. La primera es *«los runs pasan a desatendidos o programados»*, que es
    exactamente lo que hace este workflow.

    `contents: read` cubre la mitad de GitHub. Esta es la otra mitad: que el
    árbol no cambie. Y la comprueba el ARNÉS, no el agente — un agente que
    certifica su propia inocencia es «el observador dentro de lo observado».
    """
    definicion = _cargar(AUDITOR)
    pasos = _pasos(definicion["jobs"]["auditar"])
    nombres = [str(p.get("name") or "") for p in pasos]
    ids = [str(p.get("id") or "") for p in pasos]

    assert "huella" in ids, "No hay paso de huella inicial; «no modificó nada» sería una promesa."
    assert "intacto" in ids, "Nadie compara la huella al final."

    i_huella = ids.index("huella")
    con_modelo = [
        i
        for i, p in enumerate(pasos)
        if any(accion in str(p.get("uses") or "") for accion in ACCIONES_CON_MODELO)
    ]
    assert con_modelo, (
        "Ningún paso de «auditar» invoca la acción del modelo. O el workflow "
        "cambió, o `ACCIONES_CON_MODELO` dejó de reconocerla — y entonces esta "
        "prueba estaría comprobando el vacío."
    )
    i_modelo = con_modelo[0]
    i_intacto = ids.index("intacto")
    assert i_huella < i_modelo < i_intacto, (
        "El orden tiene que ser huella → modelo → comprobación; "
        f"es {nombres[i_huella]} / {nombres[i_modelo]} / {nombres[i_intacto]}."
    )

    guion_intacto = str(pasos[i_intacto].get("run") or "")
    for señal in ("git rev-parse HEAD", "git status --porcelain", "git branch"):
        assert señal in guion_intacto, f"La huella final no mira `{señal}`."

    # El paso que recoge el informe tiene que USAR el veredicto de la huella. Sin
    # esto, la comprobación existiría y no serviría para nada.
    guion_recoger = next(str(p.get("run") or "") for p in pasos if p.get("id") == "recoger")
    assert "INTACTO" in guion_recoger, (
        "El paso que recoge el informe ignora el resultado de la huella: la "
        "comprobación no tendría ninguna consecuencia."
    )


def test_estas_pruebas_miran_algo() -> None:
    """Guardián de la guardiana.

    Todas las comprobaciones de arriba pasan trivialmente si el barrido deja de
    encontrar material: si el fichero del Auditor desaparece, si sus trabajos
    dejan de parsearse, o si `_ejecuta_modelo` deja de reconocer la acción
    porque cambió de nombre. Una prueba que no puede fallar es peor que
    ninguna: afirma que todo va bien.
    """
    assert AUDITOR.is_file(), f"No existe {AUDITOR.name}; las pruebas de arriba no miran nada."
    assert RUNBOOK.is_file(), "No existe el runbook; el workflow no tendría qué leer."

    definicion = _cargar(AUDITOR)
    jobs = definicion.get("jobs") or {}
    assert set(jobs) == {"auditar", "publicar"}, (
        f"ADR-016 parte el trabajo en «auditar» y «publicar»; hay {sorted(jobs)}."
    )

    con_modelo = [n for n, j in jobs.items() if _ejecuta_modelo(j)]
    assert con_modelo == ["auditar"], (
        f"Se esperaba que solo «auditar» ejecutara un modelo; ejecutan {con_modelo}. "
        "Si la lista está vacía, `ACCIONES_CON_MODELO` dejó de reconocer la acción "
        "y la comprobación de permisos está mirando el vacío."
    )

    ciclo = _workflows_del_ciclo()
    assert len(ciclo) >= 4, (
        f"Solo {len(ciclo)} workflows del ciclo reaccionan a etiquetas: "
        "el barrido no los está leyendo y las comprobaciones de solapamiento "
        f"pasarían por vacío. Encontrados: {sorted(ciclo)}"
    )
