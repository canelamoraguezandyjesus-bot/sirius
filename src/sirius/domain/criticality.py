"""Criticality: a second, independent signal on ``Memory``/``Decision`` —
*how much it matters*, not *what it is about* (``category``, D7).

Decisión 1 del propietario (02-09-2026,
``docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md``, sección
«Decisión del propietario y plan»; ADR-126): el laboratorio deriva la
categoría de la criticidad, y producción etiquetaba por tema, así que ni el
índice de categoría ni la regla de rescate RF-25/RF-26 veían lo crítico. La
señal correcta es la del propio canon de 47 casos, ``criticidad.nivel``: dos
valores posibles, nunca más. ``None`` — "nadie la ha marcado" — no es un
miembro del enum, igual que ``category`` es ``str | None`` con ``None`` fuera
de cualquier vocabulario.

M18b (este módulo) solo introduce la señal; no la cablea a nada (M19 el
índice y el rescate, M20 la siembra, M21 la propuesta automática).
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Criticality"]


class Criticality(StrEnum):
    """Los dos niveles de criticidad que el canon reconoce. Un ``Memory``/
    ``Decision`` sin marcar tiene ``criticality is None`` — ordinario — que
    deliberadamente no es un tercer miembro de este enum."""

    CRITICO = "CRITICO"
    IMPORTANTE = "IMPORTANTE"
