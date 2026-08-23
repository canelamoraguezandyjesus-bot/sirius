"""Compatibilidad de los scripts de automatización con el Python del runner.

Los workflows de automatización invocan estos scripts con `python3` a secas y
**sin** `actions/setup-python`: se ejecutan con el intérprete del sistema del
runner `ubuntu-latest`, que hoy es 3.12. El proyecto, en cambio, se desarrolla y
se valida con 3.14 (`requires-python`), así que la sintaxis nueva pasa Quality
sin problema y revienta en producción — donde no hay ninguna prueba mirando.

Ya ocurrió: `except OSError, json.JSONDecodeError:` (PEP 758, 3.14) se coló en
`sirius_convergence.py`. Quality lo dio por bueno; en el runner habría sido un
`SyntaxError` al arrancar, es decir, la puerta de convergencia caída en todas
las rondas. Se detectó por lectura, no por una prueba. Esta prueba cierra ese
hueco: analiza cada script con la versión de lenguaje del runner y falla si usa
sintaxis que ese intérprete no entiende.

Alcance honesto: `ast.parse(feature_version=...)` comprueba **sintaxis**, no
biblioteca estándar. Un `itertools.batched` (3.12) o un módulo nuevo pasarían
esta prueba y fallarían en tiempo de ejecución. Cubre la clase de fallo que ya
se ha materializado aquí, no todas las incompatibilidades imaginables.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOMATION_DIR = REPO_ROOT / "scripts" / "automation"

# Versión del intérprete del sistema en el runner `ubuntu-latest` (Ubuntu 24.04).
# Si los workflows pasan a fijar el intérprete con `actions/setup-python`, este
# par debe subir en el mismo cambio: es la única definición del contrato.
RUNNER_PYTHON = (3, 12)

# Scripts que los workflows o la biblioteca Bash ejecutan con `python3` a secas.
# Se listan de forma explícita para que añadir un script nuevo a un workflow
# obligue a incluirlo aquí conscientemente.
SCRIPTS_RUN_ON_THE_RUNNER = (
    # `sirius_check_docs.py` NO lo descubre `test_the_listed_scripts_are_the_ones_
    # the_workflows_invoke`: esa derivación recorre `.github/workflows/*.yml` y
    # `scripts/automation/*.sh`, y este script se invoca desde el campo
    # «Validaciones obligatorias» del cuerpo de un Work Item, que no es un
    # fichero del árbol. La derivación no está mal; es ciega a ese sitio de
    # invocación, y por eso este va a mano y con este comentario.
    "sirius_check_docs.py",
    "sirius_aggregate_reviews.py",
    "sirius_codex_review.py",
    "sirius_convergence.py",
    "validate_issue_body.py",
)

#: El módulo compartido no vive en `scripts/automation/` -vive en el paquete,
#: y `sirius_convergence.py` lo carga por ruta de fichero (H-13, incidencia
#: #275)-, así que no puede entrar en la tupla de arriba, que resuelve nombres
#: contra ese directorio. Pero lo compila el MISMO `python3` del runner en
#: cuanto `sirius_convergence.py` lo carga, así que necesita exactamente la
#: misma comprobación, y por eso tiene la suya propia justo debajo.
MODULO_COMPARTIDO = (
    Path(__file__).resolve().parents[2] / "src" / "sirius_engine" / "round_history.py"
)


@pytest.mark.parametrize("name", SCRIPTS_RUN_ON_THE_RUNNER)
def test_script_parses_with_the_runner_python(name: str) -> None:
    path = AUTOMATION_DIR / name
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(path), feature_version=RUNNER_PYTHON)
    except SyntaxError as exc:  # pragma: no cover - el mensaje es el valor
        version = ".".join(str(part) for part in RUNNER_PYTHON)
        pytest.fail(
            f"{name} usa sintaxis que Python {version} no entiende "
            f"(línea {exc.lineno}): {exc.msg}. Los workflows lo ejecutan con el "
            f"`python3` del sistema del runner ({version}), no con el intérprete "
            "del entorno de desarrollo."
        )


def test_el_modulo_compartido_tambien_compila_con_el_python_del_runner() -> None:
    """Lo carga `sirius_convergence.py`, que corre con el `python3` del sistema."""
    source = MODULO_COMPARTIDO.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(MODULO_COMPARTIDO), feature_version=RUNNER_PYTHON)
    except SyntaxError as exc:  # pragma: no cover - el mensaje es el valor
        version = ".".join(str(part) for part in RUNNER_PYTHON)
        pytest.fail(
            f"round_history.py usa sintaxis que Python {version} no entiende "
            f"(línea {exc.lineno}): {exc.msg}. Lo carga sirius_convergence.py, que "
            "los workflows ejecutan con el `python3` del sistema del runner."
        )


def test_the_listed_scripts_are_the_ones_the_workflows_invoke() -> None:
    """La lista no puede quedarse atrás sin que nadie se entere.

    Recorre los workflows y la biblioteca Bash buscando invocaciones
    `python3 ... <algo>.py` y comprueba que todo script de
    `scripts/automation` que aparezca esté en la lista de arriba.
    """
    invoked: set[str] = set()
    sources = list((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    sources += list(AUTOMATION_DIR.glob("*.sh"))
    for source_path in sources:
        text = source_path.read_text(encoding="utf-8")
        for token in text.replace('"', " ").replace("'", " ").split():
            if token.endswith(".py") and (AUTOMATION_DIR / Path(token).name).is_file():
                invoked.add(Path(token).name)

    missing = invoked - set(SCRIPTS_RUN_ON_THE_RUNNER)
    assert not missing, (
        f"Estos scripts se invocan desde workflows o desde la biblioteca Bash pero no "
        f"están cubiertos por la comprobación de sintaxis del runner: {sorted(missing)}"
    )
