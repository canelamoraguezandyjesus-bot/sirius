"""El juez con el modelo local (pieza E de ADR-233, PA-R02-08 y PA-R02-09)."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable

from sirius.application.send_message import render_identity
from sirius.domain.reply_judge import (
    JUDGE_MAX_OUTPUT_TOKENS,
    SCORE_TASK,
    VERDICT_TASK,
    TrickVerdict,
    parse_score,
)
from sirius.domain.reply_judge import parse_verdict as parse_trick_verdict
from sirius.domain.robot_seed import TONE_FRAME, example_turns
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.llm import LLMCompleted, LLMError, LLMProvider, LLMRequest

__all__ = ["JudgeError", "LLMReplyJudge"]


class JudgeError(RuntimeError):
    """El juez no pudo dar su nota o su veredicto."""


class LLMReplyJudge:
    """El juez, con el modelo local elegido para la charla.

    Solo pregunta a lo que devuelve ``local_provider``. La raíz de composición
    le da siempre un proveedor de Ollama de este ordenador, así que el juez no
    cuesta dinero aunque la charla vaya por OpenAI. Sin modelo local elegido,
    ``local_provider`` devuelve ``None`` y el juez no puntúa.

    Sus instrucciones empiezan por la identidad, como las de la charla, para
    que sepa quién es Sirius; después va lo que se le pide como juez.
    """

    def __init__(
        self,
        identity_repository: IdentityRepository,
        local_provider: Callable[[], LLMProvider | None],
    ) -> None:
        self._identity_repository = identity_repository
        self._local_provider = local_provider
        #: Las notas que está pidiendo, cada una con su proveedor, para poder cortarlas.
        self._scoring: dict[str, LLMProvider] = {}
        #: Los veredictos de las preguntas trampa que está pidiendo. Los corta su hoja al
        #: cerrarse (``cancel_verdicts``), no un turno de voz: esos los pide él (ADR-253).
        self._judging: dict[str, LLMProvider] = {}
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Corta las notas que está pidiendo: un turno de voz no las espera (ADR-252). Esas
        respuestas se quedan sin nota y se puntúan la vez siguiente."""
        _cut(self._lock, self._scoring)

    def cancel_verdicts(self) -> None:
        """Corta los veredictos que está pidiendo: lo pide la hoja de las preguntas trampa al
        cerrarse (ADR-253). El veredicto cortado falla, como cualquier otro."""
        _cut(self._lock, self._judging)

    def score(self, reply: str, *, should_stop: Callable[[], bool] | None = None) -> int:
        answer = self._ask(
            SCORE_TASK,
            f"Respuesta de Sirius:\n{reply}",
            in_flight=self._scoring,
            should_stop=should_stop,
        )
        score = parse_score(answer)
        if score is None:
            msg = "El juez no dio una nota del 1 al 5."
            raise JudgeError(msg)
        return score

    def verdict(
        self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
    ) -> TrickVerdict:
        said = f"Lo que le dijo a Sirius:\n{bad_idea}\n\nLo que contestó Sirius:\n{reply}"
        answer = self._ask(VERDICT_TASK, said, in_flight=self._judging, should_stop=should_stop)
        verdict = parse_trick_verdict(answer)
        if verdict is None:
            msg = "El juez no dijo si le lleva la contraria o le da la razón."
            raise JudgeError(msg)
        return verdict

    def _ask(
        self,
        task: str,
        input_text: str,
        *,
        in_flight: dict[str, LLMProvider],
        should_stop: Callable[[], bool] | None = None,
    ) -> str:
        """Lo que contesta el modelo local a ``task``. Mientras se pide queda apuntado en
        ``in_flight``, de donde lo corta ``cancel`` o ``cancel_verdicts``, y no se pide si
        ``should_stop`` ya dice que pare."""
        provider = self._local_provider()
        if provider is None:
            msg = "No hay modelo local elegido para el juez."
            raise JudgeError(msg)
        identity = self._identity_repository.get_current_identity()
        if identity is None:
            msg = "No hay identidad vigente."
            raise JudgeError(msg)
        # El juez no conversa: juzga cómo suena Sirius, y para eso ve los ejemplos
        # enteros, no los tres de cada turno (ADR-240).
        version = identity.current_version
        request = LLMRequest(
            operation_id=f"juez-{uuid.uuid4()}",
            instructions=(
                f"{render_identity(version, version.examples, frame=TONE_FRAME)}\n\n{task}"
            ),
            input_text=input_text,
            # Una nota o una palabra: sin pensar antes, que se comería el tope (ADR-252).
            max_output_tokens=JUDGE_MAX_OUTPUT_TOKENS,
            may_think=False,
            # Ve todos los ejemplos, escritos por turnos: si siguiera el diálogo, la nota o
            # el veredicto se perderían detrás (ronda 1 de Codex sobre la PR #701).
            stop=example_turns(version.examples),
        )
        with self._lock:
            # Se mira y se apunta a la vez: quien le para pone su bandera antes de cortar,
            # así que o la ve aquí, o el corte encuentra apuntada la petición (ADR-252).
            if should_stop is not None and should_stop():
                msg = "Al juez le pidieron parar antes de preguntar."
                raise JudgeError(msg)
            in_flight[request.operation_id] = provider
        try:
            return _answer(provider, request)
        finally:
            with self._lock:
                del in_flight[request.operation_id]


def _cut(lock: threading.Lock, in_flight: dict[str, LLMProvider]) -> None:
    """Corta, desde otro hilo, las peticiones apuntadas en ``in_flight``."""
    with lock:
        pending = list(in_flight.items())
    for operation_id, provider in pending:
        provider.cancel(operation_id)


def _answer(provider: LLMProvider, request: LLMRequest) -> str:
    for event in provider.stream_response(request):
        if isinstance(event, LLMCompleted):
            return event.text
        if isinstance(event, LLMError):
            raise JudgeError(event.message)
    msg = "El juez no terminó."
    raise JudgeError(msg)
