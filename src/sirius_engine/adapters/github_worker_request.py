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
    echo "- Plazo de esta ejecución (ADR-228): tu paso muere a las ${plazo_utc} UTC
    (${PLAZO_MIN} minutos desde ahora; ...)"
    echo "- El archivo de veredicto debe escribirse en la ruta exacta de la
    variable de entorno SIRIUS_VERDICT_FILE."
    echo "SIRIUS_PROMPT_EOF"

Desde ADR-228 el contexto lleva el reloj del implementador: dos horas que el
workflow calcula con ``date -u`` al preparar el prompt. La proyección las
reproduce a partir de ``ahora`` (:func:`linea_de_plazo`), con los MISMOS
números que el YAML (``PLAZO_DEL_IMPLEMENTADOR_MIN``,
``RESERVA_PARA_LA_VALIDACION_MIN``; una guarda en
``tests/automation/test_implementador_con_reloj.py`` exige que coincidan), y
la prueba de no-divergencia fija la hora del guión con un ``date`` de arnés.
Sin ``ahora`` la proyección no lleva la línea: es el prompt tal como era
antes del reloj, y se declara.

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

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sirius_engine.domain.profile import AgentProfile

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Los dos números del reloj del implementador (ADR-228), los mismos que fija el
#: paso del prompt del workflow (`PLAZO_MIN`, `RESERVA_MIN`).
PLAZO_DEL_IMPLEMENTADOR_MIN = 50
RESERVA_PARA_LA_VALIDACION_MIN = 16

_CONTEXTO_TEMPLATE = (
    "\n"
    "## Contexto de esta ejecución\n"
    "- Repositorio: {repo}\n"
    "- Incidencia de trabajo: #{issue_number}\n"
    "- Rama base: {base_branch}\n"
    "{plazo}"
    "- El archivo de veredicto debe escribirse en la ruta exacta de la variable"
    " de entorno SIRIUS_VERDICT_FILE.\n"
)

_LINEA_DE_PLAZO = (
    "- Plazo de esta ejecución (ADR-228): tu paso muere a las {plazo_utc} UTC "
    "({plazo_min} minutos desde ahora; comprueba la hora con `date -u`). Arranca la "
    "validación final no más tarde de las {limite_validacion_utc} UTC: la cadena completa "
    "tarda entre 9 y 15 minutos. Si a esa hora no has terminado, deja de implementar, "
    "valida lo hecho una sola vez, empuja lo que tengas y escribe el veredicto con lo hecho "
    "y lo que falta (`FAILED_SAFELY` si no está entregable): un diagnóstico a tiempo vale "
    "más que morir en el tope sin decir nada.\n"
)


def linea_de_plazo(ahora: datetime) -> str:
    """La línea del reloj tal como la escribe el workflow para un prompt preparado en ``ahora``."""
    instante = ahora.astimezone(UTC)
    return _LINEA_DE_PLAZO.format(
        plazo_utc=(instante + timedelta(minutes=PLAZO_DEL_IMPLEMENTADOR_MIN)).strftime("%H:%M:%SZ"),
        plazo_min=PLAZO_DEL_IMPLEMENTADOR_MIN,
        limite_validacion_utc=(
            instante
            + timedelta(minutes=PLAZO_DEL_IMPLEMENTADOR_MIN - RESERVA_PARA_LA_VALIDACION_MIN)
        ).strftime("%H:%M:%SZ"),
    )


def read_procedure_text(profile: AgentProfile, *, repo_root: Path | None = None) -> str:
    """Leer el procedimiento del perfil tal cual está en el árbol.

    Es la única fuente de verdad del texto: nunca se duplica el contenido de
    ``prompts/*.md`` dentro del perfil, para que ambos no puedan divergir.
    """
    raiz = repo_root if repo_root is not None else _REPO_ROOT
    return (raiz / profile.procedimiento_ref).read_text(encoding="utf-8")


def project_github_prompt(
    *,
    procedure_text: str,
    repo: str,
    issue_number: int,
    base_branch: str = "main",
    ahora: datetime | None = None,
) -> str:
    """Reproducir la concatenación exacta del paso "Preparar instrucciones..." del workflow.

    ``ahora`` es el instante en que el workflow prepara el prompt: con él la
    proyección lleva la línea del reloj (ADR-228); sin él, no la lleva.
    """
    return procedure_text + _CONTEXTO_TEMPLATE.format(
        repo=repo,
        issue_number=issue_number,
        base_branch=base_branch,
        plazo=linea_de_plazo(ahora) if ahora is not None else "",
    )
