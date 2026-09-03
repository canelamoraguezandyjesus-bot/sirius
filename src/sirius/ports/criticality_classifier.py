"""Port for automatic criticality proposal (M21a, ADR-130).

A single-method ``Protocol`` calcado de ``CategoryClassifierPort``, con una
diferencia deliberada en el nombre del método (``propose``, no
``classify``): esta señal nunca se escribe automáticamente (M18b, ADR-126 —
«Sirius propone, el usuario decide»), así que ningún caller puede tratar su
resultado como si fuera ya una decisión tomada.
"""

from __future__ import annotations

from typing import Protocol

from sirius.domain.criticality import Criticality

__all__ = ["CriticalityClassifierPort"]


class CriticalityClassifierPort(Protocol):
    """Propone un nivel de criticidad para un contenido, sin decidirlo.

    Implementations must never propagate an exception: any internal failure
    (model unavailable, connection refused, timeout, a response outside the
    two-level vocabulary) is reported as ``None`` — exactly like "I could not
    decide" — never as a raised error. ``None`` does NOT mean "ordinario"
    (that is a real, user-decidable outcome): it means there is no proposal
    at all. Callers (``ProposeCriticalityUseCase``) rely on this to fail open
    without a ``try``/``except`` of their own.
    """

    def propose(self, content: str) -> Criticality | None:
        """Return a proposed ``Criticality``, or ``None`` if no confident
        proposal could be made."""
        ...
