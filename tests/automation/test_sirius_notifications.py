"""Una etiqueta notificable escrita con el GITHUB_TOKEN no notifica a nadie.

GitHub suprime los eventos que produce el `GITHUB_TOKEN` para evitar recursión
entre workflows. Cuando los tres roles se mudaron a Actions, las etiquetas
pasaron a escribirse con ese token y `notify-sirius-state.yml` dejó de recibir
el `issues: labeled`: el contrato §7 los declara notificables y nunca volvieron
a avisar. No fue un estado histórico, fue una regresión silenciosa.

POR QUÉ ESTA PRUEBA ESTÁ ESCRITA AL REVÉS QUE LAS DOS ANTERIORES

Ha fallado dos veces, y las dos por la misma razón de fondo:

1. La primera versión comprobaba que el PAT aparecía EN ALGÚN SITIO DEL FICHERO.
   Se satisfacía con cualquier otra aparición —el `checkout`, la acción de
   Claude— y pasaba con la mutación puesta.
2. La segunda estrechó el ámbito a EN ALGÚN SITIO DEL PASO. Mejor, pero la misma
   forma: un paso con cuatro llamadas pasaba si UNA usaba el PAT. Así se coló el
   defecto que encontró la refutación de AUDITOR-V0-RUN-001: `sirius:failed-safely`
   se escribía en crudo en tres sitios y ese estado —justo el que existe para
   avisar de que la automatización se ha parado— no avisaba nunca.

Dos rondas, misma familia. La raíz no es el ámbito: es que preguntar «¿está
presente lo bueno?» se satisface con UNA aparición y no dice nada de las demás.
Estrechar el ámbito una tercera vez sería el tercer parche de la misma familia.

Esta versión pregunta lo contrario: **¿hay alguna escritura mala?** Para poder
responderlo sin interpretar shell —reconstruir desde fuera la semántica de otro
sistema es lo que costó quince defectos según ADR-001— el repositorio adopta una
convención que hace la respuesta textual:

    Ninguna función cruda de escritura de etiquetas se invoca directamente en un
    workflow. Solo se la llama desde una envoltura de UNA línea que exporta el
    PAT; el resto del guion llama a la envoltura.

Con esa convención, la comprobación no necesita saber qué es una subshell: basta
con que todo nombre crudo aparezca en una línea que también exporte el PAT.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
NOTIFICADOR = WORKFLOWS / "notify-sirius-state.yml"

ETIQUETA_EN_CONDICION = re.compile(r"github\.event\.label\.name == '(sirius:[a-z-]+)'")

# Las funciones que escriben etiquetas de verdad. Son las CRUDAS: escriben con el
# token que tengan delante, sea cual sea.
ESCRITORAS_CRUDAS = (
    "sirius_transition",
    "sirius_set_issue_labels",
    "sirius_apply_verdict.sh",
)

# Una línea que exporta el PAT. Es lo que convierte una llamada cruda en legítima.
EXPORTA_EL_PAT = re.compile(r'export\s+GH_TOKEN="\$\{?SIRIUS_TRIGGER_TOKEN')

# El secreto que lleva la identidad real.
PAT = "SIRIUS_BOT_TOKEN"


def _estados_notificables() -> set[str]:
    return set(ETIQUETA_EN_CONDICION.findall(NOTIFICADOR.read_text(encoding="utf-8")))


def _pasos_con_guion() -> list[tuple[str, str, dict[str, object]]]:
    """Todo paso con `run:` de TODOS los workflows.

    Se recorre el directorio entero en vez de una lista fija de ficheros. La
    lista fija era el otro agujero de la versión anterior: `review-sirius-work.yml`
    escribía `sirius:failed-safely` y no estaba en ella, así que nadie lo miraba.
    """
    pasos: list[tuple[str, str, dict[str, object]]] = []
    for ruta in sorted(WORKFLOWS.glob("*.yml")):
        definicion = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        for job in (definicion.get("jobs") or {}).values():
            for paso in job.get("steps") or []:
                if isinstance(paso, dict) and paso.get("run"):
                    pasos.append((ruta.name, str(paso.get("name") or "(sin nombre)"), paso))
    return pasos


def test_el_notificador_sigue_declarando_los_seis_estados_del_contrato() -> None:
    # Sin esto, la prueba siguiente se satisface vaciando el `if:` del notificador.
    estados = _estados_notificables()
    assert estados == {
        "sirius:implementing",
        "sirius:repair-requested",
        "sirius:ready-for-merge",
        "sirius:blocked-decision",
        "sirius:failed-safely",
        "sirius:completed",
    }, f"El contrato §7 declara seis estados notificables; el notificador escucha {estados}."


def test_ninguna_escritura_de_etiqueta_usa_el_github_token() -> None:
    """Por LLAMADA, y buscando la mala, no la buena.

    Un paso es legítimo de dos maneras, y solo de esas dos:

    - el paso entero corre con el PAT (`env.GH_TOKEN` es el secreto), o
    - cada aparición de una escritora cruda está en una línea que exporta el PAT,
      es decir, es la definición de la envoltura.

    Cualquier otra aparición es una escritura con el GITHUB_TOKEN.
    """
    infracciones: list[str] = []

    for fichero, nombre_paso, paso in _pasos_con_guion():
        guion = str(paso.get("run") or "")
        entorno = paso.get("env") or {}
        assert isinstance(entorno, dict)
        paso_con_pat = PAT in str(entorno.get("GH_TOKEN", ""))

        for numero, linea in enumerate(guion.splitlines(), start=1):
            for cruda in ESCRITORAS_CRUDAS:
                # Invocación, no mención: el nombre delimitado. Descarta los
                # comentarios que hablan de la función sin llamarla.
                if not re.search(rf"(?:^|[\s;(&|]){re.escape(cruda)}(?:\s|$)", linea):
                    continue
                if linea.lstrip().startswith("#"):
                    continue
                if paso_con_pat or EXPORTA_EL_PAT.search(linea):
                    continue
                infracciones.append(
                    f"{fichero} · paso «{nombre_paso}» · línea {numero} del guion: "
                    f"llama a `{cruda}` sin el PAT delante.\n      {linea.strip()}"
                )

    assert not infracciones, (
        "Estas escrituras de etiqueta van con el GITHUB_TOKEN. GitHub suprime ese "
        "`issues: labeled` y la notificación no llega nunca:\n\n"
        + "\n".join(f"  - {i}" for i in infracciones)
        + "\n\n  Arreglo: llamar a la envoltura de una línea que exporta "
        "SIRIUS_TRIGGER_TOKEN, no a la función cruda."
    )


def test_la_prueba_anterior_mira_donde_se_escriben_las_etiquetas() -> None:
    """Guardián de la guardiana.

    `test_ninguna_escritura_de_etiqueta_usa_el_github_token` pasa trivialmente si
    deja de encontrar llamadas —porque cambien los nombres de las funciones,
    porque el glob no encuentre los workflows, o porque el YAML deje de
    parsearse—. Una prueba que no puede fallar es peor que ninguna: dice que todo
    va bien. Esto ancla que sigue habiendo material que vigilar.
    """
    pasos = _pasos_con_guion()
    assert len(pasos) > 10, (
        f"Solo {len(pasos)} pasos con `run:`; el barrido no está leyendo los workflows."
    )

    con_escritura = [
        (fichero, nombre)
        for fichero, nombre, paso in pasos
        if any(cruda in str(paso.get("run") or "") for cruda in ESCRITORAS_CRUDAS)
    ]
    assert len(con_escritura) >= 8, (
        f"Solo {len(con_escritura)} pasos escriben etiquetas. Si el ciclo no ha "
        "encogido, es que los nombres de ESCRITORAS_CRUDAS han dejado de coincidir "
        f"y la prueba de arriba está vigilando el vacío. Encontrados: {con_escritura}"
    )

    ficheros = {fichero for fichero, _ in con_escritura}
    assert {
        "advance-sirius-after-quality.yml",
        "complete-sirius-after-merge.yml",
        "implement-sirius-work.yml",
        "repair-sirius-work.yml",
        "review-sirius-work.yml",
    } <= ficheros, f"Faltan workflows escritores conocidos; solo se ven {sorted(ficheros)}."
