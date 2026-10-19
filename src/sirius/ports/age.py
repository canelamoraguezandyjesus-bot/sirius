"""El puerto de la edad: la que aparenta una cara, y si se lee segura (pieza F de la 0.4,
ADR-264).

Sin tipos de ninguna biblioteca: el de verdad, con el modelo de la edad de InsightFace, vive
en ``sirius.adapters.recognition.age`` y se carga solo si está instalado, y las pruebas
ponen dobles. Lo que lee es el recorte de una cara que da la vista, tal como lo da.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AgeUnavailable(RuntimeError):
    """No se puede estimar la edad en este ordenador: falta lo que instala la orden, o no
    carga. Dice por qué en ``reason``."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class AgeReading:
    """La edad que aparenta una cara, en años, y si se lee segura: de lejos, o sin estar de
    frente, no."""

    years: int
    sure: bool


class AgeEstimator[Crop](Protocol):
    """Quien estima la edad de una cara."""

    #: Con qué la estima, para decirlo: «insightface».
    name: str

    def estimate(self, crop: Crop) -> AgeReading:
        """La edad que aparenta la cara de ``crop``. No guarda el recorte ni la edad."""
        ...
