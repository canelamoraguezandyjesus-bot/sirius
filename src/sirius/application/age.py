"""La regla de los críos y los ancianos frágiles: con la edad que aparenta cada cara, y ante
la duda, no insulta (pieza F de la 0.4, ADR-264).

- **Quién pide cuidado**: quien aparenta menos de ``CHILD_UNDER`` años, un crío; quien
  aparenta ``ELDER_FROM`` o más, un anciano; y aquel cuya edad no se lee segura o no se
  puede estimar. Son 18 y 70 con un margen: el modelo se equivoca en años, y equivocarse a
  un lado cuesta un insulto a un crío, y al otro, un Sirius más majo.
- **La regla** va en las instrucciones de la petición cuando hay alguien así delante de la
  cámara; sin cámara no se sabe quién hay, y no va: la semilla sigue diciendo lo suyo.
- **El estimador se carga la primera vez** que hace falta, en el hilo de la vista. Si no
  carga, se dice una vez por qué y no se vuelve a intentar; desde entonces, la edad de
  quien aparezca no se sabe, y eso es duda.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence

from sirius.infrastructure.logging import get_logger
from sirius.ports.age import AgeEstimator, AgeReading, AgeUnavailable

_logger = get_logger(__name__)

#: Por debajo de esto, un crío.
CHILD_UNDER = 20
#: Desde esto, un anciano.
ELDER_FROM = 65
#: El título de la regla y lo que dice.
CARE_HEADING = "# Con quién te cortas"
CARE_RULE = (
    "Delante tienes a un crío, a un anciano o a alguien cuya edad no ves clara: nada de "
    "insultos ni de burradas, ni en broma. Te cortas y eres majo."
)


def needs_care(readings: Sequence[AgeReading | None]) -> bool:
    """Si alguno de ``readings`` pide cuidado: un crío, un anciano, o una edad que no se lee
    segura o no se sabe."""
    return any(
        reading is None
        or not reading.sure
        or reading.years < CHILD_UNDER
        or reading.years >= ELDER_FROM
        for reading in readings
    )


def care_block() -> str:
    """La regla, con su título, para las instrucciones de la petición."""
    return f"{CARE_HEADING}\n{CARE_RULE}"


class Ages[Crop]:
    """La edad que aparenta cada cara, con el estimador que se carga la primera vez."""

    def __init__(self, load: Callable[[], AgeEstimator[Crop]]) -> None:
        self._load = load
        self._lock = threading.Lock()
        self._estimator: AgeEstimator[Crop] | None = None
        #: Por qué no se puede estimar, si no carga; vacío si carga o aún no lo ha intentado.
        self._unavailable = ""
        self._failed = False

    @property
    def unavailable(self) -> str:
        """Por qué no se puede estimar la edad; vacío si se puede o aún no se ha intentado."""
        return self._unavailable

    @property
    def name(self) -> str:
        """Con qué la estima, una vez cargado; vacío si aún no."""
        estimator = self._estimator
        return "" if estimator is None else estimator.name

    def estimate(self, crop: Crop) -> AgeReading | None:
        """La edad que aparenta la cara de ``crop``; ``None`` si no se puede estimar. Un
        fallo al estimarla se apunta una vez, con su tipo, y esa vez no se sabe."""
        estimator = self._ensure()
        if estimator is None:
            return None
        try:
            return estimator.estimate(crop)
        except Exception as error:
            if not self._failed:
                self._failed = True
                _logger.error("El estimador de la edad ha fallado (%s)", type(error).__name__)
            return None

    def _ensure(self) -> AgeEstimator[Crop] | None:
        estimator = self._estimator
        if estimator is not None:
            return estimator
        with self._lock:
            if self._estimator is not None:
                return self._estimator
            if self._unavailable:
                return None
            try:
                self._estimator = self._load()
            except AgeUnavailable as error:
                self._unavailable = error.reason
            except Exception as error:
                self._unavailable = f"el modelo de la edad no carga ({error})"
            else:
                return self._estimator
            _logger.info("No se puede estimar la edad: %s", self._unavailable)
            return None
