"""Caso de uso de la prueba a ciegas: elegir el modelo de la charla (pieza C de ADR-233).

Pregunta las 20 preguntas a dos o tres modelos con la misma identidad con la
que conversa Sirius, prepara la hoja barajada y sin nombres, cuenta lo que
elige el propietario y, cuando él confirma, deja el modelo ganador para la
charla. Elegir no pasa nunca sin él: ``choose`` solo lo llama la ventana
cuando el propietario pulsa.
"""

from __future__ import annotations

import itertools
import random
import threading
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
from sirius.domain.robot_seed import example_turns
from sirius.infrastructure.logging import get_logger
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.llm import LLMCancelled, LLMCompleted, LLMError, LLMProvider, LLMRequest

__all__ = ["RETRY_ADVICE", "BlindTestUseCase"]

#: Lo que dice el aviso de un modelo que no contesta: qué hacer (ADR-247).
RETRY_ADVICE = "Vuelve a pulsar Empezar; si se repite, desmarca ese modelo."

#: Cuántas veces se vuelve a pedir una respuesta que falla antes de parar la prueba: un
#: fallo suelto no tira lo que llevaba (incidencia #696).
RETRIES = 1

_logger = get_logger(__name__)


#: Lo que dice la prueba si se cierra la hoja a mitad.
_CANCELLED = "La prueba a ciegas se canceló."


class _Cancelled(BlindTestError):
    """Se cerró la hoja a mitad: no es un fallo del modelo, y no se vuelve a pedir."""


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
        care: Callable[[], str] = lambda: "",
    ) -> None:
        """``seed_examples`` elige los ejemplos de la semilla de cada pregunta, como en
        la charla (ADR-240). ``model_capabilities`` dice qué sabe hacer un modelo, o
        lanza ``BlindTestError`` con el motivo si no se sabe (ADR-247). ``care`` da la
        regla de no insultar si delante hay alguien que la pide, o vacío: las respuestas
        se enseñan como de Sirius (ronda 2 de Codex sobre la PR #703)."""
        self._identity_repository = identity_repository
        self._provider_for = provider_for
        self._list_models = list_models
        self._model_capabilities = model_capabilities
        self._choose_model = choose_model
        self._current_model = current_model
        self._rng = rng or random.Random()
        self._seed_examples = seed_examples or SeedExamplePicker()
        self._care = care
        # Las respuestas ya dadas, por versión de la identidad, modelo, pregunta y regla,
        # mientras Sirius siga abierto: un «Empezar» después de un fallo pide solo las que
        # faltan, y una pedida sin la regla no vale cuando hace falta.
        self._answered: dict[tuple[int, str, str, str], str] = {}
        # La respuesta que está pidiendo cada pasada, para cortarlas al cerrar la hoja. Una
        # por pasada, y no una sola para todas: una pasada que acaba tarde, tras cerrar su
        # hoja, no puede borrar la de la siguiente, que ya no se cortaría (#696).
        self._in_flight: dict[int, tuple[LLMProvider, str]] = {}
        self._runs = itertools.count()
        self._lock = threading.Lock()

    def questions(self) -> tuple[str, ...]:
        return BLIND_TEST_QUESTIONS

    def installed_models(self, should_stop: Callable[[], bool] = lambda: False) -> OfferedModels:
        """Los modelos de Ollama que conversan, que son los que ofrece la prueba, y los
        que se quedan fuera, con su motivo.

        Si Ollama no contesta, ``BlindTestError`` con la explicación: la ventana
        no sabe nada de Ollama, solo de la prueba. Si no dice qué sabe hacer un
        modelo, ese se queda fuera y los demás se ofrecen igual (ADR-247).

        ``should_stop`` se mira antes de pedir la lista y antes de preguntar qué sabe hacer
        cada modelo: si cierran la hoja mientras pregunta, no se pregunta más, y lo que
        devuelve ya no lo usa nadie (ronda 1 de Codex sobre la PR #698).
        """
        chat: list[str] = []
        left_out: list[tuple[str, str]] = []
        if should_stop():
            return OfferedModels(chat=(), left_out=())
        for model in self._list_models():
            if should_stop():
                break
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
        # mismas instrucciones, como en la charla (ADR-240, ronda 2 de Codex). La regla
        # de no insultar, igual: se mira al llegar a la pregunta, y vale para todos.
        instructions: dict[str, str] = {}
        cares: dict[str, str] = {}
        #: Los comienzos de turno de sus ejemplos: dónde deja de escribir cada respuesta
        #: (incidencia #700).
        stops: dict[str, tuple[str, ...]] = {}
        total = len(models) * len(questions)
        done = 0
        answers: dict[str, list[str]] = {}
        run = next(self._runs)
        try:
            for model in models:
                provider = self._provider_for(model)
                answers[model] = []
                for number, question in enumerate(questions, start=1):
                    operation_id = f"prueba-a-ciegas-{number}"
                    # Se apunta antes de mirar si se cerró la hoja: un cierre, o lo ve esta
                    # mirada, o lo corta ``cancel()``; nunca se pierde entre las dos, ni
                    # mientras se eligen los ejemplos, que pide huellas a Ollama (#696).
                    with self._lock:
                        self._in_flight[run] = (provider, operation_id)
                    if should_stop():
                        raise _Cancelled(_CANCELLED)
                    if question not in cares:
                        cares[question] = self._care()
                    care = cares[question]
                    key = (version.id, model, question, care)
                    answer = self._answered.get(key)
                    if answer is None:
                        if question not in instructions:
                            examples = self._seed_examples.pick(version.examples, question)
                            identity_text = render_identity(version, examples)
                            instructions[question] = (
                                f"{identity_text}\n\n{care}" if care else identity_text
                            )
                            stops[question] = example_turns(examples)
                        try:
                            answer = self._ask(
                                provider,
                                model,
                                instructions[question],
                                stops[question],
                                question,
                                operation_id,
                                should_stop,
                            )
                        except _Cancelled:
                            raise
                        except BlindTestError:
                            _logger.error(
                                "La prueba a ciegas falló en %s de %s, con el modelo %s",
                                done + 1,
                                total,
                                model,
                            )
                            raise
                        self._answered[key] = answer
                    answers[model].append(answer)
                    done += 1
                    if on_progress is not None:
                        on_progress(done, total)
        finally:
            with self._lock:
                self._in_flight.pop(run, None)
        return prepare_blind_test(questions, answers, self._rng)

    def cancel(self) -> None:
        """Corta las respuestas que se estén pidiendo: al cerrar la hoja a mitad, no se espera
        a que el modelo acabe (incidencia #696). Todas: la de una pasada anterior que aún no
        ha acabado ya estaba cortada, y la hoja abierta es una sola."""
        with self._lock:
            in_flight = list(self._in_flight.values())
        for provider, operation_id in in_flight:
            provider.cancel(operation_id)

    def _ask(
        self,
        provider: LLMProvider,
        model: str,
        instructions: str,
        stop: tuple[str, ...],
        question: str,
        operation_id: str,
        should_stop: Callable[[], bool],
    ) -> str:
        """Pide una respuesta, y si falla la vuelve a pedir ``RETRIES`` veces antes de parar."""
        for attempt in range(RETRIES + 1):
            try:
                return _answer(provider, model, instructions, stop, question, operation_id)
            except _Cancelled:
                raise
            except BlindTestError:
                if attempt == RETRIES or should_stop():
                    raise
        raise AssertionError  # pragma: no cover: el bucle siempre devuelve o lanza

    def result(self, sheet: BlindTestSheet, choices: Mapping[int, str]) -> BlindTestResult:
        return tally(sheet, choices)

    def choose(self, model: str) -> None:
        """Deja ``model`` como modelo de la charla. Solo cuando el propietario lo confirma."""
        self._choose_model(model)


def _answer(
    provider: LLMProvider,
    model: str,
    instructions: str,
    stop: tuple[str, ...],
    question: str,
    operation_id: str,
) -> str:
    request = LLMRequest(
        operation_id=operation_id, instructions=instructions, input_text=question, stop=stop
    )
    for event in provider.stream_response(request):
        if isinstance(event, LLMCompleted):
            return event.text.strip()
        if isinstance(event, LLMCancelled):
            raise _Cancelled(_CANCELLED)
        if isinstance(event, LLMError):
            msg = f"El modelo {model} no contestó: {event.message} {RETRY_ADVICE}"
            raise BlindTestError(msg)
    msg = f"El modelo {model} no terminó su respuesta. {RETRY_ADVICE}"
    raise BlindTestError(msg)
