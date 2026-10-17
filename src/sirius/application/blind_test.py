"""Caso de uso de la prueba a ciegas: elegir el modelo de la charla (pieza C de ADR-233).

Pregunta las 20 preguntas a dos o tres modelos con la misma identidad con la
que conversa Sirius, prepara la hoja barajada y sin nombres, cuenta lo que
elige el propietario y, cuando él confirma, deja el modelo ganador para la
charla. Elegir no pasa nunca sin él: ``choose`` solo lo llama la ventana
cuando el propietario pulsa.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence

from sirius.application.seed_examples import SeedExamplePicker
from sirius.application.send_message import render_identity
from sirius.domain.blind_test import (
    BLIND_TEST_QUESTIONS,
    CHAT_CAPABILITY,
    NOT_A_CHAT_MODEL,
    BlindTestError,
    BlindTestResult,
    BlindTestSheet,
    OfferedModels,
    prepare_blind_test,
    tally,
)
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.llm import LLMCompleted, LLMError, LLMProvider, LLMRequest

__all__ = ["RETRY_ADVICE", "BlindTestUseCase"]

#: Lo que dice el aviso de un modelo que no contesta: qué hacer (ADR-247).
RETRY_ADVICE = "Vuelve a pulsar Empezar; si se repite, desmarca ese modelo."


class BlindTestUseCase:
    """Prepara la prueba, la cuenta y deja el modelo elegido para la charla."""

    def __init__(
        self,
        *,
        identity_repository: IdentityRepository,
        provider_for: Callable[[str], LLMProvider],
        list_models: Callable[[], tuple[str, ...]],
        model_capabilities: Callable[[str], tuple[str, ...]],
        choose_model: Callable[[str], None],
        current_model: Callable[[], str | None],
        rng: random.Random | None = None,
        seed_examples: SeedExamplePicker | None = None,
    ) -> None:
        """``seed_examples`` elige los ejemplos de la semilla de cada pregunta, como en
        la charla (ADR-240). ``model_capabilities`` dice qué sabe hacer un modelo, o
        lanza ``BlindTestError`` con el motivo si no se sabe (ADR-247)."""
        self._identity_repository = identity_repository
        self._provider_for = provider_for
        self._list_models = list_models
        self._model_capabilities = model_capabilities
        self._choose_model = choose_model
        self._current_model = current_model
        self._rng = rng or random.Random()
        self._seed_examples = seed_examples or SeedExamplePicker()

    def questions(self) -> tuple[str, ...]:
        return BLIND_TEST_QUESTIONS

    def installed_models(self) -> OfferedModels:
        """Los modelos de Ollama que conversan, que son los que ofrece la prueba, y los
        que se quedan fuera, con su motivo.

        Si Ollama no contesta, ``BlindTestError`` con la explicación: la ventana
        no sabe nada de Ollama, solo de la prueba. Si no dice qué sabe hacer un
        modelo, ese se queda fuera y los demás se ofrecen igual (ADR-247).
        """
        chat: list[str] = []
        left_out: list[tuple[str, str]] = []
        for model in self._list_models():
            try:
                capabilities = self._model_capabilities(model)
            except BlindTestError as exc:
                left_out.append((model, str(exc)))
                continue
            if CHAT_CAPABILITY in capabilities:
                chat.append(model)
            else:
                left_out.append((model, NOT_A_CHAT_MODEL))
        return OfferedModels(chat=tuple(chat), left_out=tuple(left_out))

    def chat_model(self) -> str | None:
        """El modelo que conversa ahora, si ya se eligió uno."""
        return self._current_model()

    def prepare(
        self,
        models: Sequence[str],
        *,
        on_progress: Callable[[int, int], None] | None = None,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> BlindTestSheet:
        """Pregunta cada pregunta a cada modelo y baraja las respuestas.

        Cada respuesta se pide con la identidad vigente, la misma que lleva la
        charla, en una petición aparte: nada de esto toca la conversación ni la
        memoria del propietario. ``should_stop`` se mira antes de cada pregunta:
        si el propietario cierra la ventana a medias, no se hacen más peticiones.
        """
        identity = self._identity_repository.get_or_create_current_identity()
        version = identity.current_version
        questions = self.questions()
        # Los ejemplos de cada pregunta se eligen al llegar a ella, después de mirar si
        # se cerró la ventana, y una sola vez: todos los modelos la contestan con las
        # mismas instrucciones, como en la charla (ADR-240, ronda 2 de Codex).
        instructions: dict[str, str] = {}
        total = len(models) * len(questions)
        done = 0
        answers: dict[str, list[str]] = {}
        for model in models:
            provider = self._provider_for(model)
            answers[model] = []
            for number, question in enumerate(questions, start=1):
                if should_stop():
                    msg = "La prueba a ciegas se canceló."
                    raise BlindTestError(msg)
                if question not in instructions:
                    instructions[question] = render_identity(
                        version, self._seed_examples.pick(version.examples, question)
                    )
                answers[model].append(
                    _answer(
                        provider,
                        model,
                        instructions[question],
                        question,
                        f"prueba-a-ciegas-{number}",
                    )
                )
                done += 1
                if on_progress is not None:
                    on_progress(done, total)
        return prepare_blind_test(questions, answers, self._rng)

    def result(self, sheet: BlindTestSheet, choices: Mapping[int, str]) -> BlindTestResult:
        return tally(sheet, choices)

    def choose(self, model: str) -> None:
        """Deja ``model`` como modelo de la charla. Solo cuando el propietario lo confirma."""
        self._choose_model(model)


def _answer(
    provider: LLMProvider, model: str, instructions: str, question: str, operation_id: str
) -> str:
    request = LLMRequest(operation_id=operation_id, instructions=instructions, input_text=question)
    for event in provider.stream_response(request):
        if isinstance(event, LLMCompleted):
            return event.text.strip()
        if isinstance(event, LLMError):
            msg = f"El modelo {model} no contestó: {event.message} {RETRY_ADVICE}"
            raise BlindTestError(msg)
    msg = f"El modelo {model} no terminó su respuesta. {RETRY_ADVICE}"
    raise BlindTestError(msg)
