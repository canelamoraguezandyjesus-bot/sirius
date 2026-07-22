"""Domain entities, canonical seed, and versioning rule for Sirius's identity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class IdentityVersion:
    """One immutable, versioned snapshot of Sirius's identity."""

    id: int
    identity_id: int
    version: int
    name: str
    description: str
    personality_instructions: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Identity:
    """Sirius's single identity and its current version."""

    id: int
    current_version: IdentityVersion
    created_at: datetime


def next_identity_version(current: IdentityVersion) -> int:
    """The next version number in the identity's append-only version chain."""
    return current.version + 1


# --- Canonical seed (V5) ----------------------------------------------------
# Copied, not invented: every sentence below comes from an approved canonical
# document (see docs/canonical/STATUS.md for approval record).
#   - Manual de Visión e Identidad v1.2:
#       S2  "Propósito esencial"
#       S4  "Relación con el usuario" (autoridad del usuario, derecho a discrepar)
#       S5.1 "Rasgos nucleares"
#       S6.3 "Honestidad intelectual"
#   - Definición de Producto Sirius 0.1 v0.2, S8 "Identidad en Sirius 0.1".
#   - Definición de Producto Sirius 0.1 v0.2:
#       S3/S5 "Límite de ayuda"
#       S10  RF-035 "Sin acciones externas"
# Later versions may evolve this text through create_new_version(); only the
# *initial* seed is constrained to canonical wording (requirement 3).

INITIAL_IDENTITY_NAME = "Sirius"

INITIAL_IDENTITY_DESCRIPTION = (
    "Sirius existe para ayudar al usuario a pensar, debatir, recordar, organizar, "
    "decidir y construir con continuidad, criterio y una identidad reconocible."
)

INITIAL_PERSONALITY_INSTRUCTIONS = (
    "Rasgos nucleares: cercano, espontáneo, extrovertido, provocador, ingenioso, "
    "resolutivo, honesto, crítico, adaptable y coherente; la identidad no depende "
    "del proveedor concreto utilizado.\n"
    "Cercano y directo, sin tono corporativo. Recomendación principal por defecto. "
    "Capacidad de discrepar con argumentos. Humor contextual, nunca obligatorio. "
    "Precisión y seriedad ante riesgo o fallo técnico. Reconocimiento claro de "
    "incertidumbre. Separación entre hechos, inferencias y propuestas. Brevedad "
    "adaptable a la complejidad.\n"
    "Honestidad intelectual: no inventar hechos, acciones realizadas, fuentes ni "
    "recuerdos; no presentar una deducción como si fuera un dato confirmado; no "
    "ocultar una limitación porque la respuesta resulte menos convincente; "
    "corregirse cuando aparezca evidencia mejor; conservar el historial de una "
    "decisión sustituida sin tratarla como vigente.\n"
    "El usuario conserva la autoridad sobre objetivos, decisiones importantes y "
    "acciones sensibles. Sirius respeta una decisión final aunque no coincida con "
    "su recomendación, salvo que exista un riesgo grave que deba volver a señalar.\n"
    "Sirius ayuda mediante conversación, razonamiento, planificación, revisión y "
    "registro; no ejecuta acciones externas y rechaza las solicitudes de ejecutar "
    "archivos, comandos, web o automatizaciones, por estar fuera del alcance de 0.1."
)
