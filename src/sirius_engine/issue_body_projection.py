"""Proyección determinista del cuerpo de incidencia (C2, incidencia #240).

``generar_cuerpo_incidencia`` reproduce la forma de la plantilla real
(``.github/ISSUE_TEMPLATE/sirius-work-item.yml``): las once secciones que
exige ``scripts/automation/validate_issue_body.py`` -Work ID, Bloque,
Objetivo, Base y dependencias, Alcance permitido, Fuera de alcance,
Requisitos y pruebas de aceptación, Validaciones obligatorias, Rama base,
Condiciones de parada, Salvaguardas-, con el contenido real del
``WorkItem`` proyectado en cada una, nunca relleno (C2-P2). El campo
declarativo ``Perfil: <ref>@<version>`` de A4
(:mod:`sirius_engine.profile_field`) viaja como una línea propia, para que
``parse_perfil_field`` lo reconozca igual que en cualquier incidencia real.

Determinista (mismo criterio que :func:`sirius_engine.worker_request.project_worker_request`):
mismo ``WorkItem`` + mismo ``profile_ref`` + mismos parámetros -> mismo
texto, siempre.
"""

from __future__ import annotations

from sirius_engine.domain.work_item import WorkItem
from sirius_engine.profile_field import ProfileRef, project_perfil_field

#: Mismo bloque de validaciones que declara por defecto
#: ``.github/ISSUE_TEMPLATE/sirius-work-item.yml``, con el prefijo ``uv run``
#: que exige este repositorio (ver ``AGENTS.md``).
VALIDACIONES_OBLIGATORIAS = (
    "- `uv run ruff format --check .`\n"
    "- `uv run ruff check .`\n"
    "- `uv run mypy src tests`\n"
    "- `uv run pytest`\n"
    "- `git diff --check`"
)

#: Mismo bloque que declara por defecto la plantilla real.
CONDICIONES_DE_PARADA = (
    "- `READY_FOR_REVIEW`\n"
    "- `BLOCKED_BY_DECISION`\n"
    "- `FAILED_SAFELY`\n"
    "- `USAGE_LIMIT_REACHED`\n"
    "- Merge automático prohibido."
)

#: Mismas tres salvaguardas irrenunciables de la plantilla real
#: (``safeguards`` de ``sirius-work-item.yml``): nunca tocar Producto ni
#: Arquitectura, nunca push directo a ``main``, nunca falsear pruebas, nunca
#: hacer merge automático.
SALVAGUARDAS = (
    "- No cambiar Producto, Arquitectura Técnica, ATD ni documentos canónicos "
    "sin decisión explícita.\n"
    "- No hacer push directo a `main`.\n"
    "- No reducir, saltar ni falsear ninguna prueba para conseguir verde.\n"
    "- No hacer merge automático: el merge sigue siendo un gesto explícito del propietario "
    "(contrato §8, sin cambios)."
)

_FUERA_DE_ALCANCE_POR_DEFECTO = (
    "Cualquier cambio no descrito en el objetivo y el alcance permitido de esta incidencia."
)


def generar_cuerpo_incidencia(
    work_item: WorkItem,
    *,
    profile_ref: ProfileRef,
    bloque: str,
    base_branch: str = "main",
) -> str:
    """Proyectar el cuerpo de incidencia de ``work_item``, listo para ``validate_issue_body.py``."""
    base_y_dependencias = (
        "Referencias autorizadas: " + ", ".join(work_item.contexto_origen) + "."
        if work_item.contexto_origen
        else "Sin referencias adicionales registradas para este WorkItem."
    )
    fuera_de_alcance = str(work_item.limites.get("fuera_de_alcance", _FUERA_DE_ALCANCE_POR_DEFECTO))
    plan_texto = (
        "\n\nPlan:\n" + "\n".join(f"- {paso}" for paso in work_item.plan) if work_item.plan else ""
    )
    return (
        "## Work ID\n\n"
        f"{work_item.work_id}\n\n"
        "## Bloque\n\n"
        f"{bloque}\n\n"
        f"{project_perfil_field(profile_ref)}\n\n"
        "## Objetivo\n\n"
        f"{work_item.objetivo}\n\n"
        "## Base y dependencias\n\n"
        f"{base_y_dependencias}\n\n"
        "## Alcance permitido\n\n"
        f"{work_item.entregable}\n\n"
        "## Fuera de alcance\n\n"
        f"{fuera_de_alcance}\n\n"
        "## Requisitos y pruebas de aceptación\n\n"
        f"{work_item.criterio_terminado}{plan_texto}\n\n"
        "## Validaciones obligatorias\n\n"
        f"{VALIDACIONES_OBLIGATORIAS}\n\n"
        "## Rama base\n\n"
        f"{base_branch}\n\n"
        "## Condiciones de parada\n\n"
        f"{CONDICIONES_DE_PARADA}\n\n"
        "## Salvaguardas\n\n"
        f"{SALVAGUARDAS}\n"
    )
