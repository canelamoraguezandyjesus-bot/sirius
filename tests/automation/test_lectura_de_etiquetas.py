"""Ninguna lectura de etiquetas depende del endpoint `/issues/{n}/labels`.

El 17 de agosto de 2026, con el mismo token y en el mismo instante,
`gh api repos/{o}/{r}/issues/186` respondía y
`gh api repos/{o}/{r}/issues/186/labels` devolvía **cuerpo vacío**. Cuatro
reintentos, cuatro fallos, en cuatro ejecuciones distintas a lo largo de más de
una hora (runs 32035648135, 32037335181, 32039249452 y 32039796936 de la
incidencia #186). Que una respondiera y la otra no descarta permisos,
autenticación y límite de tasa: los tres habrían roto ambas.

El objeto de la incidencia ya trae `labels`, así que
``gh api repos/{o}/{r}/issues/{n} --jq '.labels[].name'`` da exactamente los
mismos nombres por una vía que sí responde — y ahorra una llamada.

Estas pruebas impiden que alguien vuelva al endpoint roto por costumbre. No
afirman que el endpoint esté mal en general ni que GitHub no lo arregle: afirman
que esta automatización no depende de él, que es lo único que está en nuestra
mano.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "automation"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# El directorio ES la lista: un script nuevo queda cubierto sin que nadie tenga
# que acordarse de añadirlo aquí.
SCRIPTS = sorted(SCRIPTS_DIR.glob("*.sh"))
WORKFLOWS = sorted(WORKFLOWS_DIR.glob("*.yml"))

# Una LLAMADA a `…/issues/<n>/labels`, no la mención del endpoint.
#
# La primera versión de esta expresión buscaba solo `issues/<algo>/labels`, y
# marcó como defecto los comentarios que explican por qué no se usa —castigando
# justo la documentación del arreglo—. Exigir `gh api` en la misma línea deja
# hablar del endpoint y prohíbe únicamente llamarlo. Cubre las tres formas en
# uso (`gh api`, `sirius_retry gh api`, `sirius_retry _sirius_gh api`), porque
# todas contienen `gh api` como subcadena.
ENDPOINT_ROTO = re.compile(r"gh api[^\n]*?issues/[^\"'\s]*?/labels")


def test_hay_scripts_y_workflows_que_comprobar() -> None:
    """Un glob vacío haría que todo lo demás pasara sin comprobar nada."""
    assert SCRIPTS, f"no se encontró ningún script en {SCRIPTS_DIR}"
    assert WORKFLOWS, f"no se encontró ningún workflow en {WORKFLOWS_DIR}"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_ningun_script_lee_las_etiquetas_por_el_endpoint_roto(script: Path) -> None:
    encontrados = ENDPOINT_ROTO.findall(script.read_text(encoding="utf-8"))
    assert not encontrados, (
        f"{script.name} vuelve a leer las etiquetas por `/issues/<n>/labels`, que "
        f"devolvió cuerpo vacío durante más de una hora el 17-08-2026 ({encontrados}). "
        "Usa `gh api repos/<o>/<r>/issues/<n> --jq '.labels[].name'`."
    )


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_ningun_workflow_lee_las_etiquetas_por_el_endpoint_roto(workflow: Path) -> None:
    encontrados = ENDPOINT_ROTO.findall(workflow.read_text(encoding="utf-8"))
    assert not encontrados, (
        f"{workflow.name} vuelve a leer las etiquetas por `/issues/<n>/labels` "
        f"({encontrados}). Usa `gh api repos/<o>/<r>/issues/<n> --jq '.labels[].name'`."
    )


def test_la_alternativa_esta_realmente_en_uso() -> None:
    """La prohibición sola sería vacua: podría cumplirse sin leer etiquetas.

    Sin esto, borrar toda lectura de etiquetas dejaría las pruebas de arriba en
    verde mientras la automatización pierde una comprobación que sí necesita.
    """
    alternativa = re.compile(r"--jq\s+'\.labels\[\]\.name'")
    usos = [s.name for s in SCRIPTS if alternativa.search(s.read_text(encoding="utf-8"))]
    assert usos, "ningún script lee ya las etiquetas: la prohibición se cumple en vacío"
