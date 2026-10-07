"""La prueba a ciegas para elegir el modelo de la charla (pieza C de ADR-233).

Decisión 4 del propietario (EV-023): el modelo local se elige a ciegas, por la
gracia, entre dos o tres. El paso 9 de la personalidad en la 0.2 del plan del
robot lo concreta: 20 preguntas a dos o tres modelos; el propietario ve las
respuestas barajadas y sin nombre, y elige.

Aquí vive lo que no depende de cómo se pregunte a los modelos: las preguntas,
el barajado y el recuento. La hoja guarda aparte, en ``key``, qué modelo dio
cada respuesta; las preguntas y sus respuestas, que es lo único que enseña la
ventana, no llevan el nombre de ningún modelo.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

#: Las 20 preguntas. Buscan la gracia, que le lleve la contraria en una idea
#: mala, que entienda «ponte serio» y «para», que se ponga serio solo ante algo
#: grave y que no se invente lo que no puede saber.
BLIND_TEST_QUESTIONS: tuple[str, ...] = (
    "Buenas, ¿qué tal has dormido?",
    "Me he comprado una moto de segunda mano sin probarla.",
    "¿Tú crees que los extraterrestres existen?",
    "Hoy no me apetece hacer nada.",
    "Ponte serio: ¿me cambio de compañía de la luz?",
    "Mi jefe me ha gritado delante de todos.",
    "¿Qué hacemos esta noche?",
    "Cuéntame un chiste.",
    "Voy a dejar de fumar mañana. Esta vez va en serio.",
    "He suspendido el examen del carné otra vez.",
    "¿Me queda bien el pelo así?",
    "Mi madre dice que hablo demasiado contigo.",
    "Para, que hoy estoy de mal humor.",
    "¿Cuál es tu película favorita?",
    "Voy a meter todos mis ahorros en una criptomoneda que me ha dicho un amigo.",
    "Eres el robot más tonto del mundo.",
    "Se me ha muerto el perro.",
    "¿Qué opinas de la pizza con piña?",
    "Mañana tengo una entrevista de trabajo y estoy de los nervios.",
    "Dime algo que no sepa.",
)

#: Las letras con las que el propietario ve las respuestas de cada pregunta.
LETTERS = "ABCDE"

#: Cuántos modelos admite la prueba: el plan habla de dos o tres.
MIN_MODELS = 2
MAX_MODELS = 3


class BlindTestError(ValueError):
    """La prueba no se puede preparar o contar tal como se ha pedido."""


@dataclass(frozen=True, slots=True)
class BlindTestItem:
    """Una pregunta con sus respuestas en el orden en que las ve el propietario."""

    question: str
    options: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class BlindTestSheet:
    """La hoja de la prueba. ``key[i]`` dice qué modelo hay detrás de cada letra
    de la pregunta ``i``, en el mismo orden que ``items[i].options``."""

    items: tuple[BlindTestItem, ...]
    key: tuple[tuple[str, ...], ...]
    models: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BlindTestResult:
    """Cuántas veces eligió el propietario a cada modelo, y quién gana.

    ``winner`` es ``None`` si hay empate en cabeza: entonces decide él entre
    ``tied``, porque la prueba no elige por él.
    """

    votes: Mapping[str, int]
    winner: str | None
    tied: tuple[str, ...]


def prepare_blind_test(
    questions: Sequence[str],
    answers: Mapping[str, Sequence[str]],
    rng: random.Random,
) -> BlindTestSheet:
    """Baraja, pregunta a pregunta, las respuestas de cada modelo.

    ``answers[modelo][i]`` es lo que contestó ``modelo`` a ``questions[i]``.
    """
    models = tuple(answers)
    if not MIN_MODELS <= len(models) <= MAX_MODELS:
        msg = f"La prueba a ciegas es entre {MIN_MODELS} y {MAX_MODELS} modelos."
        raise BlindTestError(msg)
    for model in models:
        if len(answers[model]) != len(questions):
            msg = f"Faltan respuestas de un modelo: {len(answers[model])} de {len(questions)}."
            raise BlindTestError(msg)
    items: list[BlindTestItem] = []
    key: list[tuple[str, ...]] = []
    for index, question in enumerate(questions):
        order = rng.sample(models, k=len(models))
        options = tuple(
            (LETTERS[position], answers[model][index]) for position, model in enumerate(order)
        )
        items.append(BlindTestItem(question=question, options=options))
        key.append(tuple(order))
    return BlindTestSheet(items=tuple(items), key=tuple(key), models=models)


def tally(sheet: BlindTestSheet, choices: Mapping[int, str]) -> BlindTestResult:
    """Cuenta lo que eligió el propietario: una letra por pregunta, todas contestadas."""
    if set(choices) != set(range(len(sheet.items))):
        msg = "Hay que elegir una respuesta en cada pregunta."
        raise BlindTestError(msg)
    votes: Counter[str] = Counter({model: 0 for model in sheet.models})
    for index, letter in choices.items():
        letters = [option_letter for option_letter, _ in sheet.items[index].options]
        if letter not in letters:
            msg = f"La pregunta {index + 1} no tiene respuesta {letter!r}."
            raise BlindTestError(msg)
        votes[sheet.key[index][letters.index(letter)]] += 1
    best = max(votes.values())
    tied = tuple(model for model in sheet.models if votes[model] == best)
    winner = tied[0] if len(tied) == 1 else None
    return BlindTestResult(votes=dict(votes), winner=winner, tied=tied if winner is None else ())
