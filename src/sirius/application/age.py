"""La regla de los críos y los ancianos frágiles: con la edad que aparenta cada cara, y ante
la duda, no insulta (pieza F de la 0.4, ADR-264).

- **Quién pide cuidado**: quien aparenta menos de ``CHILD_UNDER`` años, un crío; quien
  aparenta ``ELDER_FROM`` o más, un anciano; y aquel cuya edad no se lee segura o no se
  puede estimar. Son 18 y 70 con un margen: el modelo se equivoca en años, y equivocarse a
  un lado cuesta un insulto a un crío, y al otro, un Sirius más majo.
- **La regla** va en las instrucciones de la petición cuando hay alguien así delante de la
  cámara; sin cámara no se sabe quién hay, y no va: la semilla sigue diciendo lo suyo. Va
  en toda petición con la que el modelo escribe como Sirius, no solo en la charla: lo
  decide ``CareWatch``, uno para todas, y ``CARE_COVERAGE`` dice de cada petición al
  modelo si la lleva o por qué no (ronda 2 de Codex sobre la PR #703).
- **El estimador se carga la primera vez** que hace falta, en el hilo de la vista. Si no
  carga, se dice una vez por qué y no se vuelve a intentar; desde entonces, la edad de
  quien aparezca no se sabe, y eso es duda.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from typing import Final

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


#: La petición escribe como Sirius y lleva la regla cuando hace falta (``CareWatch``).
CARRIES_THE_RULE: Final = "escribe como Sirius y lleva la regla cuando hace falta"

#: Cada petición al modelo, por la función que la construye, y si lleva la regla o por qué
#: no. Una petición nueva no puede quedarse fuera sin que nadie lo decida: lo vigila
#: ``tests/unit/test_regla_en_cada_peticion.py``, que las busca todas en el código (ronda
#: 2 de Codex sobre la PR #703: la regla iba puesta camino a camino, y a cada camino nuevo
#: se le olvidaba).
CARE_COVERAGE: Final[dict[str, str]] = {
    "sirius.application.send_message.SendMessageUseCase._send": CARRIES_THE_RULE,
    "sirius.application.send_message.CommandVoice.request": CARRIES_THE_RULE,
    "sirius.application.blind_test._answer": CARRIES_THE_RULE,
    "sirius.application.trick_questions._complete": CARRIES_THE_RULE,
    "sirius.application.reply_judge.LLMReplyJudge._ask": (
        "puntúa una respuesta ya escrita: no escribe nada que lea u oiga nadie"
    ),
    "sirius.application.robot_conversation.LLMConversationSummarizer.summarize": (
        "resume la charla para la memoria, en tercera persona: no se le enseña a nadie"
    ),
    "sirius.application.dream.LLMFactExtractor.extract": (
        "saca hechos de la charla para la memoria: no se le enseña a nadie"
    ),
}


class CareWatch:
    """Si hay que cortarse: con alguien delante que pide cuidado (``needs_care``), sí; si
    no se puede saber la edad de nadie, también, ante la duda, y se apunta una vez; sin
    vista que lo diga, no. Uno por cada sitio que pide al modelo que escriba como Sirius,
    todos con la misma lectura de la vista."""

    def __init__(
        self, in_front_ages: Callable[[], Sequence[AgeReading | None] | None] | None = None
    ) -> None:
        self._ages = in_front_ages
        self._failed = False

    def watch(self, in_front_ages: Callable[[], Sequence[AgeReading | None] | None]) -> None:
        """Le dice de dónde saber la edad que aparentan los que tiene delante: de la vista,
        la de cada uno o ``None`` si no se sabe, o ``None`` si no ve."""
        self._ages = in_front_ages

    def needed(self) -> bool:
        """Si delante hay alguien con quien se corta, o no se sabe."""
        ages = self._ages
        if ages is None:
            return False
        try:
            readings = ages()
        except Exception as error:
            if not self._failed:
                self._failed = True
                _logger.warning(
                    "No se sabe la edad de los que tiene delante (%s)", type(error).__name__
                )
            return True
        return readings is not None and needs_care(readings)

    def block(self) -> str:
        """La regla, con su título, si hace falta; vacío si no."""
        return care_block() if self.needed() else ""


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
