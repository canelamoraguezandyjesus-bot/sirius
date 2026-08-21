"""Doble de pruebas de :class:`RunActionsProbe` (C1, incidencia #232).

Mismo patrón que :class:`~sirius_engine.adapters.fixture_mirror.FixedGitHubMirrorReader`
(A3): respuestas fijas por clave, y una clave sin configurar devuelve
``NO_DISPONIBLE`` en vez de fallar con ``KeyError``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sirius_engine.ports.run_actions_probe import LecturaEstado, LecturaRunActionsSnapshot


@dataclass
class FixedRunActionsProbe:
    """Implementación de :class:`RunActionsProbe` respaldada por respuestas fijas."""

    snapshots_por_run: dict[tuple[str, str], LecturaRunActionsSnapshot] = field(
        default_factory=dict
    )

    def leer(self, *, repo: str, run_id: str) -> LecturaRunActionsSnapshot:
        return self.snapshots_por_run.get(
            (repo, run_id),
            LecturaRunActionsSnapshot(
                estado=LecturaEstado.NO_DISPONIBLE, error="fixture sin configurar"
            ),
        )
