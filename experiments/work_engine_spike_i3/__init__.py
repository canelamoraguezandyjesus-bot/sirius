"""Spike I3 (incidencia #182): patrón de escritura seguro del almacén del Work Engine.

Código desechable (ADR-020, ADR-026): evalúa el patrón, no fija la
representación definitiva del almacén. Reutiliza el dominio y el puerto de
A1 (:mod:`sirius_engine`) sin reimplementarlos.
"""

from __future__ import annotations
