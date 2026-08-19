"""Adapter GitHub: proyección textual del ``WorkerRequest`` (arquitectura §7.1, §5.1).

Reproduce EXACTAMENTE la concatenación que hoy hace el paso "Preparar
instrucciones para Claude Code" de
``.github/workflows/implement-sirius-work.yml`` -leído para esta prueba,
nunca modificado (incidencia #202, alcance permitido):

.. code-block:: bash

    echo "prompt<<SIRIUS_PROMPT_EOF"
    cat scripts/automation/prompts/implementer.md
    echo ""
    echo "## Contexto de esta ejecución"
    echo "- Repositorio: ${GH_REPO}"
    echo "- Incidencia de trabajo: #${ISSUE_NUMBER}"
    echo "- Rama base: main"
    echo "- El archivo de veredicto debe escribirse en la ruta exacta de la
    variable de entorno SIRIUS_VERDICT_FILE."
    echo "SIRIUS_PROMPT_EOF"

``cat`` imprime el fichero tal cual -incluido su salto de línea final-, así
que la reproducción exacta necesita el mismo salto de línea EXTRA que aporta
el ``echo ""`` antes del bloque de contexto: por eso este módulo no recorta
ni añade ningún carácter al ``procedure_text`` leído, solo concatena.

La prueba de no-divergencia (A4-P2, ``tests/engine/test_worker_request.py``)
ejecuta el guión bash real de ese paso, con variables de entorno de una
incidencia fixture, y compara su salida byte a byte contra
:func:`project_github_prompt`.
"""

from __future__ import annotations

from pathlib import Path

from sirius_engine.domain.profile import AgentProfile

_REPO_ROOT = Path(__file__).resolve().parents[3]

_CONTEXTO_TEMPLATE = (
    "\n"
    "## Contexto de esta ejecución\n"
    "- Repositorio: {repo}\n"
    "- Incidencia de trabajo: #{issue_number}\n"
    "- Rama base: {base_branch}\n"
    "- El archivo de veredicto debe escribirse en la ruta exacta de la variable"
    " de entorno SIRIUS_VERDICT_FILE.\n"
)


def read_procedure_text(profile: AgentProfile, *, repo_root: Path | None = None) -> str:
    """Leer el procedimiento del perfil tal cual está en el árbol.

    Es la única fuente de verdad del texto: nunca se duplica el contenido de
    ``prompts/*.md`` dentro del perfil, para que ambos no puedan divergir.
    """
    raiz = repo_root if repo_root is not None else _REPO_ROOT
    return (raiz / profile.procedimiento_ref).read_text(encoding="utf-8")


def project_github_prompt(
    *, procedure_text: str, repo: str, issue_number: int, base_branch: str = "main"
) -> str:
    """Reproducir la concatenación exacta del paso "Preparar instrucciones..." del workflow."""
    return procedure_text + _CONTEXTO_TEMPLATE.format(
        repo=repo, issue_number=issue_number, base_branch=base_branch
    )
