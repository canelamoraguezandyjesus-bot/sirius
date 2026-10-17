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
from sirius.domain.robot_seed import TONE_FRAME
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
        #: Las notas que está pidiendo, cada una con su proveedor, para poder cortarlas. Los
        #: veredictos de las preguntas trampa no: esas las pide él a propósito.
        self._scoring: dict[str, LLMProvider] = {}
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Corta las notas que está pidiendo: un turno de voz no las espera (ADR-252). Esas
        respuestas se quedan sin nota y se puntúan la vez siguiente."""
        with self._lock:
            scoring = list(self._scoring.items())
        for operation_id, provider in scoring:
            provider.cancel(operation_id)

    def score(self, reply: str, *, should_stop: Callable[[], bool] | None = None) -> int:
        answer = self._ask(
            SCORE_TASK, f"Respuesta de Sirius:\n{reply}", scoring=True, should_stop=should_stop
        )
        score = parse_score(answer)
        if score is None:
            msg = "El juez no dio una nota del 1 al 5."
            raise JudgeError(msg)
        return score

    def verdict(self, bad_idea: str, reply: str) -> TrickVerdict:
        said = f"Lo que le dijo a Sirius:\n{bad_idea}\n\nLo que contestó Sirius:\n{reply}"
        answer = self._ask(VERDICT_TASK, said)
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
        scoring: bool = False,
        should_stop: Callable[[], bool] | None = None,
    ) -> str:
        """Lo que contesta el modelo local a ``task``. Si es una nota (``scoring``),
        ``cancel`` la corta, y no se pide si ``should_stop`` ya dice que pare."""
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
        )
        if not scoring:
            return _answer(provider, request)
        with self._lock:
            # Se mira y se apunta a la vez: quien le para pone su bandera antes de cortar,
            # así que o la ve aquí, o el corte encuentra apuntada la nota (ADR-252).
            if should_stop is not None and should_stop():
                msg = "Al juez le pidieron parar antes de pedir la nota."
                raise JudgeError(msg)
            self._scoring[request.operation_id] = provider
        try:
            return _answer(provider, request)
        finally:
            with self._lock:
                del self._scoring[request.operation_id]


def _answer(provider: LLMProvider, request: LLMRequest) -> str:
    for event in provider.stream_response(request):
        if isinstance(event, LLMCompleted):
            return event.text
        if isinstance(event, LLMError):
            raise JudgeError(event.message)
    msg = "El juez no terminó."
    raise JudgeError(msg)
